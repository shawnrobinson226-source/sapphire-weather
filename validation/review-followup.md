# Dashboard review follow-up â€” 2026-10-17

Version 0.2.1 remains an unsigned preview on weather-dashboard. Main is unchanged.

Independent Claude review examined the complete 0.2.0 source packet and dashboard screenshot. Its original response is claude-review.md. Review findings were checked against pinned Sapphire dev 70b975bc42675dce51d1563b8b66097307b5d142 rather than accepted without verification.

## Changes and verification

- Public-chat context binding refuses requests after chat switches. Unknown/malformed privacy state and limbo refuse. Ordinary public chats omit private_chat in this host; authoritative active, non-vaulted public metadata verifies that state. Guards recheck state before cache/provider work, while streaming (host checks throttled to 250 ms), and before returning. A request already started while public cannot be unsent; a subsequent privacy change suppresses the result and cache insertion.
- Provider streams have a progress deadline, size cap and resource closure. This is not a strict overall deadline including DNS/connect or waiting for the global cache lock. Requests remain serialized through that lock.
- Date labels follow the location timezone, including midnight/DST boundaries. Fetch date and age are visible; expired or previous-day snapshots are labelled stale. No automatic background provider polling was added.
- Late settings loads cannot overwrite user interaction. Defaults align with manifest metric/three days. Slider value text and non-JSON error handling improved; current precipitation replaces a duplicate low-temperature metric.
- Malformed context tokens, including non-ASCII strings, produce a controlled refusal before import/network work. Cancelled app loads also recheck their lifecycle before dispatch after awaiting context.
- Missing canonical module produces a controlled error. The actual loader and tool executor share that module/cache.

Observed final offline checks: 30 Python tests and 4 JavaScript tests passed. Commands: python -m unittest discover -s tests -v; node --test tests/test_format.mjs.

Eight actual-host integration assertions passed using the real ChatSessionManager, SQLite-backed disposable history, real authenticated HTTP routes, real CSRF session token, and a counting fake provider boundary. See real-session-results.json. They cover public execution/shared tool cache, old public context while a private chat is active, stale context between public chats, a real privacy toggle, in-flight privacy change, limbo refusal and server shutdown. Private/stale gates made zero provider calls. The in-flight test started one call while public and refused its result after the toggle. The temporary integration server stopped; the separate dashboard preview may remain running for operator inspection.

Claude's proposed Springfield refresh defect was not reproduced: a live qualified-city request returned HTTP 200 and the same Springfield, Illinois, United States. See city-refresh-verification.json. The full query already reaches the geocoder; no speculative geocoder rewrite was made.

Source checks confirmed the host dispatches route handlers in worker threads and the real shell exposes its session CSRF meta token. The integration rendered that actual shell and verified the token, rather than relying solely on the preview HTML.

## Remaining limits

Real privacy toggles here used the host's legacy private flag without a configured encryption vault. Vault unlock/lock lifecycle, a full LLM/voice session, proxy-on live routing and older host releases remain unverified. No commercial provider/key, core.images output, background polling or production installation was added. Global request serialization can queue concurrent callers. Existing everyday Sapphire, DES, AXIS and TRI environments were not modified or started.

## Follow-up review closure

Claude's second review found no blockers, retracted its Springfield finding, and recommended readiness after two named fixes. Its unedited response is claude-followup-review.md; it reviewed source and our reported evidence without executing tests.

Both named fixes were then completed: metadata is now required for explicit-false as well as omitted privacy flags, and host guard calls during streaming are limited to once per 250 ms, with separate before/after guards. The deadline remains checked per received byte. Unit coverage now includes a byte-yielding response, deterministic slow-drip deadline/resource closure, throttled guard-call count, explicit-false vaulted metadata, non-active metadata, and malformed context tokens. This is a simulated slow drip, not a measured real timeout test.

The final real-session integration run passed all eight assertions. A further real core.net run with actual real-session metadata guards performed two bounded Open-Meteo requests for the qualified Springfield city and one-day forecast: nine host guard calls total, 1.937 seconds, uncached success at the same city. See live-stream-results.json. This also reconfirms qualified-city handling with the revised transport, rather than relying solely on the earlier preview observation.

Non-gating findings addressed: actual settings fallback and initial controls now agree on metric/three days, stale guidance acknowledges cache expiry, midnight fetch formatting uses hourCycle h23, and a stale/unmounted app does not dispatch after awaiting its context token. Explicit user-saved imperial/seven-day settings still override defaults, as intended. Manual reload is required after a chat-context change. Global-lock queuing and actual encrypted vault lifecycle remain the stated limitations, without claims that those were tested.
