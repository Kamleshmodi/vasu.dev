from datetime import timedelta

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from aapcategory.models import Category, Designer
from appaccounts.models import VendorProfile
from appmens.models import NewProduct as MenProduct
from appmens.models import ProductImage as MenProductImage
from appmens.models import ProductVariation as MenVariation
from appwomens.models import NewProduct as WomenProduct
from appwomens.models import ProductImage as WomenProductImage
from appwomens.models import ProductVariation as WomenVariation


BACKOFFICE_INPUT_CLASS = 'backoffice-input'
BACKOFFICE_CHECKBOX_CLASS = 'backoffice-checkbox'
SIZE_REQUIRED_TYPES = {'clothing', 'footwear', 'dresses'}
WOMEN_CATEGORY_CHOICES = [
    ('clothing', 'Clothing'),
    ('footwear', 'Footwear'),
    ('dresses', 'Dresses'),
    ('accessories', 'Accessories'),
    ('bags', 'Bags'),
    ('beauty', 'Beauty Products'),
]
MEN_CATEGORY_CHOICES = [
    ('clothing', 'Clothing'),
    ('footwear', 'Footwear'),
    ('dresses', 'Dresses'),
    ('accessories', 'Accessories'),
    ('bags', 'Bags'),
]


class BackofficeStyledFormMixin:
    def apply_backoffice_styles(self):
        for field in self.fields.values():
            existing_class = field.widget.attrs.get('class', '')
            css_class = BACKOFFICE_CHECKBOX_CLASS if isinstance(field.widget, forms.CheckboxInput) else BACKOFFICE_INPUT_CLASS
            field.widget.attrs['class'] = f'{existing_class} {css_class}'.strip()


class VendorProfileForm(BackofficeStyledFormMixin, forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = ['business_name', 'contact_email', 'contact_phone', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_backoffice_styles()


class WomenVendorProductForm(BackofficeStyledFormMixin, forms.ModelForm):
    class Meta:
        model = WomenProduct
        fields = [
            'product_name',
            'brand',
            'designer',
            'category',
            'price',
            'front_image',
            'back_image',
            'product_description',
            'is_available',
        ]
        widgets = {
            'product_description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(gender='women').order_by('category_name')
        self.fields['designer'].queryset = Designer.objects.filter(gender='women').order_by('name')
        self.fields['price'].widget.attrs['step'] = '0.01'
        self.apply_backoffice_styles()


class MenVendorProductForm(BackofficeStyledFormMixin, forms.ModelForm):
    class Meta:
        model = MenProduct
        fields = [
            'product_name',
            'brand',
            'designer',
            'category',
            'price',
            'front_image',
            'back_image',
            'description',
            'is_available',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(gender='men').order_by('category_name')
        self.fields['designer'].queryset = Designer.objects.filter(gender='men').order_by('name')
        self.fields['price'].widget.attrs['step'] = '0.01'
        self.apply_backoffice_styles()


class ProductSaleForm(BackofficeStyledFormMixin, forms.Form):
    is_enabled = forms.BooleanField(
        required=False,
        label='Add this product to the sale list',
    )
    discount_percentage = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=100,
        decimal_places=2,
        max_digits=5,
        label='Discount (%)',
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def __init__(self, *args, sale_instance=None, **kwargs):
        self.sale_instance = sale_instance
        super().__init__(*args, **kwargs)

        if sale_instance:
            self.initial.update(
                {
                    'is_enabled': True,
                    'discount_percentage': sale_instance.discount_percentage,
                    'start_date': sale_instance.start_date,
                    'end_date': sale_instance.end_date,
                }
            )
        else:
            self.initial.setdefault('start_date', timezone.localdate())
            self.initial.setdefault('end_date', timezone.localdate() + timedelta(days=7))

        self.fields['discount_percentage'].widget.attrs['step'] = '0.01'
        self.apply_backoffice_styles()

    def clean(self):
        cleaned_data = super().clean()
        is_enabled = cleaned_data.get('is_enabled')
        discount_percentage = cleaned_data.get('discount_percentage')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if not is_enabled:
            return cleaned_data

        if discount_percentage in {None, ''}:
            self.add_error('discount_percentage', 'Enter the discount percentage for the sale.')
        if not start_date:
            self.add_error('start_date', 'Select when the sale should start.')
        if not end_date:
            self.add_error('end_date', 'Select when the sale should end.')
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', 'Sale end date must be on or after the start date.')

        return cleaned_data

    def save(self, product, sale_model):
        existing_sales = list(
            sale_model.objects.filter(product=product).order_by('-end_date', '-start_date', '-id')
        )

        if not self.cleaned_data.get('is_enabled'):
            if existing_sales:
                sale_model.objects.filter(product=product).delete()
            return None

        sale = existing_sales[0] if existing_sales else sale_model(product=product)
        sale.product = product
        sale.discount_percentage = float(self.cleaned_data['discount_percentage'])
        sale.start_date = self.cleaned_data['start_date']
        sale.end_date = self.cleaned_data['end_date']
        sale.save()

        if existing_sales and len(existing_sales) > 1:
            sale_model.objects.filter(product=product).exclude(pk=sale.pk).delete()

        return sale


class BaseVendorVariationForm(BackofficeStyledFormMixin, forms.ModelForm):
    category_choices = []

    class Meta:
        fields = ['size', 'color', 'stock', 'category_type']
        widgets = {
            'stock': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category_type'].required = True
        self.fields['category_type'].choices = self.category_choices
        self.fields['stock'].min_value = 1
        self.apply_backoffice_styles()

    def clean(self):
        cleaned_data = super().clean()
        category_type = (cleaned_data.get('category_type') or '').strip().lower()
        size = (cleaned_data.get('size') or '').strip()

        if category_type and category_type in SIZE_REQUIRED_TYPES and not size:
            self.add_error('size', 'Size is required for this product section.')

        return cleaned_data


class WomenVariationForm(BaseVendorVariationForm):
    category_choices = WOMEN_CATEGORY_CHOICES

    class Meta(BaseVendorVariationForm.Meta):
        model = WomenVariation


class MenVariationForm(BaseVendorVariationForm):
    category_choices = MEN_CATEGORY_CHOICES

    class Meta(BaseVendorVariationForm.Meta):
        model = MenVariation


class BaseVendorVariationFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        active_rows = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            if form.cleaned_data.get('DELETE'):
                continue

            if not form.cleaned_data:
                continue

            category_type = form.cleaned_data.get('category_type')
            stock = form.cleaned_data.get('stock')

            if not category_type and any(form.cleaned_data.get(field) for field in ['size', 'color', 'stock']):
                form.add_error('category_type', 'Select the section for this variation.')

            if stock is not None and stock < 1:
                form.add_error('stock', 'Stock must be at least 1.')

            if category_type:
                active_rows += 1

        if active_rows == 0:
            raise forms.ValidationError('Add at least one product variation to save this product.')


class BaseVendorGalleryImageForm(BackofficeStyledFormMixin, forms.ModelForm):
    class Meta:
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_backoffice_styles()


class WomenGalleryImageForm(BaseVendorGalleryImageForm):
    class Meta(BaseVendorGalleryImageForm.Meta):
        model = WomenProductImage


class MenGalleryImageForm(BaseVendorGalleryImageForm):
    class Meta(BaseVendorGalleryImageForm.Meta):
        model = MenProductImage


WomenVariationFormSet = inlineformset_factory(
    WomenProduct,
    WomenVariation,
    form=WomenVariationForm,
    formset=BaseVendorVariationFormSet,
    extra=0,
    can_delete=True,
)

MenVariationFormSet = inlineformset_factory(
    MenProduct,
    MenVariation,
    form=MenVariationForm,
    formset=BaseVendorVariationFormSet,
    extra=0,
    can_delete=True,
)

WomenGalleryImageFormSet = inlineformset_factory(
    WomenProduct,
    WomenProductImage,
    form=WomenGalleryImageForm,
    extra=1,
    can_delete=True,
)

MenGalleryImageFormSet = inlineformset_factory(
    MenProduct,
    MenProductImage,
    form=MenGalleryImageForm,
    extra=1,
    can_delete=True,
)
