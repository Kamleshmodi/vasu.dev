from django import forms
from django.contrib.auth import authenticate
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from urllib.parse import urlsplit

from .models import Account

GENDER_CHOICES = (
    ('Women', 'Women'),
    ('Men', 'Men'),
    ('Both', 'Both'),
)

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = Account
        fields = ['username', 'email', 'password1', 'password2', 'gender']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = None
        self.assigned_username = None

    def _build_unique_username(self, requested_username):
        cleaned_base = ''.join(str(requested_username or '').split()) or 'user'
        max_length = Account._meta.get_field('username').max_length
        base = cleaned_base[: max_length - 4]
        candidate = cleaned_base[:max_length]

        suffix = 1
        while Account.objects.filter(username__iexact=candidate).exists():
            candidate = f'{base}{suffix:03d}'
            suffix += 1

        return candidate

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('Please enter a username.')

        self.original_username = username
        self.assigned_username = self._build_unique_username(username)
        return self.assigned_username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        user = authenticate(email=email, password=password)
        if not user:
            raise forms.ValidationError("Wrong email or password")

        cleaned_data['user'] = user
        return cleaned_data


def _normalise_password_reset_domain(value):
    domain = str(value or '').strip()
    if not domain:
        return ''
    if '://' in domain:
        return urlsplit(domain).netloc.strip()
    return domain


class VasuPasswordResetForm(PasswordResetForm):
    def save(
        self,
        domain_override=None,
        subject_template_name='registration/password_reset_subject.txt',
        email_template_name='registration/password_reset_email.html',
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        configured_domain = _normalise_password_reset_domain(
            getattr(settings, 'PASSWORD_RESET_DOMAIN', '')
        )
        request_domain = _normalise_password_reset_domain(
            request.get_host() if request is not None else ''
        )
        effective_domain = (
            _normalise_password_reset_domain(domain_override)
            or configured_domain
            or request_domain
            or None
        )

        configured_protocol = str(getattr(settings, 'PASSWORD_RESET_PROTOCOL', '')).strip().lower()
        if configured_protocol == 'https':
            effective_use_https = True
        elif configured_protocol == 'http':
            effective_use_https = False
        else:
            effective_use_https = use_https

        return super().save(
            domain_override=effective_domain,
            subject_template_name=subject_template_name,
            email_template_name=email_template_name,
            use_https=effective_use_https,
            token_generator=token_generator,
            from_email=from_email,
            request=request,
            html_email_template_name=html_email_template_name,
            extra_email_context=extra_email_context,
        )
