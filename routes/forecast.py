"""Authenticated app routes, bound to the public chat present on app entry."""
import hashlib
import hmac
import importlib
import secrets

_context_key = secrets.token_bytes(32)  # ephemeral binding, not authentication
_missing = object()


def _state():
    from core.api_fastapi import get_system
    manager = get_system().llm_chat.session_manager
    chat = manager.get_chat_settings()
    if not isinstance(chat, dict) or not chat or ('private_chat' in chat and not isinstance(chat['private_chat'], bool)):
        raise ValueError('Chat privacy is unavailable')
    effective = getattr(manager, '_effective_chat_name', None)
    name = effective() if callable(effective) else getattr(manager, 'active_chat_name', None)
    if not isinstance(name, str) or not name:
        raise ValueError('Chat identity is unavailable')
    return name, chat.get('private_chat', _missing), chat.get('mode')


def _token(state):
    return hmac.new(_context_key, repr(state).encode('utf-8'), hashlib.sha256).hexdigest()


def _public_state():
    try:
        state = _state()
    except Exception:
        return None, ({'error':'Weather cannot verify chat privacy. Open a public chat and reload Weather.'}, 503)
    if state[1] is True or state[2] == 'limbo':
        return None, ({'error':'Weather uses an external service. Open a public chat and reload Weather.'}, 403)
    # Metadata is authoritative even when settings explicitly say public.
    try:
        from core.api_fastapi import get_system
        manager = get_system().llm_chat.session_manager
        row = next(r for r in manager.list_chat_files() if r.get('name') == state[0])
        if row.get('private_chat') is not False or row.get('vaulted') is not False or row.get('is_active') is not True or _state() != state:
            raise ValueError('Unverified public chat')
    except Exception:
        return None, ({'error':'Weather cannot verify a public chat. Reload Weather from a public chat.'}, 503)
    return state + (False, True), None


def handle_context(**_):
    state, error = _public_state()
    return error if error else {'context':_token(state)}


def handle_forecast(body=None, settings=None, **_):
    state, error = _public_state()
    if error:
        return error
    if not isinstance(body, dict):
        return {'error':'Weather arguments must be an object.'}, 400
    arguments = dict(body)
    context = arguments.pop('_context', '')
    if not isinstance(context, str) or len(context) != 64 or not context.isascii() or not hmac.compare_digest(context, _token(state)):
        return {'error':'Chat changed. Reload Weather from a public chat.'}, 409
    try:
        weather = importlib.import_module('plugins.sapphire-weather.tools.weather')
    except Exception:
        return {'error':'Weather is not loaded. Reload the plugin and try again.'}, 503
    def unchanged():
        try:
            current, error = _public_state()
            return error is None and current == state
        except Exception:
            return False
    try:
        # Recheck before every cache/provider operation and response return.
        with weather.guarded_request(unchanged):
            result = weather.get_weather(arguments, settings)
            if not unchanged():
                raise weather.PrivacyChanged('Chat changed or became private. Reload Weather from a public chat.')
            return {'success':True, 'weather':result}
    except weather.PrivacyChanged as exc:
        return {'error':str(exc)}, 403
    except weather.AmbiguousLocation as exc:
        return {'error':'Which place did you mean?', 'choices':exc.choices}, 409
    except weather.WeatherError as exc:
        return {'error':str(exc)}, 400
    except Exception:
        return {'error':'Weather is unavailable. Please try again.'}, 503
