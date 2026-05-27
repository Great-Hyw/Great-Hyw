<!-- 顶部标题 -->
<h1 align="center">Hi 👋, I'm Great-Hyw</h1>
<h3 align="center">🚀 热爱编程 | 🌤️ 关注天气 | 🐍 GitHub 贡献达人</h3>

---

<!-- 动态打字效果 -->
<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&pause=1000&center=true&vCenter=true&width=435&lines=Welcome+to+my+GitHub!;Full+Stack+Developer;Open+Source+Enthusiast;Keep+Learning+Everyday" alt="Typing SVG" />
</p>

---

## 🌤️ 实时天气组件

<p align="center">
  <a href="https://github.com/saadeghi/daisyui">
    <img src="https://wttr.in/SaltLakeCity.png?m" alt="weather" />
  </a>
</p>

> 你可以把 `SaltLakeCity` 改成自己的城市，例如：`Beijing`、`Shanghai`、`Tokyo`。

---

## 📊 GitHub 数据统计

<p align="center">
  <img height="180em" src="https://github-readme-stats.vercel.app/api?username=Great-Hyw&show_icons=true&theme=tokyonight" />
  <img height="180em" src="https://github-readme-stats.vercel.app/api/top-langs/?username=Great-Hyw&layout=compact&theme=tokyonight" />
</p>

---

## 🔥 连续提交记录

<p align="center">
  <img src="https://streak-stats.demolab.com?user=Great-Hyw&theme=tokyonight" />
</p>

---

## 🐍 贪吃蛇贡献图

<p align="center">
  <img src="https://raw.githubusercontent.com/Great-Hyw/Great-Hyw/output/github-contribution-grid-snake.svg" alt="snake" />
</p>

### ⚙️ 配置贪吃蛇动画

在仓库 `.github/workflows/` 目录下创建 `snake.yml`

```yaml
name: generate animation

on:
  schedule:
    - cron: "0 */12 * * *"
  workflow_dispatch:

jobs:
  generate:
    permissions:
      contents: write
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: generate github-contribution-grid-snake.svg
        uses: Platane/snk/svg-only@v3
        with:
          github_user_name: Great-Hyw
          outputs: |
            dist/github-contribution-grid-snake.svg
            dist/github-contribution-grid-snake-dark.svg?palette=github-dark

      - name: push github-contribution-grid-snake.svg to the output branch
        uses: crazy-max/ghaction-github-pages@v3.1.0
        with:
          target_branch: output
          build_dir: dist
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
