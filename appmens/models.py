from django.db import models
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from aapcategory.models import Category, Designer

SIZES = [
    ('30', '30'), ('32', '32'), ('34', '34'),
    ('36', '36'), ('38', '38'), ('40', '40'),
    ('S', 'Small'), ('M', 'Medium'), ('L', 'Large'), ('XL', 'XL'),
    ('XXL', 'XXL'), ('XXXL', 'XXXL'),
    ('Free Size', 'Free Size'),
]

FSIZES = [
    ('5', '5'), ('6', '6'), ('7', '7'),
    ('8', '8'), ('9', '9'), ('10', '10'),
    ('11', '11'), ('12', '12'), ('13', '13'),
    ('14', '14'), ('15', '15'), ('16', '16'),

]

COLORS = [
    ('-', '-'),('Black', 'Black'), ('White', 'White'), ('Blue', 'Blue'),
    ('Red', 'Red'), ('Green', 'Green'), ('Grey', 'Grey'),('Multi Color', 'Multi Color'),
    ('Pink', 'Pink'), ('Yellow', 'Yellow'), ('Brown', 'Brown'), ('Purple', 'Purple'),
    ('Orange', 'Orange'), ('Cyan', 'Cyan'), ('Magenta', 'Magenta'),
    ('Blank', 'Blank'),
]

CATEGORY_TYPE_CHOICES = [
    ('clothing', 'Clothing'),
    ('footwear', 'Footwear'),
    ('dresses', 'Dresses'),
    ('accessories', 'Accessories'),
    ('bags', 'Bags'),
    ('beauty', 'Beauty Products'),
]

class NewProductChoices(models.TextChoices):
    CLOTHING = 'Clothing', 'Clothing'
    FOOTWEAR = 'Footwear', 'Footwear'
    ACCESSORIES = 'Accessories', 'Accessories'
    DRESSES = 'Dresses', 'Dresses'
    BAGS = 'Bags', 'Bags'
    SALE = 'Sale', 'Sale'

class NewProduct(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    brand = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='mens_products_created', on_delete=models.SET_NULL, null=True, blank=True)
    designer = models.ForeignKey(Designer, on_delete=models.CASCADE, related_name='mens_products')
    gender = models.CharField(max_length=10, default='Mens')
    description = models.TextField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    front_image = models.ImageField(upload_to='photos/products')
    back_image = models.ImageField(upload_to='photos/products')
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="mens_products")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_name


class ProductImage(models.Model):
    product = models.ForeignKey(NewProduct, related_name='gallery_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='photos/products')
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Gallery image for {self.product.product_name}"
    
class ProductVariation(models.Model):
    product = models.ForeignKey(NewProduct, related_name='variations', on_delete=models.CASCADE)
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    stock = models.IntegerField(default=1)
    # product_type = models.CharField(max_length=50, blank=True, null=True)
    category_type = models.CharField(max_length=50, choices=CATEGORY_TYPE_CHOICES, blank=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.size} - {self.color} - {self.category_type}"

class Clothing(models.Model):
    product = models.ForeignKey(NewProduct, on_delete=models.CASCADE)
    size = models.CharField(max_length=50, choices=SIZES)
    color = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.size} - {self.color}"


class Footwear(models.Model):
    product = models.ForeignKey(NewProduct, on_delete=models.CASCADE)
    size = models.CharField(max_length=50, choices=FSIZES)
    color = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.size} - {self.color}"


class Accessories(models.Model):
    product = models.ForeignKey(NewProduct, on_delete=models.CASCADE)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.size} - {self.color}"


class Dresses(models.Model):
    product = models.ForeignKey(NewProduct, on_delete=models.CASCADE)
    size = models.CharField(max_length=50, choices=SIZES)
    color = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.size} - {self.color}"


class Bags(models.Model):
    product = models.ForeignKey(NewProduct, on_delete=models.CASCADE)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.size} - {self.color}"


class SaleItems(models.Model):
    product = models.ForeignKey(NewProduct, on_delete=models.CASCADE)
    discount_percentage = models.FloatField()
    start_date = models.DateField()
    end_date = models.DateField()
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.product_name} - Sale: {self.discount_percentage}% off"

    def save(self, *args, **kwargs):
        base_price = Decimal(str(self.product.price or 0))
        discount_percentage = Decimal(str(self.discount_percentage or 0))
        discount_percentage = min(max(discount_percentage, Decimal('0')), Decimal('100'))
        self.sale_price = (
            base_price * (Decimal('100') - discount_percentage) / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

class Happenings(models.Model):
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(max_length=200, blank=True)
    image = models.ImageField(upload_to='photos/mens_features/')

    def __str__(self):
        return self.title

class HomeTemplate(models.Model):
    product_type = models.CharField(
        max_length=20,
        choices=NewProductChoices.choices
    )
    home_template_image = models.ImageField(upload_to='photos/home_template')

    def __str__(self):
        return f"Home Template for {self.product_type}"
