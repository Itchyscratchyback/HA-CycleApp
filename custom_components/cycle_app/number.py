"""Luteal length number."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import CycleEntity
from .manager import CycleManager


class LutealLength(CycleEntity, NumberEntity):
    _attr_native_min_value = 10
    _attr_native_max_value = 17
    _attr_native_step = 1

    @property
    def native_value(self) -> float:
        return self.manager.luteal

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_set_luteal(int(value))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    manager: CycleManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LutealLength(manager, entry, "Luteal Length", "luteal_length")])
