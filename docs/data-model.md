# Data Model

This document tracks every database table, its fields, and relationships.
Updated whenever a model is added or changed.

## `accounts.User`

Custom user model. Email is the login identifier; no username field.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key, auto-generated |
| `email` | EmailField | Unique, indexed, lowercased on save |
| `first_name` | CharField(150) | Optional |
| `last_name` | CharField(150) | Optional |
| `phone` | CharField(32) | Optional |
| `password` | CharField(128) | Hashed by Django (`pbkdf2`) |
| `is_active` | Boolean | Default `True` |
| `is_staff` | Boolean | Default `False` — grants admin access |
| `is_superuser` | Boolean | From `PermissionsMixin` |
| `date_joined` | DateTime | Default `now()` |
| `last_login` | DateTime | From `AbstractBaseUser`, nullable |
| `groups` | M2M → `auth.Group` | From `PermissionsMixin` |
| `user_permissions` | M2M → `auth.Permission` | From `PermissionsMixin` |

`USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`.

## `auth.Group`, `auth.Permission`, `django_admin_log`, `django_content_type`

Standard Django tables. Present but not yet used by business logic — will be
used for role-based permissions in Phase 7.

## `django_migrations`

Django's migration tracker.

## `django_session`

Used only for Django admin sessions. API auth uses JWT, not sessions.

---

## Planned (not yet implemented)

- `catalog.Category` — Phase 6.5
- `catalog.Product` — Phase 8
- `catalog.ProductVariant` — Phase 8
- `catalog.CategoryAttribute` — Phase 8
- `orders.Cart`, `orders.Order`, `orders.OrderItem` — Phase 9
- `payments.Payment`, `payments.LedgerEntry` — Phase 10
- `auctions.Auction`, `auctions.Bid` — Phase 11
- `rfq.RFQ`, `rfq.Quotation` — Phase 12
- `inventory.StockMovement` — Phase 13
- `messaging.Conversation`, `messaging.Message` — Phase 14
