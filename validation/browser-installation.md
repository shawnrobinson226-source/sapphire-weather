# Browser installation test — October 17, 2026

**Result: passed within a disposable Sapphire API host.** Plugin source was unchanged from the previously verified V1 implementation.

## Installation and isolation

The plugin was copied into the disposable checkout's standard `user/plugins/sapphire-weather/` directory and loaded by Sapphire's real plugin loader. Only Weather was enabled. The original checkout remained at dev commit `70b975bc42675dce51d1563b8b66097307b5d142` with no tracked source modifications.

Sapphire's actual FastAPI application, session login, CSRF middleware, plugin list/settings endpoints, shared `plugin-settings-renderer.js`, and `plugins-api.js` were used. A labelled test page hosted those settings controls and a button that invoked the real function manager. It was a focused integration page, not the complete Sapphire assistant.

A separate scratch authentication profile and distinct `weather_trial_session` browser cookie were used. A disposable workspace virtual environment supplied Uvicorn 0.54.0, Click 8.5.0, and h11 0.16.0; it reused already installed host libraries read-only. No dependency was installed into the existing Python or Sapphire environments. Tokenizer and font downloads were disabled. The web server bound only to `127.0.0.1:18763`.

## Observed in the browser

1. Logged into the disposable profile using Sapphire's real login flow.
2. Loaded Weather's five settings through Sapphire's actual manifest renderer.
3. Saved test city `Los Angeles, California`, imperial units, three forecast days, a ten-second timeout, and a ten-minute cache through the authenticated, CSRF-protected settings API.
4. Reloaded the browser page and confirmed the saved city, units, and forecast length remained selected. The on-disk plugin settings JSON matched all five fields.
5. Requested weather without location/unit arguments. The saved city was geocoded and the tool returned current modelled conditions plus three forecast days in Fahrenheit and mph, with provider attribution.
6. Selected the private-chat test and requested weather. The real host refused the endpoint tool with `requires network access and is blocked in this private chat`.
7. Cleared the private-chat test and requested again. A labelled cached result returned with the original fetch timestamp.

Evidence:

- [Persisted settings screenshot](browser-settings.png)
- [Successful forecast screenshot](browser-forecast.png)

## Shutdown and limits

The temporary server was stopped after the test. A subsequent socket check confirmed loopback port 18763 refused connections. Existing Sapphire, DES, AXIS, and TRI environments were not started, modified, or installed into.

The login redirect briefly opened Sapphire's normal application shell. Unrelated chat/status/history/TTS routes reported missing-system-component errors because the test deliberately omitted the session manager, model, and audio services. Those errors did not occur on the tested Weather settings/save/execution flow. This test establishes the focused Weather UI/API integration, not a full assistant startup or LLM/voice integration.
