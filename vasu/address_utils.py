import json
import re
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / 'data'
INDIA_CATALOG_PATH = DATA_DIR / 'india_address_catalog.json'
DELIVERY_COUNTRY = 'India'
INDIA_PIN_PATTERN = re.compile(r'^[1-9]\d{5}$')

# Approximate India Post circle prefixes used for offline state-aware validation.
INDIA_STATE_PIN_PREFIXES = {
    'Andaman And Nicobar Islands': ('744',),
    'Andhra Pradesh': tuple(str(prefix) for prefix in range(51, 54)),
    'Arunachal Pradesh': ('79',),
    'Assam': ('78',),
    'Bihar': tuple(str(prefix) for prefix in range(80, 86)),
    'Chandigarh': ('160',),
    'Chhattisgarh': ('49',),
    'Dadra And Nagar Haveli And Daman And Diu': ('396',),
    'Delhi': ('11',),
    'Goa': ('403', '404', '405'),
    'Gujarat': tuple(str(prefix) for prefix in range(36, 40)),
    'Haryana': ('12', '13'),
    'Himachal Pradesh': ('17',),
    'Jammu And Kashmir': ('18', '19'),
    'Jharkhand': ('82', '83'),
    'Karnataka': tuple(str(prefix) for prefix in range(56, 60)),
    'Kerala': ('67', '68', '69'),
    'Ladakh': ('194',),
    'Lakshadweep': ('682',),
    'Madhya Pradesh': tuple(str(prefix) for prefix in range(45, 49)),
    'Maharashtra': tuple(str(prefix) for prefix in range(40, 45)),
    'Manipur': ('79',),
    'Meghalaya': ('79',),
    'Mizoram': ('79',),
    'Nagaland': ('79',),
    'Odisha': ('75', '76', '77'),
    'Puducherry': ('605', '609'),
    'Punjab': ('14', '15', '16'),
    'Rajasthan': tuple(str(prefix) for prefix in range(30, 35)),
    'Sikkim': ('737',),
    'Tamil Nadu': tuple(str(prefix) for prefix in range(60, 65)),
    'Telangana': ('50',),
    'Tripura': ('79',),
    'Uttar Pradesh': tuple(str(prefix) for prefix in range(20, 29)),
    'Uttarakhand': ('24', '25', '26', '28'),
    'West Bengal': ('70', '71', '72', '73', '74'),
}


def normalize_location_name(value):
    return ' '.join(str(value or '').strip().split())


@lru_cache(maxsize=1)
def load_india_address_catalog():
    if not INDIA_CATALOG_PATH.exists():
        return {'states': []}

    with INDIA_CATALOG_PATH.open('r', encoding='utf-8') as handle:
        payload = json.load(handle)
    return payload.get(DELIVERY_COUNTRY, {'states': []})


@lru_cache(maxsize=1)
def get_india_address_index():
    catalog = load_india_address_catalog()
    states = catalog.get('states', [])
    state_map = {}
    for entry in states:
        state_name = normalize_location_name(entry.get('name'))
        state_map[state_name] = {
            'districts': [normalize_location_name(item) for item in entry.get('districts', []) if item],
            'cities': [normalize_location_name(item) for item in entry.get('cities', []) if item],
        }
    return state_map


def get_delivery_country_choices():
    return [(DELIVERY_COUNTRY, DELIVERY_COUNTRY)]


def get_address_options(country=DELIVERY_COUNTRY, state=''):
    country = normalize_location_name(country) or DELIVERY_COUNTRY
    supports_cascade = country == DELIVERY_COUNTRY
    states = []
    districts = []
    cities = []

    if supports_cascade:
        state_index = get_india_address_index()
        states = sorted(state_index.keys())
        state_name = normalize_location_name(state)
        state_entry = state_index.get(state_name, {})
        districts = state_entry.get('districts', [])
        cities = state_entry.get('cities', [])

    return {
        'country': country,
        'supports_cascade': supports_cascade,
        'states': states,
        'districts': districts,
        'cities': cities,
    }


def validate_india_address(state, district, city):
    state = normalize_location_name(state)
    district = normalize_location_name(district)
    city = normalize_location_name(city)
    state_index = get_india_address_index()
    state_entry = state_index.get(state)
    if not state_entry:
        return False, 'Please choose a valid state.'
    if district and district not in state_entry['districts']:
        return False, 'Please choose a valid district for the selected state.'
    if city and city not in state_entry['cities']:
        return False, 'Please choose a valid city for the selected state.'
    return True, ''


def validate_postal_code(country, state, postal_code):
    country = normalize_location_name(country)
    state = normalize_location_name(state)
    postal_code = normalize_location_name(postal_code)

    if country != DELIVERY_COUNTRY:
        return False, 'Delivery is currently available only for India.'

    if not INDIA_PIN_PATTERN.fullmatch(postal_code):
        return False, 'Please enter a valid 6-digit Indian PIN code.'

    prefixes = INDIA_STATE_PIN_PREFIXES.get(state)
    if not prefixes:
        return True, 'PIN format looks valid.'

    if any(postal_code.startswith(prefix) for prefix in prefixes):
        return True, 'PIN code looks valid for the selected state.'
    return False, 'This PIN code does not match the selected state.'


def validate_delivery_address(country, state, district, city, postal_code):
    country = normalize_location_name(country)
    if country != DELIVERY_COUNTRY:
        return False, 'Please choose India as the delivery country.'

    is_valid_location, location_message = validate_india_address(state, district, city)
    if not is_valid_location:
        return False, location_message

    is_valid_postal, postal_message = validate_postal_code(country, state, postal_code)
    if not is_valid_postal:
        return False, postal_message

    return True, postal_message
