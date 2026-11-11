from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import Category, Conversation, Favorite, Message, ProviderProfile, Report, Review, ServiceRequest


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "order", "provider_count")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Providers")
    def provider_count(self, obj):
        return obj.providers.count()


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "verification_badge", "id_type", "has_document", "is_test",
                    "rating_avg", "created_at")
    list_filter = ("verification_status", "category", "city", "is_test", "is_available")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email", "phone", "city", "pincode")
    readonly_fields = ("rating_avg", "rating_count", "profile_views", "jobs_completed", "verified_at", "created_at",
                       "document_link")
    actions = ("approve", "reject", "reset_to_pending")
    fieldsets = (
        (None, {"fields": ("user", "slug", "category", "headline", "bio", "skills", "languages",
                           "experience_years", ("rate", "rate_unit"))}),
        ("Location", {"fields": ("city", "area", "pincode", ("latitude", "longitude"), "service_radius_km")}),
        ("Contact", {"fields": ("phone", "whatsapp", "show_phone", "working_hours")}),
        ("Options", {"fields": ("is_available", "home_visit", "emergency_service")}),
        ("Verification", {"fields": ("verification_status", "id_type", "id_number_last4", "id_document",
                                     "document_link", "verification_note", "verified_at", "is_test")}),
        ("Stats", {"fields": ("rating_avg", "rating_count", "profile_views", "jobs_completed", "created_at")}),
    )

    @admin.display(description="Status", ordering="verification_status")
    def verification_badge(self, obj):
        colors = {"verified": "#16a34a", "pending": "#d97706", "rejected": "#dc2626"}
        return format_html('<b style="color:{}">{}</b>', colors.get(obj.verification_status, "#555"),
                           obj.get_verification_status_display())

    @admin.display(boolean=True, description="Doc")
    def has_document(self, obj):
        return bool(obj.id_document)

    @admin.display(description="Uploaded document")
    def document_link(self, obj):
        if not obj.id_document:
            return "-"
        return format_html('<a href="{}" target="_blank">Open document</a>', obj.id_document.url)

    @admin.action(description="Approve selected providers (mark verified)")
    def approve(self, request, queryset):
        n = queryset.update(verification_status=ProviderProfile.Verification.VERIFIED, verified_at=timezone.now(),
                            verification_note="")
        self.message_user(request, f"{n} provider(s) verified.", messages.SUCCESS)

    @admin.action(description="Reject selected providers")
    def reject(self, request, queryset):
        n = queryset.update(verification_status=ProviderProfile.Verification.REJECTED, verified_at=None,
                            verification_note="Documents could not be verified. Please upload a clear, valid ID.")
        self.message_user(request, f"{n} provider(s) rejected.", messages.WARNING)

    @admin.action(description="Move back to pending review")
    def reset_to_pending(self, request, queryset):
        queryset.update(verification_status=ProviderProfile.Verification.PENDING, verified_at=None)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "customer", "provider", "preferred_date", "status", "is_urgent", "created_at")
    list_filter = ("status", "is_urgent")
    search_fields = ("title", "customer__username", "provider__user__username")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("provider", "author", "rating", "created_at")
    list_filter = ("rating",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("provider", "reporter", "reason", "resolved", "created_at")
    list_filter = ("resolved", "reason")
    list_editable = ("resolved",)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("customer", "provider", "updated_at")
    inlines = [MessageInline]


admin.site.register(Favorite)
admin.site.site_header = "Skill Search administration"
admin.site.site_title = "Skill Search admin"
admin.site.index_title = "Verify providers, manage categories and bookings"
