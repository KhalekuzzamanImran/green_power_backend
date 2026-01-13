from typing import List

from django.apps import apps


def resolve_user_roles(user) -> List[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return []

    if getattr(user, "is_superuser", False):
        return ["admin"]

    UserProfile = apps.get_model("api", "UserProfile")
    try:
        role = user.profile.role.name
    except UserProfile.DoesNotExist:
        role = "user"
    return [role]
