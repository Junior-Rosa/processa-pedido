from django.urls import path, include

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('', include('painel.urls')),
    path('', include('loja.urls')),
]
