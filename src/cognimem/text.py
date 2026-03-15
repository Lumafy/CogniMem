from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "is",
    "are",
    "with",
    "用户",
    "我们",
    "这个",
    "需要",
    "一个",
    "进行",
}


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in TOKEN_RE.findall(text):
        token = raw_token.lower()
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            if len(token) <= 2:
                parts = [token]
            else:
                parts = [token[i : i + 2] for i in range(len(token) - 1)]
            tokens.extend(parts)
        else:
            tokens.append(token)
    return [token for token in tokens if token not in STOPWORDS]


def summarize_text(text: str, max_tokens: int = 36) -> str:
    stripped = " ".join(text.split())
    if len(stripped) <= 120:
        return stripped
    pieces = re.split(r"[。！？!?；;\n]+", stripped)
    summary = next((piece.strip() for piece in pieces if piece.strip()), stripped)
    if len(summary) <= 120:
        return summary
    return summary[:117] + "..."


def keyword_scores(text: str, limit: int = 8) -> list[str]:
    counts = Counter(tokenize(text))
    ranked = sorted(
        counts.items(),
        key=lambda item: (
            0 if re.fullmatch(r"[A-Za-z0-9_]+", item[0]) else 1,
            -item[1],
            item[0],
        ),
    )
    return [token for token, _ in ranked[:limit]]


def tf_vector(text: str) -> dict[str, float]:
    counts = Counter(tokenize(text))
    if not counts:
        return {}
    norm = math.sqrt(sum(count * count for count in counts.values()))
    return {token: count / norm for token, count in counts.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(token, 0.0) for token, weight in left.items())
