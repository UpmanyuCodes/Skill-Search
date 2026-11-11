"""Random but realistic data for the testing tool and the demo seed command."""

import random

from django.db import transaction

from accounts.models import User

from .models import Category, ProviderProfile

FIRST_NAMES = ["Ramesh", "Suresh", "Anita", "Priya", "Vikram", "Arjun", "Kavita", "Sunil", "Meena", "Rahul",
               "Pooja", "Imran", "Farah", "Deepak", "Neha", "Amit", "Sanjay", "Lakshmi", "Harpreet", "Joseph",
               "Rohit", "Sneha", "Manoj", "Divya", "Karan", "Ayesha", "Gopal", "Ritu", "Vijay", "Shalini"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Reddy", "Iyer", "Khan", "Das", "Nair",
              "Yadav", "Mehta", "Joshi", "Chauhan", "Mishra", "Pillai", "Fernandes", "Bose", "Rao"]

# name, icon, description, typical skills, (min rate, max rate), rate unit
CATEGORIES = [
    ("Plumber", "droplet", "Leaks, taps, pipes, water tanks and bathroom fittings",
     ["leak repair", "tap fitting", "pipe installation", "water tank cleaning", "drain unclogging",
      "geyser installation"], (200, 600), "visit"),
    ("Electrician", "lightning-charge", "Wiring, switches, fans, lights and appliance installation",
     ["house wiring", "fan installation", "MCB repair", "inverter setup", "light fitting", "short circuit repair"],
     (200, 700), "visit"),
    ("Home Tutor", "book", "School subjects, competitive exams and languages at your home",
     ["maths", "science", "English", "CBSE", "ICSE", "JEE foundation", "spoken English"], (300, 900), "hour"),
    ("Carpenter", "hammer", "Furniture repair, doors, windows and modular work",
     ["furniture repair", "door fitting", "modular kitchen", "bed repair", "polishing"], (300, 900), "visit"),
    ("AC Repair", "snow", "AC service, gas filling and installation",
     ["AC service", "gas refill", "split AC installation", "cooling problem", "window AC"], (400, 1500), "visit"),
    ("Painter", "palette", "Interior and exterior painting, waterproofing",
     ["interior painting", "texture painting", "waterproofing", "wood polish"], (800, 2500), "day"),
    ("House Cleaning", "stars", "Deep cleaning of homes, kitchens and bathrooms",
     ["deep cleaning", "kitchen cleaning", "bathroom cleaning", "sofa shampoo"], (500, 3000), "visit"),
    ("Appliance Repair", "tools", "Washing machine, fridge, microwave and RO repair",
     ["washing machine", "refrigerator", "microwave", "RO purifier", "TV repair"], (250, 800), "visit"),
    ("Mechanic", "gear", "Bike and car repair, servicing at your doorstep",
     ["bike service", "car service", "puncture repair", "battery jumpstart", "oil change"], (200, 1200), "visit"),
    ("Beautician", "scissors", "Salon services at home: hair, makeup, grooming",
     ["haircut", "bridal makeup", "facial", "waxing", "mehendi"], (300, 3000), "session"),
    ("Pest Control", "bug", "Cockroach, termite, bed bug and mosquito control",
     ["cockroach control", "termite treatment", "bed bugs", "mosquito fogging"], (600, 2500), "visit"),
    ("Cook", "egg-fried", "Home cooks for daily meals and parties",
     ["north indian", "south indian", "party cooking", "tiffin", "baking"], (3000, 12000), "month"),
    ("Driver", "car-front", "Personal drivers for daily commute or outstation trips",
     ["city driving", "outstation", "night driving", "automatic cars"], (600, 1200), "day"),
    ("Fitness Trainer", "heart-pulse", "Personal training and yoga at home",
     ["yoga", "weight loss", "strength training", "zumba"], (400, 1500), "session"),
]

# A few Indian cities with a centre point so random providers land in real areas.
CITIES = {
    "Delhi": (28.6139, 77.2090, ["Karol Bagh", "Lajpat Nagar", "Dwarka", "Rohini", "Saket", "Janakpuri"]),
    "Mumbai": (19.0760, 72.8777, ["Andheri", "Bandra", "Dadar", "Powai", "Borivali", "Thane"]),
    "Bengaluru": (12.9716, 77.5946, ["Koramangala", "Indiranagar", "Whitefield", "Jayanagar", "HSR Layout"]),
    "Lucknow": (26.8467, 80.9462, ["Gomti Nagar", "Hazratganj", "Aliganj", "Indira Nagar", "Alambagh"]),
    "Pune": (18.5204, 73.8567, ["Kothrud", "Baner", "Hadapsar", "Wakad", "Viman Nagar"]),
    "Jaipur": (26.9124, 75.7873, ["Malviya Nagar", "Vaishali Nagar", "Mansarovar", "C-Scheme"]),
}

HEADLINES = [
    "{years}+ years of reliable {cat} work",
    "Trusted {cat} serving {area} and nearby",
    "Quick, neat and affordable {cat}",
    "Certified {cat} - same day service",
    "Experienced {cat}, transparent pricing",
]


def ensure_categories():
    created = []
    for order, (name, icon, desc, *_rest) in enumerate(CATEGORIES):
        cat, was_created = Category.objects.get_or_create(
            name=name, defaults={"icon": icon, "description": desc, "order": order}
        )
        if was_created:
            created.append(cat)
    return created


def _category_meta(category):
    for name, _icon, _desc, skills, rate_range, unit in CATEGORIES:
        if name == category.name:
            return skills, rate_range, unit
    return ["general work"], (300, 1000), "visit"


def _unique_username(base):
    base = base.lower().replace(" ", "")[:20] or "provider"
    username, n = base, 1
    while User.objects.filter(username=username).exists():
        n += 1
        username = f"{base}{n}"
    return username


@transaction.atomic
def create_test_provider(full_name="", category=None, city="", lat=None, lng=None, password="testpass123",
                         rng=random):
    """Create a verified provider with plausible data. Returns the profile."""
    ensure_categories()
    category = category or rng.choice(list(Category.objects.all()))
    if not full_name:
        full_name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    first, _, last = full_name.partition(" ")

    if lat is not None and lng is not None:
        # Scatter within ~6 km of the given point.
        lat = lat + rng.uniform(-0.05, 0.05)
        lng = lng + rng.uniform(-0.05, 0.05)
        city = city or "Nearby"
        area = rng.choice(["Sector " + str(rng.randint(1, 60)), "Main Market", "Civil Lines", "Old City"])
    else:
        if city and city.title() in CITIES:
            city = city.title()
        if city not in CITIES and not city:
            city = rng.choice(list(CITIES))
        centre = CITIES.get(city)
        if centre:
            lat = centre[0] + rng.uniform(-0.08, 0.08)
            lng = centre[1] + rng.uniform(-0.08, 0.08)
            area = rng.choice(centre[2])
        else:
            area = ""

    skills, (low, high), unit = _category_meta(category)
    years = rng.randint(1, 20)
    phone = "9" + "".join(str(rng.randint(0, 9)) for _ in range(9))
    username = _unique_username(first + (last[:1] if last else ""))

    user = User.objects.create_user(
        username=username, email=f"{username}@example.test", password=password,
        first_name=first, last_name=last, role=User.Role.PROVIDER, phone=phone, city=city,
    )
    headline = rng.choice(HEADLINES).format(years=years, cat=category.name.lower(), area=area or city)
    profile = ProviderProfile.objects.create(
        user=user,
        category=category,
        headline=headline[:120],
        bio=(f"Hi, I'm {first}. I have been working as a {category.name.lower()} for {years} years in {city}. "
             f"I carry my own tools, give an estimate before starting and clean up after the job."),
        skills=", ".join(rng.sample(skills, k=min(len(skills), rng.randint(2, 4)))),
        languages=rng.choice(["Hindi, English", "Hindi", "English, Marathi", "Kannada, English", "Hindi, Urdu"]),
        experience_years=years,
        rate=round(rng.randint(low, high), -1),
        rate_unit=unit,
        city=city,
        area=area,
        pincode=str(rng.randint(110001, 560100)),
        latitude=lat,
        longitude=lng,
        service_radius_km=rng.choice([5, 10, 15, 20]),
        phone=phone,
        whatsapp=phone,
        is_available=rng.random() > 0.2,
        home_visit=True,
        emergency_service=rng.random() > 0.6,
        verification_status=ProviderProfile.Verification.VERIFIED,
        verification_note="Auto-verified by the testing tool",
        is_test=True,
    )
    return profile
