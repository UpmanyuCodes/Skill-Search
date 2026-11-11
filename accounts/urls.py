from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_choice, name="signup"),
    path("signup/customer/", views.signup_customer, name="signup_customer"),
    path("signup/provider/", views.signup_provider, name="signup_provider"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html", authentication_form=LoginForm,
                                                redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_edit, name="profile"),
    path("provider/new/", views.become_provider, name="become_provider"),
    path("provider/edit/", views.provider_edit, name="provider_edit"),
    path("provider/availability/", views.toggle_availability, name="toggle_availability"),
    path("password/change/", auth_views.PasswordChangeView.as_view(
        template_name="accounts/simple_form.html", success_url=reverse_lazy("accounts:dashboard"),
        extra_context={"title": "Change password"}), name="password_change"),
    path("password/reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/simple_form.html", email_template_name="accounts/password_reset_email.txt",
        success_url=reverse_lazy("accounts:password_reset_done"),
        extra_context={"title": "Reset your password"}), name="password_reset"),
    path("password/reset/sent/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/message.html",
        extra_context={"title": "Check your email",
                       "text": "If an account exists for that email, we sent a link to reset the password."}),
         name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/simple_form.html", success_url=reverse_lazy("accounts:login"),
        extra_context={"title": "Choose a new password"}), name="password_reset_confirm"),
]
