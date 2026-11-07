from functools import wraps

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import APIToken


def api_auth_required(view_func):
    """Accept either an authenticated session or Authorization: Token <key>."""
    @wraps(view_func)
    @csrf_exempt
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Token "):
            key = auth[6:].strip()
            token = APIToken.objects.filter(key=key).select_related("user").first()
            if token:
                token.last_used_at = timezone.now()
                token.save(update_fields=["last_used_at"])
                request.user = token.user
                return view_func(request, *args, **kwargs)

        return JsonResponse(
            {"error": "Authentication required. Use session or Authorization: Token <key>."},
            status=401,
        )
    return wrapper