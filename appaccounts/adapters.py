import mimetypes
import uuid
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.apps import apps
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils.text import slugify

from .models import Account


_ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
_MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024


def _build_unique_username(email):
    base = slugify((email or 'user').split('@')[0]) or 'user'
    username = base[:30]
    suffix = 1

    while Account.objects.filter(username=username).exists():
        suffix_text = f'-{suffix}'
        username = f"{base[:30 - len(suffix_text)]}{suffix_text}"
        suffix += 1

    return username


def _extract_social_avatar_url(sociallogin, data=None):
    account = getattr(sociallogin, 'account', None)
    extra_data = getattr(account, 'extra_data', {}) or {}
    candidates = []

    if isinstance(data, dict):
        candidates.extend([data.get('picture'), data.get('avatar_url')])

    image_data = extra_data.get('image')
    image_url = image_data.get('url') if isinstance(image_data, dict) else None
    candidates.extend([
        extra_data.get('picture'),
        extra_data.get('avatar_url'),
        image_url,
    ])

    if account:
        try:
            candidates.append(account.get_avatar_url())
        except Exception:
            pass

    for candidate in candidates:
        normalized_url = str(candidate or '').strip()
        if normalized_url:
            return normalized_url

    return ''


def _guess_image_extension(url, content_type):
    path = urlparse(url).path or ''
    extension = ''

    if '.' in path:
        extension = f".{path.rsplit('.', 1)[-1]}".lower()
    if extension == '.jpe':
        extension = '.jpg'
    if extension not in _ALLOWED_IMAGE_EXTENSIONS:
        extension = ''

    if not extension and content_type:
        guessed_extension = mimetypes.guess_extension(content_type.split(';', 1)[0].strip().lower()) or ''
        if guessed_extension == '.jpe':
            guessed_extension = '.jpg'
        if guessed_extension in _ALLOWED_IMAGE_EXTENSIONS:
            extension = guessed_extension

    return extension or '.jpg'


def _download_remote_image(url):
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return None, None

    request = Request(url, headers={'User-Agent': 'VASU/1.0'})
    try:
        with urlopen(request, timeout=8) as response:
            content_type = str(response.headers.get('Content-Type') or '')
            image_bytes = response.read(_MAX_PROFILE_IMAGE_BYTES + 1)
    except Exception:
        return None, None

    if not image_bytes or len(image_bytes) > _MAX_PROFILE_IMAGE_BYTES:
        return None, None

    extension = _guess_image_extension(url, content_type)
    return image_bytes, extension


def _sync_social_profile_photo(user, sociallogin, data=None):
    if not user or not getattr(user, 'pk', None):
        return

    avatar_url = _extract_social_avatar_url(sociallogin, data=data)
    if not avatar_url:
        return

    try:
        UserProfile = apps.get_model('aapstore', 'UserProfile')
        profile, _ = UserProfile.objects.get_or_create(user=user)
    except Exception:
        return

    if profile.profile_picture:
        return

    image_bytes, extension = _download_remote_image(avatar_url)
    if not image_bytes:
        return

    filename = f"google-{user.pk}-{uuid.uuid4().hex[:10]}{extension}"
    try:
        profile.profile_picture.save(filename, ContentFile(image_bytes), save=True)
    except Exception:
        return


class VasuAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            from .views import get_login_redirect_url

            return reverse(get_login_redirect_url(request.user))
        return super().get_login_redirect_url(request)


class VasuSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            existing_user = getattr(getattr(sociallogin, 'account', None), 'user', None) or getattr(sociallogin, 'user', None)
            _sync_social_profile_photo(existing_user, sociallogin)
            return

        email = (
            sociallogin.account.extra_data.get('email')
            or getattr(sociallogin.user, 'email', '')
            or ''
        ).strip().lower()
        email_is_verified = bool(
            sociallogin.account.extra_data.get('email_verified')
            or sociallogin.account.extra_data.get('verified_email')
        )

        if not email or not email_is_verified:
            return

        existing_user = Account.objects.filter(email__iexact=email).first()
        if not existing_user:
            return

        if hasattr(existing_user, 'email_verified') and not existing_user.email_verified:
            existing_user.email_verified = True
            existing_user.save(update_fields=['email_verified'])

        sociallogin.connect(request, existing_user)
        _sync_social_profile_photo(existing_user, sociallogin)

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        email = (data.get('email') or sociallogin.account.extra_data.get('email') or '').strip().lower()
        if email:
            user.email = email

        if not getattr(user, 'username', ''):
            user.username = _build_unique_username(email)

        if hasattr(user, 'email_verified'):
            user.email_verified = True

        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if hasattr(user, 'email_verified') and not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        _sync_social_profile_photo(user, sociallogin)

        return user
