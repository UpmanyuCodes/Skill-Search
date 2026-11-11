from django import template
from django.utils.html import format_html, format_html_join

register = template.Library()


@register.simple_tag
def stars(rating, size=""):
    """Render a 0-5 rating as Bootstrap star icons."""
    rating = float(rating or 0)
    icons = []
    for i in range(1, 6):
        if rating >= i - 0.25:
            icons.append(("bi-star-fill",))
        elif rating >= i - 0.75:
            icons.append(("bi-star-half",))
        else:
            icons.append(("bi-star",))
    return format_html('<span class="stars {}" aria-label="{} out of 5">{}</span>', size, round(rating, 1),
                       format_html_join("", '<i class="bi {}"></i>', icons))


@register.filter
def km(value):
    if value is None:
        return ""
    if value < 1:
        return f"{int(value * 1000)} m"
    return f"{value:.1f} km"


@register.inclusion_tag("partials/field.html")
def field(bound_field, col=""):
    return {"f": bound_field, "col": col}


@register.simple_tag(takes_context=True)
def qs_replace(context, **kwargs):
    """Current query string with some keys replaced (used for pagination)."""
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()


TONES = ["blue", "orange", "green", "pink", "teal", "amber", "red", "sky"]


@register.filter
def tone(obj):
    """A stable colour class for a category (or any object / number)."""
    key = getattr(obj, "pk", obj)
    try:
        return "tone-" + TONES[(int(key) - 1) % len(TONES)]
    except (TypeError, ValueError):
        return "tone-blue"


STATUS_COLORS = {"pending": "warning", "accepted": "primary", "declined": "secondary",
                 "completed": "success", "cancelled": "secondary", "verified": "success", "rejected": "danger"}


@register.filter
def status_color(status):
    return STATUS_COLORS.get(status, "secondary")
