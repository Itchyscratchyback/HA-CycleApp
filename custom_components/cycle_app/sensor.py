from __future__ import annotations

from datetime import datetime, date, timezone
import json
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Data stored by Cycle App"


def _record_content(record: dict[str, Any]) -> str:
    """Convert a JSON record to the legacy parser representation."""
    if record.get("content"):
        return str(record["content"])
    timestamp = record.get("timestamp")
    cycle_day = record.get("cycle_day")
    if timestamp and cycle_day is not None:
        return f"{timestamp}|{cycle_day}"
    return ""


def _read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if len(lines) > 1:
        parts: list[str] = []
        for line in lines:
            try:
                obj = json.loads(line)
                parts.append(_record_content(obj))
            except Exception:
                parts.append(line)
        return [p for p in parts if p]
    try:
        obj = json.loads(raw)
        content = _record_content(obj) or raw
        return [content] if content else []
    except Exception:
        if not raw:
            return []
        return [p for p in [s.strip() for s in raw.split(',')] if p]


def _parse_entry(content: str) -> tuple[int, int] | None:
    # returns (epoch_ms, value)
    s = content.strip()
    if not s:
        return None
    if "|" in s:
        parts = s.split("|", 1)
        ts = parts[0].strip()
        val_str = parts[1].strip()
        try:
            val = int(val_str)
        except Exception:
            try:
                val = int(float(val_str))
            except Exception:
                val = 1
    else:
        ts = s
        val = 1
    # parse ts as datetime or date
    dt = None
    try:
        # try full ISO parse
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        try:
            # try date only YYYY-MM-DD
            d = date.fromisoformat(ts)
            dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        except Exception:
            return None
    epoch_ms = int(dt.timestamp() * 1000)
    return (epoch_ms, val)


class HistoryCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, path: str) -> None:
        super().__init__(hass, _LOGGER, name="cycle_app_history", update_interval=None)
        self.path = path
        # store parsed points
        self.data: dict[str, Any] = {"points": []}

    async def _async_update_data(self) -> dict[str, Any]:
        # read file and parse entries
        try:
            lines = await self.hass.async_add_executor_job(_read_lines, self.path)
            pts = []
            for l in lines:
                parsed = _parse_entry(l)
                if parsed:
                    pts.append({"x": parsed[0], "y": parsed[1]})
            pts.sort(key=lambda p: p["x"]) if pts else None
            return {"points": pts}
        except Exception as err:
            raise UpdateFailed(err)


class BaseHistorySensor(SensorEntity):
    _attr_attribution = ATTR_ATTRIBUTION

    def __init__(self, coordinator: HistoryCoordinator, name: str, unique_id: str):
        self.coordinator = coordinator
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.get("points") is not None)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))
        # request initial refresh
        await self.coordinator.async_request_refresh()

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class IntercourseHistoryCount(BaseHistorySensor):
    @property
    def native_value(self):
        return len(self.coordinator.data.get("points", []))


class IntercourseTimeline(BaseHistorySensor):
    @property
    def native_value(self):
        return len(self.coordinator.data.get("points", []))

    @property
    def extra_state_attributes(self):
        return {"series": self.coordinator.data.get("points", []), "attribution": ATTRIBUTION}


class LastIntercourseDate(BaseHistorySensor):
    @property
    def native_value(self):
        pts = self.coordinator.data.get("points", [])
        if not pts:
            return None
        last = pts[-1]
        ts = int(last.get("x"))
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        return dt.isoformat()


class IntercourseCountCurrentCycle(BaseHistorySensor):
    @property
    def native_value(self):
        try:
            current_day = int(self.hass.states.get("sensor.cycle_day").state)
        except Exception:
            current_day = 0

        try:
            last_period = self.hass.states.get("sensor.last_period_start").state
            cycle_start = int(datetime.fromisoformat(last_period).replace(
                tzinfo=timezone.utc
            ).timestamp() * 1000)
        except Exception:
            cycle_start = 0

        count = 0
        for point in self.coordinator.data.get("points", []):
            try:
                day = int(point.get("y", 0))
            except Exception:
                day = 0
            if (
                day > 0
                and day <= current_day
                and int(point.get("x", 0)) >= cycle_start
            ):
                count += 1
        return count


class IntercourseCountFertileWindow(BaseHistorySensor):
    @property
    def native_value(self):
        start_state = self.hass.states.get("sensor.peak_fertility_start")
        end_state = self.hass.states.get("sensor.peak_fertility_end")
        if not start_state or not end_state:
            return 0

        try:
            peak_start = date.fromisoformat(start_state.state)
            peak_end = date.fromisoformat(end_state.state)
        except (TypeError, ValueError):
            return 0

        # A newly reported period starts a new cycle. Prefer the calculated
        # sensor, then fall back to the raw period history if that sensor or
        # an optional input_datetime is unavailable.
        cycle_start = 0
        cycle_entities = (
            "sensor.last_period_start",
            "input_datetime.last_period_start",
        )
        for entity_id in cycle_entities:
            cycle_state = self.hass.states.get(entity_id)
            if not cycle_state or cycle_state.state in ("unknown", "unavailable", ""):
                continue
            try:
                cycle_start = datetime.fromisoformat(cycle_state.state).replace(
                    tzinfo=timezone.utc
                ).timestamp() * 1000
                break
            except (TypeError, ValueError):
                continue

        if cycle_start == 0:
            history = self.hass.states.get("input_text.period_start_history")
            if history and history.state not in ("unknown", "unavailable", ""):
                dates = []
                for value in history.state.split(","):
                    try:
                        dates.append(date.fromisoformat(value.strip()))
                    except ValueError:
                        continue
                if dates:
                    cycle_start = datetime.combine(
                        max(dates), datetime.min.time(), tzinfo=timezone.utc
                    ).timestamp() * 1000

        count = 0
        for point in self.coordinator.data.get("points", []):
            try:
                timestamp = int(point.get("x", 0))
                point_date = datetime.fromtimestamp(
                    timestamp / 1000,
                    tz=timezone.utc,
                ).date()
            except (TypeError, ValueError, OSError):
                continue
            if (
                timestamp >= cycle_start
                and peak_start <= point_date <= peak_end
            ):
                count += 1
        return count


class DaysSinceIntercourse(BaseHistorySensor):
    _attr_native_unit_of_measurement = "d"

    @property
    def native_value(self):
        points = self.coordinator.data.get("points", [])
        if not points:
            return None
        last_timestamp = int(points[-1].get("x", 0)) / 1000
        return int((datetime.now(timezone.utc).timestamp() - last_timestamp) / 86400)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    path = hass.config.path("data/ha_cycle_app/intercourse_history.json")
    coordinator = HistoryCoordinator(hass, path)
    # perform initial refresh
    await coordinator.async_request_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entities = [
        IntercourseHistoryCount(coordinator, "Intercourse History Count", f"{DOMAIN}_history_count"),
        IntercourseTimeline(coordinator, "Intercourse Timeline", f"{DOMAIN}_timeline"),
        LastIntercourseDate(coordinator, "Last Intercourse Date", "last_intercourse_date"),
        IntercourseCountCurrentCycle(
            coordinator,
            "Intercourse Count Current Cycle",
            "intercourse_count_current_cycle",
        ),
        IntercourseCountFertileWindow(
            coordinator,
            "Intercourse Count Fertile Window",
            "intercourse_count_fertile_window",
        ),
        DaysSinceIntercourse(
            coordinator,
            "Days Since Intercourse",
            "days_since_intercourse",
        ),
    ]

    async_add_entities(entities, update_before_add=False)
