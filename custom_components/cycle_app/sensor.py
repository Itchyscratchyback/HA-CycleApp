"""Sensors for Cycle App."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN, NOT_SELECTED
from .engine import CycleStats
from .entity import CycleEntity
from .manager import CycleManager


@dataclass(frozen=True)
class StatSpec:
    name: str
    unique_id: str
    value: Callable[[CycleStats], Any]
    unit: str | None = None
    is_date: bool = False


def _lengths(s: CycleStats) -> str:
    return ",".join(str(v) for v in s.cycle_lengths)


STAT_SENSORS: tuple[StatSpec, ...] = (
    StatSpec("Period Dates Count", "period_dates_count", lambda s: s.period_dates_count),
    StatSpec("Cycle Count", "cycle_count", lambda s: s.cycle_count),
    StatSpec("Last Period Start", "last_period_start", lambda s: s.last_period_start, is_date=True),
    StatSpec("Previous Period Start", "previous_period_start", lambda s: s.previous_period_start, is_date=True),
    StatSpec("Cycle Lengths Calculated", "cycle_lengths_calculated", _lengths),
    StatSpec("Last Cycle Length Robust", "last_cycle_length_robust", lambda s: s.last_cycle_length, "d"),
    StatSpec("Shortest Cycle Length", "shortest_cycle_length", lambda s: s.shortest_cycle_length, "d"),
    StatSpec("Longest Cycle Length", "longest_cycle_length", lambda s: s.longest_cycle_length, "d"),
    StatSpec("Cycle Length Median", "cycle_length_median", lambda s: s.median, "d"),
    StatSpec("Cycle Sample Size", "cycle_sample_size", lambda s: s.sample_size),
    StatSpec("Cycle Outlier Count", "cycle_outlier_count", lambda s: s.outlier_count),
    StatSpec("Cycle Length Mean Robust", "cycle_length_mean_robust", lambda s: s.mean_robust, "d"),
    StatSpec("Cycle Length StdDev Robust", "cycle_length_stddev_robust", lambda s: s.stddev, "d"),
    StatSpec("Cycle Data Quality", "cycle_data_quality", lambda s: s.quality),
    StatSpec("Cycle Prediction Confidence", "cycle_prediction_confidence", lambda s: s.confidence),
    StatSpec("Cycle Length Preferred", "cycle_length_preferred", lambda s: s.preferred_length, "d"),
    StatSpec("Cycle Day", "cycle_day", lambda s: s.cycle_day, "d"),
    StatSpec("Predicted Next Period Date", "predicted_next_period_date", lambda s: s.next_period, is_date=True),
    StatSpec("Days To Next Period", "days_to_next_period", lambda s: s.days_to_next_period, "d"),
    StatSpec("Predicted Ovulation Date", "predicted_ovulation_date", lambda s: s.ovulation, is_date=True),
    StatSpec("Days To Ovulation", "days_to_ovulation", lambda s: s.days_to_ovulation, "d"),
    StatSpec("Fertility Score", "fertility_score", lambda s: s.fertility_score, "/10"),
    StatSpec("Fertility Status", "fertility_status", lambda s: s.fertility_status),
    StatSpec("Predicted Next Ovulation Date", "predicted_next_ovulation_date", lambda s: s.next_ovulation, is_date=True),
    StatSpec("Earliest Expected Period", "earliest_expected_period", lambda s: s.earliest_period, is_date=True),
    StatSpec("Latest Expected Period", "latest_expected_period", lambda s: s.latest_period, is_date=True),
    StatSpec("Predicted Following Period Date", "predicted_following_period_date", lambda s: s.following_period, is_date=True),
    StatSpec("Days To Next Ovulation Date", "days_to_next_ovulation_date", lambda s: s.days_to_next_ovulation, "d"),
    StatSpec("Pre Period Date", "pre_period_date", lambda s: s.pre_period, is_date=True),
    StatSpec("Days To Pre Period", "days_to_pre_period", lambda s: s.days_to_pre_period, "d"),
    StatSpec("Cycle Phase Color", "cycle_phase_color", lambda s: s.phase_color),
    StatSpec("Cycle Phase", "cycle_phase", lambda s: s.phase),
    StatSpec("Earliest Ovulation Date", "earliest_ovulation_date", lambda s: s.earliest_ovulation, is_date=True),
    StatSpec("Latest Ovulation Date", "latest_ovulation_date", lambda s: s.latest_ovulation, is_date=True),
    StatSpec("Fertility Window Start", "fertility_window_start", lambda s: s.window_start, is_date=True),
    StatSpec("Fertility Window End", "fertility_window_end", lambda s: s.window_end, is_date=True),
    StatSpec("Peak Fertility Start", "peak_fertility_start", lambda s: s.peak_start, is_date=True),
    StatSpec("Peak Fertility End", "peak_fertility_end", lambda s: s.peak_end, is_date=True),
    StatSpec("Fertility Window Status", "fertility_window_status", lambda s: s.window_status),
)


class CycleStatSensor(CycleEntity, SensorEntity):
    def __init__(self, manager: CycleManager, entry: ConfigEntry, spec: StatSpec) -> None:
        super().__init__(manager, entry, spec.name, spec.unique_id)
        self._spec = spec
        self._attr_native_unit_of_measurement = spec.unit
        if spec.is_date:
            self._attr_device_class = SensorDeviceClass.DATE

    @property
    def native_value(self) -> Any:
        return self._spec.value(self.manager.stats)


class IntercourseTimelineRaw(CycleEntity, SensorEntity):
    @property
    def native_value(self) -> str:
        return self.manager.last_intercourse_text


class IntercourseHistoryCount(CycleEntity, SensorEntity):
    @property
    def native_value(self) -> int:
        return len(self.manager.points)


class IntercourseTimeline(CycleEntity, SensorEntity):
    # Large attributes are kept out of the recorder database.
    _unrecorded_attributes = frozenset({"series", "records"})

    @property
    def native_value(self) -> int:
        return len(self.manager.points)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "series": self.manager.points,
            "records": [
                {k: v for k, v in r.items() if v not in ("", None, NOT_SELECTED)}
                for r in self.manager.intercourse
            ],
        }


class LastIntercourseDate(CycleEntity, SensorEntity):
    @property
    def native_value(self) -> str | None:
        points = self.manager.points
        if not points:
            return None
        return datetime.fromtimestamp(points[-1]["x"] / 1000, tz=timezone.utc).isoformat()


def _day_start_ms(day: date) -> float:
    return datetime.combine(day, time.min, tzinfo=timezone.utc).timestamp() * 1000


class IntercourseCountCurrentCycle(CycleEntity, SensorEntity):
    @property
    def native_value(self) -> int:
        stats = self.manager.stats
        start = _day_start_ms(stats.last_period_start) if stats.last_period_start else 0
        return sum(
            1
            for p in self.manager.points
            if 0 < p["y"] <= stats.cycle_day and p["x"] >= start
        )


class IntercourseCountFertileWindow(CycleEntity, SensorEntity):
    @property
    def native_value(self) -> int:
        stats = self.manager.stats
        if not stats.peak_start or not stats.peak_end:
            return 0
        start = _day_start_ms(stats.last_period_start) if stats.last_period_start else 0
        count = 0
        for p in self.manager.points:
            day = datetime.fromtimestamp(p["x"] / 1000, tz=timezone.utc).date()
            if p["x"] >= start and stats.peak_start <= day <= stats.peak_end:
                count += 1
        return count


class DaysSinceIntercourse(CycleEntity, SensorEntity):
    _attr_native_unit_of_measurement = "d"

    @property
    def native_value(self) -> int | None:
        points = self.manager.points
        if not points:
            return None
        return int((dt_util.utcnow().timestamp() - points[-1]["x"] / 1000) / 86400)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    manager: CycleManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[CycleEntity] = [
        CycleStatSensor(manager, entry, spec) for spec in STAT_SENSORS
    ]
    entities += [
        IntercourseTimelineRaw(manager, entry, "Intercourse Timeline Raw", "intercourse_timeline_raw"),
        IntercourseHistoryCount(manager, entry, "Intercourse History Count", f"{DOMAIN}_history_count"),
        IntercourseTimeline(manager, entry, "Intercourse Timeline", f"{DOMAIN}_timeline"),
        LastIntercourseDate(manager, entry, "Last Intercourse Date", "last_intercourse_date"),
        IntercourseCountCurrentCycle(manager, entry, "Intercourse Count Current Cycle", "intercourse_count_current_cycle"),
        IntercourseCountFertileWindow(manager, entry, "Intercourse Count Fertile Window", "intercourse_count_fertile_window"),
        DaysSinceIntercourse(manager, entry, "Days Since Intercourse", "days_since_intercourse"),
    ]
    async_add_entities(entities)
