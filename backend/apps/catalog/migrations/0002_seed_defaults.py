"""Seed default categories and Zambian provinces into the database.

Data lives in the DB, not in frontend components. Admins can edit or
deactivate these from /admin/catalog/category/ after this migration runs.
"""
from django.db import migrations


CATEGORIES = [
    ("Electronics", "electronics", "📱", 10),
    ("Fashion", "fashion", "👕", 20),
    ("Home & Furniture", "home-furniture", "🛋️", 30),
    ("Vehicles", "vehicles", "🚗", 40),
    ("Agriculture", "agriculture", "🌾", 50),
    ("Construction", "construction", "🏗️", 60),
    ("Industrial Equipment", "industrial-equipment", "⚙️", 70),
    ("Office Supplies", "office-supplies", "📚", 80),
]

PROVINCES = [
    ("Central", "CE"),
    ("Copperbelt", "CB"),
    ("Eastern", "EA"),
    ("Luapula", "LP"),
    ("Lusaka", "LK"),
    ("Muchinga", "MU"),
    ("Northern", "NO"),
    ("North-Western", "NW"),
    ("Southern", "SO"),
    ("Western", "WE"),
]


def seed(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Province = apps.get_model("catalog", "Province")

    for name, slug, icon, order in CATEGORIES:
        Category.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "icon": icon, "display_order": order, "is_active": True},
        )

    for name, code in PROVINCES:
        Province.objects.get_or_create(
            code=code,
            defaults={"name": name, "country_code": "ZM", "is_active": True},
        )


def unseed(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Province = apps.get_model("catalog", "Province")
    Category.objects.filter(slug__in=[c[1] for c in CATEGORIES]).delete()
    Province.objects.filter(code__in=[p[1] for p in PROVINCES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
