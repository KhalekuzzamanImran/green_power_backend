from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from apps.api.models import Role, UserProfile


class GreenPowerAdminSite(admin.AdminSite):
    site_header = "Green Power Admin"
    site_title = "Green Power Admin"
    index_title = "Administration"

    def has_permission(self, request):
        user = request.user
        if not user.is_active or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        try:
            return user.profile.role.name == "admin"
        except UserProfile.DoesNotExist:
            return False


admin_site = GreenPowerAdminSite()

class RoleUserCreationForm(UserCreationForm):
    role = forms.ModelChoiceField(queryset=Role.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.all()
        default_role = Role.objects.filter(name="admin").first() or Role.objects.filter(name="user").first()
        if default_role:
            self.fields["role"].initial = default_role


class RoleUserChangeForm(UserChangeForm):
    role = forms.ModelChoiceField(queryset=Role.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.all()
        role = None
        if self.instance and self.instance.pk:
            try:
                role = self.instance.profile.role
            except UserProfile.DoesNotExist:
                role = None
        if role is None and self.instance and self.instance.is_superuser:
            role = Role.objects.filter(name="admin").first()
        if role is None:
            role = Role.objects.filter(name="admin").first() or Role.objects.filter(name="user").first()
        self.fields["role"].initial = role


class RoleUserAdmin(UserAdmin):
    add_form = RoleUserCreationForm
    form = RoleUserChangeForm
    list_display = ("username", "email", "role_name", "is_staff", "is_active")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Permissions", {"fields": ("role", "is_active")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2", "role", "is_active"),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        role = form.cleaned_data.get("role")
        if role is None:
            role = Role.objects.filter(name="user").first()
        if obj.is_superuser:
            role = Role.objects.filter(name="admin").first() or role
        if role and role.name == "admin":
            obj.is_staff = True
        else:
            obj.is_superuser = False
            obj.is_staff = False
        super().save_model(request, obj, form, change)
        if role:
            UserProfile.objects.update_or_create(user=obj, defaults={"role": role})

    def role_name(self, obj):
        try:
            return obj.profile.role.name
        except UserProfile.DoesNotExist:
            return "-"

    role_name.short_description = "role"


User = get_user_model()
admin_site.register(User, RoleUserAdmin)
admin_site.register(Role)
