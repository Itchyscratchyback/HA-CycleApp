"""Cycle App: menstrual cycle tracking and fertility predictions."""
from __future__ import annotations

from datetime import date

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .manager import CycleManager

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_ADD_PERIOD = "add_period_start"
SERVICE_REMOVE_PERIOD = "remove_period_start"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager = CycleManager(hass)
    await manager.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    @callback
    def _midnight(_now) -> None:
        manager.async_refresh()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight, hour=0, minute=0, second=5)
    )

    async def _add(call: ServiceCall) -> None:
        day: date | None = call.data.get("date")
        await manager.async_add_period(day)

    async def _remove(call: ServiceCall) -> None:
        await manager.async_remove_period(call.data["date"])

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_PERIOD, _add, vol.Schema({vol.Optional("date"): cv.date})
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_PERIOD, _remove, vol.Schema({vol.Required("date"): cv.date})
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.services.async_remove(DOMAIN, SERVICE_ADD_PERIOD)
        hass.services.async_remove(DOMAIN, SERVICE_REMOVE_PERIOD)
    return unloaded
