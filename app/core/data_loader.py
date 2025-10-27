from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class WordEntry:
    word: str
    phonetic: str
    meaning: str
    example: str


@dataclass(frozen=True)
class Essay:
    title: str
    level: str
    content: str


class DataLoaderError(RuntimeError):
    """Raised when a data set cannot be loaded."""


def _load_json_file(path: Path) -> list:
    if not path.exists():
        raise DataLoaderError(f"数据文件缺失: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise DataLoaderError(f"无法解析数据文件 {path}: {exc}") from exc


def load_words(level: str) -> List[WordEntry]:
    level = level.lower()
    filename = {
        "cet4": "cet4_words.json",
        "cet6": "cet6_words.json",
    }.get(level)

    if filename is None:
        raise ValueError("level must be 'cet4' or 'cet6'")

    raw_items = _load_json_file(DATA_DIR / filename)
    result: List[WordEntry] = []
    for item in raw_items:
        try:
            result.append(
                WordEntry(
                    word=item["word"].strip(),
                    phonetic=item.get("phonetic", ""),
                    meaning=item.get("meaning", ""),
                    example=item.get("example", ""),
                )
            )
        except KeyError as exc:
            raise DataLoaderError(f"词汇数据缺失字段: {exc}") from exc
    if not result:
        raise DataLoaderError(f"{level.upper()} 词汇数据为空")
    return result


def load_essays(level: Optional[str] = None) -> List[Essay]:
    raw_items = _load_json_file(DATA_DIR / "essays.json")
    essays: List[Essay] = []
    for item in raw_items:
        essays.append(
            Essay(
                title=item.get("title", ""),
                level=item.get("level", ""),
                content=item.get("content", ""),
            )
        )
    if level:
        level = level.lower()
        essays = [essay for essay in essays if essay.level.lower() == level]
    if not essays:
        raise DataLoaderError("作文数据为空")
    return essays


def sample_word(level: str) -> WordEntry:
    words = load_words(level)
    return random.choice(words)


def sample_essay(level: Optional[str] = None) -> Essay:
    essays = load_essays(level)
    return random.choice(essays)
