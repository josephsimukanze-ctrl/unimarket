from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.decorators import login_required
from .forms import ProfileForm, RegisterForm, UserEditForm
from .models import UserRole
from .permissions import user_manager_required


User = get_user_model()


# ═══════════════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════════════
class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("dashboards:home")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("dashboards:home")


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("dashboards:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


# ═══════════════════════════════════════════════════════
# Self-service profile (any logged-in user)
# ═══════════════════════════════════════════════════════
@login_required
def profile_view(request):
    """Let the current user edit their own profile + upload an avatar."""
    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(
        request,
        "accounts/profile.html",
        {"form": form},
    )


# ═══════════════════════════════════════════════════════
# User management (User Manager / Admin only)
# ═══════════════════════════════════════════════════════
@user_manager_required
def manage_users(request):
    """List all users with search + role filter."""
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()

    users_qs = (
        User.objects
        .select_related("vendor")
        .order_by("-date_joined")
    )

    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
        )

    if role and role in dict(UserRole.choices):
        users_qs = users_qs.filter(role=role)

    paginator = Paginator(users_qs, 25)
    page = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page": page,
        "users": page.object_list,
        "search_query": q,
        "role_filter": role,
        "roles": UserRole.choices,
        "total_users": users_qs.count(),
    }
    return render(request, "accounts/manage_users.html", context)


@user_manager_required
def edit_user(request, user_id):
    """Edit any user's profile, role, and active status (admin-level)."""
    target = get_object_or_404(User, id=user_id)

    # Safety: a user manager can't edit a superuser unless they are one
    if target.is_superuser and not request.user.is_superuser:
        messages.error(request, "Only superusers can edit superuser accounts.")
        return redirect("accounts:manage_users")

    if request.method == "POST":
        form = UserEditForm(
            request.POST,
            request.FILES,
            instance=target,
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"User “{target.username}” updated.")
            return redirect("accounts:manage_users")
    else:
        form = UserEditForm(instance=target)

    return render(
        request,
        "accounts/edit_user.html",
        {"form": form, "target": target},
    )


@user_manager_required
def toggle_user_active(request, user_id):
    """Quick action: activate / deactivate a user account."""
    if request.method != "POST":
        return redirect("accounts:manage_users")

    target = get_object_or_404(User, id=user_id)

    if target == request.user:
        messages.error(request, "You can't deactivate your own account.")
        return redirect("accounts:manage_users")

    if target.is_superuser and not request.user.is_superuser:
        messages.error(request, "Only superusers can deactivate superuser accounts.")
        return redirect("accounts:manage_users")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])

    state = "activated" if target.is_active else "deactivated"
    messages.success(request, f"User “{target.username}” {state}.")
    return redirect("accounts:manage_users")