from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def user_manager_required(view_func):
    """
    Decorator: allow access only to User Managers, Admins and superusers.
    Redirects to login if anonymous, shows 403 if logged in but unauthorized.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")

        if not request.user.can_manage_users():
            messages.error(request, "You don't have permission to manage users.")
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return _wrapped