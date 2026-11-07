from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Notification
from .services import mark_all_read

@login_required
def notification_list(request):
    from django.utils import timezone

    base_qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")

    unread_count = base_qs.filter(read_at__isnull=True).count()

    filter_param = request.GET.get("filter", "").strip()
    if filter_param == "unread":
        notifications = base_qs.filter(read_at__isnull=True)
    elif filter_param == "read":
        notifications = base_qs.filter(read_at__isnull=False)
    else:
        notifications = base_qs

    # Limit to most recent 100
    notifications = notifications[:100]

    return render(
        request,
        "notifications/list.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )

@login_required
def notification_open(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.read_at:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    if notification.url:
        return redirect(notification.url)
    return redirect("notifications:list")


@login_required
def notification_mark_all_read(request):
    if request.method == "POST":
        count = mark_all_read(request.user)
        messages.success(request, f"Marked {count} notification(s) as read.")
    return redirect("notifications:list")