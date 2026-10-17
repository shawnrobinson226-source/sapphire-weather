# Sapphire Weather

Independent Sapphire plugin for current modelled conditions and one to seven forecast days, including today. No key or additional Python packages are required beyond Sapphire's existing runtime. Version 0.2.0 adds a native visual Weather app alongside the conversational tool. No background tasks, device geolocation, or DES/AXIS/TRI connections.

## Visual dashboard

Open **Apps > Weather** after enabling the plugin. The dashboard presents one prominent current temperature, separate wind/feels-like/precipitation cards, and selectable daily forecast cards. The °F/°C control converts the loaded measurements immediately. The day slider reveals one to seven days without extra provider requests. Selecting a day updates its detail panel; ambiguous cities appear as selectable place buttons. Preferences > Save current view remembers the city, units, and visible forecast length through Sapphire's standard settings API.

The app requests a seven-day snapshot, then filters locally; the conversational tool continues to request the chosen number of days. SVG weather illustrations represent provider condition codes. The dashboard adapts to narrow screens, supports keyboard focus, and honours reduced-motion preferences. It does not invent hourly data or comfort scores.

The app's authenticated POST route checks the active chat's privacy setting server-side, separately from the tool manager's gate. Private or unverifiable chat state refuses before reading forecast caches or making provider calls. The app clears its displayed forecast after a failed request rather than presenting it as current.

## Install

1. Use a disposable Sapphire environment first. This release targets the plugin contracts audited at Sapphire dev commit `70b975bc42675dce51d1563b8b66097307b5d142`; compatibility with older releases is not established.
2. Copy this repository's contents into `user/plugins/sapphire-weather/` so `plugin.json` is directly inside that folder.
3. Enable unsigned community plugins if appropriate for that disposable environment, then enable **Weather** in Settings > Plugins. This package is unsigned.
4. Set a default city with region/country if desired, units, forecast length, timeout, and cache duration. Save Changes. Add `weather_get` to the chat's toolset.
5. Ask “What is the weather in Los Angeles, California?” or “Give me a three-day forecast in imperial units.” If several locations match, choose one; the assistant should call again with its coordinates.

`weather_get` accepts optional `location`, `country_code`, `latitude`, `longitude`, `units` (`metric`/`imperial`), and `days` (1–7). Supply both coordinates together, without a place name/filter. With no location arguments, the saved default city is used. No default city is bundled.

## Privacy, networking, and provider limits

Weather is an external API tool (`is_local: "endpoint"`, `network: true`) and refuses private chats before accessing either the network or cache. All HTTP calls use Sapphire's `core.net`; no direct-network fallback or proxy-setting changes are made. Only fixed HTTPS geocoding and forecast endpoints are used; redirects are refused. Two requests may be needed for a city query. Connection/read timeouts are 2–20 seconds each, not a total wall-clock deadline.

Place searches send the entered place name; forecasts send coordinates to Open-Meteo. Its API privacy terms say server logs may contain coordinates and are deleted after 90 days. The plugin writes no files or request logs. A thread-safe in-memory cache holds at most 64 response entries and is not persisted between processes; responses show their UTC fetch time. Expired responses are not served as fresh during outages. Exact city-name matches are preferred over prefix matches for nearby landmarks; multiple exact city matches still require a choice.

Open-Meteo's keyless free API is for **noncommercial** use, with limits below 10,000 calls/day, 5,000/hour and 600/minute (plus the published monthly allowance). This plugin does not centrally meter shared-IP traffic. Commercial deployment requires a separate provider/access decision; this release has no paid-key support. See [terms](https://open-meteo.com/en/terms), [forecast API](https://open-meteo.com/en/docs), and [geocoding API](https://open-meteo.com/en/docs/geocoding-api).

Every successful result includes Open-Meteo / GeoNames attribution. Weather data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); this does not remove service access restrictions. Results are modelled weather, not verified local station readings. Forecast dates and current timestamps use the provider's location timezone; the provider's ISO timestamps use a fixed UTC offset across the requested range. No hourly DST conversion is attempted. V1 is not an emergency-alert service.

## Tests

From this repository root run `python -m unittest discover -s tests -v`. Tests stub only the external transport/privacy boundary, use no network, and create no persistent user state. Do not add `tests/__init__.py` (Sapphire's plugin collection convention).

Sapphire's root test discovery skips `user/`; run these tests explicitly after installing there. Host integration and bounded live-provider checks are documented in `VALIDATION.md` with their actual results. Passing unit tests alone does not establish a working Sapphire UI installation.

## Remove

Disable Weather, remove it from toolsets, and remove its plugin folder. Sapphire stores saved settings separately at `user/webui/plugins/sapphire-weather.json`; use its settings reset if you want to clear them. The plugin makes no core modifications.
