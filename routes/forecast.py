"""Authenticated app route. The host supplies auth/CSRF and rate limits."""
import importlib


def handle_forecast(body=None, settings=None, **_):
    # HTTP app requests are outside the tool manager's private-chat gate.
    # Read the active chat from the host; never trust a browser privacy flag.
    try:
        from core.api_fastapi import get_system
        chat = get_system().llm_chat.session_manager.get_chat_settings()
        if not isinstance(chat, dict) or not isinstance(chat.get('private_chat', False), bool):
            raise ValueError('No chat settings')
    except Exception:
        return {'error': 'Weather cannot verify chat privacy. Open a public chat and try again.'}, 503
    if chat.get('private_chat', False):
        return {'error': 'Weather uses an external service. Switch to a public chat to check the forecast.'}, 403
    weather = importlib.import_module('plugins.sapphire-weather.tools.weather')
    try:
        return {'success': True, 'weather': weather.get_weather(body, settings)}
    except weather.AmbiguousLocation as exc:
        return {'error': 'Which place did you mean?', 'choices': exc.choices}, 409
    except weather.WeatherError as exc:
        return {'error': str(exc)}, 400
    except Exception:
        return {'error': 'Weather is unavailable. Please try again.'}, 503
