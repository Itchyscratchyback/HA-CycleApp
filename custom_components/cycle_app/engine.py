"""Pure cycle calculations (no Home Assistant dependencies)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .const import (
    DEFAULT_CYCLE_LENGTH,
    MAX_CYCLE_LENGTH,
    MAX_CYCLE_SAMPLES,
    MIN_CYCLE_LENGTH,
)

PHASE_COLORS = {
    "Period": "#ff6fa5",
    "Follicular": "#63a4ff",
    "Fertile": "#ffd54f",
    "Ovulation": "#ff4444",
}
DEFAULT_PHASE_COLOR = "#6ecb63"

_SCORES = {
    0: 10, 1: 9, 2: 9, 3: 9, 4: 8, 5: 8, 6: 7, 7: 7,
    -1: 10, -2: 9, -3: 8, -4: 6, -5: 4,
}


def _round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def _median(vals: list[int]) -> float:
    ordered = sorted(vals)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2


@dataclass(frozen=True)
class CycleStats:
    """All values derived from period history."""

    period_dates_count: int
    cycle_count: int
    last_period_start: date | None
    previous_period_start: date | None
    cycle_lengths: list[int]
    last_cycle_length: int
    shortest_cycle_length: int
    longest_cycle_length: int
    median: float
    sample_size: int
    outlier_count: int
    mean_robust: float
    stddev: float
    quality: str
    confidence: str
    preferred_length: int
    cycle_day: int
    next_period: date | None
    days_to_next_period: int
    ovulation: date | None
    days_to_ovulation: int | None
    fertility_score: int
    fertility_status: str
    next_ovulation: date | None
    earliest_period: date | None
    latest_period: date | None
    following_period: date | None
    days_to_next_ovulation: int
    pre_period: date | None
    days_to_pre_period: int | None
    phase: str
    phase_color: str
    earliest_ovulation: date | None
    latest_ovulation: date | None
    window_start: date | None
    window_end: date | None
    peak_start: date | None
    peak_end: date | None
    window_status: str | None


def compute(periods: list[date], luteal: int, today: date) -> CycleStats:
    """Compute every derived cycle value."""
    dates = sorted(set(periods))
    n_dates = len(dates)
    last = dates[-1] if n_dates else None
    previous = dates[-2] if n_dates > 1 else None

    lengths: list[int] = []
    for earlier, later in zip(dates, dates[1:]):
        diff = (later - earlier).days
        if MIN_CYCLE_LENGTH <= diff <= MAX_CYCLE_LENGTH:
            lengths.append(diff)
    lengths = lengths[-MAX_CYCLE_SAMPLES:]

    sample = len(lengths)
    if sample:
        median = _median(lengths)
        if sample % 2 == 0:
            median = round(median, 1)
        outliers = sum(1 for v in lengths if abs(v - median) > 10)
        kept = [v for v in lengths if abs(v - median) <= 10]
        mean_robust = round(sum(kept) / len(kept), 1) if kept else median
        mean = sum(lengths) / sample
        stddev = (
            round((sum((v - mean) ** 2 for v in lengths) / sample) ** 0.5, 1)
            if sample > 1
            else 0.0
        )
    else:
        median = DEFAULT_CYCLE_LENGTH
        outliers = 0
        mean_robust = DEFAULT_CYCLE_LENGTH
        stddev = 0.0

    if sample >= 12 and outliers == 0:
        quality = "Excellent"
    elif sample >= 8 and outliers <= 1:
        quality = "Good"
    elif sample >= 4:
        quality = "Fair"
    else:
        quality = "Poor"

    if sample >= 12 and stddev <= 2:
        confidence = "High"
    elif sample >= 6 and stddev <= 4:
        confidence = "Medium"
    else:
        confidence = "Low"

    preferred = int(mean_robust)
    cycle_day = (today - last).days + 1 if last else 0

    next_period = last + timedelta(days=preferred) if last else None
    days_to_next = max((next_period - today).days, 0) if next_period else 0
    ovulation = next_period - timedelta(days=luteal) if next_period else None
    days_to_ov = (ovulation - today).days if ovulation else None

    score = _SCORES.get(days_to_ov if days_to_ov is not None else 99, 2)
    status = "High" if score >= 8 else "Medium" if score >= 5 else "Low"

    following = next_period + timedelta(days=preferred) if next_period else None
    next_ov = following - timedelta(days=luteal) if following else None
    days_to_next_ov = (next_ov - today).days if next_ov else 999

    std_round = _round_half_up(stddev)
    earliest_period = (
        next_period - timedelta(days=std_round) if next_period else None
    )
    latest_period = (
        next_period + timedelta(days=std_round) if next_period else None
    )

    pre_period = next_period - timedelta(days=5) if next_period else None
    days_to_pre = (pre_period - today).days if pre_period else None

    ov_for_phase = days_to_ov if days_to_ov is not None else 999
    if cycle_day <= 5:
        phase = "Period"
    elif ov_for_phase > 5:
        phase = "Follicular"
    elif ov_for_phase > 0:
        phase = "Fertile"
    elif ov_for_phase == 0:
        phase = "Ovulation"
    else:
        phase = "Luteal"

    std_int = int(stddev)
    earliest_ov = ovulation - timedelta(days=std_int) if ovulation else None
    latest_ov = ovulation + timedelta(days=std_int) if ovulation else None
    window_start = earliest_ov - timedelta(days=5) if earliest_ov else None
    window_end = latest_ov
    width = {"High": 1, "Medium": 2}.get(confidence, 3)
    peak_start = ovulation - timedelta(days=width) if ovulation else None
    peak_end = ovulation + timedelta(days=width) if ovulation else None

    if peak_start and peak_end and window_start and window_end:
        if peak_start <= today <= peak_end:
            window_status = "Peak Fertility"
        elif window_start <= today <= window_end:
            window_status = "Fertile Window"
        else:
            window_status = "Low Fertility"
    else:
        window_status = None

    return CycleStats(
        period_dates_count=n_dates,
        cycle_count=max(n_dates - 1, 0),
        last_period_start=last,
        previous_period_start=previous,
        cycle_lengths=lengths,
        last_cycle_length=lengths[-1] if lengths else 0,
        shortest_cycle_length=min(lengths) if lengths else 0,
        longest_cycle_length=max(lengths) if lengths else 0,
        median=median,
        sample_size=sample,
        outlier_count=outliers,
        mean_robust=mean_robust,
        stddev=stddev,
        quality=quality,
        confidence=confidence,
        preferred_length=preferred,
        cycle_day=cycle_day,
        next_period=next_period,
        days_to_next_period=days_to_next,
        ovulation=ovulation,
        days_to_ovulation=days_to_ov,
        fertility_score=score,
        fertility_status=status,
        next_ovulation=next_ov,
        earliest_period=earliest_period,
        latest_period=latest_period,
        following_period=following,
        days_to_next_ovulation=days_to_next_ov,
        pre_period=pre_period,
        days_to_pre_period=days_to_pre,
        phase=phase,
        phase_color=PHASE_COLORS.get(phase, DEFAULT_PHASE_COLOR),
        earliest_ovulation=earliest_ov,
        latest_ovulation=latest_ov,
        window_start=window_start,
        window_end=window_end,
        peak_start=peak_start,
        peak_end=peak_end,
        window_status=window_status,
    )


def parse_date(value: Any) -> date | None:
    """Parse a strict YYYY-MM-DD value."""
    text = str(value).strip()
    if len(text) != 10:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def intercourse_points(records: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Convert stored records to sorted {x: epoch_ms, y: cycle_day} points."""
    points: list[dict[str, int]] = []
    for record in records:
        try:
            stamp = datetime.fromisoformat(str(record["timestamp"]))
        except (KeyError, ValueError):
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        try:
            day = int(record.get("cycle_day", 1))
        except (TypeError, ValueError):
            day = 1
        points.append({"x": int(stamp.timestamp() * 1000), "y": day})
    points.sort(key=lambda p: p["x"])
    return points
