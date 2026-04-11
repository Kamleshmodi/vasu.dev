# from django.shortcuts import render, get_object_or_404
# from aapcategory.models import Category  
# from aapstore.models import ProductWomen

# def WomensNew(request):
#     products = ProductWomen.objects.filter(is_available=True)
#     categories = Category.objects.all()
#     item_count = products.count()
#     return render(request, 'womens/Wnew.html', {
#         'products': products,
#         'categories': categories,
#         'item_count': item_count,
#     })

# def WomensNewByCategory(request, category_slug):
#     category = get_object_or_404(Category, slug=category_slug)
#     products = ProductWomen.objects.filter(category=category, is_available=True)
#     categories = Category.objects.all()
#     item_count = products.count()
#     return render(request, 'womens/Wnew.html', {
#         'products': products,
#         'categories': categories,
#         'item_count': item_count,
#     })




