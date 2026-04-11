import json
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote, urlencode

# --- Django Core Imports ---
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Trim, Lower
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST


# --- Local App Imports ---
from .forms import UserForm, UserProfileForm
from .ai_utils import ai_reply
from .address_utils import (
    DELIVERY_COUNTRY,
    get_address_options,
    get_delivery_country_choices,
    normalize_location_name,
    validate_delivery_address,
    validate_postal_code,
)
from .backoffice import (
    admin_order_management_dashboard,
    admin_mark_order_delivered,
    admin_moderate_rating,
    admin_control_center,
    admin_update_payment_record,
    admin_update_account_role,
    assign_delivery_partner,
    delivery_collect_payment,
    delivery_dashboard,
    payment_management_dashboard,
    update_order_item_status,
    vendor_dashboard,
    vendor_order_management_dashboard,
    vendor_payment_dashboard,
    vendor_product_create,
    vendor_product_delete,
    vendor_product_edit,
)
from aapstore.forms import ProductRatingForm
from appaccounts.views import get_login_redirect_url

# Aapstore Models (UserProfile ko yahan merge kar diya)
from aapstore.models import (
    Product, ProductRating, Wishlist, Cart, Variation, Gender, Order, OrderItem, UserProfile
)
from aapcategory.models import Category, Designer

# --- Women's App Imports (Fixed aliases) ---
from appwomens.models import (
    NewProduct as NewProductW,
    ProductVariation as VariationW, # Isko alias de diya
    Clothing as WomenClothing,
    Dresses as WomenDresses,
    Footwear as WomenFootwear,
    Accessories as WomenAccessories,
    Bags as WomenBags,
    BeautyProducts,
    SaleItems as WomenSaleItems,
    Shops,
    Kendalls_editions
)

# --- Men's App Imports ---
from appmens.models import (
    NewProduct as NewProductM, 
    ProductVariation as VariationM, # Isko bhi alias de diya
    Clothing as MenClothing, 
    Footwear as MenFootwear,
    Accessories as MenAccessories, 
    Bags as MenBags, 
    SaleItems as MenSaleItems,
    Happenings
)

SHIPPING_CHARGE = 100
VALID_PAYMENT_METHODS = {choice.value for choice in Order.PaymentMethod}
MONEY_QUANTUM = Decimal('0.01')
ZERO_DECIMAL = Decimal('0.00')
SALE_MODEL_BY_PRODUCT_MODEL = {
    NewProductW: WomenSaleItems,
    NewProductM: MenSaleItems,
}


def to_money(value):
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def get_discounted_price_for_sale(base_price, sale):
    base_price = to_money(base_price)
    candidate_prices = []

    discount_percentage = Decimal(str(getattr(sale, 'discount_percentage', 0) or 0))
    discount_percentage = min(max(discount_percentage, ZERO_DECIMAL), Decimal('100'))
    if discount_percentage > 0:
        discounted_price = base_price * (Decimal('100') - discount_percentage) / Decimal('100')
        candidate_prices.append(to_money(discounted_price))

    sale_price = getattr(sale, 'sale_price', None)
    if sale_price not in (None, ''):
        normalized_sale_price = to_money(sale_price)
        if normalized_sale_price > 0:
            candidate_prices.append(normalized_sale_price)

    if not candidate_prices:
        return base_price

    return max(ZERO_DECIMAL, min(candidate_prices))


def build_active_sale_lookup(products, on_date=None):
    current_date = on_date or timezone.localdate()
    sale_model_product_ids = defaultdict(set)

    for product in products:
        if not product or not getattr(product, 'pk', None):
            continue

        sale_model = SALE_MODEL_BY_PRODUCT_MODEL.get(product.__class__)
        if sale_model:
            sale_model_product_ids[sale_model].add(product.pk)

    sale_lookup = {}
    for sale_model, product_ids in sale_model_product_ids.items():
        active_sales = sale_model.objects.select_related('product').filter(
            product_id__in=product_ids,
            start_date__lte=current_date,
            end_date__gte=current_date,
        )
        for sale in active_sales:
            product = sale.product
            key = (product.__class__, sale.product_id)
            discounted_price = get_discounted_price_for_sale(product.price, sale)
            existing_sale = sale_lookup.get(key)
            if not existing_sale or discounted_price < existing_sale['discounted_price']:
                sale_lookup[key] = {
                    'sale': sale,
                    'discounted_price': discounted_price,
                }

    return sale_lookup


def apply_sale_price(product, sale_lookup=None):
    if not product:
        return product

    original_price = to_money(getattr(product, 'original_price', getattr(product, 'price', 0)))
    sale_entry = None
    if getattr(product, 'pk', None):
        if sale_lookup is None:
            sale_lookup = build_active_sale_lookup([product])
        sale_entry = sale_lookup.get((product.__class__, product.pk))

    discounted_price = sale_entry['discounted_price'] if sale_entry else original_price
    active_sale = sale_entry['sale'] if sale_entry else None

    product.original_price = original_price
    product.display_price = discounted_price
    product.price = discounted_price
    product.is_on_sale = discounted_price < original_price
    product.active_sale = active_sale
    product.discount_percentage = getattr(active_sale, 'discount_percentage', 0) if active_sale else 0
    return product


def prepare_products_for_display(products, sort=None):
    products = list(products)
    sale_lookup = build_active_sale_lookup(products)
    for product in products:
        apply_sale_price(product, sale_lookup)

    if sort == 'price_low':
        products.sort(key=lambda product: product.price)
    elif sort == 'price_high':
        products.sort(key=lambda product: product.price, reverse=True)

    return products


def prepare_grouped_products(grouped_products, sort=None):
    grouped_items = list(grouped_products.items())
    sale_lookup = build_active_sale_lookup(product for product, _ in grouped_items)
    for product, _ in grouped_items:
        apply_sale_price(product, sale_lookup)

    if sort == 'price_low':
        grouped_items.sort(key=lambda product_group: product_group[0].price)
    elif sort == 'price_high':
        grouped_items.sort(key=lambda product_group: product_group[0].price, reverse=True)

    return grouped_items


def decorate_orderable_items(items):
    items = list(items)
    sale_lookup = build_active_sale_lookup(
        item.content_object for item in items if getattr(item, 'content_object', None)
    )

    for item in items:
        product = item.content_object
        if not product:
            continue

        apply_sale_price(product, sale_lookup)
        quantity = getattr(item, 'quantity', 1) or 1
        item.display_price = product.price
        item.original_price = product.original_price
        item.is_on_sale = product.is_on_sale
        item.line_total = to_money(product.price * quantity)

    return items


def get_product_detail_url(product):
    slug = getattr(product, 'slug', None)
    if not slug:
        return '#'

    gender = str(getattr(product, 'gender', '')).lower().strip()
    if gender in {'women', 'womens', 'woman', 'female'}:
        return reverse('product_detail', args=[slug])
    if gender in {'men', 'mens', 'man', 'male'}:
        return reverse('product_detail_men', args=[slug])
    return '#'


def get_product_rating_summary(product):
    content_type = ContentType.objects.get_for_model(product.__class__)
    ratings = ProductRating.objects.filter(
        content_type=content_type,
        object_id=product.id,
        approval_status=ProductRating.ApprovalStatus.APPROVED,
    )
    summary = ratings.aggregate(average_rating=Avg('rating'), review_count=Count('id'))
    recent_reviews = list(ratings.select_related('user')[:5])
    return {
        'average_rating': summary['average_rating'],
        'review_count': summary['review_count'] or 0,
        'recent_reviews': recent_reviews,
    }


def build_order_context(orders_queryset, user=None):
    orders = list(orders_queryset.prefetch_related('items'))
    rating_lookup = {}
    if user and orders:
        ratings = ProductRating.objects.filter(user=user, order__in=orders).select_related('order_item')
        rating_lookup = {rating.order_item_id: rating for rating in ratings}

    for order in orders:
        order.display_status = getattr(order, 'status', None) or Order.Status.PROCESSING
        order.status = order.display_status
        order.is_completed_status = order.display_status in {Order.Status.DELIVERED, 'Completed'}
        order.can_rate = order.display_status == Order.Status.DELIVERED
        order.display_items = []

        for item in order.items.all():
            product = item.content_object
            if not product:
                continue

            item.product_name = getattr(product, 'product_name', 'Product')
            item.product_image_url = getattr(getattr(product, 'front_image', None), 'url', '')
            item.product_url = get_product_detail_url(product)
            item.display_price = to_money(item.price)
            item.line_total = to_money(item.price * item.quantity)
            item.existing_rating = rating_lookup.get(item.id)
            item.review_status = getattr(item.existing_rating, 'approval_status', '')
            order.display_items.append(item)

    return orders


def validate_order_payload(data):
    required_fields = {
        'fullName': 'Please enter your full name.',
        'mobile': 'Please enter your mobile number.',
        'address': 'Please enter your address.',
        'country': 'Please choose your country.',
        'state': 'Please choose your state.',
        'district': 'Please choose your district.',
        'city': 'Please enter your city.',
        'zipCode': 'Please enter your zip code.',
        'paymentMethod': 'Please choose a payment method.',
    }
    for field, error_message in required_fields.items():
        if not str(data.get(field, '')).strip():
            raise ValueError(error_message)

    mobile = re.sub(r'\D', '', str(data.get('mobile', '')))
    if not 10 <= len(mobile) <= 15:
        raise ValueError('Please enter a valid mobile number.')

    country = normalize_location_name(data.get('country', '') or DELIVERY_COUNTRY)
    state = normalize_location_name(data.get('state', ''))
    district = normalize_location_name(data.get('district', '') or data.get('city', ''))
    city = normalize_location_name(data.get('city', ''))
    zip_code = normalize_location_name(data.get('zipCode', ''))

    is_valid_address, validation_message = validate_delivery_address(
        country=country,
        state=state,
        district=district,
        city=city,
        postal_code=zip_code,
    )
    if not is_valid_address:
        raise ValueError(validation_message)

    payment_method = str(data.get('paymentMethod', '')).strip().lower()
    if payment_method not in VALID_PAYMENT_METHODS:
        raise ValueError('Unsupported payment method selected.')

    payment_reference = str(data.get('transactionId', '')).strip()
    if payment_method == Order.PaymentMethod.CASH:
        payment_reference = payment_reference or 'COD'
    elif not payment_reference:
        raise ValueError('Payment reference is required for this payment method.')

    if payment_method in {Order.PaymentMethod.UPI, Order.PaymentMethod.QRCODE} and not re.fullmatch(r'\d{12}', payment_reference):
        raise ValueError('A valid 12-digit payment reference is required.')

    return {
        'full_name': str(data.get('fullName', '')).strip(),
        'mobile': mobile,
        'address': str(data.get('address', '')).strip(),
        'city': city,
        'district': district,
        'state': state,
        'country': country,
        'zip_code': zip_code,
        'payment_method': payment_method,
        'payment_reference': payment_reference[:120],
    }

def get_product_model(gender):
    """
    Gender string ke hisaab se sahi Product model (NewProductM ya NewProductW) return karta hai.
    """
    gender_lower = gender.lower().strip()
    
    # Pehle 'women' check karein ya exact list use karein
    if gender_lower in ['women', 'womens', 'woman', 'female']:
        return NewProductW
    elif gender_lower in ['men', 'mens', 'man', 'male']:
        return NewProductM
        
    return None

# Common Helper
def get_categories_for_products(queryset, gender_field):
    return Category.objects.filter(**{f"{gender_field}__in": queryset.values_list('product_id', flat=True)}).distinct()


def get_unique_filter_values(values):
    unique = {}
    for value in values:
        if value is None:
            continue
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in unique:
            unique[key] = cleaned
    return sorted(unique.values(), key=lambda item: item.lower())


def normalize_discount_filter(raw_value):
    value = str(raw_value or '').strip().lower()
    if not value or value == 'all':
        return ''
    if value in {'on', 'any', 'sale', 'on_sale'}:
        return 'on'

    try:
        threshold = Decimal(value)
    except Exception:
        return ''

    threshold = min(max(threshold, ZERO_DECIMAL), Decimal('100'))
    return threshold.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def filter_products_by_discount(products, discount_filter):
    if not discount_filter:
        return products

    if discount_filter == 'on':
        return [product for product in products if getattr(product, 'is_on_sale', False)]

    return [
        product
        for product in products
        if getattr(product, 'is_on_sale', False)
        and Decimal(str(getattr(product, 'discount_percentage', 0) or 0)) >= discount_filter
    ]


def filter_grouped_products_by_discount(grouped_products, discount_filter):
    if not discount_filter:
        return grouped_products

    if discount_filter == 'on':
        return [
            (product, variations)
            for product, variations in grouped_products
            if getattr(product, 'is_on_sale', False)
        ]

    return [
        (product, variations)
        for product, variations in grouped_products
        if getattr(product, 'is_on_sale', False)
        and Decimal(str(getattr(product, 'discount_percentage', 0) or 0)) >= discount_filter
    ]


def get_grouped_designers(designers):
    grouped = defaultdict(list)
    for designer in designers:
        name = (designer.name or '').strip()
        if not name:
            continue

        first_char = name[0].upper()
        letter = first_char if first_char.isalpha() else '#'
        grouped[letter].append(designer)

    ordered_groups = []
    if grouped.get('#'):
        ordered_groups.append(('#', grouped['#']))

    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if grouped.get(letter):
            ordered_groups.append((letter, grouped[letter]))

    return ordered_groups

# -------------------- WOMEN --------------------
def Index(request):
    products = Product.objects.filter(is_available=True).order_by('-created_date')
    context = {
        'products': products,
        'item_count': products.count(),
        'categories': Category.objects.all(),
    }
    return render(request, 'womens/index.html', context)

def WomensNew(request):
    category_slug = request.GET.get('category')    
    color = request.GET.get('color')
    size = request.GET.get('size')
    brand = request.GET.get('brand')
    designer = request.GET.get('designer')
    search_query = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    products = NewProductW.objects.select_related('category').filter(is_available=True, gender='Women')
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(category__category_name__icontains=search_query)
            | Q(designer__name__icontains=search_query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if designer: products = products.filter(designer__id=designer)
    if color: products = products.filter(variations__color__iexact=color)
    if size: products = products.filter(variations__size__iexact=size)
    if brand: products = products.filter(brand__iexact=brand)
    if min_price and max_price: products = products.filter(price__gte=min_price, price__lte=max_price)
    products = products.distinct()
    if sort == "price_low": products = products.order_by("price")
    elif sort == "price_high": products = products.order_by("-price")
    else: products = products.order_by("-created_date")
    filtered_products = products
    all_products_queryset = WomenClothing.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(womens_products__in=filtered_products).distinct()
    colors = get_unique_filter_values(filtered_products.values_list('variations__color', flat=True))
    sizes = get_unique_filter_values(filtered_products.values_list('variations__size', flat=True))
    brands = get_unique_filter_values(filtered_products.values_list('brand', flat=True))
    products = prepare_products_for_display(filtered_products, sort=sort)
    products = filter_products_by_discount(products, discount)
    grouped = defaultdict(list)
    for product in products: grouped[product].append(None)
    return render(request, 'womens/Wnew.html', {'products': list(grouped.items()),'item_count': len(grouped),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'brands': brands,'selected_category': category_slug,})

def WomensDesigners(request):
    selected_designer_id = request.GET.get('designer')

    designers = Designer.objects.filter(
        womens_products__is_available=True,
        womens_products__gender='Women',
    ).distinct().order_by('name')

    selected_designer = None
    products = NewProductW.objects.none()

    if selected_designer_id:
        selected_designer = designers.filter(id=selected_designer_id).first()
        if selected_designer:
            products = NewProductW.objects.filter(
                is_available=True,
                gender='Women',
                designer=selected_designer,
            ).select_related('designer', 'category').order_by('-created_date')
            products = prepare_products_for_display(products)

    grouped_designers = get_grouped_designers(designers)

    return render(
        request,
        'womens/Wdesigners.html',
        {
            'grouped_designers': grouped_designers,
            'selected_designer': selected_designer,
            'selected_products': products,
            'selected_designer_id': str(selected_designer_id or ''),
        },
    )

def WomensClothing(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = WomenClothing.objects.select_related('product').filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if size: items = items.filter(size__iexact=size)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items: grouped[item.product].append(item)
    all_products_queryset = WomenClothing.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    colors = WomenClothing.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = (items.annotate(clean_size=Trim(Lower('size'))).values_list('clean_size', flat=True).exclude(clean_size__isnull=True).exclude(clean_size__exact='').distinct())
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'womens/Wclothing.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def WomensDresses(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = WomenDresses.objects.filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if size: items = items.filter(size__iexact=size)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items: grouped[item.product].append(item)
    all_products_queryset = WomenDresses.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    colors = WomenDresses.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = WomenDresses.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'womens/Wdresses.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def WomensShoes(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = WomenFootwear.objects.filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if size: items = items.filter(size__iexact=size)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items: grouped[item.product].append(item)
    all_products_queryset = WomenFootwear.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    colors = WomenFootwear.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = (items.annotate(clean_size=Trim(Lower('size'))).values_list('clean_size', flat=True).exclude(clean_size__isnull=True).exclude(clean_size__exact='').distinct())
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'womens/Wshoes.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def WomensBags(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = WomenBags.objects.select_related('product').filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items:
        if item.product.slug: grouped[item.product].append(item)
    all_products_queryset = WomenBags.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    colors = WomenBags.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = WomenBags.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'womens/Wbags.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def WomensAccessories(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = WomenAccessories.objects.select_related('product').filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items:
        if item.product.slug: grouped[item.product].append(item)
    all_products_queryset = WomenAccessories.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    colors = WomenAccessories.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = WomenAccessories.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'womens/Waccessories.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def WomensBeauty(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = BeautyProducts.objects.select_related('product').filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items:
        if item.product.slug: grouped[item.product].append(item)
    all_products_queryset = BeautyProducts.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(womens_products__id__in=all_products_queryset).distinct()
    colors = BeautyProducts.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = BeautyProducts.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'womens/Wbeauty.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def WomensSale(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    sort = request.GET.get('sort')
    discount = normalize_discount_filter(request.GET.get('discount'))
    current_date = timezone.localdate()

    base_items = WomenSaleItems.objects.select_related('product').filter(
        product__is_available=True,
        start_date__lte=current_date,
        end_date__gte=current_date,
    )

    items = base_items
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(product__variations__color__iexact=color)
    if size: items = items.filter(product__variations__size__iexact=size)

    items = items.distinct()

    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by('-product__created_date')

    grouped = defaultdict(list)
    for item in items:
        if item.product.slug: grouped[item.product].append(item)

    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)

    all_products = base_items.values_list('product', flat=True)
    categories = Category.objects.filter(womens_products__in=all_products).distinct()
    designers = Designer.objects.filter(womens_products__in=all_products).distinct()
    colors = get_unique_filter_values(base_items.values_list('product__variations__color', flat=True))
    sizes = get_unique_filter_values(base_items.values_list('product__variations__size', flat=True))

    return render(request, 'womens/Wsale.html', {
        'products': grouped_items,
        'item_count': len(grouped_items),
        'categories': categories,
        'designers': designers,
        'colors': colors,
        'sizes': sizes,
        'selected_category': category_slug,
    })

def WomensShops(request):
    shop_items = Shops.objects.filter(product__is_available=True, is_vasu_soap=True)
    trending_items = Shops.objects.filter(product__is_available=True, is_trending=True)
    return render(request, 'womens/Wshops.html', {'shop_items': shop_items,'trending_items': trending_items,})

def KendallEdit(request):
    editions = Kendalls_editions.objects.all()
    return render(request, 'womens/kendall_edit.html', {'editions': editions})

def Product_Detail(request, slug):
    product = get_object_or_404(
        NewProductW.objects.prefetch_related('variations', 'gallery_images'),
        slug=slug,
    )
    apply_sale_price(product)
    context = {
        'product': product,
        'variations': product.variations.all(),
        **get_product_rating_summary(product),
    }
    return render(request, 'womens/product_detail.html', context)

# -------------------- MEN --------------------
def MensIndex(request):
    return render(request, 'mens/home_men.html')

def MensNew(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    discount = normalize_discount_filter(request.GET.get('discount'))
    search_query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort')
    products = NewProductM.objects.filter(is_available=True, gender='Mens')
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(category__category_name__icontains=search_query)
            | Q(designer__name__icontains=search_query)
        )
    if category_slug: products = products.filter(category__slug=category_slug)
    if designer: products = products.filter(designer__id=designer)
    if color: products = products.filter(variations__color__iexact=color)
    if size: products = products.filter(variations__size__iexact=size)
    products = products.distinct()
    if sort == "price_low": products = products.order_by("price")
    elif sort == "price_high": products = products.order_by("-price")
    else: products = products.order_by("-created_date")
    filtered_products = products
    categories = Category.objects.annotate(product_count=Count('mens_products', filter=Q(mens_products__gender='Mens', mens_products__is_available=True))).filter(product_count__gt=0)
    designers = Designer.objects.filter(mens_products__in=filtered_products).distinct()
    colors = get_unique_filter_values(filtered_products.values_list('variations__color', flat=True))
    sizes = get_unique_filter_values(filtered_products.values_list('variations__size', flat=True))
    products = prepare_products_for_display(filtered_products, sort=sort)
    products = filter_products_by_discount(products, discount)
    return render(request, 'mens/Mnew.html', {'products': products,'item_count': len(products),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def MensDesigners(request):
    selected_designer_id = request.GET.get('designer')

    designers = Designer.objects.filter(
        mens_products__is_available=True,
        mens_products__gender='Mens',
    ).distinct().order_by('name')

    selected_designer = None
    products = NewProductM.objects.none()

    if selected_designer_id:
        selected_designer = designers.filter(id=selected_designer_id).first()
        if selected_designer:
            products = NewProductM.objects.filter(
                is_available=True,
                gender='Mens',
                designer=selected_designer,
            ).select_related('designer', 'category').order_by('-created_date')
            products = prepare_products_for_display(products)

    grouped_designers = get_grouped_designers(designers)

    return render(
        request,
        'mens/Mdesigners.html',
        {
            'grouped_designers': grouped_designers,
            'selected_designer': selected_designer,
            'selected_products': products,
            'selected_designer_id': str(selected_designer_id or ''),
        },
    )

def MensClothing(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = MenClothing.objects.filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if size: items = items.filter(size__iexact=size)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items: grouped[item.product].append(item)
    all_products_queryset = MenClothing.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    colors = MenClothing.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = MenClothing.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'mens/Mclothing.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def MensShoes(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = MenFootwear.objects.filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if size: items = items.filter(size__iexact=size)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items: grouped[item.product].append(item)
    all_products_queryset = MenFootwear.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    colors = MenFootwear.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = MenFootwear.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'mens/Mshoes.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def MensBags(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = MenBags.objects.select_related('product').filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items:
        if item.product.slug: grouped[item.product].append(item)
    all_products_queryset = MenBags.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    colors = MenBags.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = MenBags.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'mens/Mbags.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def MensAccessories(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    discount = normalize_discount_filter(request.GET.get('discount'))
    sort = request.GET.get('sort')
    items = MenAccessories.objects.select_related('product').filter(product__is_available=True)
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(color__iexact=color)
    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by("-product__created_date")
    grouped = defaultdict(list)
    for item in items:
        if item.product.slug: grouped[item.product].append(item)
    all_products_queryset = MenAccessories.objects.filter(product__is_available=True).values_list('product_id', flat=True)
    categories = Category.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    designers = Designer.objects.filter(mens_products__id__in=all_products_queryset).distinct()
    colors = MenAccessories.objects.filter(product__is_available=True).values_list('color', flat=True).distinct()
    sizes = MenAccessories.objects.filter(product__is_available=True).values_list('size', flat=True).distinct()
    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)
    return render(request, 'mens/Maccessories.html', {'products': grouped_items,'item_count': len(grouped_items),'categories': categories,'designers': designers,'colors': colors,'sizes': sizes,'selected_category': category_slug,})

def MensSale(request):
    category_slug = request.GET.get('category')
    designer = request.GET.get('designer')
    color = request.GET.get('color')
    size = request.GET.get('size')
    sort = request.GET.get('sort')
    discount = normalize_discount_filter(request.GET.get('discount'))
    current_date = timezone.localdate()

    base_items = MenSaleItems.objects.select_related('product').filter(
        product__is_available=True,
        start_date__lte=current_date,
        end_date__gte=current_date,
    )

    items = base_items
    if category_slug: items = items.filter(product__category__slug=category_slug)
    if designer: items = items.filter(product__designer__id=designer)
    if color: items = items.filter(product__variations__color__iexact=color)
    if size: items = items.filter(product__variations__size__iexact=size)

    items = items.distinct()

    if sort == "price_low": items = items.order_by("product__price")
    elif sort == "price_high": items = items.order_by("-product__price")
    else: items = items.order_by('-product__created_date')

    grouped = defaultdict(list)
    for item in items:
        if item.product.slug: grouped[item.product].append(item)

    grouped_items = prepare_grouped_products(grouped, sort=sort)
    grouped_items = filter_grouped_products_by_discount(grouped_items, discount)

    all_products = base_items.values_list('product', flat=True)
    categories = Category.objects.filter(mens_products__in=all_products).distinct()
    designers = Designer.objects.filter(mens_products__in=all_products).distinct()
    colors = get_unique_filter_values(base_items.values_list('product__variations__color', flat=True))
    sizes = get_unique_filter_values(base_items.values_list('product__variations__size', flat=True))

    return render(request, 'mens/Msale.html', {
        'products': grouped_items,
        'item_count': len(grouped_items),
        'categories': categories,
        'designers': designers,
        'colors': colors,
        'sizes': sizes,
        'selected_category': category_slug,
    })

def MensHappening(request):
    return render(request, 'mens/Mhappening.html', {'happenings': Happenings.objects.all(),'categories': Category.objects.all(),'item_count': Happenings.objects.count()})

def Product_Detail_Men(request, slug):
    product = get_object_or_404(
        NewProductM.objects.prefetch_related('variations', 'gallery_images'),
        slug=slug,
    )
    apply_sale_price(product)
    context = {
        'product': product,
        'variations': product.variations.all(),
        **get_product_rating_summary(product),
    }
    return render(request, 'mens/product_detail.html', context)

# -------------------- COMMON --------------------
def Login(request):
    if request.user.is_authenticated:
        return redirect(get_login_redirect_url(request.user))
    return redirect('login_register')

def NeedHelp(request):
    return render(request, 'need_help.html')


# ===================================================================
# FINAL FIXED CART, WISHLIST, AND ORDER LOGIC
# ===================================================================


@require_POST
@login_required
def wishlist_add(request, gender, product_id):
    ProductModel = get_product_model(gender)
    if not ProductModel:
        messages.error(request, "Invalid product category.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    product = get_object_or_404(ProductModel, id=product_id)
    content_type = ContentType.objects.get_for_model(ProductModel)

    # Check agar product pehle se wishlist mein hai
    if Wishlist.objects.filter(user=request.user, content_type=content_type, object_id=product.id).exists():
        # --- YAHAN CHANGE KIYA HAI (Added 'request') ---
        messages.warning(request, f'{product.product_name} is already in your wishlist.')
    else:
        Wishlist.objects.create(user=request.user, content_type=content_type, object_id=product.id)
        messages.success(request, f'{product.product_name} has been added to your wishlist.')
        
    return redirect(request.META.get('HTTP_REFERER', '/'))

@require_POST
@login_required
def add_to_cart(request, gender, product_id):
    """
    Cart mein product add karta hai, lekin pehle stock check karta hai.
    """
    ProductModel = get_product_model(gender)
    if not ProductModel:
        messages.error(request, "Invalid product category.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    product = get_object_or_404(ProductModel, id=product_id)
    content_type = ContentType.objects.get_for_model(ProductModel)
    
    # === STOCK CHECK LOGIC ===
    total_stock = product.variations.aggregate(total=Sum('stock'))['total'] or 0
    if total_stock < 1:
        messages.error(request, f"Sorry, {product.product_name} is not available in stock.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    cart_item, created = Cart.objects.get_or_create(
        user=request.user, content_type=content_type, object_id=product.id,
        defaults={'quantity': 1}
    )
    
    if not created:
        # Agar item pehle se cart mein hai, to check karein ki stock se zyada na ho
        if cart_item.quantity < total_stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.info(request, f'{product.product_name} quantity increased.')
        else:
            messages.warning(request, f'{product.product_name} stock limit reached.')
    else:
        messages.success(request, f'{product.product_name} Added to cart.')
    
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def wishlist_view(request):
    wishlist_items_qs = Wishlist.objects.filter(user=request.user).select_related('content_type')
    valid_items = [item for item in wishlist_items_qs if item.content_object]
    decorate_orderable_items(valid_items)
    return render(request, 'cart/wishlist.html', {'wishlist_items': valid_items})

@login_required
def cart_view(request):
    cart_items_qs = decorate_orderable_items(
        Cart.objects.filter(user=request.user).select_related('content_type')
    )
    valid_items, items_to_delete = [], []
    total_price = ZERO_DECIMAL

    for item in cart_items_qs:
        product = item.content_object
        if product and getattr(product, 'is_available', False):
            total_stock = product.variations.aggregate(total=Sum('stock'))['total'] or 0
            item.total_stock = total_stock
            valid_items.append(item)
            total_price += item.line_total
        else:
            items_to_delete.append(item.id)

    if items_to_delete:
        Cart.objects.filter(id__in=items_to_delete).delete()
        messages.warning(request, "Some items were removed from your cart as they are no longer available.")

    return render(request, 'cart/cart.html', {'cart_items': valid_items, 'total_price': to_money(total_price)})

@require_POST
@login_required
def update_cart_quantity(request, item_id):
    try:
        data = json.loads(request.body or '{}')
        action = data.get('action')
        cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
        product = cart_item.content_object
        
        if not product or not product.is_available:
            return JsonResponse({'success': False, 'error': 'Product not available.'})

        total_stock = product.variations.aggregate(total=Sum('stock'))['total'] or 0

        if action == 'increase' and cart_item.quantity < total_stock:
            cart_item.quantity += 1
        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1
        elif action == 'increase':
             return JsonResponse({'success': False, 'error': f'Stock limit of {total_stock} reached.'})
        
        cart_item.save()
        
        all_cart_items = decorate_orderable_items(
            Cart.objects.filter(user=request.user).select_related('content_type')
        )
        new_total_price = sum(
            item.line_total
            for item in all_cart_items
            if item.content_object and getattr(item.content_object, 'is_available', False)
        )

        return JsonResponse(
            {
                'success': True,
                'new_quantity': cart_item.quantity,
                'new_total': float(to_money(new_total_price)),
            }
        )
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not update quantity right now.'}, status=500)

@require_POST
@login_required
def wishlist_remove(request, gender, product_id):
    ProductModel = get_product_model(gender)
    if not ProductModel:
        messages.error(request, "Invalid product category.")
        return redirect('wishlist_view')

    product = get_object_or_404(ProductModel, id=product_id)
    content_type = ContentType.objects.get_for_model(ProductModel)
    Wishlist.objects.filter(user=request.user, content_type=content_type, object_id=product.id).delete()
    messages.success(request, f'{product.product_name} has been removed from your wishlist.')
    return redirect('wishlist_view')

@require_POST
@login_required
def remove_from_cart(request, gender, product_id):
    ProductModel = get_product_model(gender)
    if not ProductModel:
        messages.error(request, "Invalid product category.")
        return redirect('cart_view')
        
    product = get_object_or_404(ProductModel, id=product_id)
    content_type = ContentType.objects.get_for_model(ProductModel)
    Cart.objects.filter(user=request.user, content_type=content_type, object_id=product.id).delete()
    messages.success(request, f'{product.product_name} has been removed from your cart.')
    return redirect('cart_view')

@login_required
def checkout(request):
    profile = None
    initial_address = {
        'full_name': '',
        'mobile': '',
        'address_line_1': '',
        'address_line_2': '',
        'country': DELIVERY_COUNTRY,
        'state': '',
        'district': '',
        'city': '',
        'postal_code': '',
    }
    if getattr(request.user, 'is_authenticated', False):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        initial_address.update(
            {
                'full_name': request.user.display_name,
                'address_line_1': profile.address_line_1,
                'address_line_2': profile.address_line_2,
                'country': profile.country or DELIVERY_COUNTRY,
                'state': profile.state,
                'district': profile.district,
                'city': profile.city,
                'postal_code': profile.postal_code,
            }
        )

    cart_items = decorate_orderable_items(Cart.objects.filter(user=request.user).select_related('content_type'))
    valid_cart_items = [item for item in cart_items if item.content_object and getattr(item.content_object, 'is_available', False)]
    subtotal = sum(item.line_total for item in valid_cart_items)
    shipping_charge = to_money(SHIPPING_CHARGE)
    total_price = to_money(subtotal + shipping_charge)
    upi_link = 'upi://pay?' + urlencode(
        {
            'pa': getattr(settings, 'PAYMENT_UPI_ID', '').strip() or '7878065935@ptyes',
            'pn': getattr(settings, 'PAYMENT_UPI_NAME', '').strip() or 'VASU',
            'am': f'{total_price:.2f}',
            'cu': 'INR',
            'tn': f'Order payment - {request.user.username}',
        }
    )
    qr_code_image_url = f'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={quote(upi_link, safe="")}'

    return render(
        request,
        'cart/checkout.html',
        {
            'cart_items': valid_cart_items,
            'subtotal': to_money(subtotal),
            'shipping_charge': shipping_charge,
            'total_price': total_price,
            'delivery_country_choices': get_delivery_country_choices(),
            'initial_address': initial_address,
            'initial_address_options': get_address_options(initial_address['country'], initial_address['state']),
            'upi_payment_url': upi_link,
            'qr_code_image_url': qr_code_image_url,
        },
    )


@require_GET
def address_options_api(request):
    country = request.GET.get('country', DELIVERY_COUNTRY)
    state = request.GET.get('state', '')
    return JsonResponse(get_address_options(country=country, state=state))


@require_GET
def validate_postal_code_api(request):
    country = request.GET.get('country', DELIVERY_COUNTRY)
    state = request.GET.get('state', '')
    postal_code = request.GET.get('postal_code', '')
    is_valid, message = validate_postal_code(country=country, state=state, postal_code=postal_code)
    return JsonResponse(
        {
            'valid': is_valid,
            'message': message,
        }
    )

@require_POST
@login_required
def place_order_api(request):
    """
    Order place karta hai aur kharide gaye products ka stock kam karta hai.
    """
    try:
        data = json.loads(request.body)
        full_name = data.get('fullName')
        mobile = data.get('mobile')
        address = data.get('address')
        city = data.get('city')
        state = data.get('state')
        zip_code = data.get('zipCode')
        payment_method = data.get('paymentMethod')

        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items:
            return JsonResponse({'success': False, 'error': 'Your cart is empty.'}, status=400)
        
        with transaction.atomic(): # Database transaction shuru
            # Pehle Order create karein
            total_price = sum(item.content_object.price * item.quantity for item in cart_items if item.content_object)
            order = Order.objects.create(
                user=request.user, full_name=full_name, mobile=mobile, address=address, city=city,
                state=state, zip_code=zip_code, total_price=total_price, payment_method=payment_method
            )

            for cart_item in cart_items:
                product = cart_item.content_object
                quantity_ordered = cart_item.quantity
                
                # Check karein ki product abhi bhi available hai ya nahi
                if not product or not product.is_available:
                    raise Exception(f"{product.product_name} is no longer available.")

                # Check karein ki order ki quantity stock se zyada na ho
                total_stock = product.variations.aggregate(total=Sum('stock'))['total'] or 0
                if quantity_ordered > total_stock:
                    raise Exception(f"{product.product_name} ke liye पर्याप्त stock nahi hai.")

                # OrderItem banayein
                OrderItem.objects.create(
                    order=order, 
                    content_object=product,
                    object_id=product.id,
                    content_type=cart_item.content_type,
                    quantity=quantity_ordered, 
                    price=product.price
                )

                # === YAHAN STOCK KAM KIYA JA RAHA HAI ===
                variations_in_stock = product.variations.filter(stock__gt=0).order_by('id')
                remaining_qty = quantity_ordered
                for variation in variations_in_stock:
                    if remaining_qty <= 0: break
                    
                    stock_to_take = min(variation.stock, remaining_qty)
                    variation.stock -= stock_to_take
                    variation.save()
                    remaining_qty -= stock_to_take
            
            # Order safal hone ke baad cart khaali karein
            cart_items.delete()

        return JsonResponse({'success': True, 'order_id': order.id, 'message': 'Your order has been placed successfully!'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
@login_required
def place_order_api(request):
    try:
        data = json.loads(request.body or '{}')
        payload = validate_order_payload(data)
        cart_items = list(Cart.objects.filter(user=request.user).select_related('content_type'))
        valid_cart_items = [
            item for item in cart_items
            if item.content_object and getattr(item.content_object, 'is_available', False)
        ]
        decorate_orderable_items(valid_cart_items)
        if not valid_cart_items:
            return JsonResponse({'success': False, 'error': 'Your cart is empty.'}, status=400)

        with transaction.atomic():
            subtotal = sum(item.line_total for item in valid_cart_items)
            total_price = to_money(subtotal + to_money(SHIPPING_CHARGE))
            order = Order.objects.create(
                user=request.user,
                full_name=payload['full_name'],
                mobile=payload['mobile'],
                address=payload['address'],
                city=payload['city'],
                district=payload['district'],
                state=payload['state'],
                country=payload['country'],
                zip_code=payload['zip_code'],
                total_price=total_price,
                payment_method=payload['payment_method'],
                payment_reference=payload['payment_reference'],
                payment_status=Order.default_payment_status_for_method(payload['payment_method']),
                account_receipt_status=Order.default_account_receipt_status_for_method(payload['payment_method']),
                account_receipt_reference=(
                    payload['payment_reference']
                    if payload['payment_method'] != Order.PaymentMethod.CASH
                    else ''
                ),
            )

            for cart_item in valid_cart_items:
                product = cart_item.content_object
                quantity_ordered = cart_item.quantity

                if not product or not product.is_available:
                    product_name = getattr(product, 'product_name', 'This product')
                    raise ValueError(f'{product_name} is no longer available.')

                total_stock = product.variations.aggregate(total=Sum('stock'))['total'] or 0
                if quantity_ordered > total_stock:
                    raise ValueError(f'Not enough stock available for {product.product_name}.')

                OrderItem.objects.create(
                    order=order,
                    vendor=getattr(product, 'vendor', None),
                    content_object=product,
                    object_id=product.id,
                    content_type=cart_item.content_type,
                    quantity=quantity_ordered,
                    price=cart_item.display_price,
                )

                variations_in_stock = product.variations.select_for_update().filter(stock__gt=0).order_by('id')
                remaining_qty = quantity_ordered
                for variation in variations_in_stock:
                    if remaining_qty <= 0:
                        break

                    stock_to_take = min(variation.stock, remaining_qty)
                    variation.stock -= stock_to_take
                    variation.save()
                    remaining_qty -= stock_to_take

            Cart.objects.filter(id__in=[item.id for item in valid_cart_items]).delete()

        return JsonResponse(
            {
                'success': True,
                'order_id': order.order_id or order.id,
                'message': 'Your order has been placed successfully!',
            }
        )
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not place your order right now.'}, status=500)

# views.py

@login_required
def active_orders(request):
    orders = build_order_context(
        Order.objects.filter(user=request.user)
        .exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
        .order_by('-created_at'),
        request.user,
    )

    context = {
        'orders': orders
    }
    return render(request, 'cart/active_orders.html', context)

@login_required 
def order_history(request):
    orders = build_order_context(Order.objects.filter(user=request.user).order_by('-created_at'), request.user)
    
    context = {
        'orders': orders
    }
    return render(request, 'accounts/order_history_v2.html', context)

@login_required
def my_account(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/my_account.html', {'profile': profile})

@login_required
def view_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = list(order.items.select_related('content_type'))
    for item in order_items:
        item.line_total = to_money(item.price * item.quantity)
    
    context = {
        'order': order,
        'order_items': order_items,
        'shipping_charge': to_money(SHIPPING_CHARGE),
    }
    return render(request, 'accounts/invoice.html', context)


@login_required
def rate_order_item(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)
    product = order_item.content_object

    if order.status != Order.Status.DELIVERED:
        messages.warning(request, 'Rating is available only after your product is delivered.')
        return redirect('order_history')

    if not product:
        messages.error(request, 'This product is no longer available for rating.')
        return redirect('order_history')

    existing_rating = ProductRating.objects.filter(order_item=order_item, user=request.user).first()
    form = ProductRatingForm(request.POST or None, request.FILES or None, instance=existing_rating)

    if request.method == 'POST' and form.is_valid():
        rating = form.save(commit=False)
        rating.user = request.user
        rating.order = order
        rating.order_item = order_item
        rating.content_type = order_item.content_type
        rating.object_id = order_item.object_id
        rating.approval_status = ProductRating.ApprovalStatus.PENDING
        rating.moderation_notes = ''
        rating.moderated_by = None
        rating.moderated_at = None
        rating.save()
        messages.success(request, 'Thanks! Your review has been submitted and is waiting for admin approval.')
        return redirect('order_history')

    context = {
        'order': order,
        'order_item': order_item,
        'product': product,
        'product_url': get_product_detail_url(product),
        'product_image_url': getattr(getattr(product, 'front_image', None), 'url', ''),
        'existing_rating': existing_rating,
        'form': form,
    }
    return render(request, 'accounts/rate_product.html', context)

@login_required
def edit_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('my_account') 

    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'accounts/edit_profile.html', context)

def legacy_chatbot_search(request):
    query = request.GET.get('query', '').strip().lower()
    if not query:
        return JsonResponse({'found': False, 'message': 'How can I help you today?'})

    # 1. CLEAN QUERY: Faltu symbols hatana
    clean_query = re.sub(r'[^\w\s]', '', query)
    words = clean_query.split()
    
    # 2. STOP WORDS: Faltu words ignore karein ('need', 'want' etc.)
    stop_words = {'i', 'want', 'to', 'show', 'me', 'similar', 'give', 'information', 'about', 'a', 'an', 'the', 'some', 'any', 'do', 'you', 'have', 'looking', 'for', 'please', 'okay', 'ok', 'can', 'is', 'there', 'need'}
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    if not keywords:
        keywords = [clean_query] if clean_query else [query]

    # 3. SMART SYNONYMS: Ek word ke badle saare words add karein
    search_terms = set(keywords)
    synonyms_dict = {
        'shoe': ['shoes', 'footwear', 'sandal', 'sneaker', 'sneakers', 'boots', 'heels'],
        'cloth': ['clothes', 'clothing', 'dress', 'shirt', 'tee', 'apparel', 'top', 'wear'],
        'bag': ['bags', 'handbag', 'handbags', 'purse', 'pochette', 'tote', 'backpack']
    }
    
    for kw in keywords:
        for key, syns in synonyms_dict.items():
            if kw == key or kw in syns:
                search_terms.add(key)
                search_terms.update(syns)
                
    search_terms = list(search_terms)

    # 4. FOOLPROOF DEEP SEARCH ENGINE
    def get_safe_products(model_class):
        # Dynamic fields detection: Sirf wahi field search karega jo database mein asal mein maujood hain!
        model_fields = [f.name for f in model_class._meta.get_fields()]
        valid_fields = ['product_name']
        
        if 'product_description' in model_fields: valid_fields.append('product_description')
        if 'brand' in model_fields: valid_fields.append('brand')
        if 'color' in model_fields: valid_fields.append('color')
        if 'size' in model_fields: valid_fields.append('size')
        
        # Relations (Assuming standard naming)
        if 'category' in model_fields: valid_fields.append('category__category_name')
        if 'designer' in model_fields: valid_fields.append('designer__name')

        final_q = Q()
        
        # Pura sentence check
        if clean_query:
            for f in valid_fields:
                final_q |= Q(**{f"{f}__icontains": clean_query})

        # Ek-ek word check
        for term in search_terms:
            for f in valid_fields:
                final_q |= Q(**{f"{f}__icontains": term})

        try:
            # Pehle sabhi valid fields mein search try karein
            return list(model_class.objects.filter(final_q, is_available=True).distinct()[:4])
        except Exception as e:
            # Agar Designer ya Category ka naam match nahi hua aur DB error aaya, toh Fallback karega
            print(f"Warning: Deep search failed, fallback to basic. Error: {e}")
            basic_q = Q()
            for term in search_terms:
                basic_q |= Q(product_name__icontains=term)
                if 'product_description' in model_fields:
                    basic_q |= Q(product_description__icontains=term)
            return list(model_class.objects.filter(basic_q, is_available=True).distinct()[:4])

    # Dono models se data nikalna
    w_prods = get_safe_products(NewProductW)
    m_prods = get_safe_products(NewProductM)
    
    all_found = w_prods + m_prods
    
    frontend_results = []
    ai_context = ""

    if all_found:
        ai_context = "Found products in database: "
        for p in all_found:
            gender_path = "product" if p.gender == 'Women' else "mens/product"
            ai_context += f"[{p.product_name} (Gender: {p.gender}), Price: {p.price}] "
            
            img_url = p.front_image.url if p.front_image else ""
            frontend_results.append({
                'name': p.product_name,
                'price': f"₹{p.price}",
                'image': img_url,
                'link': f"/{gender_path}/{p.slug}/",
                'gender': p.gender
            })
    else:
        ai_context = "No products found in the database matching these keywords."

    for product in frontend_results:
        if isinstance(product.get('price'), str):
            product['price'] = product['price'].replace('â‚¹', 'Rs. ')

    # 5. GENERATE AI REPLY
    ai_message = ai_reply(query, ai_context)

    return JsonResponse({
        'found': len(frontend_results) > 0,
        'message': ai_message,
        'products': frontend_results
    })


CHATBOT_STOP_WORDS = {
    'i', 'want', 'to', 'show', 'me', 'similar', 'give', 'information', 'about',
    'a', 'an', 'the', 'some', 'any', 'do', 'you', 'have', 'looking', 'for',
    'please', 'okay', 'ok', 'can', 'is', 'there', 'need', 'find', 'with',
}

CHATBOT_SYNONYMS = {
    'shoe': ['shoes', 'footwear', 'sandal', 'sandals', 'sneaker', 'sneakers', 'boots', 'heels'],
    'dress': ['dress', 'dresses', 'gown', 'gowns'],
    'bag': ['bag', 'bags', 'handbag', 'handbags', 'purse', 'tote', 'backpack'],
    'top': ['top', 'tops', 'shirt', 'shirts', 'tee', 'tees', 'blouse'],
    'beauty': ['beauty', 'cosmetic', 'cosmetics', 'makeup', 'skincare'],
}

CHATBOT_SUPPORT_RESPONSES = {
    'order_help': "To order a product: 1) Open the product page, 2) Click Add to Cart, 3) Go to My Bag, 4) Click Checkout, 5) Enter address and choose payment, then place your order.",
    'shipping': "Shipping: We provide pan-India delivery. Orders are usually delivered within 3 to 5 business days.",
    'payment': "Payment options: Card, UPI, QR code, and Cash on Delivery are available at checkout.",
    'return': "Return/Exchange: You can request return or exchange for eligible unused items within 7 days.",
    'track': "To track your order, open My Account and check your Order History section.",
}


def build_chatbot_search_terms(query):
    normalized_query = re.sub(r'[^\w\s-]', ' ', (query or '').lower()).strip()
    words = [word for word in normalized_query.split() if word]
    keywords = [word for word in words if word not in CHATBOT_STOP_WORDS and len(word) > 1]
    if not keywords and normalized_query:
        keywords = [normalized_query]

    search_terms = set(keywords or words or [normalized_query])
    for term in list(search_terms):
        for base_term, synonyms in CHATBOT_SYNONYMS.items():
            if term == base_term or term in synonyms:
                search_terms.add(base_term)
                search_terms.update(synonyms)

    return normalized_query, [term for term in search_terms if term]


def get_chatbot_support_intent(query):
    normalized_query = re.sub(r'\s+', ' ', (query or '').lower()).strip()
    if not normalized_query:
        return None

    if any(
        phrase in normalized_query
        for phrase in (
            'how to order',
            'how can i order',
            'how do i order',
            'how to place order',
            'place an order',
            'place order',
            'order process',
            'checkout process',
        )
    ):
        return 'order_help'

    if any(word in normalized_query for word in ('shipping', 'delivery', 'deliver')):
        return 'shipping'
    if any(word in normalized_query for word in ('payment', 'upi', 'card', 'cod', 'cash on delivery')):
        return 'payment'
    if any(word in normalized_query for word in ('return', 'exchange', 'refund')):
        return 'return'
    if any(word in normalized_query for word in ('track', 'tracking', 'where is my order', 'order status')):
        return 'track'

    return None


def search_catalog_products(model_class, cleaned_query, search_terms, limit=4):
    if not cleaned_query and not search_terms:
        return []

    model_field_names = {field.name for field in model_class._meta.get_fields()}
    search_fields = ['product_name']

    for field_name in ('brand', 'gender', 'product_description', 'description'):
        if field_name in model_field_names:
            search_fields.append(field_name)

    if 'category' in model_field_names:
        search_fields.append('category__category_name')
    if 'designer' in model_field_names:
        search_fields.append('designer__name')
    if 'variations' in model_field_names:
        search_fields.extend(['variations__size', 'variations__color', 'variations__category_type'])

    query_filter = Q()
    if cleaned_query:
        for field in search_fields:
            query_filter |= Q(**{f'{field}__icontains': cleaned_query})

    for term in search_terms:
        for field in search_fields:
            query_filter |= Q(**{f'{field}__icontains': term})

    queryset = (
        model_class.objects.select_related('category', 'designer')
        .prefetch_related('variations')
        .filter(is_available=True)
        .filter(query_filter)
        .distinct()
        .order_by('-modified_date', '-created_date')
    )
    return list(queryset[:limit])


def serialize_chatbot_product(product):
    sizes = []
    seen_sizes = set()
    for variation in product.variations.all():
        size = (variation.size or '').strip()
        if not size:
            continue
        normalized_size = size.lower()
        if normalized_size in seen_sizes:
            continue
        seen_sizes.add(normalized_size)
        sizes.append(size)
        if len(sizes) == 4:
            break

    gender = str(getattr(product, 'gender', '')).lower().strip()
    detail_path = 'product' if gender in {'women', 'womens', 'woman', 'female'} else 'mens/product'

    return {
        'name': product.product_name,
        'price': f'Rs. {getattr(product, "display_price", product.price)}',
        'image': product.front_image.url if getattr(product, 'front_image', None) else '',
        'link': f'/{detail_path}/{product.slug}/' if product.slug else '#',
        'gender': product.gender,
        'brand': product.brand,
        'category': getattr(product.category, 'category_name', ''),
        'sizes': ', '.join(sizes),
    }


@require_GET
def chatbot_search(request):
    query = request.GET.get('query', '').strip()
    if not query:
        return JsonResponse({'found': False, 'message': 'How can I help you today?', 'products': []})

    support_intent = get_chatbot_support_intent(query)
    if support_intent:
        return JsonResponse(
            {
                'found': False,
                'message': CHATBOT_SUPPORT_RESPONSES.get(support_intent, 'How can I help you today?'),
                'products': [],
            }
        )

    cleaned_query, search_terms = build_chatbot_search_terms(query)
    womens_products = search_catalog_products(NewProductW, cleaned_query, search_terms, limit=4)
    mens_products = search_catalog_products(NewProductM, cleaned_query, search_terms, limit=4)

    combined_results = []
    seen_products = set()
    for product in womens_products + mens_products:
        product_key = (product.__class__.__name__, product.id)
        if product_key in seen_products:
            continue
        seen_products.add(product_key)
        combined_results.append(product)
        if len(combined_results) == 6:
            break

    combined_results = prepare_products_for_display(combined_results)
    serialized_products = [serialize_chatbot_product(product) for product in combined_results]
    ai_context = (
        '; '.join(
            f"{product['name']} | {product['brand']} | {product['category']} | {product['price']}"
            for product in serialized_products
        )
        if serialized_products
        else 'No products found in the database matching this query.'
    )

    return JsonResponse(
        {
            'found': bool(serialized_products),
            'message': ai_reply(query, ai_context),
            'products': serialized_products,
        }
    )


@require_GET
def health_check(request):
    return JsonResponse({'status': 'ok'})














