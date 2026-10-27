"""Selects for logging intercourse."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SELECTS
from .entity import CycleEntity
from .manager import CycleManager


class CycleSelect(CycleEntity, SelectEntity):
    def __init__(self, manager: CycleManager, entry: ConfigEntry, key: str) -> None:
        name, options = SELECTS[key]
        super().__init__(manager, entry, name, key)
        self._key = key
        self._attr_options = options

    @property
    def current_option(self) -> str:
        return self.manager.selections[self._key]

    async def async_select_option(self, option: str) -> None:
        self.manager.async_select(self._key, option)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    manager: CycleManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CycleSelect(manager, entry, key) for key in SELECTS])
