"""Core views."""
from datetime import datetime, timezone

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness probe. No authentication required."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):  # noqa: ANN001, ANN201
        return Response(
            {
                "status": "ok",
                "version": "0.1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
