#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「可悬停」的提交日历，并写回 README.md 的自动更新区块。

原理：snake 是 <img> 里的 SVG，图片不能悬停、也不能带 tooltip；
所以这里改用 HTML <table> 的单元格 title 属性 —— 鼠标悬停在格子上时，
浏览器会显示「2026-11-20（周五）· 5 次提交」这样的原生提示。

数据来源（无需 token）：
    https://github.com/users/<username>/contributions
该页面是 GitHub 个人主页贡献图的真实数据，每个格子自带 data-date / data-level，
并配有 <tool-tip> 文本（"5 contributions on November 20th."），据此可还原每天次数。

用法：
    python scripts/contrib_calendar.py                # 默认 13 周，用户 Great-Hyw
    python scripts/contrib_calendar.py --weeks 18     # 更长时间范围
    python scripts/contrib_calendar.py --dry-run      # 只打印，不改 README

仅依赖 Python 标准库。
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
import urllib.request

USER = "Great-Hyw"
README = "README.md"
START_MARK = "<!--START_SECTION:contribs-->"
END_MARK = "<!--END_SECTION:contribs-->"

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAY_SHORT = ["一", "二", "三", "四", "五", "六", "日"]
# data-level 0..4 → 用字符密度表示深浅（颜色不可控，只能用字符表现强度）
LEVEL_CHARS = ["·", "░", "▒", "▓", "█"]

TD_RE = re.compile(r"<td\b([^>]*)>")
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
TIP_RE = re.compile(r"<tool-tip\b([^>]*)>(.*?)</tool-tip>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; contrib-calendar/1.0)",
            "Accept": "text/html",
            # 固定英文，保证 tooltip 文案是 "5 contributions on ..." 方便正则解析
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_with_retry(url: str, attempts: int = 3, timeout: int = 30) -> str:
    """网络抖动时重试几次（github.com 偶尔会断连接）。"""
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fetch(url, timeout)
        except Exception as exc:
            last_exc = exc
            print(f"[warn] 第 {i + 1} 次拉取失败：{exc}", file=sys.stderr)
            if i + 1 < attempts:
                time.sleep(2 * (i + 1))
    assert last_exc is not None
    raise last_exc


def parse_counts(page: str) -> dict[str, int]:
    """id(contribution-day-component-w-d) -> 当天提交次数"""
    counts: dict[str, int] = {}
    pending: list[tuple[str, str]] = []  # (tooltip for, text)
    for m in TIP_RE.finditer(page):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        text = TAG_RE.sub("", m.group(2)).strip()
        for_id = attrs.get("for", "")
        if for_id:
            pending.append((for_id, text))
    for for_id, text in pending:
        # 英文页面："5 contributions on November 20th." / "No contributions on ..."
        # 中文页面（万一被本地化）："11月20日有 5 次贡献" / "没有贡献"
        mnum = re.search(r"(\d+)\s*(?:contributions?\b|次提交|次贡献)", text)
        if mnum:
            counts[for_id] = int(mnum.group(1))
        elif "No contributions" in text or "没有贡献" in text or "无贡献" in text:
            counts[for_id] = 0
    return counts


def parse_days(page: str) -> dict[str, tuple[str, int, int]]:
    """date -> (cell_id, level, count)"""
    counts = parse_counts(page)
    days: dict[str, tuple[str, int, int]] = {}
    for m in TD_RE.finditer(page):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        date = attrs.get("data-date")
        if not date:
            continue
        cid = attrs.get("id", "")
        try:
            level = int(attrs.get("data-level", "0") or 0)
        except ValueError:
            level = 0
        count = counts.get(cid, -1)
        days[date] = (cid, level, count)
    return days


def build_table(days: dict[str, tuple[str, int, int]], weeks: int) -> str:
    if not days:
        return "<sub>（暂无数据）</sub>"
    dates = sorted(dt.date.fromisoformat(d) for d in days)
    last_day = dates[-1]
    # 以周一为一周开始
    last_monday = last_day - dt.timedelta(days=last_day.weekday())
    first_monday = last_monday - dt.timedelta(days=7 * (weeks - 1))
    week_starts = [first_monday + dt.timedelta(days=7 * i) for i in range(weeks)]

    today = dt.date.today()
    rows: list[str] = []

    # 月份行
    month_cells = ['<td align="center"></td>']
    shown_months: set[tuple[int, int]] = set()
    for ws in week_starts:
        key = (ws.year, ws.month)
        # 只有当这一周包含该月 1 号之后的前 7 天时标注月份
        if ws.day <= 7 and key not in shown_months:
            shown_months.add(key)
            month_cells.append(f'<td align="center"><sub>{ws.month}月</sub></td>')
        else:
            month_cells.append('<td align="center"></td>')
    rows.append("<tr>" + "".join(month_cells) + "</tr>")

    total = 0
    for wd in range(7):
        cells = [f'<td align="center"><sub>{WEEKDAY_SHORT[wd]}</sub></td>']
        for ws in week_starts:
            day = ws + dt.timedelta(days=wd)
            if day > today:
                cells.append('<td align="center"></td>')
                continue
            info = days.get(day.isoformat())
            if info is None:
                cells.append('<td align="center"></td>')
                continue
            _cid, level, count = info
            level = max(0, min(4, level))
            if count is None or count < 0:
                title = f"{day.isoformat()}（{WEEKDAY_CN[wd]}）"
            else:
                total += count
                title = f"{day.isoformat()}（{WEEKDAY_CN[wd]}）· {count} 次提交"
            cells.append(
                f'<td align="center" title="{title}">{LEVEL_CHARS[level]}</td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    span_start = week_starts[0].isoformat()
    span_end = min(today, last_day).isoformat()
    legend = (
        f'<sub>近 {weeks} 周（{span_start} → {span_end}）共 {total} 次提交　·　'
        "字符越密 = 当天提交越多：· ░ ▒ ▓ █　·　"
        "把鼠标停在格子上即可看当天日期与次数</sub>"
    )
    table = '<table align="center">\n' + "\n".join(rows) + "\n</table>"
    return table + "\n\n" + legend


def replace_block(text: str, body: str) -> str:
    if START_MARK not in text or END_MARK not in text:
        raise SystemExit(
            "README 中找不到贡献日历标记，请先手动添加：\n"
            f"{START_MARK}\n{END_MARK}"
        )
    start = text.index(START_MARK) + len(START_MARK)
    end = text.index(END_MARK)
    return text[:start] + "\n\n" + body + "\n\n" + text[end:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=USER)
    ap.add_argument("--readme", default=README)
    ap.add_argument("--weeks", type=int, default=13)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    url = f"https://github.com/users/{args.user}/contributions"
    try:
        page = fetch_with_retry(url)
    except Exception as exc:  # 网络异常时保留旧内容，避免 Action 变红
        print(f"[warn] 拉取贡献数据失败：{exc}", file=sys.stderr)
        return 0

    days = parse_days(page)
    print(f"[info] 解析到 {len(days)} 天数据，来源 {url}")
    if len(days) < 30:
        # 页面结构可能变了：宁可保留旧内容，也不要覆盖成「暂无数据」
        print("[warn] 解析出的天数异常，保留 README 原内容", file=sys.stderr)
        return 0
    body = build_table(days, args.weeks)
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