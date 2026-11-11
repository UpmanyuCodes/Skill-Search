import datetime
import random

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Category, Conversation, Favorite, ProviderProfile, Report, Review, ServiceRequest, haversine_km
from .search import SearchParams, search_providers
from .testdata import create_test_provider

DELHI = (28.6139, 77.2090)


def make_customer(username="cust", **extra):
    return User.objects.create_user(username=username, email=f"{username}@x.test", password="pass12345!", **extra)


class SearchTests(TestCase):
    def setUp(self):
        rng = random.Random(1)
        self.plumber = Category.objects.get(slug="plumber")
        self.tutor = Category.objects.get(slug="home-tutor")
        self.near = create_test_provider("Near Plumber", self.plumber, city="Delhi", rng=rng)
        self.near.latitude, self.near.longitude = DELHI[0] + 0.01, DELHI[1]
        self.near.save()
        self.far = create_test_provider("Far Plumber", self.plumber, city="Mumbai", rng=rng)
        self.tutor_p = create_test_provider("Maths Teacher", self.tutor, city="Delhi", rng=rng)
        self.pending = create_test_provider("Pending Guy", self.plumber, city="Delhi", rng=rng)
        self.pending.verification_status = ProviderProfile.Verification.PENDING
        self.pending.save()

    def test_haversine(self):
        self.assertAlmostEqual(haversine_km(28.6139, 77.2090, 19.0760, 72.8777), 1148, delta=10)

    def test_category_filter_excludes_unverified(self):
        results, _ = search_providers(SearchParams.from_querydict({"category": "plumber"}))
        self.assertIn(self.near, results)
        self.assertIn(self.far, results)
        self.assertNotIn(self.tutor_p, results)
        self.assertNotIn(self.pending, results)

    def test_location_radius(self):
        results, _ = search_providers(SearchParams.from_querydict(
            {"category": "plumber", "lat": DELHI[0], "lng": DELHI[1], "radius": "5"}))
        self.assertEqual(results, [self.near])
        self.assertLess(results[0].distance, 2)

    def test_city_and_keyword(self):
        results, _ = search_providers(SearchParams.from_querydict({"city": "mumbai"}))
        self.assertEqual(results, [self.far])
        results, _ = search_providers(SearchParams.from_querydict({"q": "maths teacher"}))
        self.assertEqual(results, [self.tutor_p])

    def test_pages_render(self):
        for url in [reverse("services:home"), reverse("services:search") + "?category=plumber&city=Delhi",
                    reverse("services:search") + f"?lat={DELHI[0]}&lng={DELHI[1]}",
                    self.near.get_absolute_url(), reverse("services:how_it_works"),
                    reverse("services:test_tools"), reverse("accounts:signup"),
                    reverse("accounts:signup_customer"), reverse("accounts:signup_provider"),
                    reverse("accounts:login"), reverse("accounts:password_reset"),
                    reverse("services:api_providers") + "?q=plumber", reverse("services:api_categories")]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unverified_profile_hidden(self):
        self.assertEqual(self.client.get(self.pending.get_absolute_url()).status_code, 404)
        self.client.force_login(self.pending.user)
        self.assertEqual(self.client.get(self.pending.get_absolute_url()).status_code, 200)

    def test_contact_details_need_login(self):
        page = self.client.get(self.near.get_absolute_url()).content.decode()
        self.assertNotIn(f"tel:{self.near.phone}", page)
        self.client.force_login(make_customer())
        page = self.client.get(self.near.get_absolute_url()).content.decode()
        self.assertIn(f"tel:{self.near.phone}", page)
        self.assertIn("wa.me/91", page)

    def test_api(self):
        data = self.client.get(reverse("services:api_providers"), {"category": "plumber", "city": "Delhi"}).json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Near Plumber")


class RegistrationTests(TestCase):
    def test_customer_signup(self):
        resp = self.client.post(reverse("accounts:signup_customer"), {
            "first_name": "Asha", "username": "asha", "email": "asha@x.test", "city": "Delhi",
            "password1": "S3cure-pass-99", "password2": "S3cure-pass-99"})
        self.assertRedirects(resp, reverse("services:search"), fetch_redirect_response=False)
        self.assertEqual(User.objects.get(username="asha").role, User.Role.CUSTOMER)

    def _provider_payload(self, **extra):
        data = {
            "user-first_name": "Raju", "user-last_name": "Kumar", "user-username": "raju", "user-email": "raju@x.test",
            "user-password1": "S3cure-pass-99", "user-password2": "S3cure-pass-99",
            "profile-category": Category.objects.get(slug="electrician").pk, "profile-headline": "Electrician",
            "profile-experience_years": 5, "profile-rate": 300, "profile-rate_unit": "visit",
            "profile-city": "Delhi", "profile-service_radius_km": 10, "profile-phone": "9876543210",
            "profile-working_hours": "9-6", "profile-is_available": "on", "profile-show_phone": "on",
        }
        data.update(extra)
        return data

    @override_settings(SKILLSEARCH_TEST_MODE=True)
    def test_provider_signup_test_mode_no_documents(self):
        resp = self.client.post(reverse("accounts:signup_provider"), self._provider_payload())
        self.assertEqual(resp.status_code, 302, resp.context and resp.context["profile_form"].errors)
        profile = ProviderProfile.objects.get(user__username="raju")
        self.assertEqual(profile.verification_status, ProviderProfile.Verification.PENDING)
        self.assertEqual(profile.user.role, User.Role.PROVIDER)

    @override_settings(SKILLSEARCH_TEST_MODE=False)
    def test_provider_signup_requires_documents_in_production(self):
        resp = self.client.post(reverse("accounts:signup_provider"), self._provider_payload())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("id_document", resp.context["profile_form"].errors)
        doc = SimpleUploadedFile("id.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        resp = self.client.post(reverse("accounts:signup_provider"), self._provider_payload(**{
            "profile-id_type": "aadhaar", "profile-id_number": "1234 5678 9012", "profile-id_document": doc}))
        self.assertEqual(resp.status_code, 302)
        profile = ProviderProfile.objects.get(user__username="raju")
        self.assertEqual(profile.id_number_last4, "9012")
        self.assertTrue(profile.id_document)
        # Test tools are disabled in production
        self.assertEqual(self.client.get(reverse("services:test_tools")).status_code, 404)
        profile.id_document.delete()

    @override_settings(SKILLSEARCH_TEST_MODE=True)
    def test_test_tool_creates_verified_providers(self):
        resp = self.client.post(reverse("services:test_tools"), {
            "category": Category.objects.get(slug="plumber").pk, "city": "Lucknow", "count": 3})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ProviderProfile.objects.verified().filter(city="Lucknow", is_test=True).count(), 3)

    def test_login_with_email(self):
        make_customer("bob")
        resp = self.client.post(reverse("accounts:login"), {"username": "bob@x.test", "password": "pass12345!"})
        self.assertEqual(resp.status_code, 302)


class BookingFlowTests(TestCase):
    def setUp(self):
        self.provider = create_test_provider("Pro Plumber", Category.objects.get(slug="plumber"), city="Delhi",
                                             rng=random.Random(3))
        self.customer = make_customer()

    def _book(self):
        self.client.force_login(self.customer)
        return self.client.post(reverse("services:book", args=[self.provider.slug]), {
            "title": "Leaking tap", "preferred_date": (timezone.localdate() + datetime.timedelta(days=1)).isoformat(),
            "address": "12 MG Road", "contact_phone": "9123456789"})

    def test_full_flow(self):
        self.assertRedirects(self._book(), reverse("accounts:dashboard"))
        req = ServiceRequest.objects.get()
        self.assertEqual(req.status, "pending")

        # Customer cannot accept their own request
        resp = self.client.post(reverse("services:update_request", args=[req.pk, "accept"]))
        self.assertEqual(resp.status_code, 403)
        # Review not allowed before completion
        self.client.post(reverse("services:review", args=[req.pk]), {"rating": 5})
        self.assertFalse(Review.objects.exists())

        self.client.force_login(self.provider.user)
        self.assertContains(self.client.get(reverse("accounts:dashboard")), "Leaking tap")
        self.client.post(reverse("services:update_request", args=[req.pk, "accept"]), {"note": "Coming at 10"})
        self.client.post(reverse("services:update_request", args=[req.pk, "complete"]))
        req.refresh_from_db()
        self.assertEqual((req.status, req.provider_note), ("completed", "Coming at 10"))

        self.client.force_login(self.customer)
        resp = self.client.post(reverse("services:review", args=[req.pk]), {"rating": 4, "comment": "Good"})
        self.assertRedirects(resp, self.provider.get_absolute_url(), fetch_redirect_response=False)
        self.provider.refresh_from_db()
        self.assertEqual((self.provider.rating_avg, self.provider.rating_count, self.provider.jobs_completed), (4, 1, 1))
        # Only one review per job
        self.client.post(reverse("services:review", args=[req.pk]), {"rating": 1})
        self.assertEqual(Review.objects.count(), 1)

    def test_past_date_rejected(self):
        self.client.force_login(self.customer)
        self.client.post(reverse("services:book", args=[self.provider.slug]), {
            "title": "x", "preferred_date": "2000-01-01", "address": "a", "contact_phone": "9123456789"})
        self.assertFalse(ServiceRequest.objects.exists())

    def test_cancel(self):
        self._book()
        req = ServiceRequest.objects.get()
        self.client.post(reverse("services:update_request", args=[req.pk, "cancel"]))
        req.refresh_from_db()
        self.assertEqual(req.status, "cancelled")

    def test_messaging_and_privacy(self):
        self.client.force_login(self.customer)
        resp = self.client.get(reverse("services:start_conversation", args=[self.provider.slug]))
        convo = Conversation.objects.get()
        self.assertRedirects(resp, convo.get_absolute_url())
        self.client.post(convo.get_absolute_url(), {"body": "Hello, are you free tomorrow?"})
        self.client.force_login(self.provider.user)
        self.assertContains(self.client.get(reverse("services:home")), 'bg-danger nav-badge">1<')
        self.assertContains(self.client.get(convo.get_absolute_url()), "are you free tomorrow")
        self.client.force_login(make_customer("stranger"))
        self.assertEqual(self.client.get(convo.get_absolute_url()).status_code, 404)

    def test_favorite_and_report(self):
        self.client.force_login(self.customer)
        url = reverse("services:toggle_favorite", args=[self.provider.slug])
        self.assertEqual(self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").json(), {"saved": True})
        self.assertTrue(Favorite.objects.exists())
        self.assertContains(self.client.get(reverse("services:favorites")), "Pro Plumber")
        self.client.post(url)
        self.assertFalse(Favorite.objects.exists())
        self.client.post(reverse("services:report", args=[self.provider.slug]), {"reason": "fraud", "details": "x"})
        self.assertEqual(Report.objects.count(), 1)

    def test_customer_becomes_provider(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("accounts:become_provider")).status_code, 200)
        resp = self.client.post(reverse("accounts:become_provider"), {
            "category": Category.objects.get(slug="home-tutor").pk, "headline": "Maths tutor",
            "experience_years": 3, "rate_unit": "hour", "city": "Delhi", "service_radius_km": 5,
            "phone": "9123456789"})
        self.assertRedirects(resp, reverse("accounts:dashboard"))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, User.Role.PROVIDER)
        self.assertContains(self.client.get(reverse("accounts:dashboard")), "waiting for ID verification")
