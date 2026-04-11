from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlencode

from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from aapcategory.models import Designer
from aapstore.models import Order, OrderItem, ProductRating
from appaccounts.models import Account, VendorProfile
from appmens.models import Accessories as MenAccessories
from appmens.models import Bags as MenBags
from appmens.models import Clothing as MenClothing
from appmens.models import Dresses as MenDresses
from appmens.models import Footwear as MenFootwear
from appmens.models import NewProduct as MenProduct
from appmens.models import ProductVariation as MenVariation
from appmens.models import SaleItems as MenSaleItems
from appwomens.models import Accessories as WomenAccessories
from appwomens.models import Bags as WomenBags
from appwomens.models import BeautyProducts
from appwomens.models import Clothing as WomenClothing
from appwomens.models import Dresses as WomenDresses
from appwomens.models import Footwear as WomenFootwear
from appwomens.models import NewProduct as WomenProduct
from appwomens.models import ProductVariation as WomenVariation
from appwomens.models import SaleItems as WomenSaleItems

from .backoffice_forms import (
    MenGalleryImageFormSet,
    MenVariationFormSet,
    MenVendorProductForm,
    ProductSaleForm,
    VendorProfileForm,
    WomenGalleryImageFormSet,
    WomenVariationFormSet,
    WomenVendorProductForm,
)


CATALOG_CONFIG = {
    'women': {
        'label': "Women's",
        'product_model': WomenProduct,
        'variation_model': WomenVariation,
        'product_form': WomenVendorProductForm,
        'variation_formset': WomenVariationFormSet,
        'gallery_formset': WomenGalleryImageFormSet,
        'sale_model': WomenSaleItems,
        'designer_gender': 'women',
        'gender_value': 'Women',
        'detail_view_name': 'product_detail',
        'category_models': {
            'clothing': WomenClothing,
            'footwear': WomenFootwear,
            'dresses': WomenDresses,
            'accessories': WomenAccessories,
            'bags': WomenBags,
            'beauty': BeautyProducts,
        },
    },
    'men': {
        'label': "Men's",
        'product_model': MenProduct,
        'variation_model': MenVariation,
        'product_form': MenVendorProductForm,
        'variation_formset': MenVariationFormSet,
        'gallery_formset': MenGalleryImageFormSet,
        'sale_model': MenSaleItems,
        'designer_gender': 'men',
        'gender_value': 'Mens',
        'detail_view_name': 'product_detail_men',
        'category_models': {
            'clothing': MenClothing,
            'footwear': MenFootwear,
            'dresses': MenDresses,
            'accessories': MenAccessories,
            'bags': MenBags,
        },
    },
}


def get_catalog_config(catalog):
    return CATALOG_CONFIG.get((catalog or '').strip().lower())


def ensure_vendor_profile(user):
    return VendorProfile.objects.get_or_create(
        user=user,
        defaults={
            'business_name': user.username,
            'contact_email': user.email,
        },
    )[0]


def ensure_vendor_access(request, allow_admin=False):
    if getattr(request.user, 'is_vendor_account', False):
        return None
    if allow_admin and getattr(request.user, 'has_admin_access', False):
        return None

    messages.error(request, 'The vendor dashboard is available only for approved vendor accounts.')
    return redirect('my_account')


def ensure_admin_access(request):
    if getattr(request.user, 'has_admin_access', False):
        return None

    messages.error(request, 'Admin access is required to open the control center.')
    return redirect('home')


def ensure_delivery_access(request):
    if getattr(request.user, 'is_delivery_partner_account', False):
        return None

    messages.error(request, 'The delivery dashboard is available only for delivery partner accounts.')
    return redirect('my_account')


def append_note(existing_notes, next_note):
    existing_notes = (existing_notes or '').strip()
    next_note = (next_note or '').strip()
    if not next_note:
        return existing_notes
    if not existing_notes:
        return next_note
    return f'{existing_notes}\n{next_note}'


def build_delivery_qr_image_url(order):
    upi_link = 'upi://pay?' + urlencode(
        {
            'pa': getattr(settings, 'PAYMENT_UPI_ID', '').strip(),
            'pn': getattr(settings, 'PAYMENT_UPI_NAME', '').strip() or 'VASU',
            'am': f'{order.total_price or Decimal("0.00"):.2f}',
            'cu': 'INR',
            'tn': f'Order {order.order_id or order.id}',
        }
    )
    return f'https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={quote(upi_link, safe="")}'


def get_delivery_partners():
    return list(
        Account.objects.filter(account_type=Account.AccountType.DELIVERY_PARTNER).order_by('username')
    )


def build_unique_slug(model, product_name, instance_id=None):
    base_slug = slugify(product_name) or 'product'
    slug = base_slug
    counter = 1

    existing = model.objects.all()
    if instance_id:
        existing = existing.exclude(pk=instance_id)

    while existing.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1

    return slug


def get_vendor_designer(owner, gender):
    designer_name = owner.display_name or owner.username
    designer, _ = Designer.objects.get_or_create(name=designer_name, gender=gender)
    return designer


def get_rating_summary_map(model, product_ids):
    if not product_ids:
        return {}

    content_type = ContentType.objects.get_for_model(model)
    summaries = ProductRating.objects.filter(
        content_type=content_type,
        object_id__in=product_ids,
        approval_status=ProductRating.ApprovalStatus.APPROVED,
    ).values('object_id').annotate(review_count=Count('id'), average_rating=Avg('rating'))

    return {summary['object_id']: summary for summary in summaries}


def build_related_item_filter(women_ids, men_ids):
    product_filter = Q()

    if women_ids:
        product_filter |= Q(
            content_type=ContentType.objects.get_for_model(WomenProduct),
            object_id__in=women_ids,
        )
    if men_ids:
        product_filter |= Q(
            content_type=ContentType.objects.get_for_model(MenProduct),
            object_id__in=men_ids,
        )

    return product_filter


def sale_sort_key(sale, on_date=None):
    current_date = on_date or timezone.localdate()
    sale_price = Decimal(str(sale.sale_price or 0))

    if sale.start_date <= current_date <= sale.end_date:
        return (0, sale_price, -sale.end_date.toordinal(), -sale.id)
    if sale.start_date > current_date:
        return (1, sale.start_date.toordinal(), sale_price, -sale.id)
    return (2, -sale.end_date.toordinal(), -sale.id)


def get_primary_sale_map(sale_model, product_ids, on_date=None):
    product_ids = [product_id for product_id in product_ids if product_id]
    if not sale_model or not product_ids:
        return {}

    current_date = on_date or timezone.localdate()
    sale_map = {}

    for sale in sale_model.objects.filter(product_id__in=product_ids).order_by('product_id', '-id'):
        existing_sale = sale_map.get(sale.product_id)
        if not existing_sale or sale_sort_key(sale, current_date) < sale_sort_key(existing_sale, current_date):
            sale_map[sale.product_id] = sale

    return sale_map


def get_primary_sale_for_product(product, sale_model=None):
    if not product or not getattr(product, 'pk', None) or not sale_model:
        return None

    return get_primary_sale_map(sale_model, [product.pk]).get(product.pk)


def get_sale_status_label(sale, on_date=None):
    if not sale:
        return None

    current_date = on_date or timezone.localdate()
    discount_label = f'{Decimal(str(sale.discount_percentage or 0)).normalize():f}'.rstrip('0').rstrip('.')
    discount_label = discount_label or '0'

    if sale.start_date <= current_date <= sale.end_date:
        return {
            'label': 'Sale Live',
            'badge_class': 'badge-live',
            'summary': f'{discount_label}% off until {sale.end_date:%d %b %Y}',
        }
    if sale.start_date > current_date:
        return {
            'label': 'Sale Scheduled',
            'badge_class': 'badge-processing',
            'summary': f'{discount_label}% off from {sale.start_date:%d %b %Y}',
        }
    return {
        'label': 'Sale Ended',
        'badge_class': 'badge-muted',
        'summary': f'Ended on {sale.end_date:%d %b %Y}',
    }


def get_product_card_image_url(product):
    image_candidates = [
        getattr(product, 'front_image', None),
        getattr(product, 'back_image', None),
    ]

    gallery_first = product.gallery_images.first() if hasattr(product, 'gallery_images') else None
    if gallery_first:
        image_candidates.append(getattr(gallery_first, 'image', None))

    for image in image_candidates:
        if not image:
            continue
        try:
            return image.url
        except (ValueError, AttributeError):
            continue

    return ''


def build_catalog_cards(products, catalog):
    config = get_catalog_config(catalog)
    if not config:
        return []

    rating_map = get_rating_summary_map(config['product_model'], [product.id for product in products])
    sale_map = get_primary_sale_map(config.get('sale_model'), [product.id for product in products])
    cards = []

    for product in products:
        rating_summary = rating_map.get(product.id, {})
        stock_total = sum((variation.stock or 0) for variation in product.variations.all())
        sale = sale_map.get(product.id)
        sale_status = get_sale_status_label(sale)

        cards.append(
            {
                'id': product.id,
                'catalog': catalog,
                'catalog_label': config['label'],
                'product': product,
                'image_url': get_product_card_image_url(product),
                'vendor_name': product.vendor.display_name if product.vendor else 'Unassigned',
                'stock_total': stock_total,
                'variation_count': product.variations.count(),
                'review_count': rating_summary.get('review_count', 0),
                'average_rating': rating_summary.get('average_rating'),
                'activity_label': (
                    'Updated'
                    if product.modified_date
                    and product.created_date
                    and (product.modified_date - product.created_date) > timedelta(seconds=1)
                    else 'New'
                ),
                'modified_date': product.modified_date,
                'sale': sale,
                'sale_status': sale_status,
                'detail_url': reverse(config['detail_view_name'], args=[product.slug]) if product.slug else '#',
                'edit_url': reverse('vendor_product_edit', args=[catalog, product.id]),
                'delete_url': reverse('vendor_product_delete', args=[catalog, product.id]),
            }
        )

    return cards


def sync_product_categories(product, catalog):
    config = get_catalog_config(catalog)
    if not config:
        return

    category_models = config['category_models']
    for category_model in category_models.values():
        category_model.objects.filter(product=product).delete()

    for variation in product.variations.all():
        category_type = (variation.category_type or '').strip().lower()
        target_model = category_models.get(category_type)
        if not target_model:
            continue

        create_data = {'product': product}
        field_names = {field.name for field in target_model._meta.fields}

        if 'size' in field_names:
            create_data['size'] = variation.size or None
        if 'color' in field_names:
            create_data['color'] = variation.color or None

        target_model.objects.create(**create_data)


def get_managed_product(request, catalog, product_id):
    config = get_catalog_config(catalog)
    if not config:
        return None

    queryset = config['product_model'].objects.select_related('vendor', 'category', 'designer').prefetch_related('variations', 'gallery_images')
    if not getattr(request.user, 'has_admin_access', False):
        queryset = queryset.filter(vendor=request.user)

    return get_object_or_404(queryset, pk=product_id)


def build_vendor_dashboard_context(user, profile_form=None):
    vendor_profile = ensure_vendor_profile(user)
    women_products = list(
        WomenProduct.objects.filter(vendor=user)
        .select_related('category', 'designer')
        .prefetch_related('variations', 'gallery_images')
    )
    men_products = list(
        MenProduct.objects.filter(vendor=user)
        .select_related('category', 'designer')
        .prefetch_related('variations', 'gallery_images')
    )

    product_cards = build_catalog_cards(women_products, 'women') + build_catalog_cards(men_products, 'men')
    product_cards.sort(key=lambda item: item['modified_date'], reverse=True)

    women_ids = [product.id for product in women_products]
    men_ids = [product.id for product in men_products]
    related_item_filter = build_related_item_filter(women_ids, men_ids)

    related_order_ids = []
    related_ratings = ProductRating.objects.none()
    average_rating = None
    if related_item_filter:
        related_order_ids = list(
            OrderItem.objects.filter(related_item_filter).values_list('order_id', flat=True).distinct()
        )
        approved_ratings = ProductRating.objects.filter(
            related_item_filter,
            approval_status=ProductRating.ApprovalStatus.APPROVED,
        )
        related_ratings = approved_ratings.select_related('user', 'order')[:6]
        average_rating = approved_ratings.aggregate(avg=Avg('rating'))['avg']

    recent_orders = Order.objects.filter(id__in=related_order_ids).select_related('user').order_by('-created_at')[:6]

    return {
        'vendor_profile': vendor_profile,
        'profile_form': profile_form or VendorProfileForm(instance=vendor_profile),
        'product_cards': product_cards,
        'recent_orders': recent_orders,
        'recent_ratings': related_ratings,
        'dashboard_stats': {
            'total_products': len(product_cards),
            'active_products': sum(1 for card in product_cards if card['product'].is_available),
            'low_stock_products': sum(1 for card in product_cards if card['stock_total'] <= 3),
            'review_count': sum(card['review_count'] for card in product_cards),
            'average_rating': average_rating,
        },
    }


def build_admin_control_context(user_query='', product_query=''):
    user_query = (user_query or '').strip()
    product_query = (product_query or '').strip()

    accounts_queryset = Account.objects.select_related('vendor_profile').order_by('-date_joined')
    if user_query:
        accounts_queryset = accounts_queryset.filter(
            Q(username__icontains=user_query)
            | Q(email__icontains=user_query)
            | Q(account_type__icontains=user_query)
            | Q(vendor_profile__business_name__icontains=user_query)
        ).distinct()

    women_products_queryset = WomenProduct.objects.select_related('vendor', 'category', 'designer').prefetch_related('variations', 'gallery_images')
    men_products_queryset = MenProduct.objects.select_related('vendor', 'category', 'designer').prefetch_related('variations', 'gallery_images')

    if product_query:
        product_filter = (
            Q(product_name__icontains=product_query)
            | Q(brand__icontains=product_query)
            | Q(category__category_name__icontains=product_query)
            | Q(vendor__username__icontains=product_query)
            | Q(vendor__email__icontains=product_query)
            | Q(vendor__vendor_profile__business_name__icontains=product_query)
        )
        women_products_queryset = women_products_queryset.filter(product_filter).distinct()
        men_products_queryset = men_products_queryset.filter(product_filter).distinct()

    accounts = list(accounts_queryset[:4])
    women_products = list(women_products_queryset.order_by('-modified_date')[:4])
    men_products = list(men_products_queryset.order_by('-modified_date')[:4])
    product_cards = build_catalog_cards(women_products, 'women') + build_catalog_cards(men_products, 'men')
    product_cards.sort(key=lambda item: item['modified_date'], reverse=True)

    recent_orders = Order.objects.select_related('user', 'delivery_partner').order_by('-created_at')[:10]
    recent_ratings = ProductRating.objects.filter(
        approval_status=ProductRating.ApprovalStatus.APPROVED,
    ).select_related('user', 'order').order_by('-updated_at')[:8]
    pending_ratings = ProductRating.objects.filter(
        approval_status=ProductRating.ApprovalStatus.PENDING,
    ).select_related('user', 'order').order_by('-updated_at')[:6]

    return {
        'accounts': accounts,
        'product_cards': product_cards[:4],
        'recent_orders': recent_orders,
        'recent_ratings': recent_ratings,
        'pending_ratings': pending_ratings,
        'role_choices': Account.AccountType.choices,
        'user_query': user_query,
        'product_query': product_query,
        'summary': {
            'customers': Account.objects.filter(account_type=Account.AccountType.CUSTOMER).count(),
            'vendors': Account.objects.filter(account_type=Account.AccountType.VENDOR).count(),
            'delivery_partners': Account.objects.filter(account_type=Account.AccountType.DELIVERY_PARTNER).count(),
            'admins': Account.objects.filter(is_superuser=True).count(),
            'orders': Order.objects.count(),
            'delivered_orders': Order.objects.filter(status=Order.Status.DELIVERED).count(),
            'ratings': ProductRating.objects.count(),
            'women_products': WomenProduct.objects.count(),
            'men_products': MenProduct.objects.count(),
            'revenue': Order.objects.aggregate(total=Count('id')),
        },
    }


STATUS_BADGE_MAP = {
    Order.PaymentStatus.PENDING: 'badge-processing',
    Order.PaymentStatus.PAID: 'badge-live',
    Order.PaymentStatus.REFUND_IN_PROCESS: 'badge-processing',
    Order.PaymentStatus.REFUNDED: 'badge-live',
    Order.PaymentStatus.FAILED: 'badge-danger',
    Order.AccountReceiptStatus.NOT_RECEIVED: 'badge-danger',
    Order.AccountReceiptStatus.PENDING: 'badge-processing',
    Order.AccountReceiptStatus.RECEIVED: 'badge-live',
    Order.AccountReceiptStatus.FAILED: 'badge-danger',
    Order.ReturnStatus.NONE: 'badge-muted',
    Order.ReturnStatus.REQUESTED: 'badge-processing',
    Order.ReturnStatus.APPROVED: 'badge-live',
    Order.ReturnStatus.PICKED_UP: 'badge-processing',
    Order.ReturnStatus.RECEIVED: 'badge-live',
    Order.ReturnStatus.COMPLETED: 'badge-live',
    Order.ReturnStatus.REJECTED: 'badge-danger',
    Order.RefundStatus.NOT_REQUIRED: 'badge-muted',
    Order.RefundStatus.PENDING: 'badge-processing',
    Order.RefundStatus.PROCESSING: 'badge-processing',
    Order.RefundStatus.COMPLETED: 'badge-live',
    Order.RefundStatus.REJECTED: 'badge-danger',
    OrderItem.FulfillmentStatus.PENDING: 'badge-processing',
    OrderItem.FulfillmentStatus.ACCEPTED: 'badge-live',
    OrderItem.FulfillmentStatus.REJECTED: 'badge-danger',
    OrderItem.FulfillmentStatus.PACKED: 'badge-processing',
    OrderItem.FulfillmentStatus.SHIPPED: 'badge-shipped',
    OrderItem.FulfillmentStatus.DELIVERED: 'badge-delivered',
}

PAYMENT_METHOD_BADGE_MAP = {
    Order.PaymentMethod.CASH: 'badge-processing',
    Order.PaymentMethod.CARD: 'badge-live',
    Order.PaymentMethod.UPI: 'badge-live',
    Order.PaymentMethod.QRCODE: 'badge-live',
}


def get_status_badge(value):
    return STATUS_BADGE_MAP.get(value, 'badge-muted')


def build_payment_dashboard_context(
    search_query='',
    payment_method='',
    payment_status='',
    account_receipt_status='',
    return_status='',
    refund_status='',
    actor=None,
    is_admin=True,
):
    search_query = (search_query or '').strip()
    payment_method = (payment_method or '').strip()
    payment_status = (payment_status or '').strip()
    account_receipt_status = (account_receipt_status or '').strip()
    return_status = (return_status or '').strip()
    refund_status = (refund_status or '').strip()

    order_amount_map = {}
    if is_admin:
        orders_queryset = Order.objects.select_related('user', 'delivery_partner').order_by('-created_at')
        if search_query:
            orders_queryset = orders_queryset.filter(
                Q(order_id__icontains=search_query)
                | Q(full_name__icontains=search_query)
                | Q(user__username__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(delivery_partner__username__icontains=search_query)
                | Q(delivery_partner__email__icontains=search_query)
                | Q(payment_reference__icontains=search_query)
                | Q(refund_reference__icontains=search_query)
            )

        if payment_method:
            orders_queryset = orders_queryset.filter(payment_method=payment_method)
        if payment_status:
            orders_queryset = orders_queryset.filter(payment_status=payment_status)
        if account_receipt_status:
            orders_queryset = orders_queryset.filter(account_receipt_status=account_receipt_status)
        if return_status:
            orders_queryset = orders_queryset.filter(return_status=return_status)
        if refund_status:
            orders_queryset = orders_queryset.filter(refund_status=refund_status)

        orders = list(orders_queryset)
        order_amount_map = {
            order.id: (order.total_price or Decimal('0.00'))
            for order in orders
        }
    else:
        vendor_items_queryset = OrderItem.objects.filter(vendor=actor).select_related('order', 'order__user', 'order__delivery_partner')
        if search_query:
            vendor_items_queryset = vendor_items_queryset.filter(
                Q(order__order_id__icontains=search_query)
                | Q(order__full_name__icontains=search_query)
                | Q(order__user__username__icontains=search_query)
                | Q(order__user__email__icontains=search_query)
                | Q(order__delivery_partner__username__icontains=search_query)
                | Q(order__delivery_partner__email__icontains=search_query)
                | Q(order__payment_reference__icontains=search_query)
                | Q(order__refund_reference__icontains=search_query)
            )

        if payment_method:
            vendor_items_queryset = vendor_items_queryset.filter(order__payment_method=payment_method)
        if payment_status:
            vendor_items_queryset = vendor_items_queryset.filter(order__payment_status=payment_status)
        if account_receipt_status:
            vendor_items_queryset = vendor_items_queryset.filter(order__account_receipt_status=account_receipt_status)
        if return_status:
            vendor_items_queryset = vendor_items_queryset.filter(order__return_status=return_status)
        if refund_status:
            vendor_items_queryset = vendor_items_queryset.filter(order__refund_status=refund_status)

        vendor_items = list(vendor_items_queryset)
        for item in vendor_items:
            order_amount_map.setdefault(item.order_id, Decimal('0.00'))
            order_amount_map[item.order_id] += (item.price or Decimal('0.00')) * (item.quantity or 0)

        orders = list(
            Order.objects.select_related('user', 'delivery_partner')
            .filter(id__in=list(order_amount_map.keys()))
            .order_by('-created_at')
        )

    total_amount = sum(order_amount_map.values(), Decimal('0.00'))
    refunded_amount = sum((order.refund_amount or Decimal('0.00')) for order in orders)

    payment_breakdown = []
    payment_labels = dict(Order.PaymentMethod.choices)
    total_orders = len(orders)
    for method_value, method_label in Order.PaymentMethod.choices:
        method_orders = [order for order in orders if order.payment_method == method_value]
        method_total = sum((order_amount_map.get(order.id) or Decimal('0.00')) for order in method_orders)
        payment_breakdown.append(
            {
                'value': method_value,
                'label': method_label,
                'count': len(method_orders),
                'total': method_total,
                'share': round((len(method_orders) / total_orders) * 100) if total_orders else 0,
                'badge_class': PAYMENT_METHOD_BADGE_MAP.get(method_value, 'badge-muted'),
            }
        )

    refund_summary = [
        {
            'label': 'No Return',
            'count': sum(1 for order in orders if order.return_status == Order.ReturnStatus.NONE),
            'badge_class': 'badge-muted',
        },
        {
            'label': 'Return Requested',
            'count': sum(1 for order in orders if order.return_status == Order.ReturnStatus.REQUESTED),
            'badge_class': 'badge-processing',
        },
        {
            'label': 'Refund In Process',
            'count': sum(
                1
                for order in orders
                if order.refund_status in {Order.RefundStatus.PENDING, Order.RefundStatus.PROCESSING}
            ),
            'badge_class': 'badge-processing',
        },
        {
            'label': 'Refund Completed',
            'count': sum(1 for order in orders if order.refund_status == Order.RefundStatus.COMPLETED),
            'badge_class': 'badge-live',
        },
    ]

    for order in orders:
        order.dashboard_amount = order_amount_map.get(order.id, order.total_price or Decimal('0.00'))
        order.method_badge_class = PAYMENT_METHOD_BADGE_MAP.get(order.payment_method, 'badge-muted')
        order.payment_badge_class = get_status_badge(order.payment_status)
        order.account_receipt_badge_class = get_status_badge(order.account_receipt_status)
        order.return_badge_class = get_status_badge(order.return_status)
        order.refund_badge_class = get_status_badge(order.refund_status)
        order.refund_amount_value = order.refund_amount or Decimal('0.00')
        order.delivery_partner_name = order.delivery_partner.display_name if order.delivery_partner else 'Unassigned'
        order.show_payment_meta = bool(
            order.refund_amount
            or order.refund_reference
            or order.refund_processed_at
            or order.account_receipt_reference
            or order.account_receipt_confirmed_at
            or order.payment_notes
        )

    return {
        'orders': orders,
        'payment_breakdown': payment_breakdown,
        'refund_summary': refund_summary,
        'filters': {
            'search_query': search_query,
            'payment_method': payment_method,
            'payment_status': payment_status,
            'account_receipt_status': account_receipt_status,
            'return_status': return_status,
            'refund_status': refund_status,
        },
        'summary_cards': [
            {
                'label': 'Visible Orders',
                'value': total_orders,
                'subtext': 'Orders in the current view',
            },
            {
                'label': 'Gross Collection' if is_admin else 'Vendor Collection',
                'value': f'Rs. {total_amount}',
                'subtext': 'Combined value of visible orders',
            },
            {
                'label': 'Returns Raised',
                'value': sum(1 for order in orders if order.return_status != Order.ReturnStatus.NONE),
                'subtext': 'Orders with any return activity',
            },
            {
                'label': 'Received in Account',
                'value': sum(1 for order in orders if order.account_receipt_status == Order.AccountReceiptStatus.RECEIVED),
                'subtext': 'Payments confirmed in your account',
            },
            {
                'label': 'Refunded Amount',
                'value': f'Rs. {refunded_amount}',
                'subtext': 'Total refund amount recorded',
            },
            {
                'label': 'Refund In Process',
                'value': sum(
                    1
                    for order in orders
                    if order.refund_status in {Order.RefundStatus.PENDING, Order.RefundStatus.PROCESSING}
                ),
                'subtext': 'Refunds still being worked on',
            },
            {
                'label': 'Refund Completed',
                'value': sum(1 for order in orders if order.refund_status == Order.RefundStatus.COMPLETED),
                'subtext': 'Orders already refunded',
            },
        ],
        'payment_method_choices': Order.PaymentMethod.choices,
        'payment_status_choices': Order.PaymentStatus.choices,
        'account_receipt_status_choices': Order.AccountReceiptStatus.choices,
        'return_status_choices': Order.ReturnStatus.choices,
        'refund_status_choices': Order.RefundStatus.choices,
        'payment_method_labels': payment_labels,
        'dashboard_eyebrow': 'Admin Payment Management' if is_admin else 'Vendor Payment Management',
        'dashboard_title': 'Orders, Payments, Returns and Refunds',
        'dashboard_description': (
            'Track every customer order payment, refund flow, and payment mix across the full platform.'
            if is_admin
            else 'Track payment information for orders that include your products and monitor return, refund, and account receipt progress.'
        ),
        'back_url_name': 'admin_control_center' if is_admin else 'vendor_dashboard',
        'back_label': 'Back to Admin Control' if is_admin else 'Back to Vendor Dashboard',
        'dashboard_url_name': 'payment_management_dashboard' if is_admin else 'vendor_payment_dashboard',
        'can_manage_payments': is_admin,
        'show_order_admin_link': is_admin,
    }


def sync_order_status_from_items(order):
    item_statuses = list(order.items.values_list('fulfillment_status', flat=True))
    if not item_statuses:
        return

    if all(status == OrderItem.FulfillmentStatus.REJECTED for status in item_statuses):
        next_status = Order.Status.CANCELLED
    elif all(status == OrderItem.FulfillmentStatus.DELIVERED for status in item_statuses):
        next_status = Order.Status.DELIVERED
    elif any(
        status in {OrderItem.FulfillmentStatus.SHIPPED, OrderItem.FulfillmentStatus.DELIVERED}
        for status in item_statuses
    ):
        next_status = Order.Status.SHIPPED
    else:
        next_status = Order.Status.PROCESSING

    if order.status != next_status:
        order.status = next_status
        order.save(update_fields=['status'])


DELIVERY_ITEM_STATUS_CHOICES = [
    (OrderItem.FulfillmentStatus.SHIPPED, 'Out for Delivery'),
    (OrderItem.FulfillmentStatus.DELIVERED, 'Delivered'),
    (OrderItem.FulfillmentStatus.REJECTED, 'Cancelled'),
]


def build_delivery_dashboard_context(actor, search_query='', order_status='', payment_status=''):
    search_query = (search_query or '').strip()
    order_status = (order_status or '').strip()
    payment_status = (payment_status or '').strip()

    orders_queryset = (
        Order.objects.select_related('user', 'delivery_partner')
        .prefetch_related('items', 'items__vendor')
        .filter(delivery_partner=actor)
        .order_by('-created_at')
    )

    if search_query:
        orders_queryset = orders_queryset.filter(
            Q(order_id__icontains=search_query)
            | Q(full_name__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(address__icontains=search_query)
            | Q(city__icontains=search_query)
            | Q(district__icontains=search_query)
            | Q(state__icontains=search_query)
            | Q(mobile__icontains=search_query)
            | Q(payment_reference__icontains=search_query)
        )
    if order_status:
        orders_queryset = orders_queryset.filter(status=order_status)
    if payment_status:
        orders_queryset = orders_queryset.filter(payment_status=payment_status)

    orders = list(orders_queryset)
    order_groups = []
    for order in orders:
        order.order_badge_class = (
            'badge-delivered'
            if order.status == Order.Status.DELIVERED
            else 'badge-cancelled'
            if order.status == Order.Status.CANCELLED
            else 'badge-shipped'
            if order.status == Order.Status.SHIPPED
            else 'badge-processing'
        )
        order.method_badge_class = PAYMENT_METHOD_BADGE_MAP.get(order.payment_method, 'badge-muted')
        order.payment_badge_class = get_status_badge(order.payment_status)
        order.account_receipt_badge_class = get_status_badge(order.account_receipt_status)
        order.can_collect_cash = (
            order.payment_method == Order.PaymentMethod.CASH
            and order.payment_status in {Order.PaymentStatus.PENDING, Order.PaymentStatus.FAILED}
        )
        order.can_collect_qr = order.can_collect_cash and bool(getattr(settings, 'PAYMENT_UPI_ID', '').strip())
        order.delivery_qr_image_url = build_delivery_qr_image_url(order) if order.can_collect_qr else ''
        order.show_payment_notes = bool((order.payment_notes or '').strip())
        order.items_for_dashboard = []
        order.visible_total = Decimal('0.00')

        for item in order.items.all():
            product = item.content_object
            item.product_name = getattr(product, 'product_name', 'Product')
            item.product_image_url = getattr(getattr(product, 'front_image', None), 'url', '')
            item.ordered_unit_price = item.price or Decimal('0.00')
            item.current_catalog_price = getattr(product, 'price', item.ordered_unit_price) or item.ordered_unit_price
            item.line_total = item.ordered_unit_price * (item.quantity or 0)
            item.has_price_mismatch = item.current_catalog_price != item.ordered_unit_price
            item.fulfillment_badge_class = get_status_badge(item.fulfillment_status)
            order.visible_total += item.line_total
            order.items_for_dashboard.append(item)

        order.subtotal = order.visible_total
        order.shipping_amount = max((order.total_price or Decimal('0.00')) - order.subtotal, Decimal('0.00'))
        order.amount_due = order.total_price or order.subtotal
        order.has_price_mismatch = any(item.has_price_mismatch for item in order.items_for_dashboard)

        order_groups.append(order)

    pending_collection_count = sum(1 for order in orders if order.can_collect_cash)
    delivered_count = sum(1 for order in orders if order.status == Order.Status.DELIVERED)
    shipped_count = sum(1 for order in orders if order.status == Order.Status.SHIPPED)
    cancelled_count = sum(1 for order in orders if order.status == Order.Status.CANCELLED)

    return {
        'orders': order_groups,
        'filters': {
            'search_query': search_query,
            'order_status': order_status,
            'payment_status': payment_status,
        },
        'summary_cards': [
            {
                'label': 'Assigned Orders',
                'value': len(order_groups),
                'subtext': 'Orders currently in your delivery queue',
            },
            {
                'label': 'Awaiting Collection',
                'value': pending_collection_count,
                'subtext': 'COD orders still waiting for payment collection',
            },
            {
                'label': 'Out for Delivery',
                'value': shipped_count,
                'subtext': 'Orders already marked on the way',
            },
            {
                'label': 'Delivered',
                'value': delivered_count,
                'subtext': 'Orders completed successfully',
            },
            {
                'label': 'Cancelled',
                'value': cancelled_count,
                'subtext': 'Orders cancelled during delivery flow',
            },
        ],
        'order_status_choices': Order.Status.choices,
        'payment_status_choices': Order.PaymentStatus.choices,
        'fulfillment_status_choices': DELIVERY_ITEM_STATUS_CHOICES,
        'dashboard_eyebrow': 'Delivery Partner Dashboard',
        'dashboard_title': 'Manage doorstep delivery and COD collections',
        'dashboard_description': (
            'Review your assigned orders, open the exact-amount QR for COD customers, and update delivery status so admin sees the latest result instantly.'
        ),
        'back_url_name': 'my_account',
        'back_label': 'Back to My Account',
        'qr_is_available': bool(getattr(settings, 'PAYMENT_UPI_ID', '').strip()),
        'upi_id': getattr(settings, 'PAYMENT_UPI_ID', '').strip(),
    }


def build_order_management_context(
    actor=None,
    is_admin=True,
    search_query='',
    state='',
    district='',
    country='',
    fulfillment_status='',
    payment_method='',
):
    search_query = (search_query or '').strip()
    state = (state or '').strip()
    district = (district or '').strip()
    country = (country or '').strip()
    fulfillment_status = (fulfillment_status or '').strip()
    payment_method = (payment_method or '').strip()

    items_queryset = OrderItem.objects.select_related('order', 'order__user', 'order__delivery_partner', 'vendor').order_by('-order__created_at', 'id')
    if not is_admin:
        items_queryset = items_queryset.filter(vendor=actor)

    if search_query:
        items_queryset = items_queryset.filter(
            Q(order__order_id__icontains=search_query)
            | Q(order__full_name__icontains=search_query)
            | Q(order__user__username__icontains=search_query)
            | Q(order__user__email__icontains=search_query)
            | Q(order__delivery_partner__username__icontains=search_query)
            | Q(order__delivery_partner__email__icontains=search_query)
            | Q(order__address__icontains=search_query)
            | Q(order__city__icontains=search_query)
            | Q(order__district__icontains=search_query)
            | Q(order__state__icontains=search_query)
            | Q(order__country__icontains=search_query)
        )
    if state:
        items_queryset = items_queryset.filter(order__state__icontains=state)
    if district:
        items_queryset = items_queryset.filter(
            Q(order__district__icontains=district) | Q(order__city__icontains=district)
        )
    if country:
        items_queryset = items_queryset.filter(order__country__icontains=country)
    if fulfillment_status:
        items_queryset = items_queryset.filter(fulfillment_status=fulfillment_status)
    if payment_method:
        items_queryset = items_queryset.filter(order__payment_method=payment_method)

    items = list(items_queryset)
    order_groups = []
    grouped_by_order = {}
    for item in items:
        product = item.content_object
        item.product_name = getattr(product, 'product_name', 'Product')
        item.product_image_url = getattr(getattr(product, 'front_image', None), 'url', '')
        item.line_total = (item.price or Decimal('0.00')) * (item.quantity or 0)
        item.fulfillment_badge_class = get_status_badge(item.fulfillment_status)

        order = item.order
        group = grouped_by_order.get(order.id)
        if not group:
            order.order_badge_class = (
                'badge-delivered'
                if order.status == Order.Status.DELIVERED
                else 'badge-cancelled'
                if order.status == Order.Status.CANCELLED
                else 'badge-shipped'
                if order.status == Order.Status.SHIPPED
                else 'badge-processing'
            )
            order.method_badge_class = PAYMENT_METHOD_BADGE_MAP.get(order.payment_method, 'badge-muted')
            order.delivery_partner_name = order.delivery_partner.display_name if order.delivery_partner else 'Unassigned'
            group = {
                'order': order,
                'items': [],
                'visible_total': Decimal('0.00'),
            }
            grouped_by_order[order.id] = group
            order_groups.append(group)

        group['items'].append(item)
        group['visible_total'] += item.line_total

    return {
        'order_groups': order_groups,
        'filters': {
            'search_query': search_query,
            'state': state,
            'district': district,
            'country': country,
            'fulfillment_status': fulfillment_status,
            'payment_method': payment_method,
        },
        'summary_cards': [
            {
                'label': 'Visible Orders',
                'value': len(order_groups),
                'subtext': 'Grouped by customer order',
            },
            {
                'label': 'Visible Order Items',
                'value': len(items),
                'subtext': 'Products currently in the result set',
            },
            {
                'label': 'Pending Action',
                'value': sum(1 for item in items if item.fulfillment_status == OrderItem.FulfillmentStatus.PENDING),
                'subtext': 'Items still waiting for review',
            },
            {
                'label': 'Accepted',
                'value': sum(
                    1 for item in items if item.fulfillment_status in {OrderItem.FulfillmentStatus.ACCEPTED, OrderItem.FulfillmentStatus.PACKED}
                ),
                'subtext': 'Items accepted for fulfillment',
            },
            {
                'label': 'Shipped / Delivered',
                'value': sum(
                    1
                    for item in items
                    if item.fulfillment_status in {OrderItem.FulfillmentStatus.SHIPPED, OrderItem.FulfillmentStatus.DELIVERED}
                ),
                'subtext': 'Items already moving or completed',
            },
            {
                'label': 'Rejected',
                'value': sum(1 for item in items if item.fulfillment_status == OrderItem.FulfillmentStatus.REJECTED),
                'subtext': 'Items declined for fulfillment',
            },
        ],
        'fulfillment_status_choices': OrderItem.FulfillmentStatus.choices,
        'payment_method_choices': Order.PaymentMethod.choices,
        'dashboard_eyebrow': 'Admin Order Management' if is_admin else 'Vendor Order Management',
        'dashboard_title': 'Manage order acceptance and delivery flow',
        'dashboard_description': (
            'Review incoming orders, filter them by shipping destination, and manage item-level fulfillment across the platform.'
            if is_admin
            else 'Review orders for your own products, accept or reject them, and keep delivery progress updated by location.'
        ),
        'back_url_name': 'admin_control_center' if is_admin else 'vendor_dashboard',
        'back_label': 'Back to Admin Control' if is_admin else 'Back to Vendor Dashboard',
        'can_manage_orders': True,
        'show_vendor_column': is_admin,
        'show_delivery_assignment': is_admin,
        'delivery_partners': get_delivery_partners() if is_admin else [],
    }


@login_required(login_url='login_register')
def vendor_dashboard(request):
    if getattr(request.user, 'has_admin_access', False) and not getattr(request.user, 'is_vendor_account', False):
        return redirect('admin_control_center')

    access_response = ensure_vendor_access(request)
    if access_response:
        return access_response

    vendor_profile = ensure_vendor_profile(request.user)
    profile_form = VendorProfileForm(request.POST or None, instance=vendor_profile)

    if request.method == 'POST':
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Vendor profile updated successfully.')
            return redirect('vendor_dashboard')
        messages.error(request, 'Could not save the profile update. Please review the form details.')

    context = build_vendor_dashboard_context(request.user, profile_form=profile_form)
    return render(request, 'accounts/vendor_dashboard.html', context)


@login_required(login_url='login_register')
def vendor_product_create(request, catalog):
    return vendor_product_upsert(request, catalog)


@login_required(login_url='login_register')
def vendor_product_edit(request, catalog, product_id):
    return vendor_product_upsert(request, catalog, product_id=product_id)


def vendor_product_upsert(request, catalog, product_id=None):
    access_response = ensure_vendor_access(request, allow_admin=True)
    if access_response:
        return access_response

    config = get_catalog_config(catalog)
    if not config:
        messages.error(request, 'Unknown catalog selected.')
        return redirect('vendor_dashboard')

    product = get_managed_product(request, catalog, product_id) if product_id else config['product_model']()
    owner = product.vendor or request.user
    sale_instance = get_primary_sale_for_product(product, config.get('sale_model'))

    ProductForm = config['product_form']
    VariationFormSet = config['variation_formset']
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    GalleryFormSet = config['gallery_formset']
    formset = VariationFormSet(request.POST or None, instance=product, prefix=f'{catalog}_variations')
    gallery_formset = GalleryFormSet(
        request.POST or None,
        request.FILES or None,
        instance=product,
        prefix=f'{catalog}_gallery',
    )
    sale_form = ProductSaleForm(
        request.POST or None,
        sale_instance=sale_instance,
        prefix=f'{catalog}_sale',
    )

    if request.method == 'POST' and form.is_valid() and formset.is_valid() and gallery_formset.is_valid() and sale_form.is_valid():
        saved_product = form.save(commit=False)
        saved_product.vendor = product.vendor or owner
        saved_product.designer = (
            form.cleaned_data.get('designer')
            or product.designer
            or get_vendor_designer(saved_product.vendor, config['designer_gender'])
        )
        saved_product.gender = config['gender_value']
        saved_product.slug = build_unique_slug(config['product_model'], saved_product.product_name, instance_id=product_id)

        if catalog == 'men' and not saved_product.back_image:
            saved_product.back_image = saved_product.front_image

        saved_product.save()
        formset.instance = saved_product
        formset.save()
        gallery_formset.instance = saved_product
        gallery_formset.save()
        sale = sale_form.save(saved_product, config['sale_model'])
        sync_product_categories(saved_product, catalog)

        if sale:
            messages.success(
                request,
                f'{saved_product.product_name} was saved and added to the sale list with {sale.discount_percentage:g}% off.',
            )
        elif sale_instance:
            messages.success(request, f'{saved_product.product_name} was saved and removed from the sale list.')
        else:
            messages.success(request, f'{saved_product.product_name} was saved successfully.')
        if request.POST.get('return_to') == 'admin' and getattr(request.user, 'has_admin_access', False):
            return redirect('admin_control_center')
        return redirect('vendor_dashboard')

    if request.method == 'POST':
        messages.error(request, 'The product could not be saved. Please review the form, variation, and sale details.')

    context = {
        'catalog': catalog,
        'catalog_label': config['label'],
        'form': form,
        'formset': formset,
        'gallery_formset': gallery_formset,
        'sale_form': sale_form,
        'sale_instance': sale_instance,
        'sale_status': get_sale_status_label(sale_instance),
        'is_edit_mode': product_id is not None,
        'product': product,
        'return_to': request.GET.get('source') or request.POST.get('return_to', ''),
    }
    return render(request, 'accounts/vendor_product_form.html', context)


@require_POST
@login_required(login_url='login_register')
def vendor_product_delete(request, catalog, product_id):
    access_response = ensure_vendor_access(request, allow_admin=True)
    if access_response:
        return access_response

    product = get_managed_product(request, catalog, product_id)
    product_name = product.product_name
    product.delete()
    messages.success(request, f'{product_name} was deleted successfully.')

    if request.POST.get('return_to') == 'admin' and getattr(request.user, 'has_admin_access', False):
        return redirect('admin_control_center')
    return redirect('vendor_dashboard')


@login_required(login_url='login_register')
def admin_control_center(request):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    context = build_admin_control_context(
        user_query=request.GET.get('user_q', ''),
        product_query=request.GET.get('product_q', ''),
    )
    return render(request, 'accounts/admin_control_center.html', context)


@login_required(login_url='login_register')
def payment_management_dashboard(request):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    context = build_payment_dashboard_context(
        search_query=request.GET.get('q', ''),
        payment_method=request.GET.get('payment_method', ''),
        payment_status=request.GET.get('payment_status', ''),
        account_receipt_status=request.GET.get('account_receipt_status', ''),
        return_status=request.GET.get('return_status', ''),
        refund_status=request.GET.get('refund_status', ''),
        actor=request.user,
        is_admin=True,
    )
    return render(request, 'accounts/payment_management_dashboard.html', context)


@login_required(login_url='login_register')
def vendor_payment_dashboard(request):
    access_response = ensure_vendor_access(request, allow_admin=False)
    if access_response:
        return access_response

    context = build_payment_dashboard_context(
        search_query=request.GET.get('q', ''),
        payment_method=request.GET.get('payment_method', ''),
        payment_status=request.GET.get('payment_status', ''),
        account_receipt_status=request.GET.get('account_receipt_status', ''),
        return_status=request.GET.get('return_status', ''),
        refund_status=request.GET.get('refund_status', ''),
        actor=request.user,
        is_admin=False,
    )
    return render(request, 'accounts/payment_management_dashboard.html', context)


@login_required(login_url='login_register')
def delivery_dashboard(request):
    access_response = ensure_delivery_access(request)
    if access_response:
        return access_response

    context = build_delivery_dashboard_context(
        actor=request.user,
        search_query=request.GET.get('q', ''),
        order_status=request.GET.get('order_status', ''),
        payment_status=request.GET.get('payment_status', ''),
    )
    return render(request, 'accounts/delivery_dashboard.html', context)


@require_POST
@login_required(login_url='login_register')
def assign_delivery_partner(request, order_id):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    order = get_object_or_404(Order, pk=order_id)
    partner_id = (request.POST.get('delivery_partner_id') or '').strip()

    if not partner_id:
        order.delivery_partner = None
        order.delivery_assigned_at = None
        order.save(update_fields=['delivery_partner', 'delivery_assigned_at'])
        messages.success(request, f'Delivery partner assignment cleared for order #{order.order_id or order.id}.')
        return redirect(request.POST.get('next') or 'admin_order_management_dashboard')

    delivery_partner = get_object_or_404(
        Account.objects.filter(account_type=Account.AccountType.DELIVERY_PARTNER),
        pk=partner_id,
    )
    order.delivery_partner = delivery_partner
    order.delivery_assigned_at = timezone.now()
    order.save(update_fields=['delivery_partner', 'delivery_assigned_at'])
    messages.success(
        request,
        f'Order #{order.order_id or order.id} assigned to delivery partner {delivery_partner.display_name}.',
    )
    return redirect(request.POST.get('next') or 'admin_order_management_dashboard')


@require_POST
@login_required(login_url='login_register')
def delivery_collect_payment(request, order_id):
    access_response = ensure_delivery_access(request)
    if access_response:
        return access_response

    order = get_object_or_404(Order, pk=order_id, delivery_partner=request.user)

    if order.payment_method != Order.PaymentMethod.CASH:
        messages.error(request, 'Only cash-on-delivery orders can be collected from the delivery dashboard.')
        return redirect(request.POST.get('next') or 'delivery_dashboard')

    if order.payment_status == Order.PaymentStatus.PAID:
        messages.info(request, f'Payment for order #{order.order_id or order.id} is already marked as paid.')
        return redirect(request.POST.get('next') or 'delivery_dashboard')

    collection_mode = (request.POST.get('collection_mode') or '').strip().lower()
    collected_at = timezone.localtime(timezone.now()).strftime('%d %b %Y, %I:%M %p')

    if collection_mode == 'cash':
        order.payment_status = Order.PaymentStatus.PAID
        order.account_receipt_status = Order.AccountReceiptStatus.NOT_RECEIVED
        order.account_receipt_reference = ''
        order.account_receipt_confirmed_at = None
        order.payment_reference = (request.POST.get('payment_reference') or '').strip() or 'Cash collected on delivery'
        order.payment_notes = append_note(
            order.payment_notes,
            f'Cash collected on delivery by {request.user.display_name} on {collected_at}.',
        )
        order.save(
            update_fields=[
                'payment_status',
                'account_receipt_status',
                'account_receipt_reference',
                'account_receipt_confirmed_at',
                'payment_reference',
                'payment_notes',
            ]
        )
        messages.success(request, f'Cash collection saved for order #{order.order_id or order.id}.')
        return redirect(request.POST.get('next') or 'delivery_dashboard')

    if collection_mode == 'qrcode':
        payment_reference = (request.POST.get('payment_reference') or '').strip()
        if payment_reference not in {'', None} and len(payment_reference) != 12:
            # Keep the regex validation below as the single source of truth.
            payment_reference = payment_reference.strip()
        if not payment_reference or not payment_reference.isdigit() or len(payment_reference) != 12:
            messages.error(request, 'Enter the 12-digit UTR received after QR payment.')
            return redirect(request.POST.get('next') or 'delivery_dashboard')

        order.payment_method = Order.PaymentMethod.QRCODE
        order.payment_status = Order.PaymentStatus.PAID
        order.account_receipt_status = Order.AccountReceiptStatus.PENDING
        order.account_receipt_reference = payment_reference
        order.account_receipt_confirmed_at = None
        order.payment_reference = payment_reference
        order.payment_notes = append_note(
            order.payment_notes,
            f'Collected through delivery QR by {request.user.display_name} on {collected_at}.',
        )
        order.save(
            update_fields=[
                'payment_method',
                'payment_status',
                'account_receipt_status',
                'account_receipt_reference',
                'account_receipt_confirmed_at',
                'payment_reference',
                'payment_notes',
            ]
        )
        messages.success(request, f'QR payment saved for order #{order.order_id or order.id}.')
        return redirect(request.POST.get('next') or 'delivery_dashboard')

    messages.error(request, 'Choose a valid collection mode before saving payment.')
    return redirect(request.POST.get('next') or 'delivery_dashboard')


@login_required(login_url='login_register')
def admin_order_management_dashboard(request):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    context = build_order_management_context(
        actor=request.user,
        is_admin=True,
        search_query=request.GET.get('q', ''),
        state=request.GET.get('state', ''),
        district=request.GET.get('district', ''),
        country=request.GET.get('country', ''),
        fulfillment_status=request.GET.get('fulfillment_status', ''),
        payment_method=request.GET.get('payment_method', ''),
    )
    return render(request, 'accounts/order_management_dashboard.html', context)


@login_required(login_url='login_register')
def vendor_order_management_dashboard(request):
    access_response = ensure_vendor_access(request, allow_admin=False)
    if access_response:
        return access_response

    context = build_order_management_context(
        actor=request.user,
        is_admin=False,
        search_query=request.GET.get('q', ''),
        state=request.GET.get('state', ''),
        district=request.GET.get('district', ''),
        country=request.GET.get('country', ''),
        fulfillment_status=request.GET.get('fulfillment_status', ''),
        payment_method=request.GET.get('payment_method', ''),
    )
    return render(request, 'accounts/order_management_dashboard.html', context)


@require_POST
@login_required(login_url='login_register')
def update_order_item_status(request, item_id):
    is_admin = getattr(request.user, 'has_admin_access', False)
    is_vendor = getattr(request.user, 'is_vendor_account', False)
    is_delivery_partner = getattr(request.user, 'is_delivery_partner_account', False)

    if not is_admin and not is_vendor and not is_delivery_partner:
        messages.error(request, 'You do not have permission to manage order items.')
        return redirect('my_account')

    items_queryset = OrderItem.objects.select_related('order', 'vendor')
    if is_vendor and not is_admin:
        items_queryset = items_queryset.filter(vendor=request.user)
    elif is_delivery_partner and not is_admin:
        items_queryset = items_queryset.filter(order__delivery_partner=request.user)

    order_item = get_object_or_404(items_queryset, pk=item_id)
    valid_statuses = {choice[0] for choice in OrderItem.FulfillmentStatus.choices}
    if is_delivery_partner:
        valid_statuses = {value for value, _label in DELIVERY_ITEM_STATUS_CHOICES}
    next_status = (request.POST.get('fulfillment_status') or '').strip()
    if next_status not in valid_statuses:
        messages.error(request, 'The selected order status is not valid.')
        return redirect(
            request.POST.get('next')
            or (
                'admin_order_management_dashboard'
                if is_admin
                else 'delivery_dashboard'
                if is_delivery_partner
                else 'vendor_order_management_dashboard'
            )
        )

    if (
        is_delivery_partner
        and next_status == OrderItem.FulfillmentStatus.DELIVERED
        and order_item.order.payment_method == Order.PaymentMethod.CASH
        and order_item.order.payment_status != Order.PaymentStatus.PAID
    ):
        messages.error(
            request,
            'Collect the COD payment first, or confirm the QR payment, before marking this order as delivered.',
        )
        return redirect(request.POST.get('next') or 'delivery_dashboard')

    order_item.fulfillment_status = next_status
    order_item.status_notes = (request.POST.get('status_notes') or '').strip()
    order_item.save(update_fields=['fulfillment_status', 'status_notes', 'status_updated_at'])
    sync_order_status_from_items(order_item.order)

    messages.success(
        request,
        f'Order item "{order_item}" updated to {order_item.fulfillment_status}.',
    )
    return redirect(
        request.POST.get('next')
        or (
            'admin_order_management_dashboard'
            if is_admin
            else 'delivery_dashboard'
            if is_delivery_partner
            else 'vendor_order_management_dashboard'
        )
    )


@require_POST
@login_required(login_url='login_register')
def admin_update_payment_record(request, order_id):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    order = get_object_or_404(Order, pk=order_id)
    valid_payment_statuses = {choice[0] for choice in Order.PaymentStatus.choices}
    valid_account_receipt_statuses = {choice[0] for choice in Order.AccountReceiptStatus.choices}
    valid_return_statuses = {choice[0] for choice in Order.ReturnStatus.choices}
    valid_refund_statuses = {choice[0] for choice in Order.RefundStatus.choices}

    selected_payment_status = (request.POST.get('payment_status') or '').strip()
    selected_account_receipt_status = (request.POST.get('account_receipt_status') or '').strip()
    selected_return_status = (request.POST.get('return_status') or '').strip()
    selected_refund_status = (request.POST.get('refund_status') or '').strip()

    if selected_payment_status not in valid_payment_statuses:
        messages.error(request, 'The selected payment status is not valid.')
        return redirect(request.POST.get('next') or 'payment_management_dashboard')
    if selected_account_receipt_status not in valid_account_receipt_statuses:
        messages.error(request, 'The selected account receipt status is not valid.')
        return redirect(request.POST.get('next') or 'payment_management_dashboard')
    if selected_return_status not in valid_return_statuses:
        messages.error(request, 'The selected return status is not valid.')
        return redirect(request.POST.get('next') or 'payment_management_dashboard')
    if selected_refund_status not in valid_refund_statuses:
        messages.error(request, 'The selected refund status is not valid.')
        return redirect(request.POST.get('next') or 'payment_management_dashboard')

    refund_amount_raw = (request.POST.get('refund_amount') or '').strip()
    refund_amount = None
    if refund_amount_raw:
        try:
            refund_amount = Decimal(refund_amount_raw)
        except InvalidOperation:
            messages.error(request, 'Please enter a valid refund amount.')
            return redirect(request.POST.get('next') or 'payment_management_dashboard')

        if refund_amount < 0:
            messages.error(request, 'Refund amount cannot be negative.')
            return redirect(request.POST.get('next') or 'payment_management_dashboard')

    order.return_status = selected_return_status
    order.refund_status = selected_refund_status
    order.account_receipt_status = selected_account_receipt_status
    order.account_receipt_reference = (request.POST.get('account_receipt_reference') or '').strip()
    order.refund_amount = refund_amount
    order.refund_reference = (request.POST.get('refund_reference') or '').strip()
    order.payment_notes = (request.POST.get('payment_notes') or '').strip()

    if selected_refund_status == Order.RefundStatus.COMPLETED:
        order.payment_status = Order.PaymentStatus.REFUNDED
        order.refund_processed_at = timezone.now()
        if order.refund_amount is None:
            order.refund_amount = order.total_price
    elif selected_refund_status in {Order.RefundStatus.PENDING, Order.RefundStatus.PROCESSING}:
        order.payment_status = Order.PaymentStatus.REFUND_IN_PROCESS
        order.refund_processed_at = None
    else:
        order.payment_status = selected_payment_status
        if selected_refund_status != Order.RefundStatus.COMPLETED:
            order.refund_processed_at = None

    if selected_account_receipt_status == Order.AccountReceiptStatus.RECEIVED:
        order.account_receipt_confirmed_at = timezone.now()
    else:
        order.account_receipt_confirmed_at = None

    order.save(
        update_fields=[
            'payment_status',
            'account_receipt_status',
            'account_receipt_reference',
            'account_receipt_confirmed_at',
            'return_status',
            'refund_status',
            'refund_amount',
            'refund_reference',
            'refund_processed_at',
            'payment_notes',
        ]
    )
    messages.success(request, f'Payment record for order #{order.order_id or order.id} updated.')
    return redirect(request.POST.get('next') or 'payment_management_dashboard')


@require_POST
@login_required(login_url='login_register')
def admin_mark_order_delivered(request, order_id):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    order = Order.objects.filter(pk=order_id).first()
    if not order:
        messages.error(request, f'Order #{order_id} was not found or has been removed.')
        return redirect('admin_control_center')

    if order.status == Order.Status.DELIVERED:
        messages.info(request, f'Order #{order.order_id or order.id} is already marked as delivered.')
        return redirect('admin_control_center')

    if order.status == Order.Status.CANCELLED:
        messages.error(request, 'Cancelled orders cannot be marked as delivered.')
        return redirect(request.POST.get('next') or 'admin_control_center')

    order.items.exclude(fulfillment_status=OrderItem.FulfillmentStatus.REJECTED).update(
        fulfillment_status=OrderItem.FulfillmentStatus.DELIVERED,
        status_updated_at=timezone.now(),
    )
    order.status = Order.Status.DELIVERED
    order.save(update_fields=['status'])
    messages.success(request, f'Order #{order.order_id or order.id} marked as delivered. Customer can now rate products.')
    return redirect(request.POST.get('next') or 'admin_control_center')


@require_POST
@login_required(login_url='login_register')
def admin_update_account_role(request, user_id):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    selected_role = request.POST.get('account_type')
    valid_roles = {choice[0] for choice in Account.AccountType.choices}
    if selected_role not in valid_roles:
        messages.error(request, 'The selected role is not valid.')
        return redirect('admin_control_center')

    account = get_object_or_404(Account, pk=user_id)
    if account == request.user and selected_role != Account.AccountType.ADMIN:
        messages.error(request, 'You cannot remove your own admin access from here.')
        return redirect('admin_control_center')

    account.account_type = selected_role
    if selected_role == Account.AccountType.ADMIN:
        account.is_admin = True
        account.is_staff = True
        account.is_superuser = True
    else:
        account.is_admin = False
        account.is_staff = False
        account.is_superuser = False
        if selected_role == Account.AccountType.VENDOR:
            ensure_vendor_profile(account)

    account.save()
    messages.success(request, f'{selected_role.title()} role assigned to {account.email}.')
    return redirect('admin_control_center')


@require_POST
@login_required(login_url='login_register')
def admin_moderate_rating(request, rating_id):
    access_response = ensure_admin_access(request)
    if access_response:
        return access_response

    rating = get_object_or_404(ProductRating.objects.select_related('user', 'order'), pk=rating_id)
    decision = (request.POST.get('decision') or '').strip().lower()

    if decision == 'approve':
        rating.approval_status = ProductRating.ApprovalStatus.APPROVED
        rating.moderation_notes = 'Approved by admin.'
        success_message = f'Review from {rating.user.display_name} is now public.'
    elif decision == 'reject':
        rating.approval_status = ProductRating.ApprovalStatus.REJECTED
        rating.moderation_notes = 'Rejected by admin.'
        success_message = f'Review from {rating.user.display_name} was rejected.'
    else:
        messages.error(request, 'Unknown review moderation decision.')
        return redirect('admin_control_center')

    rating.moderated_by = request.user
    rating.moderated_at = timezone.now()
    rating.save(update_fields=['approval_status', 'moderation_notes', 'moderated_by', 'moderated_at'])
    messages.success(request, success_message)
    return redirect('admin_control_center')
