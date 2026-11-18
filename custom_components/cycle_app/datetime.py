"""Date/time of the intercourse that is about to be logged."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import CycleEntity
from .manager import CycleManager


class LogDateTime(CycleEntity, DateTimeEntity):
    """When empty the activity is logged at the current time."""

    @property
    def native_value(self) -> datetime | None:
        return self.manager.log_time

    async def async_set_value(self, value: datetime) -> None:
        self.manager.async_set_log_time(value)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    manager: CycleManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LogDateTime(manager, entry, "Intercourse Date Time", "intercourse_datetime")])