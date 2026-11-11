import datetime

from django import forms
from django.conf import settings
from django.utils import timezone

from accounts.forms import StyledFormMixin

from .models import Category, Message, ProviderProfile, Report, Review, ServiceRequest

ALLOWED_DOC_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
MAX_DOC_SIZE = 5 * 1024 * 1024


class ProviderProfileForm(StyledFormMixin, forms.ModelForm):
    id_number = forms.CharField(
        label="ID number", max_length=20, required=False,
        help_text="Used once for verification; only the last 4 characters are stored.",
    )

    class Meta:
        model = ProviderProfile
        fields = (
            "category", "headline", "bio", "skills", "languages", "experience_years", "rate", "rate_unit",
            "city", "area", "pincode", "latitude", "longitude", "service_radius_km",
            "phone", "whatsapp", "show_phone", "working_hours",
            "is_available", "home_visit", "emergency_service",
            "id_type", "id_document",
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell customers about your work, tools and guarantees."}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "skills": forms.TextInput(attrs={"placeholder": "leak repair, tap fitting, bathroom installation"}),
            "languages": forms.TextInput(attrs={"placeholder": "Hindi, English"}),
        }
        labels = {"rate": "Starting price (₹)", "service_radius_km": "I travel up to (km)", "id_type": "ID document type"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "Choose your service"
        # Real verification is mandatory unless the site runs in test mode
        # or the provider already submitted documents earlier.
        already_submitted = bool(self.instance.pk and self.instance.id_document)
        self.verification_required = not settings.SKILLSEARCH_TEST_MODE and not already_submitted
        for name in ("id_type", "id_number", "id_document"):
            self.fields[name].required = self.verification_required

    def clean_id_document(self):
        doc = self.cleaned_data.get("id_document")
        if doc and hasattr(doc, "size"):
            if doc.size > MAX_DOC_SIZE:
                raise forms.ValidationError("File too large (max 5 MB).")
            if not doc.name.lower().endswith(ALLOWED_DOC_EXTENSIONS):
                raise forms.ValidationError("Upload a PDF, JPG or PNG file.")
        return doc

    def clean_id_number(self):
        number = self.cleaned_data.get("id_number", "").replace(" ", "").strip()
        if number and len(number) < 6:
            raise forms.ValidationError("That ID number looks too short.")
        return number

    def save(self, commit=True):
        profile = super().save(commit=False)
        number = self.cleaned_data.get("id_number")
        if number:
            profile.id_number_last4 = number[-4:]
        # A changed document means it has to be checked again.
        if "id_document" in self.changed_data and profile.verification_status == ProviderProfile.Verification.REJECTED:
            profile.verification_status = ProviderProfile.Verification.PENDING
        if commit:
            profile.save()
        return profile


class TestProviderForm(StyledFormMixin, forms.Form):
    """Testing tool: create a ready-to-use verified provider in one step."""

    full_name = forms.CharField(max_length=120, required=False, help_text="Leave blank for a random name")
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label="Random category")
    city = forms.CharField(max_length=100, required=False, help_text="Leave blank to use your own city")
    near_me = forms.BooleanField(required=False, initial=True, label="Place them near my location")
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    count = forms.IntegerField(min_value=1, max_value=25, initial=1, label="How many?")


class ServiceRequestForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ("title", "description", "preferred_date", "preferred_time", "address", "contact_phone", "is_urgent")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Describe the job so the provider can prepare."}),
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
            "preferred_time": forms.TimeInput(attrs={"type": "time"}),
        }
        labels = {"is_urgent": "This is urgent"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["preferred_date"].widget.attrs["min"] = today.isoformat()
        self.fields["preferred_date"].initial = today + datetime.timedelta(days=1)

    def clean_preferred_date(self):
        date = self.cleaned_data["preferred_date"]
        if date < timezone.localdate():
            raise forms.ValidationError("Pick today or a future date.")
        return date


class ProviderResponseForm(forms.Form):
    note = forms.CharField(max_length=255, required=False,
                           widget=forms.TextInput(attrs={"class": "form-control form-control-sm",
                                                         "placeholder": "Optional note to the customer"}))


class ReviewForm(StyledFormMixin, forms.ModelForm):
    rating = forms.TypedChoiceField(choices=[(i, i) for i in range(5, 0, -1)], coerce=int,
                                    widget=forms.RadioSelect)

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": "How was the service?"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].widget.attrs["class"] = "btn-check"


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "class": "form-control",
                                                 "placeholder": "Write a message..."})}
        labels = {"body": ""}


class ReportForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason", "details")
        widgets = {"details": forms.Textarea(attrs={"rows": 3})}
