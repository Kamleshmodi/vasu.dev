import json
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aapcategory.models import Category, Designer
from aapstore.models import Cart, Order, OrderItem, ProductRating
from appwomens.models import NewProduct, ProductVariation, SaleItems as WomenSaleItems


SMALL_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
    b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


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
        cls._temp_media_root = tempfile.mkdtemp(prefix='vasu-test-media-')
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media_root)
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
            total_price=Decimal('2099.00'),
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

    @override_settings(OPENAI_CHAT_ENABLED=False, OPENAI_API_KEY='', OPENAI_CHAT_MODEL='')
    def test_chatbot_search_returns_matching_products(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'dress'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['found'])
        self.assertGreaterEqual(len(payload['products']), 1)
        self.assertEqual(payload['products'][0]['name'], self.product.product_name)
        self.assertIn('I found matching products', payload['message'])

    @override_settings(OPENAI_CHAT_ENABLED=False, OPENAI_API_KEY='', OPENAI_CHAT_MODEL='')
    def test_chatbot_search_handles_shipping_questions_without_products(self):
        response = self.client.get(reverse('chatbot_search'), {'query': 'shipping info'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['found'])
        self.assertEqual(payload['products'], [])
        self.assertIn('Shipping:', payload['message'])

    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('health_check'))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

    def test_profile_pages_render_with_custom_account_model(self):
        self.client.force_login(self.user)

        my_account_response = self.client.get(reverse('my_account'))
        edit_profile_response = self.client.get(reverse('edit_profile'))

        self.assertEqual(my_account_response.status_code, 200)
        self.assertEqual(edit_profile_response.status_code, 200)
        self.assertContains(my_account_response, self.user.username)
        self.assertContains(edit_profile_response, 'Email Address')

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
                'refund_amount': '2099.00',
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
        self.assertEqual(order.refund_amount, Decimal('2099.00'))
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
