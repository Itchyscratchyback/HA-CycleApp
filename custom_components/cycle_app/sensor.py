from __future__ import annotations

from datetime import datetime, date, timezone
import json
import os
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Data stored by Cycle App"


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
                parts.append(obj.get("content", ""))
            except Exception:
                parts.append(line)
        return [p for p in parts if p]
    try:
        obj = json.loads(raw)
        content = obj.get("content", raw)
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
            lines = _read_lines(self.path)
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
    def state(self):
        return len(self.coordinator.data.get("points", []))


class IntercourseTimeline(BaseHistorySensor):
    @property
    def state(self):
        return len(self.coordinator.data.get("points", []))

    @property
    def extra_state_attributes(self):
        return {"series": self.coordinator.data.get("points", []), "attribution": ATTRIBUTION}


class LastIntercourseDate(BaseHistorySensor):
    @property
    def state(self):
        pts = self.coordinator.data.get("points", [])
        if not pts:
            return "none"
        last = pts[-1]
        ts = int(last.get("x"))
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        return dt.isoformat()


class IntercourseCountCurrentCycle(BaseHistorySensor):
    @property
    def state(self):
        # Read directly from the file to ensure up-to-date counts
        try:
            lines = _read_lines(self.coordinator.path)
        except Exception:
            lines = []

        try:
            current_day = int(self.hass.states.get("sensor.cycle_day").state)
        except Exception:
            current_day = 0

        count = 0
        for l in lines:
            parsed = _parse_entry(l)
            if not parsed:
                continue
            _, val = parsed
            try:
                day = int(val)
            except Exception:
                day = 0
            if day > 0 and day <= current_day:
                count += 1
        return count


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    path = hass.config.path("data/ha_cycle_app/intercourse_history.json")
    coordinator = HistoryCoordinator(hass, path)
    # perform initial refresh
    await coordinator.async_request_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entities = [
        IntercourseHistoryCount(coordinator, "Intercourse History Count", f"{DOMAIN}_history_count"),
        IntercourseTimeline(coordinator, "Intercourse Timeline", f"{DOMAIN}_timeline"),
        LastIntercourseDate(coordinator, "Last Intercourse Date", f"{DOMAIN}_last"),
        IntercourseCountCurrentCycle(coordinator, "Intercourse Count Current Cycle", f"{DOMAIN}_count_current_cycle"),
    ]

    async_add_entities(entities, update_before_add=False)
