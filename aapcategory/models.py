from django.core.exceptions import ValidationError  
from django.db import models
from django.utils.text import slugify
from django.urls import reverse

class Category(models.Model):
    GENDER_CHOICES = [
        ('women', 'Women'),
        ('men', 'Men'),
    ]

    category_name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(max_length=255, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    class Meta:
        db_table = 'category'
        verbose_name = 'category'
        verbose_name_plural = 'categories'
        unique_together = ('category_name', 'gender')

    def save(self, *args, **kwargs):
        base_slug = slugify(f"{self.category_name}-{self.gender}")
        slug = base_slug
        counter = 1
        while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        self.slug = slug
        super().save(*args, **kwargs)

    def get_url(self):
        return reverse('products_by_category_name', args=[self.slug])

    def __str__(self):
        return self.category_name

    def clean(self):
        if Category.objects.filter(category_name=self.category_name, gender=self.gender).exclude(pk=self.pk).exists():
            raise ValidationError("This category name with this gender already exists.")


class Designer(models.Model):
    GENDER_CHOICES = [
        ('women', 'Women'),
        ('men', 'Men'),
    ]

    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    class Meta:
        unique_together = ('name', 'gender') 

    def __str__(self):
        return f"{self.name} ({self.gender})"
