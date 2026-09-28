import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import aiohttp
from aiohttp import web
import pytest
from custom_components.tydom350.api import TydomClient, AuthenticationError, normalize_host
from custom_components.tydom350.protocol import parse_lights, parse_heating, parse_consumption
from custom_components.tydom350.light import TydomLight
from custom_components.tydom350.select import TydomMode
from custom_components.tydom350.sensor import TydomConsumption
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.exceptions import HomeAssistantError

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / 'tests/fixtures' / (name + '.html')).read_text()


@pytest.mark.asyncio
async def test_http_transport_and_command_allowlist():
    seen = []
    async def handler(request):
        seen.append((request.path, dict(request.query)))
        if request.path.endswith('.shtml'):
            name = Path(request.path).stem
            return web.Response(body=source(name).replace('COUNT=12', 'COUNT=987').encode('latin1'), content_type='text/html')
        return web.Response(status=302, headers={'Location': '/P/light.shtml'})
    app = web.Application()
    app.router.add_get('/{tail:.*}', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            client = TydomClient(session, f'127.0.0.1:{port}')
            snapshot = await client.snapshot()
            assert snapshot['temperature'] == 21.5
            assert len(seen) == 4
            await client.send(snapshot['lights']['0']['commands']['on'])
            assert len(seen) == 6  # no redirect replay
            assert seen[-1][1] == {'COUNT':'987', 'LIGHT':'0', 'V':'101'}
            for params in [{'CONSO':'0'}, {'LOCK':'1'}, {'COUNT':'10','MODE':'5'},
                           {'COUNT':'12','LIGHT':'99','V':'101'}]:
                with pytest.raises(ValueError):
                    await client.send(params)
            assert len(seen) == 6
    finally:
        await runner.cleanup()


def coordinator():
    zones, mode = parse_heating(source('therm'))
    c = MagicMock()
    c.client.base_url = 'http://192.0.2.1'
    c.last_update_success = True
    c.data = {'lights':parse_lights(source('light')), 'zones':zones, 'mode':mode,
              'consumption':parse_consumption(source('conso'))}
    c.execute = AsyncMock()
    c.async_request_refresh = AsyncMock()
    return c


@pytest.mark.asyncio
async def test_light_never_claims_verified_state_and_failed_command_does_not_change_it():
    c = coordinator()
    entity = TydomLight(c, SimpleNamespace(entry_id='test'), '0', 'Lampe test')
    entity.async_write_ha_state = MagicMock()
    assert entity.is_on is None
    assert entity.assumed_state
    await entity.async_turn_on()
    assert entity.is_on is True
    c.execute.side_effect = HomeAssistantError('failed')
    with pytest.raises(HomeAssistantError):
        await entity.async_turn_off()
    assert entity.is_on is True
    assert entity.extra_state_attributes['retour_etat_physique'] is False


@pytest.mark.asyncio
async def test_zone_command_has_correct_scope_and_refreshes():
    c = coordinator()
    entity = TydomMode(c, SimpleNamespace(entry_id='test'), '1', 'Zone B')
    assert entity.options == ['Éco', 'Confort']
    assert entity.current_option == 'Éco'
    await entity.async_select_option('Confort')
    c.execute.assert_awaited_once_with({'COUNT':'11','ZONE':'1','ALL':'3'})
    c.async_request_refresh.assert_awaited_once()
    assert not TydomMode(c, SimpleNamespace(entry_id='test'), '2', 'N/A').entity_registry_enabled_default


def test_money_sensor_cannot_masquerade_as_energy():
    c = coordinator()
    sensor = TydomConsumption(c, SimpleNamespace(entry_id='test'), 'heating', c.data['consumption']['heating'])
    assert sensor.native_value == 0
    assert sensor.device_class == SensorDeviceClass.MONETARY
    assert sensor.native_unit_of_measurement == 'EUR'
    assert sensor.state_class is None
    c.data['consumption']['heating']['unit'] = 'kWh'
    assert not sensor.available
    assert sensor.native_value is None


@pytest.mark.parametrize('value', ['http://user:pass@host', 'http://host/path', 'file:///tmp/x', 'http://host?x=1'])
def test_invalid_host(value):
    with pytest.raises(ValueError):
        normalize_host(value)
