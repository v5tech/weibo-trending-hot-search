# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目用途

每小时抓取一次微博实时热搜榜（`https://s.weibo.com/top/summary?cate=realtimehot`），按天合并去重后写回三处：`raw/<YYYYMM>/<YYYY-MM-DD>.json` 当日快照、`archives/<YYYYMM>/<YYYY-MM-DD>.{md,csv}` 归档、`README.md` 的 `<!-- BEGIN --> ... <!-- END -->` 块。由 GitHub Actions 每小时跑 `python3 main.py` + `git push`。

## 运行

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python3 main.py
```

## 关键不变量与陷阱

- `merge(date, new)` 把当日同 key 取 `max(existing, new)` 热度后降序写回。当日 JSON 因此是"截至此刻见过的所有热搜以及它们曾达到过的最高热度"，**不是瞬时榜单**。
- `fetch_weibo` 内有硬编码微博 `Cookie`，CI 用它跑了几年。不要顺手"清理"——会让 GitHub Actions 立刻全线失败。
