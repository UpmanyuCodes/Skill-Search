from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SkillSearchUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "city", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "city")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    fieldsets = UserAdmin.fieldsets + (
        ("Skill Search", {"fields": ("role", "phone", "avatar", "address", "city", "pincode", "latitude", "longitude")}),
    )
