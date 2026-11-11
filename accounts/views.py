from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from services.forms import ProviderProfileForm
from services.models import Favorite, ServiceRequest

from .forms import ProfileForm, SignupForm
from .models import User


def signup_choice(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return render(request, "accounts/signup_choice.html")


def signup_customer(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Skill Search, {user.first_name}! Start by searching for a service.")
        return redirect(request.GET.get("next") or "services:search")
    return render(request, "accounts/signup_customer.html", {"form": form})


def signup_provider(request):
    if request.user.is_authenticated:
        return redirect("accounts:become_provider")
    user_form = SignupForm(request.POST or None, prefix="user")
    profile_form = ProviderProfileForm(request.POST or None, request.FILES or None, prefix="profile")
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        with transaction.atomic():
            user = user_form.save(commit=False)
            user.role = User.Role.PROVIDER
            user.phone = user.phone or profile_form.cleaned_data["phone"]
            user.city = user.city or profile_form.cleaned_data["city"]
            user.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
        login(request, user)
        messages.success(request, "Your provider profile was created and sent for verification.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/signup_provider.html", {"user_form": user_form, "profile_form": profile_form})


@login_required
def become_provider(request):
    """Existing customers can also list their own service."""
    if hasattr(request.user, "provider_profile"):
        return redirect("accounts:provider_edit")
    form = ProviderProfileForm(
        request.POST or None, request.FILES or None,
        initial={"phone": request.user.phone, "city": request.user.city, "pincode": request.user.pincode},
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            request.user.role = User.Role.PROVIDER
            request.user.save(update_fields=["role"])
        messages.success(request, "Your provider profile was created and sent for verification.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/provider_form.html", {"form": form, "creating": True})


@login_required
def provider_edit(request):
    profile = getattr(request.user, "provider_profile", None)
    if profile is None:
        return redirect("accounts:become_provider")
    form = ProviderProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Provider profile updated.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/provider_form.html", {"form": form, "creating": False, "profile": profile})


@login_required
def toggle_availability(request):
    profile = getattr(request.user, "provider_profile", None)
    if request.method == "POST" and profile:
        profile.is_available = not profile.is_available
        profile.save(update_fields=["is_available"])
        state = "available for new work" if profile.is_available else "marked as busy"
        messages.info(request, f"You are now {state}.")
    return redirect("accounts:dashboard")


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/profile_form.html", {"form": form})


@login_required
def dashboard(request):
    user = request.user
    profile = getattr(user, "provider_profile", None)
    my_requests = (ServiceRequest.objects.filter(customer=user)
                   .select_related("provider__user", "provider__category", "review"))
    context = {
        "profile": profile,
        "my_requests": my_requests[:20],
        "favorites": Favorite.objects.filter(user=user).select_related("provider__user", "provider__category")[:12],
        "conversations": user.conversations.select_related("provider__user")[:5],
    }
    if profile:
        incoming = profile.requests.select_related("customer")
        context.update({
            "incoming": incoming[:30],
            "stats": {
                "pending": incoming.filter(status=ServiceRequest.Status.PENDING).count(),
                "accepted": incoming.filter(status=ServiceRequest.Status.ACCEPTED).count(),
                "completed": incoming.filter(status=ServiceRequest.Status.COMPLETED).count(),
                "views": profile.profile_views,
                "rating": profile.rating_avg,
                "reviews": profile.rating_count,
                "saved": profile.favorited_by.count(),
            },
            "provider_conversations": profile.conversations.select_related("customer")[:5],
        })
    return render(request, "accounts/dashboard.html", context)
