"""Tests for login, refresh, and me endpoints."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        email="alice@example.com",
        password="Str0ngPass!2026",
        first_name="Alice",
        last_name="Mulenga",
    )


@pytest.mark.django_db
def test_login_success(client, user):
    response = client.post(
        reverse("login"),
        {"email": "alice@example.com", "password": "Str0ngPass!2026"},
        format="json",
    )
    assert response.status_code == 200
    data = response.json()
    assert "access" in data
    assert "refresh" in data
    assert data["user"]["email"] == "alice@example.com"
    assert "password" not in data["user"]


@pytest.mark.django_db
def test_login_wrong_password(client, user):
    response = client.post(
        reverse("login"),
        {"email": "alice@example.com", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_login_unknown_email(client):
    response = client.post(
        reverse("login"),
        {"email": "nobody@example.com", "password": "Str0ngPass!2026"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_me_requires_auth(client):
    response = client.get(reverse("me"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_user(client, user):
    # Log in to get a token
    login = client.post(
        reverse("login"),
        {"email": "alice@example.com", "password": "Str0ngPass!2026"},
        format="json",
    ).json()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login['access']}")

    response = client.get(reverse("me"))
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["full_name"] == "Alice Mulenga"


@pytest.mark.django_db
def test_refresh_returns_new_access(client, user):
    login = client.post(
        reverse("login"),
        {"email": "alice@example.com", "password": "Str0ngPass!2026"},
        format="json",
    ).json()

    response = client.post(
        reverse("token_refresh"),
        {"refresh": login["refresh"]},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.json()
