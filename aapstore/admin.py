from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from .models import Product, Variation, Wishlist, Cart, Gender, Order, OrderItem, ProductRating, UserEvent, SupportRequest

# ---------- Product Image Preview (Helper Function) ----------
def preview_image(obj):
    if obj.front_image:
        return format_html('<img src="{}" width="50" height="60" style="object-fit:cover;" />', obj.front_image.url)
    return "No Image"
preview_image.short_description = 'Preview'

# ---------- Admin for old Product model ----------
class VariationInline(admin.TabularInline):
    model = Variation
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'is_available', 'category', 'gender', 'created_date', preview_image)
    list_filter = ('is_available', 'category', 'gender')
    list_editable = ('is_available',)
    search_fields = ('product_name', 'brand')
    prepopulated_fields = {'slug': ('product_name',)}
    inlines = [VariationInline]

# ---------- Custom Admin for Cart and Wishlist (using GenericForeignKey) ----------
class CartWishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_name', 'product_price', 'quantity_or_date')
    list_filter = ('user', 'added_date')
    search_fields = ('user__username', 'content_type__model', 'object_id')
    readonly_fields = ('user', 'content_type', 'object_id') # Make these read-only in admin

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('content_object')

    def product_name(self, obj):
        if obj.content_object:
            return obj.content_object.product_name
        return "N/A (Product Deleted)"
    product_name.short_description = 'Product Name'

    def product_price(self, obj):
        if obj.content_object:
            return obj.content_object.price
        return "N/A"
    product_price.short_description = 'Price'

    def quantity_or_date(self, obj):
        if hasattr(obj, 'quantity'):
            return f'Qty: {obj.quantity}'
        return f'Date: {obj.added_date.strftime("%Y-%m-%d")}'
    quantity_or_date.short_description = 'Details'

# Register Wishlist and Cart with the custom admin class
@admin.register(Wishlist)
class WishlistAdmin(CartWishlistAdmin):
    pass

@admin.register(Cart)
class CartAdmin(CartWishlistAdmin):
    pass

# ---------- Admin: Order and OrderItem (YAHAN BADLAV KIYA GAYA HAI) ----------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Naye OrderItem model ke hisaab se fields ko update kiya gaya hai
    fields = (
        'content_object',
        'vendor',
        'price',
        'quantity',
        'fulfillment_status',
        'status_notes',
        'status_updated_at',
    )
    readonly_fields = fields  # Sabhi fields ko read-only banaya gaya hai

    # Add/Delete permission ko band kar diya gaya hai
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_id',
        'user',
        'delivery_partner',
        'payment_method',
        'payment_status',
        'account_receipt_status',
        'status',
        'return_status',
        'refund_status',
        'total_price',
        'full_name',
        'created_at',
    )
    list_filter = (
        'status',
        'payment_method',
        'payment_status',
        'account_receipt_status',
        'delivery_partner',
        'return_status',
        'refund_status',
        'created_at',
    )
    search_fields = (
        'order_id',
        'user__username',
        'full_name',
        'district',
        'country',
        'delivery_partner__username',
        'delivery_partner__email',
        'payment_reference',
        'refund_reference',
    )
    readonly_fields = (
        'user',
        'created_at',
        'total_price',
        'full_name',
        'mobile',
        'address',
        'city',
        'district',
        'state',
        'country',
        'zip_code',
        'payment_reference',
        'account_receipt_reference',
        'account_receipt_confirmed_at',
        'refund_processed_at',
    )
    inlines = [OrderItemInline]


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'user', 'rating', 'approval_status', 'order', 'updated_at', 'review_image_preview')
    list_filter = ('rating', 'approval_status', 'updated_at')
    search_fields = ('user__username', 'title', 'review')
    readonly_fields = (
        'order',
        'order_item',
        'user',
        'content_type',
        'object_id',
        'created_at',
        'updated_at',
        'review_image_preview',
        'moderated_at',
        'moderated_by',
    )
    actions = ('approve_reviews', 'reject_reviews')

    def review_image_preview(self, obj):
        if obj.review_image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:8px;" />', obj.review_image.url)
        return 'No Image'
    review_image_preview.short_description = 'Review Image'

    @admin.action(description='Approve selected reviews')
    def approve_reviews(self, request, queryset):
        queryset.update(
            approval_status=ProductRating.ApprovalStatus.APPROVED,
            moderated_at=timezone.now(),
            moderated_by_id=request.user.id,
            moderation_notes='Approved by admin.',
        )

    @admin.action(description='Reject selected reviews')
    def reject_reviews(self, request, queryset):
        queryset.update(
            approval_status=ProductRating.ApprovalStatus.REJECTED,
            moderated_at=timezone.now(),
            moderated_by_id=request.user.id,
            moderation_notes='Rejected by admin.',
        )

# Register any remaining models
# admin.site.register(Gender)


@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'event_name', 'user', 'page_path', 'anonymous_id')
    list_filter = ('event_type', 'created_at')
    search_fields = ('event_name', 'page_path', 'user__email', 'user__username', 'anonymous_id', 'session_key')
    readonly_fields = (
        'created_at',
        'event_type',
        'event_name',
        'user',
        'page_path',
        'referrer',
        'session_key',
        'anonymous_id',
        'ip_address',
        'user_agent',
        'properties',
    )

    def has_add_permission(self, request):
        return False


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_id',
        'created_at',
        'request_type',
        'severity',
        'status',
        'name',
        'email',
        'order',
    )
    list_filter = ('request_type', 'severity', 'status', 'created_at')
    search_fields = ('ticket_id', 'subject', 'message', 'email', 'name', 'order__order_id')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at', 'reporter_user', 'ip_address', 'user_agent')

