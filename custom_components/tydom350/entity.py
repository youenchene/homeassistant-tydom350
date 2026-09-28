"""Common gateway identity."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN


class TydomEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator)
        self._attr_unique_id = f'{entry.entry_id}_{key}'
        self._attr_name = name
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)},
            name='TYDOM 350', manufacturer='Delta Dore', model='TYDOM 350 PC',
            configuration_url=coordinator.client.base_url)
