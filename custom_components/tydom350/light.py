"""On/off controls. Legacy X2D exposes no verified light state."""
from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.exceptions import HomeAssistantError
from .entity import TydomEntity


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities(TydomLight(c, entry, key, item['name']) for key, item in c.data['lights'].items())


class TydomLight(TydomEntity, LightEntity):
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF
    _attr_assumed_state = True

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator, entry, f'light_{key}', name or f'Éclairage {int(key)+1}')
        self.key = key
        self._attr_is_on = None

    @property
    def available(self):
        return super().available and self.key in self.coordinator.data['lights']

    @property
    def extra_state_attributes(self):
        return {'retour_etat_physique': False, 'source_etat': 'derniere_commande_home_assistant',
                'note': 'État estimé ; les commandes murales ne sont pas détectées.'}

    async def _send(self, action):
        item = self.coordinator.data['lights'].get(self.key)
        if not self.available or not item:
            raise HomeAssistantError('Éclairage indisponible')
        await self.coordinator.execute(item['commands'][action])
        self._attr_is_on = action == 'on'
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        await self._send('on')

    async def async_turn_off(self, **kwargs):
        await self._send('off')
