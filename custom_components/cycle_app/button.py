"""Buttons for Cycle App."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import CycleEntity
from .manager import CycleManager


class PeriodStartedButton(CycleEntity, ButtonEntity):
    _attr_icon = "mdi:calendar-plus"

    async def async_press(self) -> None:
        await self.manager.async_add_period()


class LogIntercourseButton(CycleEntity, ButtonEntity):
    _attr_icon = "mdi:heart"

    async def async_press(self) -> None:
        await self.manager.async_log_intercourse()


class ClearIntercourseButton(CycleEntity, ButtonEntity):
    _attr_icon = "mdi:delete"

    async def async_press(self) -> None:
        await self.manager.async_clear_intercourse()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    manager: CycleManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PeriodStartedButton(manager, entry, "Period Started", "period_started"),
            LogIntercourseButton(manager, entry, "Log Intercourse", "log_intercourse"),
            ClearIntercourseButton(manager, entry, "Clear Intercourse History", "clear_intercourse_history"),
        ]
    )
