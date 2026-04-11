from django.urls import path
from .views import custom_logout
from . import views

urlpatterns = [
    path('login/', views.login_register, name='login_register'),
    path('logout/', custom_logout, name='logout'),
]