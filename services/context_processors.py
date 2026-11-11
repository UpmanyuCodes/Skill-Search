from django.conf import settings
from django.db.models import Q

from .models import Message, ServiceRequest


def site_context(request):
    ctx = {"TEST_MODE": settings.SKILLSEARCH_TEST_MODE, "unread_count": 0, "pending_requests": 0}
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        ctx["unread_count"] = (Message.objects.filter(is_read=False)
                               .filter(Q(conversation__customer=user) | Q(conversation__provider__user=user))
                               .exclude(sender=user).count())
        if hasattr(user, "provider_profile"):
            ctx["pending_requests"] = ServiceRequest.objects.filter(
                provider=user.provider_profile, status=ServiceRequest.Status.PENDING).count()
    return ctx
