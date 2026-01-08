from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address, get_ipaddr
from starlette.requests import Request

def get_request_identifier(request: Request) -> str:
    """
    Identify user by X-Telegram-User-ID header if available (from Bot),
    otherwise fall back to IP address.
    """
    telegram_user_id = request.headers.get("X-Telegram-User-ID")
    if telegram_user_id:
        return str(telegram_user_id)
        
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
        
    return get_ipaddr(request) or "127.0.0.1"

# Initialize limiter
limiter = Limiter(key_func=get_request_identifier, enabled=True)