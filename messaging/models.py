import uuid

from django.conf import settings
from django.db import models


class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=255, blank=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="threads"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.subject or f"Thread {self.id.hex[:8]}"

    # ── Convenience ─────────────────────────────────────
    @property
    def last_message(self):
        """Most recent message — use with `.prefetch_related('messages')`."""
        return self.messages.order_by("-created_at").first()

    def other_participant(self, user):
        """The other party in a 1-to-1 thread."""
        return self.participants.exclude(pk=user.pk).first()

    def unread_count_for(self, user) -> int:
        """Messages in this thread not yet read by `user`, excluding own messages."""
        return (
            self.messages
            .filter(read_at__isnull=True)
            .exclude(sender=user)
            .count()
        )


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(blank=True)   # ← allow body-less messages (files only)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["thread", "created_at"])]

    def __str__(self) -> str:
        return f"{self.sender} @ {self.created_at:%Y-%m-%d %H:%M}"

    # ── Convenience ─────────────────────────────────────
    @property
    def has_attachments(self) -> bool:
        return self.attachments.exists()

    def mark_read(self):
        """Stamp read_at if not already marked."""
        if not self.read_at:
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])


class MessageAttachment(models.Model):
    """A file attached to a message — image, video, or document."""

    class FileType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="messages/%Y/%m/")
    file_type = models.CharField(max_length=20, choices=FileType.choices)
    original_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)  # bytes
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        indexes = [models.Index(fields=["message", "file_type"])]

    def __str__(self) -> str:
        return self.original_name or self.file.name

    # ── Convenience ─────────────────────────────────────
    @property
    def is_image(self) -> bool:
        return self.file_type == self.FileType.IMAGE

    @property
    def is_video(self) -> bool:
        return self.file_type == self.FileType.VIDEO

    @property
    def is_document(self) -> bool:
        return self.file_type == self.FileType.DOCUMENT

    @property
    def size_display(self) -> str:
        """Human-readable file size: '2.4 MB', '128 KB', '512 B'."""
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    @classmethod
    def detect_type(cls, content_type: str) -> str:
        """Map MIME type → FileType value."""
        if content_type.startswith("image/"):
            return cls.FileType.IMAGE
        if content_type.startswith("video/"):
            return cls.FileType.VIDEO
        return cls.FileType.DOCUMENT