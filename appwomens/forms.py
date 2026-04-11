from django import forms
from .models import NewProduct, Clothing, Footwear, Dresses, Accessories, Bags, ProductVariation
from .models import CATEGORY_TYPE_CHOICES

# Color input widget (already used in admin)
COLOR_CHOICES = [
    'Black', 'White', 'Blue', 'Red', 'Green', 'Grey', 'Multi Color',
    'Pink', 'Yellow', 'Brown', 'Purple', 'Orange', 'Cyan', 'Magenta', 'Blank'
]

class ColorTextInput(forms.TextInput):
    input_type = 'text'
    template_name = 'admin/widgets/color_datalist.html'

    def get_context(self, name, value, attrs):
        attrs = attrs or {}
        attrs['list'] = f"{name}_colors"
        context = super().get_context(name, value, attrs)
        context['widget']['datalist'] = COLOR_CHOICES
        context['widget']['attrs']['list'] = f"{name}_colors"
        context['widget']['datalist_id'] = f"{name}_colors"
        return context


# New Product form
class WomensProductForm(forms.ModelForm):
    class Meta:
        model = NewProduct
        fields = '__all__'

# Product Variations
class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = ['size', 'color', 'stock', 'product_type', 'category_type']
        widgets = {
            'category_type': forms.Select(choices=CATEGORY_TYPE_CHOICES),
        }

# Forms with color picker
class ClothingForm(forms.ModelForm):
    class Meta:
        model = Clothing
        fields = '__all__'
        widgets = {'color': ColorTextInput()}

class FootwearForm(forms.ModelForm):
    class Meta:
        model = Footwear
        fields = '__all__'
        widgets = {'color': ColorTextInput()}

class DressesForm(forms.ModelForm):
    class Meta:
        model = Dresses
        fields = '__all__'
        widgets = {'color': ColorTextInput()}

class AccessoriesForm(forms.ModelForm):
    class Meta:
        model = Accessories
        fields = '__all__'
        widgets = {'color': ColorTextInput()}

class BagsForm(forms.ModelForm):
    class Meta:
        model = Bags
        fields = '__all__'
        widgets = {'color': ColorTextInput()}
