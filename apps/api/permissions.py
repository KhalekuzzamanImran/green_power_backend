from typing import Iterable

from django.conf import settings
from rest_framework.permissions import BasePermission

from .roles import resolve_user_roles


class RoleRequired(BasePermission):
    """
    Require the current user to have one of the view's required roles.
    """

    def has_permission(self, request, view) -> bool:
        required_roles: Iterable[str] | None = getattr(view, "required_roles", None)
        if not required_roles:
            required_roles = getattr(settings, "API_DEFAULT_ROLES", ())
        if not required_roles:
            return True
        user_roles = set(resolve_user_roles(request.user))
        return bool(user_roles.intersection(required_roles))
