import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from services.models import ProviderProfile, Review, ServiceRequest
from services.testdata import CITIES, ensure_categories, create_test_provider

COMMENTS = [
    "Came on time and fixed the problem quickly. Highly recommended!",
    "Very professional and polite. Fair price.",
    "Good work, cleaned up after finishing.",
    "Explained everything clearly before starting. Will book again.",
    "Decent service but arrived a bit late.",
    "Excellent! Solved an issue two others couldn't.",
]


class Command(BaseCommand):
    help = "Fill the database with demo customers, verified providers, bookings and reviews."

    def add_arguments(self, parser):
        parser.add_argument("--providers", type=int, default=60)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **opts):
        rng = random.Random(opts["seed"])
        ensure_categories()

        demo, created = User.objects.get_or_create(
            username="demo", defaults={"email": "demo@example.test", "first_name": "Demo", "last_name": "User",
                                       "city": "Delhi", "phone": "9876543210",
                                       "latitude": CITIES["Delhi"][0], "longitude": CITIES["Delhi"][1]})
        if created:
            demo.set_password("demo12345")
            demo.save()

        customers = [demo]
        for i in range(8):
            u, made = User.objects.get_or_create(
                username=f"customer{i + 1}",
                defaults={"email": f"customer{i + 1}@example.test", "first_name": rng.choice(
                    ["Asha", "Ravi", "Nikhil", "Sara", "Tanvi", "Kabir", "Mohit", "Isha"]), "city": "Delhi"})
            if made:
                u.set_password("demo12345")
                u.save()
            customers.append(u)

        cities = list(CITIES)
        new = []
        for i in range(opts["providers"]):
            # Weight towards Delhi so the demo user sees plenty nearby.
            city = "Delhi" if i % 3 == 0 else rng.choice(cities)
            new.append(create_test_provider(city=city, rng=rng))

        for p in new:
            for _ in range(rng.randint(0, 5)):
                customer = rng.choice(customers[1:])
                req = ServiceRequest.objects.create(
                    customer=customer, provider=p, title=f"{p.category.name} needed",
                    description="Demo booking", preferred_date=timezone.localdate() - timedelta(days=rng.randint(1, 90)),
                    address=f"{rng.randint(1, 300)}, {p.area or p.city}", contact_phone="9000000000",
                    status=ServiceRequest.Status.COMPLETED)
                Review.objects.create(provider=p, author=customer, service_request=req,
                                      rating=rng.choices([5, 4, 3, 2], weights=[5, 4, 1, 0.3])[0],
                                      comment=rng.choice(COMMENTS))
            p.refresh_rating()

        # One provider waiting for verification, to show the admin workflow.
        pending = ProviderProfile.objects.filter(verification_status="pending").count()
        if not pending:
            p = create_test_provider(city="Delhi", rng=rng)
            p.verification_status = ProviderProfile.Verification.PENDING
            p.is_test = False
            p.verification_note = ""
            p.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(new)} providers. Log in as demo / demo12345 (customer in Delhi). "
            f"Every provider's password is testpass123."))
