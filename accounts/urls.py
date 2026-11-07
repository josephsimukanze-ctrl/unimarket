from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    CustomLoginView,
    CustomLogoutView,
    RegisterView,
    edit_user,
    manage_users,
    toggle_user_active,
)

app_name = "accounts"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),

    # Password reset — 4 views, each needs a template
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html",
        email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/auth/password-reset/done/",
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html",
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/auth/reset/done/",
    ), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html",
    ), name="password_reset_complete"),

    # ── Manage users (User Manager / Admin only) ────────
    path("manage/", manage_users, name="manage_users"),
    path("manage/<uuid:user_id>/edit/", edit_user, name="edit_user"),
    path("manage/<uuid:user_id>/toggle-active/", toggle_user_active, name="toggle_user_active"),
]