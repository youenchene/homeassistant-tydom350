import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('protocol', ROOT / 'custom_components/tydom350/protocol.py')
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)


def fixture(name):
    return (ROOT / 'tests/fixtures' / (name + '.html')).read_text()


class ProtocolTests(unittest.TestCase):
    def test_gateway_format_temperature(self):
        self.assertEqual(p.parse_index(fixture('index')), 21.5)

    def test_gateway_format_light_commands(self):
        lights = p.parse_lights(fixture('light'))
        self.assertEqual(set(lights), {'0'})
        self.assertEqual(lights['0']['name'], 'Lampe test')
        self.assertEqual(lights['0']['commands']['on'], {'COUNT':'12','LIGHT':'0','V':'101'})
        self.assertNotIn('state', lights['0'])

    def test_malformed_gateway_html_preserves_zone_names(self):
        zones, mode = p.parse_heating(fixture('therm'))
        self.assertEqual([v['name'] for v in zones.values()], ['Zone A', 'Zone B', 'N/A'])
        self.assertEqual([v['state'] for v in zones.values()], ['eco'] * 3)
        self.assertEqual(mode['state'], 'auto')
        self.assertEqual(set(mode['commands']), {'off', 'auto'})
        self.assertEqual(zones['1']['commands']['comfort'], {'COUNT':'11','ZONE':'1','ALL':'3'})

    def test_money_is_not_energy(self):
        heating = p.parse_consumption(fixture('conso'))['heating']
        self.assertEqual(heating['value'], 0)
        self.assertEqual(heating['unit'], 'EUR')

    def test_energy_decimal_and_thousands(self):
        page = fixture('conso').replace('0 EUR', '1 234,5 kWh')
        self.assertEqual(p.parse_consumption(page)['heating']['value'], 1234.5)
        self.assertEqual(p.parse_consumption(page)['heating']['unit'], 'kWh')

    def test_missing_measurement_is_not_zero(self):
        self.assertEqual(p.parse_consumption(fixture('conso').replace('0 EUR', '-- EUR')), {})
        self.assertIsNone(p.parse_index(fixture('index').replace('21,5 °C', '-- °C')))

    def test_changing_page_tokens(self):
        lights = p.parse_lights(fixture('light').replace('COUNT=12', 'COUNT=765'))
        self.assertEqual(lights['0']['commands']['on']['COUNT'], '765')
        zones, mode = p.parse_heating(fixture('therm').replace('COUNT=10', 'COUNT=991').replace('COUNT=11', 'COUNT=992'))
        self.assertEqual(zones['0']['commands']['eco']['COUNT'], '992')
        self.assertEqual(mode['commands']['auto']['COUNT'], '991')

    def test_euro_symbol(self):
        self.assertEqual(p.parse_consumption(fixture('conso').replace('0 EUR', '12,50 €'))['heating']['unit'], 'EUR')

    def test_auth_page_rejected(self):
        with self.assertRaises(p.ProtocolError):
            p.parse_lights('<html>Login</html>')

    def test_only_local_unambiguous_commands(self):
        for href in ['http://evil.test/cgi-bin/Cmd_X2D.cgi?COUNT=12',
                     '/cgi-bin/Chg_Param.cgi?RESET=1',
                     '/cgi-bin/Cmd_X2D.cgi?COUNT=12&COUNT=10']:
            self.assertIsNone(p.command(href))

    def test_global_off_never_becomes_per_zone_off(self):
        zones, _ = p.parse_heating(fixture('therm'))
        self.assertTrue(all(set(v['commands']) == {'eco', 'comfort'} for v in zones.values()))


if __name__ == '__main__':
    unittest.main()
