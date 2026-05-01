import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from allauth.socialaccount.models import SocialApp

from .forms import LoginForm, RegisterForm
from .models import Account, VendorProfile


def _login_rate_limit_attempts():
    return max(getattr(settings, 'LOGIN_RATE_LIMIT_ATTEMPTS', 5), 1)


def _login_rate_limit_window_seconds():
    return max(getattr(settings, 'LOGIN_RATE_LIMIT_WINDOW_SECONDS', 900), 60)


def _login_rate_limit_block_seconds():
    return max(getattr(settings, 'LOGIN_RATE_LIMIT_BLOCK_SECONDS', 900), 60)


def _normalise_email(email):
    return str(email or '').strip().lower()


def _get_unverified_account_by_email(email):
    normalized_email = _normalise_email(email)
    if not normalized_email:
        return None

    account = Account.objects.filter(email__iexact=normalized_email).only('id', 'email', 'email_verified').first()
    if account and not account.email_verified:
        return account
    return None


def _get_client_ip(request):
    forwarded_for = (request.META.get('HTTP_X_FORWARDED_FOR') or '').strip()
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or '').strip() or 'unknown'


def _login_rate_limit_scopes(ip_address, email):
    scopes = [f'ip:{ip_address}']
    if email:
        scopes.append(f'ip-email:{ip_address}:{email}')
    return scopes


def _login_fail_count_key(scope):
    return f'login_fail_count:{scope}'


def _login_block_key(scope):
    return f'login_blocked_until:{scope}'


def _get_login_block_seconds_remaining(ip_address, email):
    now = time.time()
    remaining_seconds = 0
    for scope in _login_rate_limit_scopes(ip_address, email):
        blocked_until = cache.get(_login_block_key(scope))
        if blocked_until:
            remaining_seconds = max(remaining_seconds, int(blocked_until - now))
    return max(remaining_seconds, 0)


def _record_failed_login(ip_address, email):
    attempts_limit = _login_rate_limit_attempts()
    window_seconds = _login_rate_limit_window_seconds()
    block_seconds = _login_rate_limit_block_seconds()

    for scope in _login_rate_limit_scopes(ip_address, email):
        fail_count_key = _login_fail_count_key(scope)
        new_count = (cache.get(fail_count_key) or 0) + 1
        cache.set(fail_count_key, new_count, window_seconds)

        if new_count >= attempts_limit:
            cache.set(
                _login_block_key(scope),
                time.time() + block_seconds,
                block_seconds,
            )
            cache.delete(fail_count_key)


def _clear_failed_login_state(ip_address, email):
    for scope in _login_rate_limit_scopes(ip_address, email):
        cache.delete(_login_fail_count_key(scope))
        cache.delete(_login_block_key(scope))


def _remaining_attempts(ip_address, email):
    attempts_limit = _login_rate_limit_attempts()
    current_count = 0
    for scope in _login_rate_limit_scopes(ip_address, email):
        current_count = max(current_count, cache.get(_login_fail_count_key(scope)) or 0)
    return max(attempts_limit - current_count, 0)


def _format_wait_time(seconds):
    if seconds < 60:
        return f'{seconds} seconds'
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    if remaining_seconds:
        return f'{minutes} minutes {remaining_seconds} seconds'
    return f'{minutes} minutes'


def send_email_verification(user, request):
    if not getattr(user, 'email', ''):
        return None

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verification_url = request.build_absolute_uri(reverse('verify_email', args=[uid, token]))
    subject = 'Verify your email for VASU'
    message = (
        f'Hi {user.username},\n\n'
        'Please verify your email address to activate your VASU account.\n\n'
        f'Verify now: {verification_url}\n\n'
        'If you did not create this account, you can ignore this email.'
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    return verification_url


def _has_google_oauth_config():
    if getattr(settings, 'GOOGLE_OAUTH_CONFIGURED_WITH_ENV', False):
        return True

    return SocialApp.objects.filter(provider='google').exists()


def _send_verification_with_feedback(request, user, success_message, failure_message):
    try:
        verification_url = send_email_verification(user, request)
        if verification_url and settings.DEBUG and 'console.EmailBackend' in settings.EMAIL_BACKEND:
            messages.info(request, f'Development verification link: {verification_url}')
        messages.success(request, success_message)
        return True
    except Exception:
        messages.warning(request, failure_message)
        return False


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

    pending_verification_email = _normalise_email(request.session.get('pending_verification_email', ''))
    pending_verification_account = _get_unverified_account_by_email(pending_verification_email)
    show_resend_verification = bool(pending_verification_account)
    resend_verification_email = pending_verification_account.email if pending_verification_account else ''

    if pending_verification_email and not pending_verification_account:
        request.session.pop('pending_verification_email', None)

    login_form = LoginForm(initial={'email': resend_verification_email} if resend_verification_email else None)
    register_form = RegisterForm()

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            submitted_email = _normalise_email(request.POST.get('email'))
            unverified_account = _get_unverified_account_by_email(submitted_email)
            show_resend_verification = bool(unverified_account)
            if unverified_account:
                resend_verification_email = unverified_account.email

            client_ip = _get_client_ip(request)
            blocked_for = _get_login_block_seconds_remaining(client_ip, submitted_email)

            if blocked_for > 0:
                messages.error(
                    request,
                    f'Too many failed login attempts. Try again in {_format_wait_time(blocked_for)}.',
                )
            else:
                login_form = LoginForm(request.POST)
                if login_form.is_valid():
                    user = login_form.cleaned_data['user']

                    if not getattr(user, 'email_verified', True):
                        request.session['pending_verification_email'] = user.email
                        _send_verification_with_feedback(
                            request,
                            user,
                            'Your email is not verified yet. We have sent a fresh verification link.',
                            'Your email is not verified yet. Please contact support if you did not receive a verification email.',
                        )
                        return redirect('login_register')

                    _clear_failed_login_state(client_ip, submitted_email)
                    login(request, user)
                    return redirect(get_login_redirect_url(user))

                _record_failed_login(client_ip, submitted_email)
                blocked_for = _get_login_block_seconds_remaining(client_ip, submitted_email)
                if blocked_for > 0:
                    messages.error(
                        request,
                        f'Too many failed login attempts. Try again in {_format_wait_time(blocked_for)}.',
                    )
                else:
                    attempts_left = _remaining_attempts(client_ip, submitted_email)
                    messages.error(request, f'Invalid login details. {attempts_left} attempt(s) remaining.')

        elif 'register_submit' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save(commit=False)
                user.email_verified = False
                user.save()
                request.session['pending_verification_email'] = user.email

                original_username = (getattr(register_form, 'original_username', '') or '').strip()
                assigned_username = (getattr(register_form, 'assigned_username', '') or '').strip()
                if original_username and assigned_username and original_username.lower() != assigned_username.lower():
                    messages.info(
                        request,
                        f'Username "{original_username}" was unavailable. Your account was created with "{assigned_username}".',
                    )

                _send_verification_with_feedback(
                    request,
                    user,
                    'Account created. Please verify your email before logging in.',
                    'Account created, but we could not send verification email right now. Please try logging in later to resend verification.',
                )
                return redirect('login_register')
            messages.error(request, 'Please fix the errors in the registration form.')

    context = {
        'login_form': login_form,
        'register_form': register_form,
        'google_oauth_enabled': getattr(settings, 'GOOGLE_OAUTH_ENABLED', False),
        'show_resend_verification': show_resend_verification,
        'resend_verification_email': resend_verification_email,
    }
    return render(request, 'login.html', context)


def google_oauth_start(request):
    if _has_google_oauth_config():
        return redirect('google_login')

    messages.error(
        request,
        'Google login is not configured yet. Add Google credentials in environment or create a Google SocialApp in Django admin.',
    )
    return redirect('login_register')


def resend_verification_email(request):
    if request.method != 'POST':
        return redirect('login_register')

    email = _normalise_email(request.POST.get('email'))
    if not email:
        messages.error(request, 'Please enter your email first, then request verification again.')
        return redirect('login_register')

    user = Account.objects.filter(email__iexact=email).first()
    if not user:
        request.session.pop('pending_verification_email', None)
        messages.info(request, 'If an account exists for this email, a verification message has been sent.')
        return redirect('login_register')

    if user.email_verified:
        request.session.pop('pending_verification_email', None)
        messages.info(request, 'This email is already verified. Please sign in.')
        return redirect('login_register')

    request.session['pending_verification_email'] = user.email

    _send_verification_with_feedback(
        request,
        user,
        'A new verification email has been sent. Please check inbox and spam folder.',
        'We could not send verification email right now. Please try again later.',
    )
    return redirect('login_register')


def verify_email(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = Account.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        messages.success(request, 'Your email has been verified. You can now log in.')
    else:
        messages.error(request, 'Verification link is invalid or has expired.')

    return redirect('login_register')


def custom_logout(request):
    logout(request)
    return redirect('/')
