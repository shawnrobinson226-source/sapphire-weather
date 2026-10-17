import copy
import importlib.util
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('weather_under_test', ROOT / 'tools/weather.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def forecast(days=3, imperial=False):
    t, v, p = ('°F', 'mph', 'inch') if imperial else ('°C', 'km/h', 'mm')
    return {
        'timezone': 'America/Los_Angeles',
        'current': dict(time='2026-10-17T14:00', temperature_2m=21, apparent_temperature=20,
                        weather_code=2, wind_speed_10m=8, precipitation=0),
        'current_units': dict(temperature_2m=t, apparent_temperature=t, wind_speed_10m=v, precipitation=p),
        'daily_units': dict(temperature_2m_max=t, temperature_2m_min=t, precipitation_probability_max='%'),
        'daily': dict(time=[f'2026-10-{17+i}' for i in range(days)], weather_code=[2]*days,
                      temperature_2m_max=[24]*days, temperature_2m_min=[15]*days,
                      precipitation_probability_max=[10]*days)
    }


class Response:
    def __init__(self, data, status=200, raw=None):
        self.status_code = status
        self.body = json.dumps(data).encode() if raw is None else raw
        self.closed = False

    def iter_content(self, size):
        yield self.body

    def close(self):
        self.closed = True


class WeatherTests(unittest.TestCase):
    def setUp(self):
        w._cache.clear()
        self.privacy = patch.object(w, '_private', return_value=False)
        self.privacy.start()
        self.addCleanup(self.privacy.stop)

    def call(self, **arguments):
        return w.execute('weather_get', arguments, None)

    def coordinates(self, **extra):
        return self.call(latitude=34.05, longitude=-118.25, **extra)

    def test_manifest_and_schema_match(self):
        manifest = json.loads((ROOT / 'plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['name'], 'sapphire-weather')
        self.assertEqual(manifest['capabilities']['tools'], ['tools/weather.py'])
        self.assertEqual({r['key']: r['default'] for r in manifest['capabilities']['settings']}, w.DEFAULTS)
        self.assertEqual(w.AVAILABLE_FUNCTIONS, [t['function']['name'] for t in w.TOOLS])
        self.assertEqual(w.TOOLS[0]['is_local'], 'endpoint')
        self.assertTrue(w.TOOLS[0]['network'])
        self.assertFalse(manifest['default_enabled'])

    def test_private_blocks_network_and_warm_cache(self):
        with patch.object(w, '_json', return_value=forecast()) as fetch:
            self.assertTrue(self.coordinates()[1])
            with patch.object(w, '_private', return_value=True):
                message, ok = self.coordinates()
                self.assertFalse(ok)
                self.assertIn('private', message)
            self.assertEqual(fetch.call_count, 1)

    def test_unknown_function_never_accesses_network(self):
        with patch.object(w, '_json') as fetch:
            self.assertFalse(w.execute('wrong', {}, None)[1])
            fetch.assert_not_called()

    def test_metric_success_has_attribution_and_timestamp(self):
        with patch.object(w, '_json', return_value=forecast()) as fetch:
            message, ok = self.coordinates()
            self.assertTrue(ok, message)
            for expected in ('21°C', '8 km/h', '2026-10-17', 'America/Los_Angeles', 'CC BY 4.0', 'GeoNames', 'Fetched'):
                self.assertIn(expected, message)
            params = fetch.call_args.args[1]
            self.assertEqual(params['timezone'], 'auto')
            self.assertEqual(params['forecast_days'], 3)

    def test_saved_settings_and_argument_overrides(self):
        with patch.object(w, '_json', return_value=forecast(1, True)) as fetch:
            result, ok = w.execute('weather_get', dict(latitude=0, longitude=0, days=1), None,
                                   dict(units='imperial', forecast_days=7, timeout_seconds=4))
            self.assertTrue(ok, result)
            self.assertIn('°F', result)
            self.assertEqual(fetch.call_args.args[2], 4)
            self.assertEqual(fetch.call_args.args[1]['precipitation_unit'], 'inch')

    def test_invalid_inputs_never_fetch(self):
        cases = [dict(latitude=91, longitude=0), dict(latitude=0), dict(longitude=0),
                 dict(latitude=True, longitude=0), dict(latitude=float('nan'), longitude=0),
                 dict(latitude=0, longitude=float('inf')), dict(latitude=0, longitude=0, days=0),
                 dict(latitude=0, longitude=0, days=8), dict(latitude=0, longitude=0, days=1.5),
                 dict(latitude=0, longitude=0, days=True), dict(location='a'), dict(location='a\nb'),
                 dict(location='x'*161), dict(location='Paris', country_code='1X'),
                 dict(latitude=0, longitude=0, location='Paris'), dict(units='kelvin'),
                 dict(url='https://example.org'), {}]
        with patch.object(w, '_json') as fetch:
            for args in cases:
                with self.subTest(args=args):
                    self.assertFalse(self.call(**args)[1])
            fetch.assert_not_called()

    def test_live_provider_imperial_wind_label(self):
        data = forecast(3, True)
        data['current_units']['wind_speed_10m'] = 'mp/h'
        with patch.object(w, '_json', return_value=data):
            message, ok = self.coordinates(units='imperial')
            self.assertTrue(ok, message)
            self.assertIn('8 mph', message)

    def test_invalid_settings_never_fetch(self):
        for settings in (dict(timeout_seconds=0), dict(timeout_seconds=21), dict(cache_minutes=0),
                         dict(forecast_days=2.5), dict(units=[]), ['bad']):
            with self.subTest(settings=settings), patch.object(w, '_json') as fetch:
                self.assertFalse(w.execute('weather_get', dict(latitude=0, longitude=0), None, settings)[1])
                fetch.assert_not_called()

    def test_default_city_and_country_filter(self):
        place = dict(results=[dict(name='Los Angeles', admin1='California', country='United States',
                                   latitude=34.05, longitude=-118.25)])
        with patch.object(w, '_json', side_effect=[place, forecast()]) as fetch:
            message, ok = w.execute('weather_get', dict(country_code='us'), None,
                                    dict(default_location='Los Angeles, California'))
            self.assertTrue(ok, message)
            self.assertIn('Los Angeles, California', message)
            self.assertEqual(fetch.call_args_list[0].args[1]['countryCode'], 'US')

    def test_ambiguous_city_does_not_fetch_weather(self):
        rows = [dict(name='Springfield', latitude=40+i, longitude=-90) for i in range(2)]
        with patch.object(w, '_json', return_value=dict(results=rows)) as fetch:
            message, ok = self.call(location='Springfield')
            self.assertFalse(ok)
            self.assertIn('Ask the user to choose', message)
            self.assertEqual(fetch.call_count, 1)

    def test_exact_city_preferred_over_prefix_landmarks(self):
        rows = [dict(name='Los Angeles Zoo', latitude=34.14, longitude=-118.28),
                dict(name='Los Angeles', latitude=34.05, longitude=-118.25)]
        with patch.object(w, '_json', side_effect=[dict(results=rows), forecast()]) as fetch:
            message, ok = self.call(location='Los Angeles, California', country_code='US')
            self.assertTrue(ok, message)
            self.assertEqual(fetch.call_args.args[1]['latitude'], 34.05)

    def test_no_geocoding_results_and_malformed_results(self):
        for data in ({}, dict(results=[]), dict(results='bad'), dict(results=[{}]), dict(results=[None])):
            w._cache.clear()
            with self.subTest(data=data), patch.object(w, '_json', return_value=data):
                self.assertFalse(self.call(location='Nowhere')[1])

    def test_cache_hit_expiry_and_units_separation(self):
        with patch.object(w, '_json', return_value=forecast()) as fetch, patch.object(w.time, 'monotonic', return_value=100):
            self.assertTrue(self.coordinates()[1])
            message, ok = self.coordinates()
            self.assertTrue(ok)
            self.assertIn('Cached; fetched', message)
            self.assertEqual(fetch.call_count, 1)
        with patch.object(w, '_json', return_value=forecast(3, True)) as fetch, patch.object(w.time, 'monotonic', return_value=100):
            self.assertTrue(self.coordinates(units='imperial')[1])
            fetch.assert_called_once()
        with patch.object(w, '_json', return_value=forecast()) as fetch, patch.object(w.time, 'monotonic', return_value=701):
            self.assertTrue(self.coordinates()[1])
            fetch.assert_called_once()

    def test_cache_is_bounded(self):
        for i in range(70):
            w._cached(('test', i), 600, lambda: {'ok': True})
        self.assertEqual(len(w._cache), 64)

    def test_invalid_response_not_cached(self):
        with patch.object(w, '_json', side_effect=[{}, forecast()]) as fetch:
            self.assertFalse(self.coordinates()[1])
            self.assertTrue(self.coordinates()[1])
            self.assertEqual(fetch.call_count, 2)

    def test_missing_measurement_explicitly_unavailable(self):
        data = forecast()
        data['current']['temperature_2m'] = None
        data['daily']['temperature_2m_max'][0] = None
        with patch.object(w, '_json', return_value=data):
            message, ok = self.coordinates()
            self.assertTrue(ok, message)
            self.assertIn('temperature unavailable', message)
            self.assertIn('high unavailable', message)

    def test_malformed_weather_is_rejected(self):
        cases = []
        for path, value in [(('current_units', 'temperature_2m'), '°F'),
                            (('daily_units', 'precipitation_probability_max'), 'bad'),
                            (('current', 'temperature_2m'), 'warm'),
                            (('current', 'time'), 'yesterday'),
                            (('daily', 'time'), ['2026-10-17']),
                            (('daily', 'time'), ['2026-10-17', '2026-10-19', '2026-10-20']),
                            (('daily', 'time'), ['2026-10-18', '2026-10-19', '2026-10-20']),
                            (('daily', 'weather_code'), ['bad']*3),
                            (('daily', 'precipitation_probability_max'), [101]*3)]:
            data = forecast()
            data[path[0]][path[1]] = value
            cases.append(data)
        for data in cases:
            w._cache.clear()
            with self.subTest(data=data), patch.object(w, '_json', return_value=data):
                self.assertFalse(self.coordinates()[1])

    def test_transport_is_fixed_facade_bounded_and_closed(self):
        response = Response({'ok': True})
        net = types.SimpleNamespace(get=unittest.mock.Mock(return_value=response))
        with patch.dict('sys.modules', {'core': types.SimpleNamespace(net=net)}):
            self.assertEqual(w._json(w.FORECAST_URL, {'latitude': 0}, 10), {'ok': True})
        self.assertTrue(response.closed)
        self.assertEqual(net.get.call_args.kwargs,
                         dict(params={'latitude': 0}, timeout=10, stream=True, allow_redirects=False))

    def test_transport_errors_and_size_limit(self):
        for response in [Response({}, 429), Response({}, 503), Response({}, 302),
                         Response({}, raw=b'bad json'), Response([]),
                         Response({'error': True}), Response({}, raw=b'x'*(w.MAX_BYTES+1))]:
            net = types.SimpleNamespace(get=lambda *a, **k: response)
            with self.subTest(status=response.status_code), patch.dict('sys.modules', {'core': types.SimpleNamespace(net=net)}):
                with self.assertRaises(w.WeatherError):
                    w._json(w.FORECAST_URL, {}, 10)
                self.assertTrue(response.closed)

    def test_transport_does_not_leak_exception_details(self):
        net = types.SimpleNamespace(get=unittest.mock.Mock(side_effect=RuntimeError('secret-proxy-password')))
        with patch.dict('sys.modules', {'core': types.SimpleNamespace(net=net)}):
            with self.assertRaises(w.WeatherError) as error:
                w._json(w.FORECAST_URL, {}, 10)
        self.assertNotIn('secret', str(error.exception))


if __name__ == '__main__':
    unittest.main()
