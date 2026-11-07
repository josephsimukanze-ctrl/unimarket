from django.utils import timezone

from .models import Notification


def notify(recipient, title, body="", url="", channel=Notification.Channel.IN_APP):
    """Create a notification. Safe to call from any app."""
    return Notification.objects.create(
        recipient=recipient,
        channel=channel,
        title=title,
        body=body,
        url=url,
    )


def unread_count(user) -> int:
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()


def mark_all_read(user) -> int:
    return Notification.objects.filter(
        recipient=user, read_at__isnull=True
    ).update(read_at=timezone.now())