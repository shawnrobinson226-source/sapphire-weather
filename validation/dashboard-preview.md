# Visual dashboard preview — 0.2.0

The dashboard is implemented as a native Sapphire `app/index.js` with scoped CSS and an authenticated plugin forecast route. It shares validation, provider calls, and caching with the conversational `weather_get` tool. It does not parse the text tool result into visual data.

## Verified October 17, 2026

- **24 offline tests passed**, including all original tool tests, structured snapshot fields, the app route's independent privacy checks, and selectable ambiguous places.
- Real plugin loading and static app delivery succeeded in the disposable pinned Sapphire host.
- Browser displayed live Los Angeles weather through the real authenticated plugin route, with current metrics and seven actual daily forecasts.
- °F/°C converted displayed temperatures and wind speeds immediately without a provider request.
- Slider changed visible forecast days from three to seven; day selection updated the detail panel and selected state.
- Preferences saved the city, unit, and horizon through Sapphire's real settings API. Reload restored the saved seven-day view.
- Searching `Springfield` produced five labelled place buttons. Choosing Springfield, Illinois loaded that location's real forecast; the default saved city remained Los Angeles.
- Narrow-screen testing exposed an internal temperature/illustration overflow. Spacing was corrected; measured `scrollWidth` equalled `clientWidth` for the app, top bar, temperature row, and daily-card grid in the narrow layout. The temporary viewport override was reset afterward.
- Four real HTTP checks passed: private chat → 403; unverifiable privacy → 503; missing session CSRF token → 403; unauthenticated request → 401. Unit tests additionally assert privacy refusal occurs before the shared weather helper is called. See `dashboard-http-results.json`.

The preview uses the unmodified Sapphire app loader, asset server, session/CSRF middleware, settings API, and plugin-route dispatcher. Its surrounding preview shell supplies only a minimal public-chat session manager and no model, audio services, or existing user credentials. The shell's simulated-privacy test endpoint is not included in the plugin.

The forecast is rendered from structured provider data. Cards use daily highs/lows and precipitation probabilities; no hourly graph, invented measurements, or artificial comfort score is supplied. SVG condition illustrations are decorative and paired with text. CSS respects reduced motion; keyboard focus is visible and retained when selecting a forecast day.

## Scope and remaining checks

The visual branch is a design preview, separate from the verified original on `main`. It has not been installed into the everyday Sapphire environment. Full assistant/LLM/voice operation, older Sapphire versions, proxy-on live routing, formal accessibility auditing, and every screen size remain unverified. No Sapphire core files or existing DES/AXIS/TRI environments were modified.

The loopback-only preview is intentionally left running for the operator to try. This differs from the earlier installation test, whose temporary server was shut down.

[Dashboard screenshot](dashboard-preview.jpg)
