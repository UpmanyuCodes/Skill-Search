from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User

from .forms import MessageForm, ProviderResponseForm, ReportForm, ReviewForm, ServiceRequestForm, TestProviderForm
from .models import Category, Conversation, Favorite, ProviderProfile, Report, ServiceRequest
from .search import SORT_CHOICES, SearchParams, provider_to_dict, search_providers
from .testdata import create_test_provider, ensure_categories


def home(request):
    categories = Category.objects.annotate(
        n=Count("providers", filter=Q(providers__verification_status=ProviderProfile.Verification.VERIFIED))
    )
    top = ProviderProfile.objects.verified().select_related("user", "category").order_by("-rating_avg", "-rating_count")[:6]
    stats = {
        "providers": ProviderProfile.objects.verified().count(),
        "categories": categories.count(),
        "jobs": ServiceRequest.objects.filter(status=ServiceRequest.Status.COMPLETED).count(),
        "customers": User.objects.filter(role=User.Role.CUSTOMER).count(),
    }
    return render(request, "services/home.html", {"categories": categories, "top_providers": top, "stats": stats})


def search(request):
    params = SearchParams.from_querydict(request.GET)
    # Fall back to the logged-in user's saved location / city.
    if not params.has_location and not params.city and request.user.is_authenticated and "city" not in request.GET:
        user = request.user
        if user.has_location:
            params.lat, params.lng = user.latitude, user.longitude
        elif user.city:
            params.city = user.city
    providers, category = search_providers(params)
    page = Paginator(providers, 12).get_page(request.GET.get("page"))
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(request.user.favorites.values_list("provider_id", flat=True))
    map_points = [provider_to_dict(p) for p in page.object_list if p.has_location]
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "services/search.html", {
        "params": params,
        "page": page,
        "total": len(providers),
        "category": category,
        "categories": Category.objects.all(),
        "sort_choices": SORT_CHOICES,
        "favorite_ids": favorite_ids,
        "map_points": map_points,
        "querystring": query.urlencode(),
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    return redirect(f"{reverse('services:search')}?category={category.slug}")


def provider_detail(request, slug):
    provider = get_object_or_404(ProviderProfile.objects.select_related("user", "category"), slug=slug)
    is_owner = request.user.is_authenticated and provider.user_id == request.user.id
    if not provider.is_verified and not (is_owner or request.user.is_staff):
        raise Http404("This provider is not verified yet.")
    if not is_owner:
        ProviderProfile.objects.filter(pk=provider.pk).update(profile_views=F("profile_views") + 1)

    distance = None
    if request.user.is_authenticated and request.user.has_location:
        distance = provider.distance_to(request.user.latitude, request.user.longitude)

    reviews = provider.reviews.select_related("author")[:20]
    rating_breakdown = []
    if provider.rating_count:
        counts = dict(provider.reviews.values_list("rating").annotate(n=Count("id")))
        rating_breakdown = [(star, counts.get(star, 0), round(counts.get(star, 0) * 100 / provider.rating_count))
                            for star in range(5, 0, -1)]
    similar = (ProviderProfile.objects.verified().filter(category=provider.category, city__iexact=provider.city)
               .exclude(pk=provider.pk).select_related("user")[:4])
    initial = {}
    if request.user.is_authenticated:
        initial = {"address": request.user.address, "contact_phone": request.user.phone}
    return render(request, "services/provider_detail.html", {
        "provider": provider,
        "is_owner": is_owner,
        "distance": distance,
        "reviews": reviews,
        "rating_breakdown": rating_breakdown,
        "similar": similar,
        "is_favorite": request.user.is_authenticated and Favorite.objects.filter(user=request.user, provider=provider).exists(),
        "booking_form": ServiceRequestForm(initial=initial),
        "report_form": ReportForm(),
    })


@login_required
@require_POST
def book_provider(request, slug):
    provider = get_object_or_404(ProviderProfile.objects.verified(), slug=slug)
    if provider.user_id == request.user.id:
        messages.error(request, "You can't book yourself.")
        return redirect(provider)
    form = ServiceRequestForm(request.POST)
    if form.is_valid():
        req = form.save(commit=False)
        req.customer = request.user
        req.provider = provider
        req.save()
        # Remember address/phone for next time.
        changed = []
        if not request.user.address:
            request.user.address = req.address
            changed.append("address")
        if not request.user.phone:
            request.user.phone = req.contact_phone
            changed.append("phone")
        if changed:
            request.user.save(update_fields=changed)
        messages.success(request, f"Request sent to {provider.name}. You'll see their response on your dashboard.")
        return redirect("accounts:dashboard")
    for field, errors in form.errors.items():
        messages.error(request, f"{form.fields[field].label if field in form.fields else ''}: {' '.join(errors)}")
    return redirect(f"{provider.get_absolute_url()}#book")


@login_required
@require_POST
def update_request(request, pk, action):
    req = get_object_or_404(ServiceRequest.objects.select_related("provider__user"), pk=pk)
    S = ServiceRequest.Status
    is_provider = req.provider.user_id == request.user.id
    is_customer = req.customer_id == request.user.id
    # action -> (who may do it, allowed current states, new state)
    transitions = {
        "accept": (is_provider, {S.PENDING}, S.ACCEPTED),
        "decline": (is_provider, {S.PENDING, S.ACCEPTED}, S.DECLINED),
        "complete": (is_provider or is_customer, {S.ACCEPTED}, S.COMPLETED),
        "cancel": (is_customer, {S.PENDING, S.ACCEPTED}, S.CANCELLED),
    }
    if action not in transitions:
        raise Http404
    allowed, from_states, new_state = transitions[action]
    if not allowed:
        return HttpResponseForbidden("Not allowed")
    if req.status not in from_states:
        messages.error(request, f"This request is already {req.get_status_display().lower()}.")
        return redirect("accounts:dashboard")
    req.status = new_state
    if is_provider:
        form = ProviderResponseForm(request.POST)
        if form.is_valid() and form.cleaned_data["note"]:
            req.provider_note = form.cleaned_data["note"]
    req.save()
    if new_state == S.COMPLETED:
        req.provider.refresh_rating()
    messages.success(request, f"Request marked as {req.get_status_display().lower()}.")
    return redirect("accounts:dashboard")


@login_required
def review_create(request, pk):
    req = get_object_or_404(ServiceRequest.objects.select_related("provider__user"), pk=pk, customer=request.user)
    if not req.can_review:
        messages.error(request, "You can review a provider once the job is completed (one review per job).")
        return redirect("accounts:dashboard")
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.provider = req.provider
        review.author = request.user
        review.service_request = req
        review.save()
        req.provider.refresh_rating()
        messages.success(request, "Thanks for your review!")
        return redirect(req.provider)
    return render(request, "services/review_form.html", {"form": form, "req": req})


@login_required
@require_POST
def toggle_favorite(request, slug):
    provider = get_object_or_404(ProviderProfile, slug=slug)
    fav, created = Favorite.objects.get_or_create(user=request.user, provider=provider)
    if not created:
        fav.delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": created})
    messages.info(request, "Saved to your list." if created else "Removed from your saved list.")
    return redirect(request.POST.get("next") or provider.get_absolute_url())


@login_required
def favorites(request):
    favs = Favorite.objects.filter(user=request.user).select_related("provider__user", "provider__category")
    return render(request, "services/favorites.html", {
        "favorites": favs, "favorite_ids": {f.provider_id for f in favs}})


@login_required
@require_POST
def report_provider(request, slug):
    provider = get_object_or_404(ProviderProfile, slug=slug)
    form = ReportForm(request.POST)
    if form.is_valid():
        if Report.objects.filter(reporter=request.user, provider=provider, resolved=False).exists():
            messages.info(request, "You already reported this provider. Our team is reviewing it.")
        else:
            report = form.save(commit=False)
            report.reporter = request.user
            report.provider = provider
            report.save()
            messages.success(request, "Thanks. Our team will review this report.")
    return redirect(provider)


# --- Messaging ------------------------------------------------------------

@login_required
def start_conversation(request, slug):
    provider = get_object_or_404(ProviderProfile.objects.verified(), slug=slug)
    if provider.user_id == request.user.id:
        messages.error(request, "That's your own profile.")
        return redirect(provider)
    convo, _ = Conversation.objects.get_or_create(customer=request.user, provider=provider)
    return redirect(convo)


def _user_conversations(user):
    return (Conversation.objects.filter(Q(customer=user) | Q(provider__user=user))
            .select_related("customer", "provider__user", "provider__category")
            .annotate(unread=Count("messages", filter=Q(messages__is_read=False) & ~Q(messages__sender=user))))


@login_required
def inbox(request):
    return render(request, "services/inbox.html", {"conversations": _user_conversations(request.user)})


@login_required
def conversation(request, pk):
    convo = get_object_or_404(Conversation.objects.select_related("customer", "provider__user"), pk=pk)
    if not convo.includes(request.user):
        raise Http404
    form = MessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        msg = form.save(commit=False)
        msg.conversation = convo
        msg.sender = request.user
        msg.save()
        convo.save(update_fields=["updated_at"])
        return redirect(f"{convo.get_absolute_url()}#bottom")
    convo.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return render(request, "services/conversation.html", {
        "convo": convo,
        "other": convo.other_party(request.user),
        "chat_messages": convo.messages.select_related("sender"),
        "form": form,
        "conversations": _user_conversations(request.user)[:15],
    })


# --- Testing tool -----------------------------------------------------------

def test_tools(request):
    """Quickly add verified providers without real documents (test mode only)."""
    if not settings.SKILLSEARCH_TEST_MODE:
        raise Http404
    ensure_categories()
    initial = {}
    if request.user.is_authenticated:
        initial = {"city": request.user.city, "latitude": request.user.latitude, "longitude": request.user.longitude}
    form = TestProviderForm(request.POST or None, initial=initial)
    created = []
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        lat = data["latitude"] if data["near_me"] else None
        lng = data["longitude"] if data["near_me"] else None
        for i in range(data["count"]):
            name = data["full_name"] if data["count"] == 1 else ""
            created.append(create_test_provider(full_name=name, category=data["category"], city=data["city"],
                                                lat=lat, lng=lng))
        messages.success(request, f"Created {len(created)} verified test provider(s). Their password is 'testpass123'.")
    pending = ProviderProfile.objects.filter(verification_status=ProviderProfile.Verification.PENDING).select_related("user", "category")
    recent_tests = ProviderProfile.objects.filter(is_test=True).select_related("user", "category").order_by("-created_at")[:10]
    return render(request, "services/test_tools.html", {
        "form": form, "created": created, "pending": pending, "recent_tests": recent_tests,
    })


@require_POST
def test_verify(request, slug):
    """In test mode anyone can approve a pending provider to skip manual verification."""
    if not settings.SKILLSEARCH_TEST_MODE:
        raise Http404
    provider = get_object_or_404(ProviderProfile, slug=slug)
    provider.verification_status = ProviderProfile.Verification.VERIFIED
    provider.verification_note = "Approved with the testing tool"
    provider.save()
    messages.success(request, f"{provider.name} is now verified and appears in search.")
    return redirect(request.POST.get("next") or "services:test_tools")


# --- Static pages & API ----------------------------------------------------

def how_it_works(request):
    return render(request, "services/how_it_works.html")


@require_GET
def api_providers(request):
    params = SearchParams.from_querydict(request.GET)
    providers, _ = search_providers(params)
    limit_arg = request.GET.get("limit", "50")
    limit = min(int(limit_arg), 100) if limit_arg.isdigit() else 50
    return JsonResponse({
        "count": len(providers),
        "results": [provider_to_dict(p, request) for p in providers[:limit]],
    })


@require_GET
def api_categories(request):
    return JsonResponse({"results": [
        {"name": c.name, "slug": c.slug, "icon": c.icon, "description": c.description}
        for c in Category.objects.all()
    ]})
