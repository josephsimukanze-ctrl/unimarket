"""Tests for the register endpoint."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_register_success(client):
    response = client.post(
        reverse("register"),
        {
            "email": "new@example.com",
            "password": "Str0ngPass!2026",
            "password_confirm": "Str0ngPass!2026",
            "first_name": "New",
            "last_name": "User",
        },
        format="json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert "password" not in data
    assert "password_confirm" not in data
    assert User.objects.filter(email="new@example.com").exists()


@pytest.mark.django_db
def test_register_duplicate_email(client):
    User.objects.create_user(email="dup@example.com", password="Str0ngPass!2026")
    response = client.post(
        reverse("register"),
        {
            "email": "dup@example.com",
            "password": "Str0ngPass!2026",
            "password_confirm": "Str0ngPass!2026",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.json()


@pytest.mark.django_db
def test_register_mismatched_passwords(client):
    response = client.post(
        reverse("register"),
        {
            "email": "mismatch@example.com",
            "password": "Str0ngPass!2026",
            "password_confirm": "Different!2026",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "password_confirm" in response.json()


@pytest.mark.django_db
def test_register_weak_password(client):
    response = client.post(
        reverse("register"),
        {
            "email": "weak@example.com",
            "password": "123",
            "password_confirm": "123",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "password" in response.json()
