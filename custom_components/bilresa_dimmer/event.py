# SPDX-License-Identifier: GPL-3.0-or-later
"""One event entity for each mode of each BILRESA dimmer.

A dimmer is a Matter device with nine buttons. Its entities are named after it with the mode ("Living Room Bilresa Dimmer mode 1")
and start in its area. Like Fast Matter switch's, they have no device of their own: Home Assistant gives a device to one
integration only. Wheel events carry ``steps`` (negative counter-clockwise); an automation uses them with the Event received
trigger and the ``bilresa_dimmer.adjust_light`` action.
"""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import BUTTON_COUNT, DOMAIN, EVENT_TYPES, MATTER_DOMAIN, MODES
from .events import dispatch_signal


def dimmer_device_ids(entities: er.EntityRegistry) -> set[str]:
    """The Matter devices with exactly the nine buttons of a BILRESA dimmer."""
    buttons: dict[str, int] = {}
    for entry in entities.entities.values():
        if entry.platform == MATTER_DOMAIN and entry.domain == "event" and entry.device_id:
            buttons[entry.device_id] = buttons.get(entry.device_id, 0) + 1
    return {device_id for device_id, count in buttons.items() if count == BUTTON_COUNT}


def unique_id(device_id: str, mode: int) -> str:
    return f"{device_id}-mode-{mode}"


class DimmerMode(EventEntity):
    """What the wheel and the wheel press of one mode report."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_event_types = EVENT_TYPES

    def __init__(self, device: dr.DeviceEntry, mode: int) -> None:
        self._device_id = device.id
        self._mode = mode
        self._attr_unique_id = unique_id(device.id, mode)
        self._attr_name = f"{device.name_by_user or device.name} mode {mode}"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, dispatch_signal(self._device_id, self._mode), self._reported))

    @callback
    def _reported(self, event_type: str, attributes: dict) -> None:
        self._trigger_event(event_type, attributes)
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Gives every dimmer its three mode entities, now and when one is added later, and takes them away with the dimmer."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    with_entities: set[str] = set()

    @callback
    def follow_dimmers(_event: Event | None = None) -> None:
        dimmers = dimmer_device_ids(entities)
        for ours in er.async_entries_for_config_entry(entities, entry.entry_id):
            device_id = ours.unique_id.rsplit("-mode-", 1)[0]
            if device_id not in dimmers:
                entities.async_remove(ours.entity_id)
                with_entities.discard(device_id)
        new = [d for d in dimmers if d not in with_entities and devices.async_get(d) is not None]
        with_entities.update(new)
        added = []
        for device_id in new:
            device = devices.async_get(device_id)
            for mode in MODES:
                if entities.async_get_entity_id("event", DOMAIN, unique_id(device_id, mode)) is None:
                    # Registered first so that the area is the dimmer's.
                    created = entities.async_get_or_create(
                        "event",
                        DOMAIN,
                        unique_id(device_id, mode),
                        config_entry=entry,
                        suggested_object_id=slugify(f"{device.name_by_user or device.name} mode {mode}"),
                    )
                    if device.area_id:
                        entities.async_update_entity(created.entity_id, area_id=device.area_id)
                added.append(DimmerMode(device, mode))
        async_add_entities(added)

    @callback
    def is_event_entity(data: er.EventEntityRegistryUpdatedData) -> bool:
        return data["entity_id"].startswith("event.")

    follow_dimmers()
    entry.async_on_unload(hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, follow_dimmers, event_filter=is_event_entity))
