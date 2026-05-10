import json
import shutil
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aapcategory.models import Category, Designer
from aapstore.models import Cart, Order, OrderItem, ProductRating, SupportRequest, UserEvent
from appwomens.models import NewProduct, ProductVariation, SaleItems as WomenSaleItems
from vasu import settings as vasu_settings


SMALL_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
    b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


class SettingsSafetyTests(SimpleTestCase):
    def test_render_generated_secret_key_is_accepted_in_production_mode(self):
        render_secret = 'B0jrphAPOY7pg92AN0c9MN4yecczLMdwnx4OkA1KFUk='

        with patch.object(vasu_settings, 'DEBUG', False):
            with patch.dict(vasu_settings.os.environ, {'SECRET_KEY': render_secret}, clear=False):
                with patch.object(vasu_settings.sys, 'argv', ['manage.py', 'runserver']):
                    secret_key = vasu_settings.build_secret_key()

        self.assertEqual(secret_key, render_secret)

    def test_collectstatic_can_use_ephemeral_secret_key_in_production_mode(self):
        with patch.object(vasu_settings, 'DEBUG', False):
            with patch.dict(vasu_settings.os.environ, {'SECRET_KEY': ''}, clear=False):
                with patch.object(vasu_settings.sys, 'argv', ['manage.py', 'collectstatic']):
                    secret_key = vasu_settings.build_secret_key()

        self.assertTrue(secret_key)
        self.assertNotEqual(secret_key, 'django-insecure-vasu-local-development-secret-key')

    def test_runserver_still_requires_real_secret_key_in_production_mode(self):
        with patch.object(vasu_settings, 'DEBUG', False):
            with patch.dict(vasu_settings.os.environ, {'SECRET_KEY': ''}, clear=False):
                with patch.object(vasu_settings.sys, 'argv', ['manage.py', 'runserver']):
                    with self.assertRaises(ImproperlyConfigured):
                        vasu_settings.build_secret_key()


@override_settings(
    ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'],
    USE_HTTPS_SECURITY=False,
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class VasuViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        test_media_parent = Path(settings.BASE_DIR) / '.tmp-test-media'
        test_media_parent.mkdir(exist_ok=True)
        test_media_root = test_media_parent / cls.__name__
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)
        cls._temp_media_root = test_media_root
        cls._media_override = override_settings(MEDIA_ROOT=str(cls._temp_media_root))
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._media_override.disable()
            shutil.rmtree(cls._temp_media_root, ignore_errors=True)

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='tester@example.com',
            username='tester',
            password='StrongPass123',
        )
        self.vendor_user = get_user_model().objects.create_user(
            email='vendor@example.com',
            username='vendoruser',
            password='StrongPass123',
            account_type='vendor',
        )
        self.delivery_user = get_user_model().objects.create_user(
            email='delivery@example.com',
            username='deliveryuser',
            password='StrongPass123',
            account_type='delivery_partner',
        )
        self.admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            username='adminuser',
            password='StrongPass123',
        )
        self.category = Category.objects.create(category_name='Dresses', gender='women')
        self.designer = Designer.objects.create(name='Studio Test', gender='women')
        self.product = NewProduct.objects.create(
            product_name='Test Dress',
            brand='VASU',
            slug='test-dress',
            gender='Women',
            vendor=self.vendor_user,
            designer=self.designer,
            price=Decimal('1999.00'),
            front_image=self.make_image('front.gif'),
            back_image=self.make_image('back.gif'),
            is_available=True,
            category=self.category,
            product_description='Comfortable test dress.',
        )
        ProductVariation.objects.create(
            product=self.product,
            size='M',
            color='Black',
            stock=5,
            category_type='dresses',
        )

    @staticmethod
    def make_image(name):
        return SimpleUploadedFile(name, SMALL_GIF, content_type='image/gif')

    def add_product_to_cart(self):
        content_type = ContentType.objects.get_for_model(NewProduct)
        return Cart.objects.create(
            user=self.user,
            content_type=content_type,
            object_id=self.product.id,
            quantity=1,
        )

    def create_order_with_item(
        self,
        status=Order.Status.PROCESSING,
        payment_method=Order.PaymentMethod.CASH,
        payment_reference='COD',
    ):
        order = Order.objects.create(
            user=self.user,
            full_name='Test User',
            mobile='9876543210',
            address='123 Test Street',
            city='Surat',
            district='Surat',
            state='Gujarat',
            country='India',
            zip_code='395006',
            total_price=Decimal('1999.00'),
            payment_method=payment_method,
            payment_reference=payment_reference,
            status=status,
        )
        item = OrderItem.objects.create(
            order=order,
            price=self.product.price,
            quantity=1,
            content_type=ContentType.objects.get_for_model(NewProduct),
            object_id=self.product.id,
        )
        return order, item

    def build_women_product_payload(
        self,
        *,
        sale_enabled=False,
        discount_percentage='',
        start_date=None,
        end_date=None,
        return_to='',
    ):
        variation = self.product.variations.get()
        payload = {
            'product_name': self.product.product_name,
            'brand': self.product.brand,
            'designer': str(self.designer.id),
            'category': str(self.category.id),
            'price': '1999.00',
            'product_description': self.product.product_description,
            'is_available': 'on',
            'women_variations-TOTAL_FORMS': '1',
            'women_variations-INITIAL_FORMS': '1',
            'women_variations-MIN_NUM_FORMS': '0',
            'women_variations-MAX_NUM_FORMS': '1000',
            'women_variations-0-id': str(variation.id),
            'women_variations-0-size': variation.size,
            'women_variations-0-color': variation.color,
            'women_variations-0-stock': str(variation.stock),
            'women_variations-0-category_type': variation.category_type,
            'women_gallery-TOTAL_FORMS': '1',
            'women_gallery-INITIAL_FORMS': '0',
            'women_gallery-MIN_NUM_FORMS': '0',
            'women_gallery-MAX_NUM_FORMS': '1000',
            'women_sale-discount_percentage': discount_percentage,
            'women_sale-start_date': start_date.isoformat() if start_date else '',
            'women_sale-end_date': end_date.isoformat() if end_date else '',
        }
        if sale_enabled:
            payload['women_sale-is_enabled'] = 'on'
        if return_to:
            payload['return_to'] = return_to
        return payload

    def test_womens_new_category_filter_does_not_crash(self):
        response = self.client.get(reverse('womens_new'), {'category': self.category.slug})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.product_name)

    @override_settings(GEMINI_CHAT_ENABLED=False, GEMINI_API_KEY='', GEMINI_CHAT_MODEL='')
    def test_chatbot_search_returns_matching_products(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'dress'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['found'])
        self.assertGreaterEqual(len(payload['products']), 1)
        self.assertEqual(payload['products'][0]['name'], self.product.product_name)
        self.assertIn('I found matching products', payload['message'])

    @override_settings(GEMINI_CHAT_ENABLED=False, GEMINI_API_KEY='', GEMINI_CHAT_MODEL='')
    def test_chatbot_search_handles_shipping_questions_without_products(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'shipping info'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['found'])
        self.assertEqual(payload['products'], [])
        self.assertIn('shipping', payload['message'].lower())

    @override_settings(GEMINI_CHAT_ENABLED=False, GEMINI_API_KEY='', GEMINI_CHAT_MODEL='')
    def test_chatbot_search_combines_support_and_product_results(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'shipping dress'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['found'])
        self.assertGreaterEqual(len(payload['products']), 1)
        self.assertEqual(payload['products'][0]['name'], self.product.product_name)
        self.assertIn('shipping', payload['message'].lower())
        self.assertIn('matching products', payload['message'])

    @override_settings(GEMINI_CHAT_ENABLED=False, GEMINI_API_KEY='', GEMINI_CHAT_MODEL='')
    def test_chatbot_search_handles_hinglish_support_question(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'order kaise karu'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['found'])
        self.assertEqual(payload['products'], [])
        self.assertIn('order', payload['message'].lower())

    @override_settings(GEMINI_CHAT_ENABLED=False, GEMINI_API_KEY='', GEMINI_CHAT_MODEL='')
    def test_chatbot_search_no_match_returns_helpful_fallback(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'zxyqv random unmatched'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['found'])
        self.assertEqual(payload['products'], [])
        self.assertIn('exact product match', payload['message'])
        self.assertIn('shipping', payload['message'].lower())

    @override_settings(GEMINI_CHAT_ENABLED=False, GEMINI_API_KEY='', GEMINI_CHAT_MODEL='')
    def test_chatbot_search_vendor_account_query_returns_admin_guidance(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'how to contact admin for vendor account'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['found'])
        self.assertEqual(payload['products'], [])
        self.assertIn('vendor account', payload['message'].lower())
        self.assertIn('need help', payload['message'].lower())

    @override_settings(GEMINI_CHAT_ENABLED=False, GEMINI_API_KEY='', GEMINI_CHAT_MODEL='')
    def test_chatbot_search_greeting_returns_welcome_without_no_match_text(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'hey good morning'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['found'])
        self.assertEqual(payload['products'], [])
        self.assertIn('welcome', payload['message'].lower())
        self.assertNotIn('exact product match', payload['message'].lower())

    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('health_check'))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

    @override_settings(DEBUG=False, SERVE_MEDIA_FILES=True)
    def test_uploaded_media_is_served_when_debug_is_disabled(self):
        response = self.client.get(self.product.front_image.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/gif')
        self.assertEqual(b''.join(response.streaming_content), SMALL_GIF)

    @override_settings(DEBUG=False, SERVE_MEDIA_FILES=True)
    def test_media_route_blocks_non_upload_paths(self):
        response = self.client.get('/media/.env')

        self.assertEqual(response.status_code, 404)

    def test_robots_txt_contains_sitemap(self):
        response = self.client.get(reverse('robots_txt'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User-agent: *')
        self.assertContains(response, 'Sitemap:')
        self.assertIn('/sitemap.xml', response.content.decode('utf-8'))

    def test_sitemap_xml_is_available(self):
        response = self.client.get(reverse('sitemap_index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<urlset', html=False)

    def test_profile_pages_render_with_custom_account_model(self):
        self.client.force_login(self.user)

        my_account_response = self.client.get(reverse('my_account'))
        edit_profile_response = self.client.get(reverse('edit_profile'))

        self.assertEqual(my_account_response.status_code, 200)
        self.assertEqual(edit_profile_response.status_code, 200)
        self.assertContains(my_account_response, self.user.username)
        self.assertContains(edit_profile_response, 'Email Address')

    def test_need_help_page_renders_support_form(self):
        response = self.client.get(reverse('need_help'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Submit Support or Bug Report')
        self.assertContains(response, 'Bug Report')

    @override_settings(SUPPORT_EMAIL='support@example.com')
    def test_need_help_page_uses_configured_support_email(self):
        response = self.client.get(reverse('need_help'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'support@example.com')
        self.assertContains(response, 'support_email_clicked')
        self.assertContains(response, 'support_phone_clicked')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.com',
        SUPPORT_EMAIL='support@example.com',
    )
    def test_need_help_submission_creates_ticket_and_sends_emails(self):
        self.client.force_login(self.user)
        order, _ = self.create_order_with_item(
            payment_method=Order.PaymentMethod.UPI,
            payment_reference='123456789012',
        )

        response = self.client.post(
            reverse('need_help'),
            data={
                'request_type': SupportRequest.RequestType.BUG,
                'severity': SupportRequest.Severity.HIGH,
                'name': 'Test User',
                'email': 'tester@example.com',
                'subject': 'Checkout fails for UPI',
                'message': 'Steps: Open checkout, choose UPI, submit valid UTR, still got random failure once.',
                'page_url': 'https://example.com/checkout/',
                'order_reference': str(order.order_id),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('need_help'))
        self.assertEqual(SupportRequest.objects.count(), 1)

        support_request = SupportRequest.objects.latest('id')
        self.assertTrue(support_request.ticket_id.startswith('SR-'))
        self.assertEqual(support_request.request_type, SupportRequest.RequestType.BUG)
        self.assertEqual(support_request.severity, SupportRequest.Severity.HIGH)
        self.assertEqual(support_request.reporter_user, self.user)
        self.assertEqual(support_request.order, order)

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn(support_request.ticket_id, mail.outbox[0].subject)
        self.assertIn(support_request.ticket_id, mail.outbox[1].subject)

    def test_place_order_api_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(
            reverse('place_order_api'),
            data=json.dumps({}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_place_order_api_rejects_invalid_payment_method(self):
        self.client.force_login(self.user)
        self.add_product_to_cart()

        response = self.client.post(
            reverse('place_order_api'),
            data=json.dumps(
                {
                    'fullName': 'Test User',
                    'mobile': '9876543210',
                    'address': '123 Test Street',
                    'country': 'India',
                    'state': 'Gujarat',
                    'district': 'Surat',
                    'city': 'Surat',
                    'zipCode': '395006',
                    'paymentMethod': 'wire',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {'success': False, 'error': 'Unsupported payment method selected.'},
        )

    @override_settings(GOOGLE_SITE_VERIFICATION='google-test-token', BING_SITE_VERIFICATION='bing-test-token')
    def test_home_page_renders_search_engine_verification_meta_tags(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'google-site-verification')
        self.assertContains(response, 'google-test-token')
        self.assertContains(response, 'msvalidate.01')
        self.assertContains(response, 'bing-test-token')

    def test_track_event_api_creates_user_event_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('track_event_api'),
            data=json.dumps(
                {
                    'eventType': 'user_event',
                    'eventName': 'wishlist_add_clicked',
                    'pagePath': '/new/',
                    'referrer': 'https://example.com/source',
                    'anonymousId': 'anon-test-001',
                    'properties': {'catalog': 'women'},
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserEvent.objects.count(), 1)
        tracked_event = UserEvent.objects.latest('id')
        self.assertEqual(tracked_event.user, self.user)
        self.assertEqual(tracked_event.event_type, UserEvent.EventType.USER_EVENT)
        self.assertEqual(tracked_event.event_name, 'wishlist_add_clicked')
        self.assertEqual(tracked_event.page_path, '/new/')
        self.assertEqual(tracked_event.properties.get('catalog'), 'women')

    def test_track_event_api_creates_page_view_for_anonymous_user(self):
        response = self.client.post(
            reverse('track_event_api'),
            data=json.dumps(
                {
                    'eventType': 'page_view',
                    'eventName': 'page_view',
                    'pagePath': '/mens/',
                    'anonymousId': 'anon-public-001',
                    'properties': {'title': 'Men Home'},
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserEvent.objects.count(), 1)
        tracked_event = UserEvent.objects.latest('id')
        self.assertIsNone(tracked_event.user)
        self.assertEqual(tracked_event.event_type, UserEvent.EventType.PAGE_VIEW)
        self.assertEqual(tracked_event.page_path, '/mens/')

    def test_track_event_api_rejects_missing_event_name(self):
        response = self.client.post(
            reverse('track_event_api'),
            data=json.dumps({'eventType': 'user_event'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(UserEvent.objects.count(), 0)

    def test_place_order_api_stores_payment_reference_for_upi_orders(self):
        self.client.force_login(self.user)
        self.add_product_to_cart()

        response = self.client.post(
            reverse('place_order_api'),
            data=json.dumps(
                {
                    'fullName': 'Test User',
                    'mobile': '9876543210',
                    'address': '123 Test Street',
                    'country': 'India',
                    'state': 'Gujarat',
                    'district': 'Surat',
                    'city': 'Surat',
                    'zipCode': '395006',
                    'paymentMethod': 'upi',
                    'transactionId': '123456789012',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        order = Order.objects.latest('id')
        self.assertEqual(order.payment_method, Order.PaymentMethod.UPI)
        self.assertEqual(order.payment_reference, '123456789012')
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.account_receipt_status, Order.AccountReceiptStatus.PENDING)
        self.assertEqual(order.account_receipt_reference, '123456789012')

    def test_place_order_api_stores_payment_reference_for_card_orders(self):
        self.client.force_login(self.user)
        self.add_product_to_cart()

        response = self.client.post(
            reverse('place_order_api'),
            data=json.dumps(
                {
                    'fullName': 'Test User',
                    'mobile': '9876543210',
                    'address': '123 Test Street',
                    'country': 'India',
                    'state': 'Gujarat',
                    'district': 'Surat',
                    'city': 'Surat',
                    'zipCode': '395006',
                    'paymentMethod': 'card',
                    'transactionId': 'CARD_MANUAL_12345',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        order = Order.objects.latest('id')
        self.assertEqual(order.payment_method, Order.PaymentMethod.CARD)
        self.assertEqual(order.payment_reference, 'CARD_MANUAL_12345')
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.account_receipt_status, Order.AccountReceiptStatus.PENDING)
        self.assertEqual(order.account_receipt_reference, 'CARD_MANUAL_12345')

    def test_place_order_api_rejects_missing_card_payment_reference(self):
        self.client.force_login(self.user)
        self.add_product_to_cart()

        response = self.client.post(
            reverse('place_order_api'),
            data=json.dumps(
                {
                    'fullName': 'Test User',
                    'mobile': '9876543210',
                    'address': '123 Test Street',
                    'country': 'India',
                    'state': 'Gujarat',
                    'district': 'Surat',
                    'city': 'Surat',
                    'zipCode': '395006',
                    'paymentMethod': 'card',
                    'transactionId': '',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {'success': False, 'error': 'Payment reference is required for this payment method.'},
        )

    def test_address_options_api_returns_state_data(self):
        response = self.client.get(reverse('address_options_api'), {'country': 'India'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['supports_cascade'])
        self.assertIn('Gujarat', payload['states'])

    def test_validate_postal_code_api_rejects_state_mismatch(self):
        response = self.client.get(
            reverse('validate_postal_code_api'),
            {'country': 'India', 'state': 'Gujarat', 'postal_code': '110001'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['valid'])
        self.assertIn('selected state', payload['message'])

    def test_place_order_api_rejects_invalid_pincode_for_selected_state(self):
        self.client.force_login(self.user)
        self.add_product_to_cart()

        response = self.client.post(
            reverse('place_order_api'),
            data=json.dumps(
                {
                    'fullName': 'Test User',
                    'mobile': '9876543210',
                    'address': '123 Test Street',
                    'country': 'India',
                    'state': 'Gujarat',
                    'district': 'Surat',
                    'city': 'Surat',
                    'zipCode': '110001',
                    'paymentMethod': 'cash',
                    'transactionId': 'COD',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('selected state', response.json()['error'])

    def test_order_history_uses_processing_fallback_status(self):
        self.client.force_login(self.user)
        self.create_order_with_item()

        response = self.client.get(reverse('order_history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Processing')

    def test_rating_page_requires_delivered_order(self):
        self.client.force_login(self.user)
        order, item = self.create_order_with_item(status=Order.Status.PROCESSING)

        response = self.client.get(reverse('rate_order_item', args=[order.id, item.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('order_history'))

    def test_user_can_rate_delivered_product(self):
        self.client.force_login(self.user)
        order, item = self.create_order_with_item(status=Order.Status.DELIVERED)

        response = self.client.post(
            reverse('rate_order_item', args=[order.id, item.id]),
            data={
                'rating': 5,
                'title': 'Loved it',
                'review': 'Premium quality and smooth delivery.',
                'review_image': self.make_image('review.gif'),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('order_history'))

        rating = ProductRating.objects.get(order_item=item)
        self.assertEqual(rating.user, self.user)
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.title, 'Loved it')
        self.assertEqual(rating.approval_status, ProductRating.ApprovalStatus.PENDING)
        self.assertTrue(bool(rating.review_image))

    def test_pending_reviews_are_hidden_from_product_detail(self):
        order, item = self.create_order_with_item(status=Order.Status.DELIVERED)
        ProductRating.objects.create(
            order=order,
            order_item=item,
            user=self.user,
            content_type=ContentType.objects.get_for_model(NewProduct),
            object_id=self.product.id,
            rating=4,
            title='Pending review',
            review='Needs admin approval first.',
            approval_status=ProductRating.ApprovalStatus.PENDING,
        )

        response = self.client.get(reverse('product_detail', args=[self.product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pending review')

    def test_admin_can_approve_pending_review(self):
        order, item = self.create_order_with_item(status=Order.Status.DELIVERED)
        rating = ProductRating.objects.create(
            order=order,
            order_item=item,
            user=self.user,
            content_type=ContentType.objects.get_for_model(NewProduct),
            object_id=self.product.id,
            rating=5,
            title='Approve me',
            review='Real purchase review.',
            approval_status=ProductRating.ApprovalStatus.PENDING,
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('admin_moderate_rating', args=[rating.id]),
            data={'decision': 'approve'},
        )

        self.assertEqual(response.status_code, 302)
        rating.refresh_from_db()
        self.assertEqual(rating.approval_status, ProductRating.ApprovalStatus.APPROVED)
        self.assertEqual(rating.moderated_by, self.admin_user)

    def test_admin_payment_dashboard_renders(self):
        self.create_order_with_item(payment_method=Order.PaymentMethod.CASH, payment_reference='COD')
        self.create_order_with_item(payment_method=Order.PaymentMethod.UPI, payment_reference='123456789012')

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('payment_management_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Management')
        self.assertContains(response, 'Cash')
        self.assertContains(response, 'UPI')

    def test_admin_can_update_payment_record_with_refund_completion(self):
        order, _ = self.create_order_with_item(
            payment_method=Order.PaymentMethod.UPI,
            payment_reference='123456789012',
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('admin_update_payment_record', args=[order.id]),
            data={
                'payment_status': Order.PaymentStatus.PAID,
                'account_receipt_status': Order.AccountReceiptStatus.RECEIVED,
                'account_receipt_reference': 'BANK-123456',
                'return_status': Order.ReturnStatus.COMPLETED,
                'refund_status': Order.RefundStatus.COMPLETED,
                'refund_amount': '1999.00',
                'refund_reference': 'RF-123456',
                'payment_notes': 'Customer return received and refund sent.',
            },
        )

        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.REFUNDED)
        self.assertEqual(order.account_receipt_status, Order.AccountReceiptStatus.RECEIVED)
        self.assertEqual(order.account_receipt_reference, 'BANK-123456')
        self.assertEqual(order.return_status, Order.ReturnStatus.COMPLETED)
        self.assertEqual(order.refund_status, Order.RefundStatus.COMPLETED)
        self.assertEqual(order.refund_amount, Decimal('1999.00'))
        self.assertEqual(order.refund_reference, 'RF-123456')
        self.assertEqual(order.payment_notes, 'Customer return received and refund sent.')
        self.assertIsNotNone(order.refund_processed_at)
        self.assertIsNotNone(order.account_receipt_confirmed_at)

    def test_vendor_payment_dashboard_renders_for_vendor_orders(self):
        self.create_order_with_item(payment_method=Order.PaymentMethod.UPI, payment_reference='123456789012')

        self.client.force_login(self.vendor_user)
        response = self.client.get(reverse('vendor_payment_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendor Payment Management')
        self.assertContains(response, '123456789012')

    def test_vendor_can_update_own_order_item_status(self):
        order, item = self.create_order_with_item()

        self.client.force_login(self.vendor_user)
        response = self.client.post(
            reverse('update_order_item_status', args=[item.id]),
            data={
                'fulfillment_status': OrderItem.FulfillmentStatus.DELIVERED,
                'status_notes': 'Delivered by vendor partner.',
            },
        )

        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(item.vendor, self.vendor_user)
        self.assertEqual(item.fulfillment_status, OrderItem.FulfillmentStatus.DELIVERED)
        self.assertEqual(item.status_notes, 'Delivered by vendor partner.')
        self.assertEqual(order.status, Order.Status.DELIVERED)

    def test_vendor_can_add_sale_to_own_product(self):
        sale_start = timezone.localdate()
        sale_end = sale_start + timedelta(days=5)

        self.client.force_login(self.vendor_user)
        response = self.client.post(
            reverse('vendor_product_edit', args=['women', self.product.id]),
            data=self.build_women_product_payload(
                sale_enabled=True,
                discount_percentage='25',
                start_date=sale_start,
                end_date=sale_end,
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('vendor_dashboard'))

        sale = WomenSaleItems.objects.get(product=self.product)
        self.assertEqual(sale.discount_percentage, 25)
        self.assertEqual(sale.start_date, sale_start)
        self.assertEqual(sale.end_date, sale_end)
        self.assertEqual(Decimal(str(sale.sale_price)), Decimal('1499.25'))

    def test_admin_can_add_sale_to_any_vendor_product(self):
        sale_start = timezone.localdate() + timedelta(days=1)
        sale_end = sale_start + timedelta(days=6)

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('vendor_product_edit', args=['women', self.product.id]),
            data=self.build_women_product_payload(
                sale_enabled=True,
                discount_percentage='15',
                start_date=sale_start,
                end_date=sale_end,
                return_to='admin',
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_control_center'))

        sale = WomenSaleItems.objects.get(product=self.product)
        self.assertEqual(sale.discount_percentage, 15)
        self.assertEqual(sale.start_date, sale_start)
        self.assertEqual(sale.end_date, sale_end)
        self.assertEqual(Decimal(str(sale.sale_price)), Decimal('1699.15'))

    def test_vendor_can_remove_product_from_sale_list(self):
        WomenSaleItems.objects.create(
            product=self.product,
            discount_percentage=20,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=3),
            sale_price=0,
        )

        self.client.force_login(self.vendor_user)
        response = self.client.post(
            reverse('vendor_product_edit', args=['women', self.product.id]),
            data=self.build_women_product_payload(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('vendor_dashboard'))
        self.assertFalse(WomenSaleItems.objects.filter(product=self.product).exists())

    def test_admin_can_assign_delivery_partner_to_order(self):
        order, _ = self.create_order_with_item()

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('assign_delivery_partner', args=[order.id]),
            data={'delivery_partner_id': self.delivery_user.id},
        )

        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.delivery_partner, self.delivery_user)
        self.assertIsNotNone(order.delivery_assigned_at)

    def test_delivery_dashboard_renders_assigned_cod_order(self):
        order, _ = self.create_order_with_item()
        order.delivery_partner = self.delivery_user
        order.delivery_assigned_at = order.created_at
        order.save(update_fields=['delivery_partner', 'delivery_assigned_at'])

        self.client.force_login(self.delivery_user)
        response = self.client.get(reverse('delivery_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delivery Partner Dashboard')
        self.assertContains(response, order.order_id)
        self.assertContains(response, 'Collect COD Payment')

    def test_delivery_partner_can_confirm_qr_collection(self):
        order, _ = self.create_order_with_item()
        order.delivery_partner = self.delivery_user
        order.delivery_assigned_at = order.created_at
        order.save(update_fields=['delivery_partner', 'delivery_assigned_at'])

        self.client.force_login(self.delivery_user)
        response = self.client.post(
            reverse('delivery_collect_payment', args=[order.id]),
            data={
                'collection_mode': 'qrcode',
                'payment_reference': '123456789012',
            },
        )

        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.payment_method, Order.PaymentMethod.QRCODE)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.account_receipt_status, Order.AccountReceiptStatus.PENDING)
        self.assertEqual(order.account_receipt_reference, '123456789012')
        self.assertEqual(order.payment_reference, '123456789012')
        self.assertIn('delivery QR', order.payment_notes)

    def test_cash_order_starts_as_not_received_in_account(self):
        order, _ = self.create_order_with_item(
            payment_method=Order.PaymentMethod.CASH,
            payment_reference='COD',
        )

        self.assertEqual(order.account_receipt_status, Order.AccountReceiptStatus.NOT_RECEIVED)
        self.assertEqual(order.account_receipt_reference, '')

    def test_delivery_partner_can_mark_assigned_item_delivered(self):
        order, item = self.create_order_with_item(
            payment_method=Order.PaymentMethod.UPI,
            payment_reference='123456789012',
        )
        order.delivery_partner = self.delivery_user
        order.delivery_assigned_at = order.created_at
        order.save(update_fields=['delivery_partner', 'delivery_assigned_at'])

        self.client.force_login(self.delivery_user)
        response = self.client.post(
            reverse('update_order_item_status', args=[item.id]),
            data={
                'fulfillment_status': OrderItem.FulfillmentStatus.DELIVERED,
                'status_notes': 'Delivered to customer by field partner.',
            },
        )

        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(item.fulfillment_status, OrderItem.FulfillmentStatus.DELIVERED)
        self.assertEqual(order.status, Order.Status.DELIVERED)

    def test_delivery_partner_cannot_update_unassigned_item(self):
        order, item = self.create_order_with_item(
            payment_method=Order.PaymentMethod.UPI,
            payment_reference='123456789012',
        )

        self.client.force_login(self.delivery_user)
        response = self.client.post(
            reverse('update_order_item_status', args=[item.id]),
            data={
                'fulfillment_status': OrderItem.FulfillmentStatus.DELIVERED,
                'status_notes': 'Should not be allowed.',
            },
        )

        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(item.fulfillment_status, OrderItem.FulfillmentStatus.PENDING)
        self.assertEqual(order.status, Order.Status.PROCESSING)

    def test_admin_order_management_dashboard_filters_by_location(self):
        order, _ = self.create_order_with_item()

        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse('admin_order_management_dashboard'),
            {'state': 'Gujarat', 'district': 'Surat', 'country': 'India'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_id)

    def test_order_history_shows_download_invoice_action(self):
        self.client.force_login(self.user)
        order, _ = self.create_order_with_item()

        response = self.client.get(reverse('order_history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Download Invoice')
        self.assertContains(response, reverse('view_invoice', args=[order.id]))
        self.assertContains(response, 'invoice_download_clicked')
        self.assertContains(response, 'order_cancel_clicked')

    @override_settings(SUPPORT_EMAIL='support@example.com')
    def test_customer_can_view_invoice(self):
        self.client.force_login(self.user)
        order, _ = self.create_order_with_item()

        response = self.client.get(reverse('view_invoice', args=[order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'INVOICE')
        self.assertContains(response, order.order_id)
        self.assertContains(response, 'support@example.com')

    def test_customer_can_cancel_cash_order(self):
        order, _ = self.create_order_with_item(
            payment_method=Order.PaymentMethod.CASH,
            payment_reference='COD',
        )
        variation = self.product.variations.first()
        variation.stock = 4
        variation.save(update_fields=['stock'])

        self.client.force_login(self.user)
        response = self.client.post(reverse('cancel_order', args=[order.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('order_history'))
        order.refresh_from_db()
        variation.refresh_from_db()

        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        self.assertEqual(order.account_receipt_status, Order.AccountReceiptStatus.NOT_RECEIVED)
        self.assertIn('Customer cancelled order', order.payment_notes)
        self.assertEqual(variation.stock, 5)

    def test_customer_cancel_prepaid_order_marks_refund_in_process(self):
        order, _ = self.create_order_with_item(
            payment_method=Order.PaymentMethod.UPI,
            payment_reference='123456789012',
        )

        self.client.force_login(self.user)
        response = self.client.post(reverse('cancel_order', args=[order.id]))

        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.REFUND_IN_PROCESS)
        self.assertEqual(order.refund_status, Order.RefundStatus.PENDING)

    def test_customer_cannot_cancel_delivered_order(self):
        order, _ = self.create_order_with_item(
            status=Order.Status.DELIVERED,
            payment_method=Order.PaymentMethod.UPI,
            payment_reference='123456789012',
        )

        self.client.force_login(self.user)
        response = self.client.post(reverse('cancel_order', args=[order.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('order_history'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
