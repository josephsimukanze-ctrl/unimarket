from vendors.models import Vendor, VendorStatus, VerificationRequest
from catalogue.models import Category


def pending_verifications(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return {"pending_verifications_total": 0}

    total = (
        Vendor.objects.filter(status=VendorStatus.PENDING).count()
        + Category.objects.filter(is_active=False).count()
        + VerificationRequest.objects.filter(
            status=VerificationRequest.Status.PENDING
        ).count()
    )
    return {"pending_verifications_total": total}