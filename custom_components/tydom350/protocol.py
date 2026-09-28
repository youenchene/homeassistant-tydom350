"""Read the legacy TYDOM 350 HTML protocol. No Home Assistant dependency."""
from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urlsplit


class ProtocolError(ValueError):
    """The gateway returned an unexpected page."""


@dataclass
class Row:
    text: str = ""
    name: str = ""
    images: list = field(default_factory=list)
    links: list = field(default_factory=list)


class Page(HTMLParser):
    """Tolerate the gateway's missing closing tr/td tags."""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = Row()
        self.in_name = False
        self.link = None
        self.feed(source)
        self.flush()

    def flush(self):
        if self.row.text.strip() or self.row.links or self.row.images:
            self.rows.append(self.row)
        self.row = Row()
        self.in_name = False
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.flush()
        elif tag == 'td':
            self.row.text += ' '
            self.in_name = 'middle' in attrs.get('class', '').split()
        elif tag == 'a':
            self.link = attrs.get('href', '')
        elif tag == 'img':
            image = attrs.get('src', '').rsplit('/', 1)[-1]
            self.row.images.append(image)
            if self.link:
                self.row.links.append((self.link, image))

    def handle_endtag(self, tag):
        if tag == 'tr':
            self.flush()
        elif tag == 'td':
            self.in_name = False
        elif tag == 'a':
            self.link = None

    def handle_data(self, data):
        self.row.text += data
        if self.in_name:
            self.row.name += data


def page(source):
    if not re.search(r'<title>\s*TYDOM 350\s*</title>', source, re.I):
        raise ProtocolError('Not a TYDOM 350 page (authentication or unsupported firmware)')
    if not re.search(r'id=[\"\']data[\"\']', source, re.I):
        raise ProtocolError('Missing TYDOM data table')
    return Page(source)


def command(href):
    """Only accept local, single-valued command parameters."""
    url = urlsplit(href)
    if url.scheme or url.netloc or url.path != '/cgi-bin/Cmd_X2D.cgi' or url.fragment:
        return None
    query = parse_qs(url.query, keep_blank_values=True)
    if any(len(v) != 1 for v in query.values()):
        return None
    return {k: v[0] for k, v in query.items()}


def number(value):
    return float(value.replace('\xa0', '').replace(' ', '').replace(',', '.'))


def parse_index(source):
    for row in page(source).rows:
        if 'temp_int.gif' in row.images:
            match = re.search(r'(-?\d+(?:[.,]\d+)?)\s*°C', row.text)
            return number(match[1]) if match else None
    return None


def parse_lights(source):
    lights = {}
    for row in page(source).rows:
        for href, image in row.links:
            q = command(href)
            if not q or set(q) != {'COUNT', 'LIGHT', 'V'} or not q['COUNT'].isdigit():
                continue
            if not q['LIGHT'].isdigit() or not 0 <= int(q['LIGHT']) <= 7:
                continue
            action = {'101': 'on', '102': 'off'}.get(q['V'])
            if action:
                item = lights.setdefault(q['LIGHT'], {'name': row.name.strip(), 'commands': {}})
                item['commands'][action] = q
    return {k: v for k, v in lights.items() if set(v['commands']) == {'on', 'off'}}


def parse_heating(source):
    zones = {}
    global_mode = {'name': 'Chauffage général', 'state': None, 'commands': {}}
    for row in page(source).rows:
        for href, image in row.links:
            q = command(href)
            if not q:
                continue
            if set(q) == {'COUNT', 'MODE'} and q['COUNT'].isdigit():
                action = {'4': 'off', '7': 'auto'}.get(q['MODE'])
                if action:
                    global_mode['commands'][action] = q
                    if image.endswith('_red.gif'):
                        global_mode['state'] = action
            elif set(q) == {'COUNT', 'ZONE', 'ALL'} and q['COUNT'].isdigit():
                if not q['ZONE'].isdigit() or not 0 <= int(q['ZONE']) <= 7:
                    continue
                action = {'0': 'eco', '3': 'comfort'}.get(q['ALL'])
                if action:
                    item = zones.setdefault(q['ZONE'], {'name': row.name.strip(), 'state': None, 'commands': {}})
                    item['commands'][action] = q
                    if image.endswith('_red.gif'):
                        item['state'] = action
    zones = {k: v for k, v in zones.items() if set(v['commands']) == {'eco', 'comfort'}}
    return zones, global_mode


def parse_consumption(source):
    measures = {}
    # Stable semantic identifiers; French gateway is the verified firmware language.
    labels = {'Totale': 'total', 'Chauffage / Clim': 'heating', 'Autres usages': 'other', 'Production': 'production'}
    for row in page(source).rows:
        key = labels.get(row.name.strip())
        if key:
            match = re.search(r'(-?\d[\d\s\xa0]*(?:[.,]\d+)?)\s*(EUR|€|kWh|Wh)(?!\w)', row.text)
            if match:
                unit = 'EUR' if match[2] == '€' else match[2]
                measures[key] = {'name': row.name.strip(), 'value': number(match[1]), 'unit': unit}
    return measures
