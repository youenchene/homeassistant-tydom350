"""Local integration for the legacy Delta Dore TYDOM 350."""
from datetime import timedelta
import logging
import aiohttp
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import TydomClient, AuthenticationError
from .const import DOMAIN, DEFAULT_INTERVAL
from .protocol import ProtocolError

PLATFORMS = [Platform.LIGHT, Platform.SENSOR, Platform.SELECT]
_LOGGER = logging.getLogger(__name__)


class TydomCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.client = TydomClient(async_get_clientsession(hass), entry.data['host'],
                                  entry.data.get('username', ''), entry.data.get('password', ''))
        self.last_commands = {}
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=entry.data.get('scan_interval', DEFAULT_INTERVAL)))

    async def _async_update_data(self):
        try:
            return await self.client.snapshot()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed('Identifiants TYDOM incorrects') from err
        except (aiohttp.ClientError, TimeoutError, ProtocolError) as err:
            raise UpdateFailed('Lecture du TYDOM 350 impossible') from err

    async def execute(self, params):
        try:
            await self.client.send(params)
        except (aiohttp.ClientError, TimeoutError, AuthenticationError, ProtocolError) as err:
            raise HomeAssistantError('Commande TYDOM non confirmée ; vérifier le boîtier avant de réessayer') from err


async def async_setup_entry(hass, entry):
    coordinator = TydomCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
