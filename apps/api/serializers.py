from django.conf import settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from .roles import resolve_user_roles


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["roles"] = resolve_user_roles(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["roles"] = resolve_user_roles(self.user)
        data["token_type"] = "Bearer"
        data["expires_in"] = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        data["refresh_expires_in"] = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        return data


class RoleTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["token_type"] = "Bearer"
        data["expires_in"] = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        if "refresh" in data:
            data["refresh_expires_in"] = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        return data
