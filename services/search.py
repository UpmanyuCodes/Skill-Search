"""Provider search shared by the HTML search page and the JSON API."""

from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import Q

from .models import Category, ProviderProfile

SORT_CHOICES = [
    ("best", "Best match"),
    ("distance", "Nearest first"),
    ("rating", "Highest rated"),
    ("price_low", "Price: low to high"),
    ("experience", "Most experienced"),
]


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class SearchParams:
    q: str = ""
    category: str = ""
    city: str = ""
    lat: float | None = None
    lng: float | None = None
    radius: float = 15
    min_rating: float | None = None
    max_price: float | None = None
    available: bool = False
    emergency: bool = False
    home_visit: bool = False
    sort: str = "best"
    errors: list = field(default_factory=list)

    @classmethod
    def from_querydict(cls, data):
        params = cls(
            q=data.get("q", "").strip()[:100],
            category=data.get("category", "").strip(),
            city=data.get("city", "").strip()[:100],
            lat=_float(data.get("lat")),
            lng=_float(data.get("lng")),
            radius=_float(data.get("radius")) or settings.SKILLSEARCH_DEFAULT_RADIUS_KM,
            min_rating=_float(data.get("min_rating")),
            max_price=_float(data.get("max_price")),
            available=data.get("available") == "1",
            emergency=data.get("emergency") == "1",
            home_visit=data.get("home_visit") == "1",
            sort=data.get("sort", "best"),
        )
        if params.lat is not None and not -90 <= params.lat <= 90:
            params.lat = None
        if params.lng is not None and not -180 <= params.lng <= 180:
            params.lng = None
        params.radius = max(1, min(params.radius, 200))
        if params.sort not in dict(SORT_CHOICES):
            params.sort = "best"
        return params

    @property
    def has_location(self):
        return self.lat is not None and self.lng is not None


def search_providers(params):
    """Return a list of verified providers matching ``params``.

    Each provider gets a ``distance`` attribute (km or None). Distance is
    computed in Python with the haversine formula so the project works on
    SQLite without GIS extensions.
    """
    qs = ProviderProfile.objects.verified().select_related("user", "category")

    category = None
    if params.category:
        category = Category.objects.filter(slug=params.category).first()
        if category:
            qs = qs.filter(category=category)

    if params.q:
        words = params.q.split()
        for word in words:
            qs = qs.filter(
                Q(headline__icontains=word) | Q(bio__icontains=word) | Q(skills__icontains=word)
                | Q(category__name__icontains=word) | Q(user__first_name__icontains=word)
                | Q(user__last_name__icontains=word) | Q(area__icontains=word)
            )

    if params.city and not params.has_location:
        qs = qs.filter(Q(city__icontains=params.city) | Q(pincode=params.city) | Q(area__icontains=params.city))
    if params.min_rating:
        qs = qs.filter(rating_avg__gte=params.min_rating)
    if params.max_price:
        qs = qs.filter(Q(rate__lte=params.max_price) | Q(rate__isnull=True))
    if params.available:
        qs = qs.filter(is_available=True)
    if params.emergency:
        qs = qs.filter(emergency_service=True)
    if params.home_visit:
        qs = qs.filter(home_visit=True)

    providers = list(qs)
    for p in providers:
        p.distance = p.distance_to(params.lat, params.lng) if params.has_location else None

    if params.has_location:
        providers = [p for p in providers if p.distance is not None and p.distance <= params.radius]

    def best_key(p):
        # Rating weighted by number of reviews, nudged by proximity and availability.
        score = p.rating_avg * min(p.rating_count, 20) / 20 * 2 + min(p.experience_years, 20) / 10
        if p.is_available:
            score += 1
        if p.distance is not None:
            score -= p.distance / 5
        return -score

    sorters = {
        "best": best_key,
        "distance": lambda p: (p.distance is None, p.distance or 0),
        "rating": lambda p: (-p.rating_avg, -p.rating_count),
        "price_low": lambda p: (p.rate is None, p.rate or 0),
        "experience": lambda p: -p.experience_years,
    }
    providers.sort(key=sorters[params.sort])
    return providers, category


def provider_to_dict(p, request=None):
    data = {
        "name": p.name,
        "slug": p.slug,
        "url": p.get_absolute_url(),
        "category": p.category.name,
        "headline": p.headline,
        "city": p.city,
        "area": p.area,
        "rating": p.rating_avg,
        "reviews": p.rating_count,
        "experience_years": p.experience_years,
        "rate": float(p.rate) if p.rate is not None else None,
        "rate_unit": p.get_rate_unit_display(),
        "available": p.is_available,
        "emergency": p.emergency_service,
        "verified": p.is_verified,
        "lat": p.latitude,
        "lng": p.longitude,
        "distance_km": round(p.distance, 1) if getattr(p, "distance", None) is not None else None,
    }
    if request is not None:
        data["url"] = request.build_absolute_uri(data["url"])
    return data
