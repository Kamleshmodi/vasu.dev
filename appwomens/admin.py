from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import (
    NewProduct, Clothing, Footwear, Accessories, Dresses,
    Bags, BeautyProducts, SaleItems, Kendalls_editions, Shops,
    HomeTemplate, ProductVariation, ProductImage
)

# ---------- Custom Color Widget ----------
class ColorTextInput(forms.TextInput):
    input_type = 'text'
    template_name = 'admin/widgets/color_datalist.html'

    def get_context(self, name, value, attrs):
        attrs = attrs or {}
        attrs['list'] = f"{name}_colors"
        context = super().get_context(name, value, attrs)
        context['widget']['datalist'] = [
            'Black', 'White', 'Blue', 'Red', 'Green', 'Grey', 'Multi Color',
            'Pink', 'Yellow', 'Brown', 'Purple', 'Orange', 'Cyan', 'Magenta', 'Blank'
        ]
        context['widget']['attrs']['list'] = f"{name}_colors"
        context['widget']['datalist_id'] = f"{name}_colors"
        return context

# ---------- Custom Forms ----------
class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = '__all__'

class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    form = ProductVariationForm
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

# ---------- Inline Category Models ----------
class BaseCategoryInline(admin.TabularInline):
    extra = 0
    can_delete = False
    readonly_fields = ('size', 'color')
    def has_add_permission(self, request, obj=None):
        return False

class ClothingInline(BaseCategoryInline):
    model = Clothing

class FootwearInline(BaseCategoryInline):
    model = Footwear

class DressesInline(BaseCategoryInline):
    model = Dresses

class AccessoriesInline(BaseCategoryInline):
    model = Accessories

class BagsInline(BaseCategoryInline):
    model = Bags

class BeautyProductsInline(BaseCategoryInline):
    model = BeautyProducts

# ---------- Image Preview ----------
def preview_image(obj):
    if obj.front_image:
        return format_html('<img src="{}" width="50" height="60" style="object-fit:cover;" />', obj.front_image.url)
    return "No Image"
preview_image.short_description = 'Preview'

# ---------- Admin: NewProduct ----------
@admin.register(NewProduct)
class NewProductAdmin(admin.ModelAdmin):
    ordering = ['-created_date']
    list_display = (
        'product_name', 'brand', 'designer', 'price',
        'category', 'is_available', 'modified_date',
        'product_description', preview_image, 'sync_button'
    )
    list_filter = ('brand', 'category', 'designer', 'is_available')
    search_fields = ('product_name', 'brand', 'category__category_name')
    prepopulated_fields = {'slug': ('product_name',)}
    inlines = [
        ProductVariationInline,
        ProductImageInline,
        ClothingInline, FootwearInline, DressesInline,
        AccessoriesInline, BagsInline, BeautyProductsInline
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'sync/<int:product_id>/',
                self.admin_site.admin_view(self.sync_to_category),
                name='sync_to_category',
            ),
        ]
        return custom_urls + urls

    def sync_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Sync Now</a>',
            f"/admin/appwomens/newproduct/sync/{obj.pk}/"
        )
    sync_button.short_description = 'Sync to Categories'
    sync_button.allow_tags = True

    def sync_to_category(self, request, product_id):
        product = NewProduct.objects.get(pk=product_id)
        variations = ProductVariation.objects.filter(product=product)

        count = 0
        for var in variations:
            type_value = (var.type or '').strip().lower()
            if type_value == 'clothing':
                Clothing.objects.get_or_create(product=product, size=var.size, color=var.color)
                count += 1
            elif type_value == 'footwear':
                Footwear.objects.get_or_create(product=product, size=var.size, color=var.color)
                count += 1
            elif type_value == 'dresses':
                Dresses.objects.get_or_create(product=product, size=var.size, color=var.color)
                count += 1
            elif type_value == 'accessories':
                Accessories.objects.get_or_create(product=product, color=var.color)
                count += 1
            elif type_value == 'bags':
                Bags.objects.get_or_create(product=product, color=var.color)
                count += 1
            elif type_value == 'beauty':
                BeautyProducts.objects.get_or_create(product=product)
                count += 1

        messages.success(request, f"✅ {count} item(s) synced based on type field.")
        return redirect(f"/admin/appwomens/newproduct/{product_id}/change/")

@admin.register(Clothing)
class ClothingAdmin(admin.ModelAdmin):
    ordering = ['-product__created_date']
    list_display = ('product',)
    

@admin.register(Dresses)
class DressesAdmin(admin.ModelAdmin):
    ordering = ['-product__created_date']
    list_display = ('product',)

@admin.register(Footwear)
class FootwearAdmin(admin.ModelAdmin):
    ordering = ['-product__created_date']
    list_display = ('product',)

@admin.register(Accessories)
class AccessoriesAdmin(admin.ModelAdmin):
    ordering = ['-product__created_date']
    list_display = ('product',)

@admin.register(Bags)
class BagsAdmin(admin.ModelAdmin):
    ordering = ['-product__created_date']
    list_display = ('product',)

@admin.register(BeautyProducts)
class BeautyAdmin(admin.ModelAdmin):
    ordering = ['-product__created_date']
    list_display = ('product', )

@admin.register(SaleItems)
class SaleItemsAdmin(admin.ModelAdmin):
    ordering = ['-product__created_date']
    list_display = ('product', 'discount_percentage', 'start_date', 'end_date', 'sale_price')

@admin.register(Shops)
class ShopItemsAdmin(admin.ModelAdmin):
    
    def preview_image(self, obj):
        if obj.front_image:
            return format_html('<img src="{}" width="50" height="60" style="object-fit:cover;" />', obj.front_image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

    list_display = ('product', 'is_trending', 'is_vasu_soap')  
    list_editable = ('is_trending', 'is_vasu_soap')
    search_fields = ('product__product_name',)

@admin.register(Kendalls_editions)
class KendallEditAdmin(admin.ModelAdmin):
    list_display = ['edition_number', 'edition_name', 'preview_image']

    def preview_image(self, obj):
        if obj.edition_image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit: cover;" />',
                obj.edition_image.url
            )
        return "(No image)"
    preview_image.short_description = "Image Preview"

@admin.register(HomeTemplate)
class HomeTemplateAdmin(admin.ModelAdmin):
    def preview_image(self, obj):
        if obj.home_template_image:
            return format_html('<img src="{}" width="60" height="70" style="object-fit:cover;" />', obj.home_template_image.url)
        return "No Image"
    preview_image.short_description = 'Preview'
    list_display = ('product_type', preview_image)
