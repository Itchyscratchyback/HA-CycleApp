"""State manager: owns period/intercourse data and persists it."""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import engine
from .const import (
    DEFAULT_LUTEAL_LENGTH,
    LEGACY_INTERCOURSE_FILE,
    LEGACY_PERIOD_FILE,
    MAX_PERIOD_DATES,
    NOT_SELECTED,
    SELECTS,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def _read_legacy(path: str) -> list[dict[str, Any]]:
    """Read NDJSON/JSON legacy files; returns a list of parsed objects."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []
    out: list[dict[str, Any]] = []
    for line in (l.strip() for l in raw.splitlines()):
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    if not out:
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                out.append(obj)
        except ValueError:
            pass
    return out


def _legacy_periods(objs: list[dict[str, Any]]) -> list[date]:
    found: list[date] = []
    for obj in objs:
        for part in str(obj.get("content", "")).split(","):
            parsed = engine.parse_date(part)
            if parsed:
                found.append(parsed)
    return found


def _legacy_intercourse(objs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for obj in objs:
        if "timestamp" in obj:
            records.append(obj)
        elif obj.get("content"):
            try:
                inner = json.loads(obj["content"])
            except (TypeError, ValueError):
                inner = None
            if isinstance(inner, dict) and "timestamp" in inner:
                records.append(inner)
    return records


class CycleManager:
    """Holds all Cycle App state."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._listeners: list[Callable[[], None]] = []
        self.periods: list[date] = []
        self.luteal: int = DEFAULT_LUTEAL_LENGTH
        self.intercourse: list[dict[str, Any]] = []
        self.selections: dict[str, str] = {key: NOT_SELECTED for key in SELECTS}
        self.stats: engine.CycleStats = engine.compute(
            [], self.luteal, dt_util.now().date()
        )

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if data is None:
            await self._async_migrate_legacy()
        else:
            self.periods = sorted(
                {d for d in map(engine.parse_date, data.get("periods", [])) if d}
            )
            self.luteal = int(data.get("luteal", DEFAULT_LUTEAL_LENGTH))
            self.intercourse = list(data.get("intercourse", []))
        self._recompute()

    async def _async_migrate_legacy(self) -> None:
        """Import data from the old YAML-package file persistence."""
        period_objs = await self.hass.async_add_executor_job(
            _read_legacy, self.hass.config.path(LEGACY_PERIOD_FILE)
        )
        inter_objs = await self.hass.async_add_executor_job(
            _read_legacy, self.hass.config.path(LEGACY_INTERCOURSE_FILE)
        )
        self.periods = sorted(set(_legacy_periods(period_objs)))[-MAX_PERIOD_DATES:]
        self.intercourse = _legacy_intercourse(inter_objs)
        if self.periods or self.intercourse:
            _LOGGER.info(
                "Imported %d period dates and %d intercourse records from legacy files",
                len(self.periods),
                len(self.intercourse),
            )
        await self._async_save()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "periods": [d.isoformat() for d in self.periods],
                "luteal": self.luteal,
                "intercourse": self.intercourse,
            }
        )

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @callback
    def async_refresh(self) -> None:
        """Recompute (e.g. at midnight) and notify entities."""
        self._recompute()
        for listener in list(self._listeners):
            listener()

    def _recompute(self) -> None:
        self.stats = engine.compute(
            self.periods, self.luteal, dt_util.now().date()
        )

    @property
    def points(self) -> list[dict[str, int]]:
        return engine.intercourse_points(self.intercourse)

    async def _async_changed(self) -> None:
        await self._async_save()
        self.async_refresh()

    # Period history
    async def async_set_periods(self, dates: list[date]) -> None:
        self.periods = sorted(set(dates))[-MAX_PERIOD_DATES:]
        await self._async_changed()

    async def async_add_period(self, day: date | None = None) -> None:
        await self.async_set_periods(
            self.periods + [day or dt_util.now().date()]
        )

    async def async_remove_period(self, day: date) -> None:
        await self.async_set_periods([d for d in self.periods if d != day])

    async def async_set_luteal(self, value: int) -> None:
        self.luteal = int(value)
        await self._async_changed()

    # Intercourse logging
    @callback
    def async_select(self, key: str, option: str) -> None:
        self.selections[key] = option
        self.async_refresh()

    async def async_log_intercourse(self) -> None:
        sel = self.selections
        kind = sel["intercourse_type"]
        raw = sel["intercourse_raw"]
        needs_creampie = raw in ("Yes", "Partially")
        valid = (
            kind != NOT_SELECTED
            and sel["intercourse_subtype2"] != NOT_SELECTED
            and raw != NOT_SELECTED
            and (kind == "Together" or sel["intercourse_subtype1"] != NOT_SELECTED)
            and (not needs_creampie or sel["intercourse_creampie"] != NOT_SELECTED)
        )
        if not valid:
            raise HomeAssistantError(
                "Select type, execution, RAW (and the dependent options) before logging"
            )
        self.intercourse.append(
            {
                "timestamp": dt_util.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "cycle_day": self.stats.cycle_day,
                "intercourse_type": kind,
                "intercourse_subtype1": (
                    "" if kind == "Together" else sel["intercourse_subtype1"]
                ),
                "intercourse_subtype2": sel["intercourse_subtype2"],
                "intercourse_raw": raw,
                "intercourse_creampie": (
                    sel["intercourse_creampie"] if needs_creampie else ""
                ),
            }
        )
        self.selections = {key: NOT_SELECTED for key in SELECTS}
        await self._async_changed()

    async def async_clear_intercourse(self) -> None:
        self.intercourse = []
        await self._async_changed()

    @property
    def last_intercourse_text(self) -> str:
        if not self.intercourse:
            return ""
        last = self.intercourse[-1]
        return f"{last.get('timestamp', '')}|{last.get('cycle_day', 0)}"
