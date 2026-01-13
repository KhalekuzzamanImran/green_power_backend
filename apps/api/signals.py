from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=get_user_model())
def ensure_superuser_role(sender, instance, created, **kwargs):
    if not instance.is_superuser:
        return

    Role = apps.get_model("api", "Role")
    UserProfile = apps.get_model("api", "UserProfile")
    admin_role, _ = Role.objects.get_or_create(name="admin")

    profile, _ = UserProfile.objects.get_or_create(user=instance, defaults={"role": admin_role})
    if profile.role_id != admin_role.id:
        profile.role = admin_role
        profile.save(update_fields=["role"])
