"""UI configuration with a read-only connection test."""
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import AuthenticationError, TydomClient, normalize_host
from .const import DOMAIN, DEFAULT_INTERVAL
from .protocol import ProtocolError


class Tydom350ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                host = normalize_host(user_input['host'])
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                client = TydomClient(async_get_clientsession(self.hass), host,
                                     user_input.get('username', ''), user_input.get('password', ''))
                await client.snapshot()
            except AuthenticationError:
                errors['base'] = 'invalid_auth'
            except (aiohttp.ClientError, TimeoutError):
                errors['base'] = 'cannot_connect'
            except (ProtocolError, ValueError):
                errors['base'] = 'invalid_gateway'
            else:
                return self.async_create_entry(title='TYDOM 350', data={**user_input, 'host': host})
        return self.async_show_form(step_id='user', data_schema=vol.Schema({
            vol.Required('host', default=''): str,
            vol.Optional('username', default=''): str,
            vol.Optional('password', default=''): str,
            vol.Required('scan_interval', default=DEFAULT_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
        }), errors=errors)
