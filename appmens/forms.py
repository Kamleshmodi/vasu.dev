from django import forms
from .models import CATEGORY_TYPE_CHOICES
from .models import NewProduct, Clothing, Footwear, Dresses, Accessories, Bags, ProductVariation
from aapcategory.models import Category
from .models import NewProduct

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

class MensProductForm(forms.ModelForm):
    class Meta:
        model = NewProduct
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(gender='men')


class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = ['size', 'color', 'stock', 'category_type']
        widgets = {
            'category_type': forms.Select(choices=CATEGORY_TYPE_CHOICES),
        }


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


