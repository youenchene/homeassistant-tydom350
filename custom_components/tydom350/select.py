"""Fil-pilote modes; do not invent temperature setpoints or per-zone off."""
from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from .entity import TydomEntity

LABELS = {'eco': 'Éco', 'comfort': 'Confort', 'off': 'Arrêt général', 'auto': 'Automatique'}


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    entities = [TydomMode(c, entry, key, item['name']) for key, item in c.data['zones'].items()]
    if c.data['mode']['commands']:
        entities.append(TydomMode(c, entry, None, 'Chauffage général'))
    async_add_entities(entities)


class TydomMode(TydomEntity, SelectEntity):
    _attr_icon = 'mdi:radiator'

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator, entry, f'heating_{key if key is not None else "global"}',
                         f'Chauffage {name}' if key is not None else name)
        self.key = key
        if name.strip().upper() == 'N/A':
            self._attr_entity_registry_enabled_default = False
            self._attr_name = f'Chauffage zone {int(key)+1} (N/A)'

    @property
    def item(self):
        return self.coordinator.data['mode'] if self.key is None else self.coordinator.data['zones'].get(self.key, {})

    @property
    def available(self):
        return super().available and bool(self.item.get('commands'))

    @property
    def options(self):
        return [LABELS[x] for x in self.item.get('commands', {})]

    @property
    def current_option(self):
        return LABELS.get(self.item.get('state'))

    @property
    def extra_state_attributes(self):
        return {'portee': 'toutes_les_zones' if self.key is None else 'zone',
                'mode_general': LABELS.get(self.coordinator.data['mode']['state']),
                'note': 'Mode affiché par la passerelle ; aucune consigne en °C exposée.'}

    async def async_select_option(self, option):
        action = next((k for k, v in LABELS.items() if v == option), None)
        if not self.available or action not in self.item.get('commands', {}):
            raise HomeAssistantError('Mode non disponible')
        await self.coordinator.execute(self.item['commands'][action])
        await self.coordinator.async_request_refresh()
