#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取天气并写回 README.md 的「今日天气」区块。

数据源：Open-Meteo（https://open-meteo.com）——免费、无需注册、无需 API Key、HTTPS。
默认城市：南昌（改城市只要改下面 CITY / LAT / LON，或在 Action 里传 --city --lat --lon）。

用法：
    python scripts/weather.py                 # 写 README.md
    python scripts/weather.py --dry-run       # 只打印，不改文件
    python scripts/weather.py --city 上海 --lat 31.2304 --lon 121.4737

仅依赖 Python 标准库。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

# ── 改这里就能换城市（经纬度去 https://open-meteo.com/en/docs 的 Geocoding 查）──
CITY = "南昌"
LAT = 28.682
LON = 115.858

README = "README.md"
START_MARK = "<!--START_SECTION:weather-->"
END_MARK = "<!--END_SECTION:weather-->"

API = "https://api.open-meteo.com/v1/forecast"

# WMO weather code → (白天 emoji, 夜间 emoji, 中文描述)
WMO = {
    0: ("☀️", "🌙", "晴"),
    1: ("🌤️", "🌙", "晴间多云"),
    2: ("⛅", "☁️", "多云"),
    3: ("☁️", "☁️", "阴"),
    45: ("🌫️", "🌫️", "有雾"),
    48: ("🌫️", "🌫️", "雾凇"),
    51: ("🌦️", "🌧️", "毛毛雨"),
    53: ("🌦️", "🌧️", "毛毛雨"),
    55: ("🌧️", "🌧️", "毛毛雨"),
    56: ("🌧️", "🌧️", "冻毛毛雨"),
    57: ("🌧️", "🌧️", "冻毛毛雨"),
    61: ("🌦️", "🌧️", "小雨"),
    63: ("🌧️", "🌧️", "中雨"),
    65: ("🌧️", "🌧️", "大雨"),
    66: ("🌧️", "🌧️", "冻雨"),
    67: ("🌧️", "🌧️", "冻雨"),
    71: ("🌨️", "🌨️", "小雪"),
    73: ("🌨️", "🌨️", "中雪"),
    75: ("❄️", "❄️", "大雪"),
    77: ("🌨️", "🌨️", "雪粒"),
    80: ("🌦️", "🌧️", "阵雨"),
    81: ("🌧️", "🌧️", "强阵雨"),
    82: ("⛈️", "⛈️", "暴阵雨"),
    85: ("🌨️", "🌨️", "阵雪"),
    86: ("❄️", "❄️", "强阵雪"),
    95: ("⛈️", "⛈️", "雷阵雨"),
    96: ("⛈️", "⛈️", "雷阵雨伴冰雹"),
    99: ("⛈️", "⛈️", "雷阵雨伴冰雹"),
}

# 蒲福风级（km/h 上限）
WIND_LEVELS = [1, 6, 12, 20, 29, 39, 50, 62, 75, 89, 103, 118]


def fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; weather-readme/1.0)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def build_url(lat: float, lon: float) -> str:
    query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "weather_code",
                    "wind_speed_10m",
                    "is_day",
                ]
            ),
            "daily": ",".join(
                ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_max"]
            ),
            "timezone": "Asia/Shanghai",
            "forecast_days": 1,
        }
    )
    return API + "?" + query


def wind_level(kmh: float) -> int:
    for level, limit in enumerate(WIND_LEVELS):
        if kmh <= limit:
            return level
    return len(WIND_LEVELS)


def describe(code: int, is_day: int) -> tuple[str, str]:
    day_emoji, night_emoji, text = WMO.get(code, ("🌡️", "🌡️", "未知天气"))
    return (day_emoji if is_day else night_emoji), text


def render(payload: dict, city: str) -> str:
    cur = payload.get("current") or {}
    daily = payload.get("daily") or {}

    code = int(cur.get("weather_code", -1))
    is_day = int(cur.get("is_day", 1))
    emoji, desc = describe(code, is_day)

    temp = float(cur.get("temperature_2m", 0.0))
    feels = float(cur.get("apparent_temperature", temp))
    humidity = int(round(float(cur.get("relative_humidity_2m", 0))))
    wind = float(cur.get("wind_speed_10m", 0.0))
    level = wind_level(wind)

    tmax = daily.get("temperature_2m_max") or [temp]
    tmin = daily.get("temperature_2m_min") or [temp]
    pop = (daily.get("precipitation_probability_max") or [None])[0]
    updated = (cur.get("time") or "").replace("T", " ")

    line1 = f"{emoji} {city} · {desc} {temp:.1f}℃"
    meta = [
        f"体感 {feels:.0f}℃",
        f"湿度 {humidity}%",
        f"风 {level} 级（{wind:.0f} km/h）",
        f"今日 {float(tmin[0]):.0f}~{float(tmax[0]):.0f}℃",
    ]
    if pop is not None:
        meta.append(f"降水概率 {int(pop)}%")
    if updated:
        meta.append(f"更新于 {updated}")

    return (
        '<div align="center">\n'
        f"  <b>{line1}</b><br />\n"
        "  <sub>" + "　·　".join(meta) + "</sub>\n"
        "</div>"
    )


def replace_block(text: str, body: str) -> str:
    if START_MARK not in text or END_MARK not in text:
        raise SystemExit(
            "README 里找不到天气标记，请先手动加一行：\n"
            f"{START_MARK}{END_MARK}"
        )
    start = text.index(START_MARK) + len(START_MARK)
    end = text.index(END_MARK)
    return text[:start] + "\n\n" + body + "\n\n" + text[end:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--readme", default=README)
    ap.add_argument("--city", default=CITY)
    ap.add_argument("--lat", type=float, default=LAT)
    ap.add_argument("--lon", type=float, default=LON)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    url = build_url(args.lat, args.lon)
    payload = None
    last_exc: Exception | None = None
    for i in range(3):
        try:
            payload = fetch_json(url)
            break
        except Exception as exc:  # 网络抖动时重试，失败则保留 README 原文
            last_exc = exc
            print(f"[warn] 第 {i + 1} 次拉取失败：{exc}", file=sys.stderr)
            if i < 2:
                time.sleep(2 * (i + 1))
    if payload is None:
        print(f"[warn] 天气接口不可用，保留 README 原内容：{last_exc}", file=sys.stderr)
        return 0

    body = render(payload, args.city)
    print(body)

    if args.dry_run:
        return 0

    with open(args.readme, encoding="utf-8") as fh:
        old = fh.read()
    new = replace_block(old, body)
    if new == old:
        print("[info] README 无变化")
    else:
        with open(args.readme, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
        print(f"[info] 已更新 {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())