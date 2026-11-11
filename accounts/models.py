from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{10,15}$",
    message="Enter a valid phone number (10-15 digits, optional leading +).",
)


class User(AbstractUser):
    """A site user. Every user is a customer; some are also service providers."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        PROVIDER = "provider", "Service provider"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=16, blank=True, validators=[phone_validator])
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    @property
    def is_provider(self):
        return self.role == self.Role.PROVIDER and hasattr(self, "provider_profile")

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        name = self.display_name.split()
        return "".join(part[0] for part in name[:2]).upper()

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    def __str__(self):
        return self.display_name
