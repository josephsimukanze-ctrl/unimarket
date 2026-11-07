import uuid

import requests
from django.conf import settings
from django.urls import reverse


class PaymentGatewayError(Exception):
    """Raised when the gateway returns an error."""


def _base_url():
    return "https://api.flutterwave.com/v3"


def _headers():
    return {
        "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def is_configured():
    return bool(getattr(settings, "FLW_SECRET_KEY", ""))


def charge_mobile_money(order, phone_number, network):
    """
    Initiate a mobile money charge (MTN or Zamtel only for Zambia).
    Returns dict with tx_ref, status, and message.
    """
    # Normalize network to Flutterwave's expected values
    network_map = {
        "mtn": "MTN",
        "zamtel": "ZAMTEL",
    }
    fw_network = network_map.get(network.lower(), "MTN")

    tx_ref = f"UNI-{order.order_number}-{uuid.uuid4().hex[:8]}"

    payload = {
        "phone_number": phone_number,
        "network": fw_network,
        "amount": float(order.total),
        "currency": order.currency,
        "fullname": order.buyer.get_full_name() or order.buyer.username,
        "email": order.buyer.email,
        "tx_ref": tx_ref,
    }

    r = requests.post(
        f"{_base_url()}/charges?type=mobile_money_zambia",
        json=payload,
        headers=_headers(),
        timeout=30,
    )

    if r.status_code != 200:
        raise PaymentGatewayError(f"Mobile money charge failed ({r.status_code}): {r.text}")

    data = r.json()
    return {
        "tx_ref": tx_ref,
        "status": data.get("data", {}).get("status", "pending"),
        "message": data.get("data", {}).get("processor_response", "Awaiting confirmation"),
    }


def charge_card(order, redirect_url, customer_email, customer_name, customer_phone):
    """
    Initiate a card payment via Flutterwave Standard.
    Returns hosted payment link the user is redirected to.
    """
    tx_ref = f"UNI-{order.order_number}-{uuid.uuid4().hex[:8]}"

    payload = {
        "tx_ref": tx_ref,
        "amount": float(order.total),
        "currency": order.currency,
        "redirect_url": redirect_url,
        "payment_options": "card",
        "customer": {
            "email": customer_email,
            "name": customer_name,
            "phonenumber": customer_phone,
        },
        "customizations": {
            "title": "UniMarket",
            "description": f"Order {order.order_number}",
        },
    }

    r = requests.post(
        f"{_base_url()}/payments",
        json=payload,
        headers=_headers(),
        timeout=30,
    )

    if r.status_code != 200:
        raise PaymentGatewayError(f"Card init failed ({r.status_code}): {r.text}")

    data = r.json()
    return {
        "link": data["data"]["link"],
        "tx_ref": tx_ref,
    }


def verify_transaction(transaction_id):
    """Verify a transaction by Flutterwave's transaction ID."""
    r = requests.get(
        f"{_base_url()}/transactions/{transaction_id}/verify",
        headers=_headers(),
        timeout=30,
    )
    if r.status_code != 200:
        raise PaymentGatewayError(f"Verify failed ({r.status_code}): {r.text}")
    return r.json().get("data", {})