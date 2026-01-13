from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .serializers import RoleTokenObtainPairSerializer, RoleTokenRefreshSerializer


class RoleTokenObtainPairView(TokenObtainPairView):
    serializer_class = RoleTokenObtainPairSerializer
    permission_classes = [AllowAny]


class RoleTokenRefreshView(TokenRefreshView):
    serializer_class = RoleTokenRefreshSerializer
    permission_classes = [AllowAny]


class RoleTokenVerifyView(TokenVerifyView):
    permission_classes = [AllowAny]
