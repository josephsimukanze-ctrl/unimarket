"""Serializers for public catalog data."""
from rest_framework import serializers

from .models import Category, Province


class CategoryPublicSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "icon", "display_order", "children")

    def get_children(self, obj):
        qs = obj.children.filter(is_active=True).order_by("display_order", "name")
        return [
            {"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon} for c in qs
        ]


class ProvincePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ("id", "name", "code", "country_code")
