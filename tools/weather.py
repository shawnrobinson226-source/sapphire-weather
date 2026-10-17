"""Independent Sapphire weather tool. No network or file access at import time."""
import json
import math
import threading
import time
from datetime import datetime, timezone

ENABLED = True
EMOJI = '🌤️'
TOOL_CATEGORY = 'web'
AVAILABLE_FUNCTIONS = ['weather_get']
TOOLS = [{
    'type': 'function', 'is_local': 'endpoint', 'network': True,
    'function': {
        'name': 'weather_get',
        'description': ('Get current modelled weather and 1–7 forecast days including today. '
                        'Use a city with region/country or coordinates; ask the user to choose '
                        'if several places match. Uses Open-Meteo; unavailable in private chats.'),
        'parameters': {
            'type': 'object', 'additionalProperties': False,
            'properties': {
                'location': {'type': 'string', 'description': 'City, region/country; defaults to the saved location.'},
                'latitude': {'type': 'number', 'minimum': -90, 'maximum': 90},
                'longitude': {'type': 'number', 'minimum': -180, 'maximum': 180},
                'country_code': {'type': 'string', 'description': 'Optional two-letter country filter for city search.'},
                'units': {'type': 'string', 'enum': ['metric', 'imperial']},
                'days': {'type': 'integer', 'minimum': 1, 'maximum': 7}
            }, 'required': []
        }
    }
}]

DEFAULTS = dict(default_location='', units='metric', forecast_days=3,
                timeout_seconds=10, cache_minutes=10)
GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
ATTRIBUTION = ('Weather: Open-Meteo (https://open-meteo.com/), CC BY 4.0 '
               '(https://creativecommons.org/licenses/by/4.0/). '
               'Place names: GeoNames (https://www.geonames.org/).')
MAX_BYTES = 524288
_cache = {}
_lock = threading.RLock()


class WeatherError(Exception):
    pass


def _number(value, name, low, high, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WeatherError(f'{name} must be a number from {low} to {high}.')
    if not math.isfinite(value) or not low <= value <= high or (integer and int(value) != value):
        raise WeatherError(f'{name} must be {"a whole number" if integer else "a number"} from {low} to {high}.')
    return int(value) if integer else float(value)


def _text(value, name, limit=160):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise WeatherError(f'{name} must be plain text, at most {limit} characters.')
    return value.strip()


def _private():
    # Defence in depth: host schemas also refuse endpoint tools in private chats.
    from core.chat.function_manager import scope_private
    return scope_private.get()


def _json(url, params, timeout):
    from core import net
    try:
        response = net.get(url, params=params, timeout=timeout, stream=True, allow_redirects=False)
        try:
            if response.status_code == 429:
                raise WeatherError('Open-Meteo rate limit reached. Please try again later.')
            if response.status_code != 200:
                raise WeatherError(f'Weather provider returned HTTP {response.status_code}. Try again later.')
            body = bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise WeatherError('Weather provider response was too large.')
            data = json.loads(body)
            if not isinstance(data, dict) or data.get('error'):
                raise WeatherError('Weather provider returned an invalid response.')
            return data
        finally:
            response.close()
    except WeatherError:
        raise
    except Exception:
        # Do not expose request URLs, proxy credentials, or provider response text.
        raise WeatherError('Weather request failed or timed out. Check connectivity/proxy and try again.') from None


def _cached(key, ttl, fetch):
    # Serialise bounded requests to avoid concurrent duplicate bursts. Memory only.
    with _lock:
        now = time.monotonic()
        for old in list(_cache):
            if now - _cache[old][0] >= ttl:
                del _cache[old]
        if key in _cache:
            return _cache[key][1], _cache[key][2], True
        value = fetch()
        stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        if len(_cache) >= 64:
            del _cache[min(_cache, key=lambda k: _cache[k][0])]
        _cache[key] = (time.monotonic(), value, stamp)
        return value, stamp, False


def _place(arguments, settings, timeout, ttl):
    lat, lon = arguments.get('latitude'), arguments.get('longitude')
    if lat is not None or lon is not None:
        if lat is None or lon is None:
            raise WeatherError('Supply both latitude and longitude.')
        if arguments.get('location') or arguments.get('country_code'):
            raise WeatherError('Use either a place name/country filter or coordinates, not both.')
        lat = _number(lat, 'Latitude', -90, 90)
        lon = _number(lon, 'Longitude', -180, 180)
        return lat, lon, f'{lat:.4f}, {lon:.4f}'
    name = _text(arguments.get('location', settings['default_location']), 'Location')
    if len(name) < 2:
        raise WeatherError('Provide a city with region/country, coordinates, or a default location in Weather settings.')
    country = _text(arguments.get('country_code', ''), 'Country code', 2).upper()
    if country and (len(country) != 2 or not country.isascii() or not country.isalpha()):
        raise WeatherError('Country code must contain two letters, such as US or GB.')
    params = dict(name=name, count=5, language='en', format='json')
    if country:
        params['countryCode'] = country
    data, _, _ = _cached(('place', name.casefold(), country), ttl,
                          lambda: _json(GEOCODING_URL, params, timeout))
    rows = data.get('results', [])
    if not isinstance(rows, list):
        raise WeatherError('Place search returned an invalid response.')
    if not rows:
        raise WeatherError('No matching place found. Try a city with region/country or coordinates.')
    # The provider uses prefix matching, so a precise city can also return its
    # zoo and neighbourhoods. Prefer exact city-name matches, retaining every
    # exact duplicate so two cities named Springfield still require a choice.
    city = name.split(',', 1)[0].strip().casefold()
    exact = [row for row in rows if isinstance(row, dict)
             and isinstance(row.get('name'), str) and row['name'].strip().casefold() == city]
    if exact:
        rows = exact
    places = {}
    for row in rows:
        if not isinstance(row, dict):
            raise WeatherError('Place search returned an invalid response.')
        la = _number(row.get('latitude'), 'Provider latitude', -90, 90)
        lo = _number(row.get('longitude'), 'Provider longitude', -180, 180)
        label = ', '.join(_text(row[k], 'Provider place name') for k in ('name', 'admin1', 'country') if row.get(k))
        if not label:
            raise WeatherError('Place search returned an unnamed location.')
        places[(la, lo)] = label
    if len(places) != 1:
        options = '\n'.join(f'- {label}: latitude {la}, longitude {lo}' for (la, lo), label in places.items())
        raise WeatherError('Several places match. Ask the user to choose, then call with that pair of coordinates:\n' + options)
    (la, lo), label = next(iter(places.items()))
    return la, lo, label


_CONDITIONS = {
    0: 'Clear', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Fog', 48: 'Depositing rime fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Dense drizzle',
    56: 'Light freezing drizzle', 57: 'Dense freezing drizzle', 61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
    66: 'Light freezing rain', 67: 'Heavy freezing rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow',
    77: 'Snow grains', 80: 'Light rain showers', 81: 'Rain showers', 82: 'Violent rain showers',
    85: 'Light snow showers', 86: 'Heavy snow showers', 95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail', 99: 'Thunderstorm with heavy hail'
}


def _condition(code):
    if code is None:
        return 'Condition unavailable'
    if isinstance(code, bool) or not isinstance(code, (int, float)) or not math.isfinite(code):
        raise WeatherError('Weather provider returned an invalid condition code.')
    return _CONDITIONS.get(code, f'Unknown weather code {code}')


def _value(value, suffix):
    if value is None:
        return 'unavailable'
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise WeatherError('Weather provider returned an invalid measurement.')
    return f'{value:g}{suffix}'


def _render(data, label, units, days, stamp, cached):
    current, daily = data.get('current'), data.get('daily')
    if not isinstance(current, dict) or not isinstance(daily, dict):
        raise WeatherError('Weather provider omitted current conditions or the daily forecast.')
    zone = _text(data.get('timezone', ''), 'Provider timezone', 80)
    if not zone:
        raise WeatherError('Weather provider omitted the timezone.')
    try:
        valid = datetime.fromisoformat(current['time'])
    except (KeyError, ValueError, TypeError):
        raise WeatherError('Weather provider omitted a valid conditions timestamp.') from None
    temp, wind, rain = ('°F', ' mph', ' in') if units == 'imperial' else ('°C', ' km/h', ' mm')
    # Verify the provider honoured the requested units; never mislabel its values.
    expected = {'temperature_2m': temp, 'apparent_temperature': temp,
                'precipitation': 'inch' if units == 'imperial' else 'mm'}
    cu, du = data.get('current_units', {}), data.get('daily_units', {})
    if not isinstance(cu, dict) or not isinstance(du, dict) or any(cu.get(k) != v for k, v in expected.items()):
        raise WeatherError('Weather provider returned unexpected units.')
    wind_labels = ('mp/h', 'mph') if units == 'imperial' else ('km/h',)
    if cu.get('wind_speed_10m') not in wind_labels:
        raise WeatherError('Weather provider returned unexpected wind units.')
    if any(du.get(k) != v for k, v in {'temperature_2m_max': temp, 'temperature_2m_min': temp,
                                      'precipitation_probability_max': '%'}.items()):
        raise WeatherError('Weather provider returned unexpected forecast units.')
    dates = daily.get('time')
    keys = ('weather_code', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_probability_max')
    if not isinstance(dates, list) or len(dates) != days or any(not isinstance(daily.get(k), list) or len(daily[k]) != days for k in keys):
        raise WeatherError('Weather provider returned an incomplete daily forecast.')
    lines = [f'Weather — {label}', f'Current modelled conditions: {valid.isoformat(timespec="minutes")} ({zone}).',
             f'{_condition(current.get("weather_code"))}; temperature {_value(current.get("temperature_2m"), temp)}; '
             f'feels like {_value(current.get("apparent_temperature"), temp)}; '
             f'wind {_value(current.get("wind_speed_10m"), wind)}; '
             f'precipitation {_value(current.get("precipitation"), rain)} over the provider reporting interval.',
             f'Forecast ({days} day(s), including today):']
    previous = None
    for i, date in enumerate(dates):
        try:
            parsed = datetime.strptime(date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise WeatherError('Weather provider returned an invalid forecast date.') from None
        if previous is not None and (parsed - previous).days != 1:
            raise WeatherError('Weather provider returned nonconsecutive forecast dates.')
        if i == 0 and parsed != valid.date():
            raise WeatherError('Weather provider returned inconsistent current and forecast dates.')
        previous = parsed
        probability = daily['precipitation_probability_max'][i]
        if probability is not None:
            _number(probability, 'Provider precipitation probability', 0, 100)
        lines.append(f'{date}: {_condition(daily["weather_code"][i])}; '
                     f'high {_value(daily["temperature_2m_max"][i], temp)}, '
                     f'low {_value(daily["temperature_2m_min"][i], temp)}; '
                     f'rain/snow chance {_value(probability, "%")}.')
    lines.extend([f'{"Cached; fetched" if cached else "Fetched"} {stamp}.', ATTRIBUTION])
    return '\n'.join(lines)


def execute(function_name, arguments, config, plugin_settings=None):
    if function_name != 'weather_get':
        return 'Unknown weather function.', False
    try:
        if _private():
            return 'Weather uses an external API and is unavailable in private chats.', False
        if not isinstance(arguments, dict):
            raise WeatherError('Weather arguments must be an object.')
        allowed = {'location', 'latitude', 'longitude', 'country_code', 'units', 'days'}
        if arguments.keys() - allowed:
            raise WeatherError('Unsupported weather argument.')
        settings = dict(DEFAULTS)
        if plugin_settings is not None:
            if not isinstance(plugin_settings, dict):
                raise WeatherError('Weather settings must be an object.')
            settings.update(plugin_settings)
        units = arguments.get('units', settings['units'])
        if units not in ('metric', 'imperial'):
            raise WeatherError('Units must be metric or imperial.')
        days = _number(arguments.get('days', settings['forecast_days']), 'Forecast days', 1, 7, True)
        timeout = _number(settings['timeout_seconds'], 'Timeout', 2, 20)
        ttl = _number(settings['cache_minutes'], 'Cache minutes', 1, 60) * 60
        la, lo, label = _place(arguments, settings, timeout, ttl)
        params = dict(latitude=la, longitude=lo, timezone='auto', forecast_days=days,
                      current='temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation',
                      daily='weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
                      temperature_unit='fahrenheit' if units == 'imperial' else 'celsius',
                      wind_speed_unit='mph' if units == 'imperial' else 'kmh',
                      precipitation_unit='inch' if units == 'imperial' else 'mm')
        # Validate before caching: malformed responses must not poison the cache.
        def fetch():
            data = _json(FORECAST_URL, params, timeout)
            _render(data, label, units, days, '', False)
            return data
        data, stamp, cached = _cached(('weather', la, lo, units, days), ttl, fetch)
        return _render(data, label, units, days, stamp, cached), True
    except WeatherError as exc:
        return str(exc), False
    except Exception:
        return 'Weather could not run. Check the Sapphire host and Weather settings.', False
