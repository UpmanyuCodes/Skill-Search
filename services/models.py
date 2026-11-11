import math

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import phone_validator


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in kilometres."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    icon = models.CharField(max_length=50, default="tools", help_text="Bootstrap icon name, e.g. 'wrench'")
    description = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:category", args=[self.slug])

    def __str__(self):
        return self.name


class ProviderQuerySet(models.QuerySet):
    def verified(self):
        return self.filter(verification_status=ProviderProfile.Verification.VERIFIED, user__is_active=True)


class ProviderProfile(models.Model):
    class Verification(models.TextChoices):
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class RateUnit(models.TextChoices):
        HOUR = "hour", "per hour"
        VISIT = "visit", "per visit"
        DAY = "day", "per day"
        SESSION = "session", "per session"
        MONTH = "month", "per month"

    class IdType(models.TextChoices):
        AADHAAR = "aadhaar", "Aadhaar card"
        PAN = "pan", "PAN card"
        VOTER = "voter", "Voter ID"
        DL = "dl", "Driving licence"
        PASSPORT = "passport", "Passport"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_profile")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="providers")
    headline = models.CharField(max_length=120, help_text="e.g. 'Licensed plumber, 10+ years experience'")
    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=255, blank=True, help_text="Comma separated, e.g. 'leak repair, pipe fitting'")
    languages = models.CharField(max_length=120, blank=True, help_text="Comma separated")
    experience_years = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(60)])
    rate = models.DecimalField(max_digits=8, decimal_places=0, null=True, blank=True)
    rate_unit = models.CharField(max_length=10, choices=RateUnit.choices, default=RateUnit.VISIT)

    # Where they work
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=120, blank=True, help_text="Locality / neighbourhood")
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    service_radius_km = models.PositiveSmallIntegerField(default=10)

    # How to reach them
    phone = models.CharField(max_length=16, validators=[phone_validator])
    whatsapp = models.CharField(max_length=16, blank=True, validators=[phone_validator])
    show_phone = models.BooleanField(default=True, help_text="Show phone/WhatsApp to logged-in users")
    working_hours = models.CharField(max_length=120, blank=True, default="Mon-Sat, 9am - 7pm")

    # Service options
    is_available = models.BooleanField(default=True, help_text="Currently taking new work")
    home_visit = models.BooleanField(default=True)
    emergency_service = models.BooleanField(default=False, help_text="Available for urgent / late-night jobs")

    # Verification
    verification_status = models.CharField(max_length=10, choices=Verification.choices, default=Verification.PENDING)
    id_type = models.CharField(max_length=10, choices=IdType.choices, blank=True)
    id_number_last4 = models.CharField(max_length=4, blank=True, help_text="Only the last 4 characters are stored")
    id_document = models.FileField(upload_to="verification/", blank=True)
    verification_note = models.CharField(max_length=255, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_test = models.BooleanField(default=False, help_text="Created through the testing tool")

    # Cached stats
    rating_avg = models.FloatField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    profile_views = models.PositiveIntegerField(default=0)
    jobs_completed = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProviderQuerySet.as_manager()

    class Meta:
        ordering = ["-rating_avg", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.user.get_full_name() or self.user.username} {self.category.name}")[:100] or "provider"
            slug, n = base, 2
            while ProviderProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        if self.verification_status == self.Verification.VERIFIED and not self.verified_at:
            self.verified_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:provider_detail", args=[self.slug])

    @property
    def name(self):
        return self.user.display_name

    @property
    def is_verified(self):
        return self.verification_status == self.Verification.VERIFIED

    @property
    def skill_list(self):
        return [s.strip() for s in self.skills.split(",") if s.strip()]

    @property
    def language_list(self):
        return [s.strip() for s in self.languages.split(",") if s.strip()]

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def whatsapp_number(self):
        number = (self.whatsapp or self.phone or "").lstrip("+")
        if len(number) == 10:  # assume India if no country code
            number = "91" + number
        return number

    def distance_to(self, lat, lng):
        return haversine_km(self.latitude, self.longitude, lat, lng)

    def refresh_rating(self):
        agg = self.reviews.aggregate(avg=Avg("rating"), n=Count("id"))
        self.rating_avg = round(agg["avg"] or 0, 2)
        self.rating_count = agg["n"]
        self.jobs_completed = self.requests.filter(status=ServiceRequest.Status.COMPLETED).count()
        self.save(update_fields=["rating_avg", "rating_count", "jobs_completed"])

    def __str__(self):
        return f"{self.name} ({self.category})"


class ServiceRequest(models.Model):
    """A booking request from a customer to a provider."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests")
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name="requests")
    title = models.CharField(max_length=120, help_text="Short summary, e.g. 'Kitchen sink leaking'")
    description = models.TextField(blank=True)
    preferred_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    address = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=16, validators=[phone_validator])
    is_urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    provider_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def can_review(self):
        return self.status == self.Status.COMPLETED and not hasattr(self, "review")

    def __str__(self):
        return f"{self.title} - {self.customer} -> {self.provider.name}"


class Review(models.Model):
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    service_request = models.OneToOneField(
        ServiceRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="review"
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}* for {self.provider.name} by {self.author}"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "provider"], name="unique_favorite")]


class Conversation(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name="conversations")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["customer", "provider"], name="unique_conversation")]

    def get_absolute_url(self):
        return reverse("services:conversation", args=[self.pk])

    def other_party(self, user):
        return self.provider.user if user == self.customer else self.customer

    def includes(self, user):
        return user == self.customer or user == self.provider.user

    def unread_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(max_length=2000)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Report(models.Model):
    class Reason(models.TextChoices):
        FAKE = "fake", "Fake profile / wrong identity"
        FRAUD = "fraud", "Fraud or overcharging"
        BEHAVIOUR = "behaviour", "Rude or unsafe behaviour"
        NO_SHOW = "no_show", "Did not show up"
        OTHER = "other", "Other"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["resolved", "-created_at"]
