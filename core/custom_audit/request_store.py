import contextvars

_current_request = contextvars.ContextVar('current_request', default=None)

def get_current_request():
    return _current_request.get()

def set_current_request(request):
    _current_request.set(request)

def clear_current_request():
    _current_request.set(None)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
