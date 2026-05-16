# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目用途

每小时抓取一次微博实时热搜榜（`https://s.weibo.com/top/summary?cate=realtimehot`），按天合并去重后写回三处：
- `raw/<YYYYMM>/<YYYY-MM-DD>.json` —— 当日全量快照（合并源/真相，热度按降序）
- `archives/<YYYYMM>/<YYYY-MM-DD>.{md,csv}` —— 当日归档（人读用）
- `README.md` 的 `<!-- BEGIN --> ... <!-- END -->` 块 —— 首页"今日热门搜索"列表

抓取与提交完全由 GitHub Actions 驱动（`.github/workflows/ci.yml` 每小时 `python3 main.py` + `git push`），本地一般不需要运行。

## 常用命令

```bash
# 首次准备环境（仓库内 .venv，禁止污染系统环境）
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 手动跑一次完整抓取流水线（会真的改写 raw/、archives/、README.md）
python3 main.py
```

仓库没有测试、lint、构建脚本——`requirements.txt` 只声明 `requests` 与 `lxml`。

## 架构要点

整条流水线是单文件 `main.py` 编排的 5 步线性流程，状态完全落盘，没有数据库或缓存：

1. `fetch_weibo(url)` —— `main.py:26` 用硬编码 Cookie + UA 抓 HTML。
2. `parse_weibo(content)` —— `main.py:41` 通过 XPath 解析 `#pl_top_realtimehot` 表格，跳过置顶（`href` 含 `javascript:void(0);`），返回 `dict[title, HotEntry]`。
3. `daily_hot_news.merge(date, new_entries)` —— `daily_hot_news.py:24` 是唯一有状态的环节：
   - 读 `raw/<YYYYMM>/<date>.json`（不存在视作空）
   - **关键不变量**：同 key 的 `hot` 取 `max(existing, new)`；同 key 出现按"取最大热度"覆盖，新增条目直接 append；最后按 `hot` 降序排序后写回。
   - 也就是说，当日 JSON 是"该日截至此刻见过的所有热搜以及它们曾达到过的最高热度"，**不是某个时刻的瞬时榜单**。
4. `save_csv(date, news)` / `update_readme(news)` / `save_archive(date, news)` —— `main.py:57/67/76` 各自读用第 3 步排序后的 dict 渲染输出。`update_readme` 用正则替换 README 中的 BEGIN/END 标记块。`_render_md_list` 是三处共享的渲染函数（`main.py:62`）。两个 archive render 的写出路径走 `_archive_path(date, ext)` 集中（`main.py:15`），与 `daily_hot_news._path(date)` 平行——前者管 `archives/` 布局，后者管 `raw/` 布局。

**渲染接口的诚实性**：`save_csv` / `save_archive` 显式收 `date`，因为输出路径和 archive md 标题都依赖它；`update_readme` 不收 `date`，因为 README 路径固定、"最后更新时间"用墙钟 `datetime.now()`。"快照归属哪一天"这一个旋钮只在 `__main__` 决定一次，再线程下去，没有 import-time 全局。

数据类型 `HotEntry` 是 `TypedDict{url: str, hot: int}`，定义在 `daily_hot_news.py:6`，被 `main.py` 反向导入用作签名。

时间统一用"UTC + 8h"算北京时间（`main.py:83-84` 在 `__main__` 内一次性算出 `ymd` 后线程下去），CI 也显式设了 `Asia/Shanghai` 时区。

## 工作时需要注意的事

- `main.py:29` 有一个硬编码的微博 `Cookie`，CI 直接使用它跑了几年；改抓取逻辑时不要顺手"清理"它，会让 GitHub Actions 立刻全线失败。
- 修改 `parse_weibo` 的字段或 `merge` 的合并规则时，要意识到下游 README/CSV/MD 三处渲染都依赖 `dict` 的**插入顺序 = 热度降序**这一约定（Python 3.7+ dict 保序）。`merge` 返回的就是已排序 dict，调用方不再排序。
- `raw/` 是 merge 的输入也是输出，是数据真相来源；`archives/` 与 README 的列表都是从 `raw/` 推导出来的展示层。如果某天数据出错，修 `raw/<YYYYMM>/<date>.json` 然后重跑 `main.py` 即可重建展示层。
- `duckdb.md` / `duckdb.sql` 是历史数据分析的草稿笔记，跟主流水线无关。
