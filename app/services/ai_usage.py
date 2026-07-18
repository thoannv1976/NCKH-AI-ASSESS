"""Ghi nhận và thống kê mức sử dụng Claude API: số lần gọi, token, ước tính chi phí.

Mỗi lần gọi API ghi một bản ghi vào collection 'ai_usage' (cộng dồn khi xem thống kê) —
tránh tranh chấp ghi đè khi chấm song song nhiều luồng.
"""
from __future__ import annotations

from app.config import now_vn

# Giá tham khảo (USD / 1 triệu token) — (input, output). Nguồn: bảng giá model Claude.
PRICING = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-opus-4-5": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
DEFAULT_PRICING = (5.0, 25.0)
USD_TO_VND = 25_500  # tỷ giá tạm tính để quy đổi tham khảo


def _num(usage, attr: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(attr) or 0)
    return int(getattr(usage, attr, 0) or 0)


def cost_usd(model: str, inp: int, out: int, cache_read: int = 0, cache_creation: int = 0) -> float:
    pi, po = PRICING.get(model, DEFAULT_PRICING)
    # input_tokens là phần KHÔNG cache; cache_read ~0.1x, cache_creation ~1.25x giá input
    return (inp * pi + cache_read * pi * 0.1 + cache_creation * pi * 1.25 + out * po) / 1_000_000


def record_usage(store, model: str, usage, kind: str = "grade") -> None:
    store.add("ai_usage", {
        "model": model,
        "input_tokens": _num(usage, "input_tokens"),
        "output_tokens": _num(usage, "output_tokens"),
        "cache_read": _num(usage, "cache_read_input_tokens"),
        "cache_creation": _num(usage, "cache_creation_input_tokens"),
        "kind": kind,
        "ts": now_vn().isoformat(),
    })


def _blank() -> dict:
    return {"calls": 0, "input": 0, "output": 0, "cache_read": 0, "cache_creation": 0, "cost_usd": 0.0}


def get_stats(store) -> dict:
    agg = _blank()
    agg["by_model"] = {}
    for r in store.all("ai_usage"):
        m = r.get("model", "?")
        inp, out = r.get("input_tokens", 0), r.get("output_tokens", 0)
        cr, cc = r.get("cache_read", 0), r.get("cache_creation", 0)
        c = cost_usd(m, inp, out, cr, cc)
        for tgt in (agg, agg["by_model"].setdefault(m, _blank())):
            tgt["calls"] += 1
            tgt["input"] += inp
            tgt["output"] += out
            tgt["cache_read"] += cr
            tgt["cache_creation"] += cc
            tgt["cost_usd"] += c
    agg["total_tokens"] = agg["input"] + agg["output"] + agg["cache_read"] + agg["cache_creation"]
    agg["cost_vnd"] = agg["cost_usd"] * USD_TO_VND
    return agg


def reset_stats(store) -> int:
    rows = store.all("ai_usage")
    for r in rows:
        store.delete("ai_usage", r["id"])
    return len(rows)
