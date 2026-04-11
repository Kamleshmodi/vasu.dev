from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ProductVariation, Clothing, Footwear, Dresses, Accessories, Bags

@receiver(post_save, sender=ProductVariation)
def auto_sync_category(sender, instance, **kwargs):
    type_value = (instance.category_type or '').strip().lower()
    product = instance.product

    if type_value == 'clothing':
        Clothing.objects.get_or_create(product=product, size=instance.size, color=instance.color)
    elif type_value == 'footwear':
        Footwear.objects.get_or_create(product=product, size=instance.size, color=instance.color)
    elif type_value == 'dresses':
        Dresses.objects.get_or_create(product=product, size=instance.size, color=instance.color)
    elif type_value == 'accessories':
        Accessories.objects.get_or_create(product=product, color=instance.color)
    elif type_value == 'bags':
        Bags.objects.get_or_create(product=product, color=instance.color)

@receiver(post_delete, sender=ProductVariation)
def auto_delete_synced_category(sender, instance, **kwargs):
    type_value = (instance.category_type or '').strip().lower()
    product = instance.product

    if type_value == 'clothing':
        Clothing.objects.filter(product=product, size=instance.size, color=instance.color).delete()
    elif type_value == 'footwear':
        Footwear.objects.filter(product=product, size=instance.size, color=instance.color).delete()
    elif type_value == 'dresses':
        Dresses.objects.filter(product=product, size=instance.size, color=instance.color).delete()
    elif type_value == 'accessories':
        Accessories.objects.filter(product=product, color=instance.color).delete()
    elif type_value == 'bags':
        Bags.objects.filter(product=product, color=instance.color).delete()
