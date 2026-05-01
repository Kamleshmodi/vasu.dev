from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .adapters import _sync_social_profile_photo
from .models import Account


class OAuthUrlConfigurationTests(SimpleTestCase):
	def test_google_allauth_callback_uses_accounts_prefix(self):
		self.assertEqual(reverse('google_login'), '/accounts/google/login/')
		self.assertEqual(reverse('google_callback'), '/accounts/google/login/callback/')


@override_settings(
	EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
	DEFAULT_FROM_EMAIL='noreply@example.com',
)
class AuthenticationSecurityTests(TestCase):
	def setUp(self):
		cache.clear()
		self.password = 'StrongPass123!'
		self.verified_user = Account.objects.create_user(
			email='verified@example.com',
			username='verified-user',
			password=self.password,
			email_verified=True,
		)

	def test_signup_creates_unverified_account_and_sends_email(self):
		response = self.client.post(
			reverse('login_register'),
			{
				'username': 'new-user',
				'email': 'newuser@example.com',
				'password1': 'NewUserPass123!',
				'password2': 'NewUserPass123!',
				'gender': 'Women',
				'register_submit': '1',
			},
		)

		self.assertRedirects(response, reverse('login_register'))
		new_user = Account.objects.get(email='newuser@example.com')
		self.assertFalse(new_user.email_verified)
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('verify', mail.outbox[0].subject.lower())

	def test_signup_with_existing_username_assigns_unique_username(self):
		response = self.client.post(
			reverse('login_register'),
			{
				'username': self.verified_user.username,
				'email': 'another-user@example.com',
				'password1': 'AnotherPass123!',
				'password2': 'AnotherPass123!',
				'gender': 'Women',
				'register_submit': '1',
			},
		)

		self.assertRedirects(response, reverse('login_register'))
		new_user = Account.objects.get(email='another-user@example.com')
		self.assertNotEqual(new_user.username.lower(), self.verified_user.username.lower())
		self.assertTrue(new_user.username.lower().startswith(self.verified_user.username.lower()))
		self.assertFalse(new_user.email_verified)

	def test_unverified_user_cannot_login(self):
		Account.objects.create_user(
			email='pending@example.com',
			username='pending-user',
			password=self.password,
			email_verified=False,
		)

		response = self.client.post(
			reverse('login_register'),
			{
				'email': 'pending@example.com',
				'password': self.password,
				'login_submit': '1',
			},
		)

		self.assertRedirects(response, reverse('login_register'))
		self.assertNotIn('_auth_user_id', self.client.session)
		self.assertEqual(len(mail.outbox), 1)

	def test_verify_email_link_marks_account_verified(self):
		user = Account.objects.create_user(
			email='verifyme@example.com',
			username='verify-me',
			password=self.password,
			email_verified=False,
		)
		uid = urlsafe_base64_encode(force_bytes(user.pk))
		token = default_token_generator.make_token(user)

		response = self.client.get(reverse('verify_email', args=[uid, token]))
		self.assertRedirects(response, reverse('login_register'))

		user.refresh_from_db()
		self.assertTrue(user.email_verified)

	def test_verified_user_can_login(self):
		response = self.client.post(
			reverse('login_register'),
			{
				'email': self.verified_user.email,
				'password': self.password,
				'login_submit': '1',
			},
		)

		self.assertRedirects(response, reverse('home'))
		self.assertEqual(int(self.client.session['_auth_user_id']), self.verified_user.pk)

	@override_settings(
		LOGIN_RATE_LIMIT_ATTEMPTS=2,
		LOGIN_RATE_LIMIT_WINDOW_SECONDS=300,
		LOGIN_RATE_LIMIT_BLOCK_SECONDS=300,
	)
	def test_login_rate_limit_blocks_brute_force_attempts(self):
		self.client.post(
			reverse('login_register'),
			{
				'email': self.verified_user.email,
				'password': 'WrongPassword1!',
				'login_submit': '1',
			},
		)

		second_response = self.client.post(
			reverse('login_register'),
			{
				'email': self.verified_user.email,
				'password': 'WrongPassword1!',
				'login_submit': '1',
			},
		)
		self.assertContains(second_response, 'Too many failed login attempts')

		blocked_response = self.client.post(
			reverse('login_register'),
			{
				'email': self.verified_user.email,
				'password': self.password,
				'login_submit': '1',
			},
		)
		self.assertContains(blocked_response, 'Too many failed login attempts')
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_password_reset_view_is_available(self):
		response = self.client.get(reverse('reset_password'))
		self.assertEqual(response.status_code, 200)

	def test_password_reset_email_uses_request_host(self):
		response = self.client.post(
			reverse('reset_password'),
			{'email': self.verified_user.email},
			HTTP_HOST='vasu.dev',
		)

		self.assertRedirects(response, reverse('password_reset_done'))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('http://vasu.dev/reset/', mail.outbox[0].body)
		self.assertNotIn('http://example.com/reset/', mail.outbox[0].body)

	@override_settings(PASSWORD_RESET_DOMAIN='accounts.vasu.dev', PASSWORD_RESET_PROTOCOL='https')
	def test_password_reset_email_uses_configured_domain_override(self):
		response = self.client.post(
			reverse('reset_password'),
			{'email': self.verified_user.email},
			HTTP_HOST='localhost:8000',
		)

		self.assertRedirects(response, reverse('password_reset_done'))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('https://accounts.vasu.dev/reset/', mail.outbox[0].body)

	def test_google_oauth_route_is_registered(self):
		response = self.client.get(reverse('google_oauth_start'))
		self.assertEqual(response.status_code, 302)
		self.assertIn(response.url, {reverse('login_register'), reverse('google_login')})

	def test_login_page_hides_resend_card_by_default(self):
		response = self.client.get(reverse('login_register'))
		self.assertNotContains(response, 'Email Confirmation Pending')

	def test_unverified_login_shows_resend_card_after_redirect(self):
		Account.objects.create_user(
			email='pending-card@example.com',
			username='pending-card-user',
			password=self.password,
			email_verified=False,
		)

		response = self.client.post(
			reverse('login_register'),
			{
				'email': 'pending-card@example.com',
				'password': self.password,
				'login_submit': '1',
			},
			follow=True,
		)

		self.assertContains(response, 'Email Confirmation Pending')
		self.assertContains(response, 'Send New Verification Link')
		self.assertContains(response, 'value="pending-card@example.com"')

	def test_register_redirect_shows_resend_card_for_new_unverified_user(self):
		response = self.client.post(
			reverse('login_register'),
			{
				'username': 'brand-new-user',
				'email': 'brandnew@example.com',
				'password1': 'BrandNewPass123!',
				'password2': 'BrandNewPass123!',
				'gender': 'Women',
				'register_submit': '1',
			},
			follow=True,
		)

		self.assertContains(response, 'Email Confirmation Pending')
		self.assertContains(response, 'Send New Verification Link')
		self.assertContains(response, 'value="brandnew@example.com"')


class SocialAvatarSyncTests(TestCase):
	def setUp(self):
		self.user = Account.objects.create_user(
			email='avatar-sync@example.com',
			username='avatar-sync',
			password='StrongPass123!',
			email_verified=True,
		)

	def _build_sociallogin(self, picture_url='https://example.com/avatar'):
		account = SimpleNamespace(extra_data={'picture': picture_url})
		account.get_avatar_url = lambda: picture_url
		return SimpleNamespace(account=account)

	def test_social_avatar_is_saved_to_user_profile_when_empty(self):
		sociallogin = self._build_sociallogin()

		class _FakeResponse:
			headers = {'Content-Type': 'image/jpeg'}

			def read(self, _limit):
				return b'fake-jpeg-bytes'

			def __enter__(self):
				return self

			def __exit__(self, exc_type, exc, tb):
				return False

		with patch('appaccounts.adapters.urlopen', return_value=_FakeResponse()):
			_sync_social_profile_photo(self.user, sociallogin)

		self.user.userprofile.refresh_from_db()
		self.assertTrue(bool(self.user.userprofile.profile_picture))
		self.assertTrue(self.user.userprofile.profile_picture.name.startswith('userprofile/google-'))

	def test_social_avatar_does_not_override_existing_profile_picture(self):
		profile = self.user.userprofile
		profile.profile_picture.save('existing-avatar.jpg', ContentFile(b'existing-bytes'), save=True)
		existing_name = profile.profile_picture.name
		sociallogin = self._build_sociallogin()

		with patch('appaccounts.adapters.urlopen') as mocked_urlopen:
			_sync_social_profile_photo(self.user, sociallogin)

		mocked_urlopen.assert_not_called()
		profile.refresh_from_db()
		self.assertEqual(profile.profile_picture.name, existing_name)
