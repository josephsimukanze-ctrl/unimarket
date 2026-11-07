from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalogue.models import Product

from .forms import MessageForm, StartThreadForm
from .models import Message, MessageAttachment, Thread


# ---------------------------------------------------------------------------
# Inbox
# ---------------------------------------------------------------------------

@login_required
def inbox(request):
    """
    List all threads for the logged-in user.

    One query per table — threads, participants, messages, attachments —
    regardless of how many threads exist.
    """
    threads = (
        Thread.objects
        .filter(participants=request.user)
        .prefetch_related(
            "participants",
            Prefetch(
                "messages",
                queryset=(
                    Message.objects
                    .select_related("sender")
                    .prefetch_related("attachments")
                    .order_by("created_at")
                ),
            ),
        )
        .order_by("-updated_at")
    )

    thread_data = []
    for thread in threads:
        msgs = list(thread.messages.all())   # prefetched, no query
        last_msg = msgs[-1] if msgs else None
        unread = sum(
            1 for m in msgs
            if m.read_at is None and m.sender != request.user
        )
        other = next(
            (p for p in thread.participants.all() if p != request.user),
            None,
        )
        thread_data.append({
            "thread": thread,
            "other": other,
            "last_msg": last_msg,
            "unread": unread,
        })

    return render(request, "messaging/inbox.html", {"thread_data": thread_data})


# ---------------------------------------------------------------------------
# Thread detail
# ---------------------------------------------------------------------------

@login_required
def thread_detail(request, pk):
    thread = get_object_or_404(
        Thread.objects.prefetch_related("participants"),
        pk=pk,
        participants=request.user,
    )

    # Mark messages from others as read (bulk update — 1 query)
    Message.objects.filter(
        thread=thread, read_at__isnull=True
    ).exclude(sender=request.user).update(read_at=timezone.now())

    if request.method == "POST":
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            body = form.cleaned_data.get("body", "").strip()
            files = request.FILES.getlist("attachments")

            if not body and not files:
                messages.error(
                    request,
                    "Message must have text or at least one file.",
                )
            else:
                msg = form.save(commit=False)
                msg.thread = thread
                msg.sender = request.user
                msg.body = body
                msg.save()

                # ── Save all uploaded attachments ──
                for f in files:
                    MessageAttachment.objects.create(
                        message=msg,
                        file=f,
                        file_type=MessageAttachment.detect_type(f.content_type),
                        original_name=f.name,
                        file_size=f.size,
                    )

                thread.save(update_fields=["updated_at"])
                return redirect("messaging:thread_detail", pk=thread.pk)
    else:
        form = MessageForm()

    thread_messages = (
        thread.messages
        .select_related("sender")
        .prefetch_related("attachments")
        .order_by("created_at")
    )

    other = thread.participants.exclude(pk=request.user.pk).first()

    return render(
        request,
        "messaging/thread_detail.html",
        {
            "thread": thread,
            "thread_messages": thread_messages,
            "other": other,
            "form": form,
        },
    )


# ---------------------------------------------------------------------------
# Start a new thread
# ---------------------------------------------------------------------------

@login_required
def start_thread(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    vendor_user = product.store.vendor.user

    if vendor_user == request.user:
        messages.error(
            request,
            "You can't message yourself about your own product.",
        )
        return redirect("catalogue:product_detail", slug=product.slug)

    if request.method == "POST":
        form = StartThreadForm(request.POST, request.FILES)
        if form.is_valid():
            thread = Thread.objects.create(
                subject=(
                    form.cleaned_data.get("subject")
                    or f"About {product.name}"
                )
            )
            thread.participants.add(request.user, vendor_user)

            msg = Message.objects.create(
                thread=thread,
                sender=request.user,
                body=form.cleaned_data.get("body", "").strip(),
            )

            # ── Save all uploaded attachments ──
            for f in request.FILES.getlist("attachments"):
                MessageAttachment.objects.create(
                    message=msg,
                    file=f,
                    file_type=MessageAttachment.detect_type(f.content_type),
                    original_name=f.name,
                    file_size=f.size,
                )

            messages.success(request, "Message sent.")
            return redirect("messaging:thread_detail", pk=thread.pk)
    else:
        form = StartThreadForm(
            initial={"subject": f"About {product.name}"}
        )

    return render(
        request,
        "messaging/start_thread.html",
        {"form": form, "product": product, "vendor_user": vendor_user},
    )