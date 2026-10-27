"""Text entities (editable period history, last intercourse entry)."""
from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .engine import parse_date
from .entity import CycleEntity
from .manager import CycleManager


class PeriodStartHistory(CycleEntity, TextEntity):
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255

    @property
    def native_value(self) -> str:
        return ",".join(d.isoformat() for d in self.manager.periods)

    async def async_set_value(self, value: str) -> None:
        dates = [d for d in (parse_date(p) for p in value.split(",")) if d]
        await self.manager.async_set_periods(dates)


class IntercourseHistoryText(CycleEntity, TextEntity):
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255

    @property
    def native_value(self) -> str:
        return self.manager.last_intercourse_text

    async def async_set_value(self, value: str) -> None:
        # Only an empty value is meaningful: it clears the history.
        if not value.strip():
            await self.manager.async_clear_intercourse()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    manager: CycleManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PeriodStartHistory(manager, entry, "Period Start History", "period_start_history"),
            IntercourseHistoryText(manager, entry, "Intercourse History", "intercourse_history"),
        ]
    )
