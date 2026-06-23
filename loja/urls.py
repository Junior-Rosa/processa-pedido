from django.urls import path

from . import views

urlpatterns = [
    path('order', views.OrderView.as_view()),
    path('health', views.HealthView.as_view()),
]
