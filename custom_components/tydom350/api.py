"""Serialized HTTP access to the small legacy embedded web server."""
import asyncio
from urllib.parse import urlsplit
import aiohttp
from .protocol import ProtocolError, parse_index, parse_lights, parse_heating, parse_consumption


class AuthenticationError(Exception):
    """Gateway needs valid HTTP credentials."""


def normalize_host(host):
    value = host.strip().rstrip('/')
    url = urlsplit(value if '://' in value else 'http://' + value)
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
        raise ValueError('Enter only a hostname, IP, or HTTP(S) origin')
    _ = url.port  # Validate a supplied port.
    return f'{url.scheme}://{url.netloc.lower()}'


class TydomClient:
    def __init__(self, session, host, username='', password=''):
        self.session = session
        self.base_url = normalize_host(host)
        self.auth = aiohttp.BasicAuth(username, password) if username else None
        self.lock = asyncio.Lock()

    async def _get(self, path, params=None):
        async with self.session.get(self.base_url + path, params=params, auth=self.auth,
                                    timeout=aiohttp.ClientTimeout(total=15), allow_redirects=False) as response:
            if response.status in (401, 403):
                raise AuthenticationError('TYDOM authentication rejected')
            # CGI often redirects to a read-only page. Never replay a command.
            if params is not None and response.status in (302, 303):
                return ''
            response.raise_for_status()
            if response.status != 200:
                raise ProtocolError('Unexpected HTTP response')
            return (await response.read()).decode('iso-8859-1')

    async def snapshot(self):
        async with self.lock:
            index = await self._get('/P/index.shtml')
            lights = parse_lights(await self._get('/P/light.shtml'))
            zones, mode = parse_heating(await self._get('/P/therm.shtml'))
            consumption = parse_consumption(await self._get('/P/conso.shtml'))
            return {'temperature': parse_index(index), 'lights': lights,
                    'zones': zones, 'mode': mode, 'consumption': consumption}

    async def send(self, params):
        # COUNT is a changing page token, NOT an operation code. Fetch a fresh
        # token immediately before every command while holding the gateway lock.
        count = params.get('COUNT', '')
        if not isinstance(count, str) or not count.isdigit():
            raise ValueError('Invalid command token')
        keys = set(params)
        if keys == {'COUNT', 'LIGHT', 'V'} and params['LIGHT'] in map(str, range(8)) and params['V'] in ('101', '102'):
            kind, page_path = 'light', '/P/light.shtml'
        elif keys == {'COUNT', 'ZONE', 'ALL'} and params['ZONE'] in map(str, range(8)) and params['ALL'] in ('0', '3'):
            kind, page_path = 'zone', '/P/therm.shtml'
        elif keys == {'COUNT', 'MODE'} and params['MODE'] in ('4', '7'):
            kind, page_path = 'mode', '/P/therm.shtml'
        else:
            raise ValueError('Unsupported TYDOM command')
        async with self.lock:
            source = await self._get(page_path)
            if kind == 'light':
                items = parse_lights(source)
                fresh = items.get(params['LIGHT'], {}).get('commands', {}).get('on' if params['V'] == '101' else 'off')
            else:
                zones, mode = parse_heating(source)
                if kind == 'zone':
                    fresh = zones.get(params['ZONE'], {}).get('commands', {}).get('eco' if params['ALL'] == '0' else 'comfort')
                else:
                    fresh = mode['commands'].get('off' if params['MODE'] == '4' else 'auto')
            if not fresh:
                raise ProtocolError('Command no longer offered by the gateway')
            await self._get('/cgi-bin/Cmd_X2D.cgi', params=fresh)
