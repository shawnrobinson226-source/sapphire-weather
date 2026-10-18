## Latest dashboard review

Version 0.2.1: 30 Python tests, 4 JavaScript tests and 8 actual-host integration assertions passed. See [review follow-up](validation/review-followup.md) for evidence and limits. Earlier results below describe earlier validation stages.

# Weather V1 validation — October 17, 2026

The sections below record the original 0.1.0 validation. For the 0.2.0 visual dashboard preview, see [dashboard validation](validation/dashboard-preview.md): 24 unit tests, four HTTP safeguard checks, and browser interaction checks.

## Result

20 offline unit tests passed. A disposable checkout of `ddxfish/sapphire` dev at `70b975bc42675dce51d1563b8b66097307b5d142` loaded and executed the plugin successfully through its actual `PluginLoader`, `FunctionManager`, and `core.net` implementations. No changes were made to existing Sapphire, DES, AXIS, or TRI checkouts or environments.

## Offline checks

Command from this plugin's root: `python -m unittest discover -s tests -v`.

Observed: 20 tests passed on Python 3.14.7, using the already installed runtime. No packages were installed. The suite covers manifest/schema consistency, input and settings bounds, settings/defaults/overrides, coordinates, exact-city preference, ambiguous and missing places, private-chat refusal before network/cache access, cache hits/expiry/size, provider-unit compatibility, missing measurements, malformed responses/dates, HTTP errors/429/redirect rejection, response-size limits, connection errors, resource closure, and exception redaction.

## Actual host integration

A separate Sapphire clone and scratch profile were used. Only Weather was scanned and enabled; built-in function discovery was skipped. Unsigned sideloading was enabled only in that test process. APPDATA/LOCALAPPDATA and config paths pointed to scratch space, credential environment overrides were removed, and a Python audit hook rejected file writes outside the disposable work directory. The host's unrelated tokenizer warm-up was prevented from downloading its encoding and used its documented character-estimate fallback. No LLM, audio service, web server, production credentials, or AXIS connection was started.

Verified:

- The real loader discovered, verified as unsigned, and loaded Weather without load errors.
- The real function manager registered `weather_get` and selected it via the plugin group.
- Saved imperial units and one forecast day merged with manifest timeout/cache defaults and reached the executor.
- Host private-chat gating refused the external tool before network access, both before and after warming its cache.
- A live imperial coordinate request returned Fahrenheit, miles per hour, and one forecast day.
- A live argument override returned Celsius, kilometres per hour, and three forecast days.
- An identical second request returned the labelled cache result while the network facade was replaced with a test that would fail on any call.
- Live city geocoding selected the exact Los Angeles city over prefix-matched landmarks and returned its forecast.
- Unloading removed `weather_get` from the execution map.

The final host run made four Open-Meteo HTTP requests. Earlier bounded trials exposed a unit-label discrepancy (`mp/h`); it was corrected and regression-tested. The final raw tool results are in `validation/live-host-results.json`. Expected private-chat refusals appear there as `success: false`; the harness asserted those refusals as passing checks.

## Limits

The initial run verified plugin loading, dispatch, privacy gating, saved-settings reads, real networking, and unloading. A subsequent browser installation test also verified the native settings renderer, authenticated save API, page-reload persistence, and live execution using browser-saved settings; see `validation/browser-installation.md`.

An LLM choosing the tool, voice playback, a full Sapphire application startup, proxy-on live routing, image output, commercial provider access, and compatibility with older Sapphire releases remain unverified.

The existing environments were not installed into or started. This is a text-only, unsigned community plugin. Open-Meteo's free service is limited to noncommercial use; provider terms and attribution requirements remain applicable.
