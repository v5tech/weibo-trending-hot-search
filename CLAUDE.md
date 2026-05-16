# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目用途

每小时抓取一次微博实时热搜榜（`https://s.weibo.com/top/summary?cate=realtimehot`），按天合并去重后写回三处：
- `raw/<YYYYMM>/<YYYY-MM-DD>.json` —— 当日全量快照（合并源/真相，热度按降序）
- `archives/<YYYYMM>/<YYYY-MM-DD>.{md,csv}` —— 当日归档
- `README.md` 的 `<!-- BEGIN --> ... <!-- END -->` 块 —— 首页"今日热门搜索"

抓取与提交由 GitHub Actions 驱动（`.github/workflows/ci.yml` 每小时 `python3 main.py` + `git push`）。

## 常用命令

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python3 main.py    # 跑一次完整流水线（真改 raw/、archives/、README.md）
```

无测试、lint、构建脚本。依赖只有 `requests` 和 `lxml`。

## 架构要点

单文件 `main.py`，线性 5 步流水线，状态完全落盘：

1. `fetch_weibo` —— 用硬编码 Cookie + UA 抓 HTML。
2. `parse_weibo` —— XPath 解析 `#pl_top_realtimehot`，跳过置顶（`href` 含 `javascript:void(0);`），返回 `dict[title, HotEntry]`。
3. `merge(date, new)` —— 唯一有状态环节：
   - 读 `raw/<YYYYMM>/<date>.json`（不存在视作空）
   - **关键不变量**：同 key 取 `max(existing, new)` 热度；新 key 直接 append；最后按热度降序排序后写回。
   - 当日 JSON 因此是"该日截至此刻见过的所有热搜以及它们曾达到过的最高热度"，**不是某时刻的瞬时榜单**。
4. `save_csv(date, news)` / `update_readme(news)` / `save_archive(date, news)` —— 渲染三处输出。`update_readme` 用正则替换 README 标记块。`_render_md_list` 是共享格式化函数。

`HotEntry` 是 `TypedDict{url: str, hot: int}`。路径布局走 `_raw_path` / `_archive_path` 两个返 `pathlib.Path` 的 helper。时间用"UTC+8h"算北京时间，在 `__main__` 一次性算出 `ymd` 线程下去——无 import-time 全局。

## 注意事项

- `fetch_weibo` 内有硬编码微博 `Cookie`，CI 用它跑了几年；改抓取逻辑时不要顺手"清理"，会让 GitHub Actions 立刻全线失败。
- 下游所有渲染依赖 `dict` 插入顺序 = 热度降序（Python 3.7+ dict 保序）。`merge` 已返回排序好的 dict，调用方不再排序。
- `raw/` 是数据真相来源；`archives/` 与 README 是从 `raw/` 推导的展示层。数据出错时修 `raw/<YYYYMM>/<date>.json` 重跑即可。
- `duckdb.md` / `duckdb.sql` 是历史数据分析的草稿笔记，跟主流水线无关。
