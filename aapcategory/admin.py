from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import Category, Designer
from appwomens.models import NewProduct as WomensProduct
from appmens.models import NewProduct as MensProduct

# Category Form
class CategoryForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        category_name = cleaned_data.get("category_name")
        gender = cleaned_data.get("gender")
        if Category.objects.filter(category_name=category_name, gender=gender).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This category name with this gender already exists.")
        return cleaned_data

# Category Admin
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    prepopulated_fields = {'slug': ('category_name',)}
    list_display = ('category_name', 'slug', 'gender')
    ordering = ['category_name']

admin.site.register(Category, CategoryAdmin)

# Designer Admin
@admin.register(Designer)
class DesignerAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'gender']
    list_filter = ['gender']
    ordering = ['name']
