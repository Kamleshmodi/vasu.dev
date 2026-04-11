from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .forms import LoginForm, RegisterForm
from django.contrib.auth import logout
from .models import Account, VendorProfile


def ensure_vendor_profile(user):
    if getattr(user, 'account_type', None) == Account.AccountType.VENDOR:
        VendorProfile.objects.get_or_create(
            user=user,
            defaults={
                'business_name': user.username,
                'contact_email': user.email,
            },
        )


def get_login_redirect_url(user):
    if getattr(user, 'has_admin_access', False):
        return 'admin_control_center'
    if getattr(user, 'is_vendor_account', False):
        ensure_vendor_profile(user)
        return 'vendor_dashboard'
    if getattr(user, 'is_delivery_partner_account', False):
        return 'delivery_dashboard'
    return 'home'

def login_register(request):
    if request.user.is_authenticated:
        return redirect(get_login_redirect_url(request.user))

    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                user = login_form.cleaned_data['user']
                login(request, user)
                return redirect(get_login_redirect_url(user))
            else:
                messages.error(request, "Invalid login details.")

        elif 'register_submit' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                register_form.save()
                messages.success(request, "Account created successfully. Please log in.")
                return redirect('login_register')
            else:
                messages.error(request, "Please fix the errors in the registration form.")

    context = {
        'login_form': login_form,
        'register_form': register_form,
    }
    return render(request, 'login.html', context)


def custom_logout(request):
    logout(request)
    return redirect('/')
