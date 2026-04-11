from .models import Wishlist, Cart

def cart_wishlist_count(request):
    cart_count = 0
    wishlist_count = 0
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count
    }