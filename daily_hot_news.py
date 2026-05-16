import json
import os
from typing import TypedDict


class HotEntry(TypedDict):
    url: str
    hot: int


def _path(date: str) -> str:
    ym = date[:7].replace('-', '')
    return f"./raw/{ym}/{date}.json"


def load(date: str) -> dict[str, HotEntry]:
    path = _path(date)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


def merge(date: str, new_entries: dict[str, HotEntry]) -> dict[str, HotEntry]:
    existing = load(date)
    for k, v in new_entries.items():
        if k in existing:
            existing[k]['hot'] = max(int(existing[k]['hot']), int(v['hot']))
        else:
            existing[k] = v
    sorted_snapshot = {
        k: v for k, v in sorted(existing.items(), key=lambda item: int(item[1]['hot']), reverse=True)
    }
    path = _path(date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sorted_snapshot, f, ensure_ascii=False, indent=2)
    return sorted_snapshot
