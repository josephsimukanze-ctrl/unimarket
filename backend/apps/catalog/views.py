"""Public catalog endpoints."""
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Province
from .serializers import CategoryPublicSerializer, ProvincePublicSerializer

User = get_user_model()


class CategoryListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        qs = Category.objects.filter(is_active=True, parent__isnull=True)
        return Response(CategoryPublicSerializer(qs, many=True).data)


class ProvinceListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        qs = Province.objects.filter(is_active=True)
        return Response(ProvincePublicSerializer(qs, many=True).data)


class PublicStatsView(APIView):
    """Real marketplace counts for the home page."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "categories": Category.objects.filter(is_active=True).count(),
                "provinces": Province.objects.filter(is_active=True).count(),
                "users": User.objects.count(),
                "sellers": 0,
                "products": 0,
            }
        )
