from django.core.management.base import BaseCommand

from apps.api.models import Role


DEFAULT_ROLES = ("admin", "user", "viewer")


class Command(BaseCommand):
    help = "Create default roles for the API."

    def handle(self, *args, **options):
        created = []
        for role in DEFAULT_ROLES:
            obj, was_created = Role.objects.get_or_create(name=role)
            if was_created:
                created.append(obj.name)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created roles: {', '.join(created)}"))
        else:
            self.stdout.write("Roles already exist.")
