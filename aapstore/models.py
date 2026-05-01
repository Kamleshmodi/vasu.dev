from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from aapcategory.models import Category, Designer
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Purane models waise hi rahenge...
class Gender(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    brand = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(max_length=500, blank=True)
    price = models.IntegerField()
    front_image = models.ImageField(upload_to='photos/products')
    back_image = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    designer = models.ForeignKey('aapcategory.Designer', on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.product_name

class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    color = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=50, blank=True)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.product.product_name} - {self.color} - {self.size}'

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    added_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Wishlist Items'

    def __str__(self):
        return f'{self.user.username} - {self.content_object}'

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    quantity = models.IntegerField(default=1)
    added_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Cart Items'

    def __str__(self):
        return f'{self.user.username} - {self.content_object}'

# --- YAHAN ORDER MODEL MEIN BADLAV KIYA GAYA HAI ---
class Order(models.Model):
    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Card'
        UPI = 'upi', 'UPI'
        QRCODE = 'qrcode', 'QR Code'
        CASH = 'cash', 'Cash'

    class PaymentStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        REFUND_IN_PROCESS = 'Refund In Process', 'Refund In Process'
        REFUNDED = 'Refunded', 'Refunded'
        FAILED = 'Failed', 'Failed'

    class AccountReceiptStatus(models.TextChoices):
        NOT_RECEIVED = 'Not Received', 'Not Received'
        PENDING = 'Pending Verification', 'Pending Verification'
        RECEIVED = 'Received in Account', 'Received in Account'
        FAILED = 'Failed', 'Failed'

    class Status(models.TextChoices):
        PROCESSING = 'Processing', 'Processing'
        SHIPPED = 'Shipped', 'Shipped'
        DELIVERED = 'Delivered', 'Delivered'
        CANCELLED = 'Cancelled', 'Cancelled'

    class ReturnStatus(models.TextChoices):
        NONE = 'No Return', 'No Return'
        REQUESTED = 'Requested', 'Requested'
        APPROVED = 'Approved', 'Approved'
        PICKED_UP = 'Picked Up', 'Picked Up'
        RECEIVED = 'Received', 'Received'
        COMPLETED = 'Completed', 'Completed'
        REJECTED = 'Rejected', 'Rejected'

    class RefundStatus(models.TextChoices):
        NOT_REQUIRED = 'Not Required', 'Not Required'
        PENDING = 'Pending', 'Pending'
        PROCESSING = 'Processing', 'Processing'
        COMPLETED = 'Completed', 'Completed'
        REJECTED = 'Rejected', 'Rejected'

    order_id = models.CharField(max_length=100, unique=True, blank=True) # Blank=True zaroori hai
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    zip_code = models.CharField(max_length=10)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PaymentMethod.choices)
    payment_reference = models.CharField(max_length=120, blank=True)
    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    account_receipt_status = models.CharField(
        max_length=30,
        choices=AccountReceiptStatus.choices,
        default=AccountReceiptStatus.NOT_RECEIVED,
    )
    account_receipt_reference = models.CharField(max_length=120, blank=True)
    account_receipt_confirmed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    return_status = models.CharField(
        max_length=30,
        choices=ReturnStatus.choices,
        default=ReturnStatus.NONE,
    )
    refund_status = models.CharField(
        max_length=30,
        choices=RefundStatus.choices,
        default=RefundStatus.NOT_REQUIRED,
    )
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    refund_reference = models.CharField(max_length=120, blank=True)
    refund_processed_at = models.DateTimeField(blank=True, null=True)
    payment_notes = models.TextField(blank=True)
    delivery_partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='assigned_delivery_orders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    delivery_assigned_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order_id} by {self.full_name}"

    @classmethod
    def default_payment_status_for_method(cls, payment_method):
        return (
            cls.PaymentStatus.PENDING
            if payment_method == cls.PaymentMethod.CASH
            else cls.PaymentStatus.PAID
        )

    @classmethod
    def default_account_receipt_status_for_method(cls, payment_method):
        return (
            cls.AccountReceiptStatus.NOT_RECEIVED
            if payment_method == cls.PaymentMethod.CASH
            else cls.AccountReceiptStatus.PENDING
        )

    def save(self, *args, **kwargs):
        if self._state.adding and self.payment_method:
            self.payment_status = self.default_payment_status_for_method(self.payment_method)
        elif not self.payment_status:
            self.payment_status = self.default_payment_status_for_method(self.payment_method)

        if (
            self._state.adding
            and self.payment_method
            and self.account_receipt_status == self.AccountReceiptStatus.NOT_RECEIVED
            and self.payment_method != self.PaymentMethod.CASH
        ):
            self.account_receipt_status = self.default_account_receipt_status_for_method(self.payment_method)
        elif self._state.adding and self.payment_method and not self.account_receipt_status:
            self.account_receipt_status = self.default_account_receipt_status_for_method(self.payment_method)
        elif not self.account_receipt_status:
            self.account_receipt_status = self.default_account_receipt_status_for_method(self.payment_method)

        if self.account_receipt_status == self.AccountReceiptStatus.RECEIVED and not self.account_receipt_confirmed_at:
            self.account_receipt_confirmed_at = timezone.now()
        elif self.account_receipt_status != self.AccountReceiptStatus.RECEIVED:
            self.account_receipt_confirmed_at = None

        if self.refund_status == self.RefundStatus.COMPLETED and not self.refund_processed_at:
            self.refund_processed_at = timezone.now()

        super().save(*args, **kwargs)
        if not self.order_id:
            self.order_id = str(self.pk + 100)
            Order.objects.filter(pk=self.pk).update(order_id=self.order_id)


class OrderItem(models.Model):
    class FulfillmentStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        ACCEPTED = 'Accepted', 'Accepted'
        REJECTED = 'Rejected', 'Rejected'
        PACKED = 'Packed', 'Packed'
        SHIPPED = 'Shipped', 'Shipped'
        DELIVERED = 'Delivered', 'Delivered'

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='managed_order_items',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    fulfillment_status = models.CharField(
        max_length=20,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.PENDING,
    )
    status_notes = models.CharField(max_length=255, blank=True)
    status_updated_at = models.DateTimeField(auto_now=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        product_name = self.content_object.product_name if self.content_object else f"ID: {self.object_id}"
        return f"{product_name} ({self.quantity})"

    def save(self, *args, **kwargs):
        if not self.vendor_id and self.content_object:
            self.vendor = getattr(self.content_object, 'vendor', None)
        super().save(*args, **kwargs)


class ProductRating(models.Model):
    RATING_CHOICES = [(value, f'{value} Star') for value in range(1, 6)]
    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    order = models.ForeignKey(Order, related_name='product_ratings', on_delete=models.CASCADE)
    order_item = models.OneToOneField(OrderItem, related_name='rating', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='product_ratings', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    title = models.CharField(max_length=120, blank=True)
    review = models.TextField(max_length=600, blank=True)
    review_image = models.ImageField(upload_to='photos/reviews', blank=True, null=True)
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    moderation_notes = models.CharField(max_length=255, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='moderated_product_ratings',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    moderated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        if self.order_item_id and (not self.content_type_id or not self.object_id):
            self.content_type = self.order_item.content_type
            self.object_id = self.order_item.object_id
        if self.order_item_id and not self.order_id:
            self.order = self.order_item.order
        super().save(*args, **kwargs)

    @property
    def product_name(self):
        return getattr(self.content_object, 'product_name', 'Product')

    def __str__(self):
        return f'{self.product_name} - {self.rating}/5'


class UserEvent(models.Model):
    class EventType(models.TextChoices):
        PAGE_VIEW = 'page_view', 'Page View'
        USER_EVENT = 'user_event', 'User Event'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='analytics_events',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.USER_EVENT)
    event_name = models.CharField(max_length=120)
    page_path = models.CharField(max_length=500, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    session_key = models.CharField(max_length=80, blank=True)
    anonymous_id = models.CharField(max_length=80, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type}:{self.event_name} ({self.created_at:%Y-%m-%d %H:%M})'


class SupportRequest(models.Model):
    class RequestType(models.TextChoices):
        SUPPORT = 'support', 'Support Question'
        BUG = 'bug', 'Bug Report'
        FEEDBACK = 'feedback', 'General Feedback'
        FEATURE = 'feature', 'Feature Request'

    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_REVIEW = 'in_review', 'In Review'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    ticket_id = models.CharField(max_length=24, unique=True, blank=True)
    reporter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='support_requests',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    order = models.ForeignKey(
        Order,
        related_name='support_requests',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    request_type = models.CharField(max_length=20, choices=RequestType.choices, default=RequestType.SUPPORT)
    severity = models.CharField(max_length=12, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField(max_length=4000)
    page_url = models.CharField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.ticket_id:
            generated_id = f'SR-{self.pk + 10000}'
            self.ticket_id = generated_id
            SupportRequest.objects.filter(pk=self.pk).update(ticket_id=generated_id)

    def __str__(self):
        return f'{self.ticket_id or "SR"} - {self.subject}'

from django.db import models
from django.conf import settings 
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='userprofile/', blank=True, null=True)
    address_line_1 = models.CharField(max_length=150, blank=True)
    address_line_2 = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default='India')
    postal_code = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return getattr(self.user, 'first_name', self.user.username)

    def full_address(self):
        return f'{self.address_line_1} {self.address_line_2}'

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return

    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return

    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
