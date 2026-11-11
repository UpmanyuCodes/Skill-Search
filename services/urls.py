from django.urls import path

from . import views

app_name = "services"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    path("pro/<slug:slug>/", views.provider_detail, name="provider_detail"),
    path("pro/<slug:slug>/book/", views.book_provider, name="book"),
    path("pro/<slug:slug>/save/", views.toggle_favorite, name="toggle_favorite"),
    path("pro/<slug:slug>/report/", views.report_provider, name="report"),
    path("pro/<slug:slug>/message/", views.start_conversation, name="start_conversation"),
    path("requests/<int:pk>/review/", views.review_create, name="review"),
    path("requests/<int:pk>/<str:action>/", views.update_request, name="update_request"),
    path("saved/", views.favorites, name="favorites"),
    path("messages/", views.inbox, name="inbox"),
    path("messages/<int:pk>/", views.conversation, name="conversation"),
    path("testing/", views.test_tools, name="test_tools"),
    path("testing/verify/<slug:slug>/", views.test_verify, name="test_verify"),
    path("api/providers/", views.api_providers, name="api_providers"),
    path("api/categories/", views.api_categories, name="api_categories"),
]
