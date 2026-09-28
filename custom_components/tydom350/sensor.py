"""Measured temperature and consumption with the unit actually supplied."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from .entity import TydomEntity


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    entities = [TydomTemperature(c, entry, 'temperature', 'Température intérieure')]
    for key, item in c.data['consumption'].items():
        entities.append(TydomConsumption(c, entry, key, item))
    async_add_entities(entities)


class TydomTemperature(TydomEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = '°C'

    @property
    def native_value(self):
        return self.coordinator.data['temperature']


class TydomConsumption(TydomEntity, SensorEntity):
    def __init__(self, c, entry, key, item):
        self.key = key
        self.unit = item['unit']
        energy = self.unit in ('Wh', 'kWh')
        super().__init__(c, entry, f'consumption_{key}_{self.unit}',
                         f'{"Consommation" if energy else "Coût"} {item["name"]}')
        self._attr_native_unit_of_measurement = self.unit
        self._attr_device_class = SensorDeviceClass.ENERGY if energy else SensorDeviceClass.MONETARY
        # The consumption page has a manual reset, so decreasing energy indicates a new cycle.
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING if energy else None

    @property
    def available(self):
        item = self.coordinator.data['consumption'].get(self.key)
        return super().available and item is not None and item['unit'] == self.unit

    @property
    def native_value(self):
        item = self.coordinator.data['consumption'].get(self.key)
        return item['value'] if item and item['unit'] == self.unit else None

    @property
    def extra_state_attributes(self):
        return {'source': 'Compteur affiché par le TYDOM 350',
                'note': 'Aucune conversion euros/kWh ; un zéro ne prouve pas que le comptage fonctionne.'}
