"""Shared entity base."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import CycleManager


class CycleEntity(Entity):
    """Base entity bound to the CycleManager."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(
        self, manager: CycleManager, entry: ConfigEntry, name: str, unique_id: str
    ) -> None:
        self.manager = manager
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Cycle App",
            manufacturer="Cycle App",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.manager.async_add_listener(self.async_write_ha_state)
        )
