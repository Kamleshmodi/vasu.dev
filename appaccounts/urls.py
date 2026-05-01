from django.urls import include, path
from .views import custom_logout
from . import views

urlpatterns = [
    path('login/', views.login_register, name='login_register'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('verify-email/resend/', views.resend_verification_email, name='resend_verification_email'),
    path('oauth/google/start/', views.google_oauth_start, name='google_oauth_start'),
    path('logout/', custom_logout, name='logout'),
    path('', include('allauth.urls')),
]
