from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from .views import health_check
from . import views

urlpatterns = [
    path("healthz", health_check),
    
    path('admin/', admin.site.urls),
    path('accounts/', include('appaccounts.urls')),

    # ---------- COMMON ----------
    path('login/', views.Login, name='login'),
    path('need-help/', views.NeedHelp, name='need_help'),
  

    # ---------- PASSWORD RESET ----------
    path('reset_password/', auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html"), name="reset_password"),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_sent.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_form.html"), name="password_reset_confirm"),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),

    # ---------- WOMEN ----------
    path('', views.Index, name='home'),
   
    path('home/', views.Index, name='womens_home'),
    path('health/', views.health_check, name='health_check'),
    # ======================================
    path('new/', views.WomensNew, name='womens_new'),
    path('designers/', views.WomensDesigners, name='womens_designers'),
    path('clothing/', views.WomensClothing, name='womens_clothing'),
    path('dresses/', views.WomensDresses, name='womens_dresses'),
    path('shoes/', views.WomensShoes, name='womens_shoes'),
    path('bags/', views.WomensBags, name='womens_bags'),
    path('accessories/', views.WomensAccessories, name='womens_accessories'),
    path('beauty/', views.WomensBeauty, name='womens_beauty'),
    path('sale/', views.WomensSale, name='womens_sale'),
    path('shops/', views.WomensShops, name='womens_shops'),
    path('kendall/', views.KendallEdit, name='kendall_edit'),
    path('product/<slug:slug>/', views.Product_Detail, name='product_detail'),
    path('api/chatbot-search/', views.chatbot_search, name='chatbot_search'),

    # ---------- MEN ----------
    path('mens/', views.MensIndex, name='mens_home'),
    path('mens/new/', views.MensNew, name='mens_new'),
    path('mens/designers/', views.MensDesigners, name='mens_designers'),
    path('mens/clothing/', views.MensClothing, name='mens_clothing'),
    path('mens/shoes/', views.MensShoes, name='mens_shoes'),
    path('mens/bags/', views.MensBags, name='mens_bags'),
    path('mens/accessories/', views.MensAccessories, name='mens_accessories'),
    path('mens/sale/', views.MensSale, name='mens_sale'),
    path('mens/happening/', views.MensHappening, name='mens_happening'),
    path('mens/product/<slug:slug>/', views.Product_Detail_Men, name='product_detail_men'),

    # ---------- CART & WISHLIST ----------
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/add/<str:gender>/<int:product_id>/', views.wishlist_add, name='wishlist_add'),
    path('wishlist/remove/<str:gender>/<int:product_id>/', views.wishlist_remove, name='wishlist_remove'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<str:gender>/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<str:gender>/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),

    # ---------- CHECKOUT & ORDER ----------
    path('checkout/', views.checkout, name='checkout'),
    path('api/address-options/', views.address_options_api, name='address_options_api'),
    path('api/validate-postal-code/', views.validate_postal_code_api, name='validate_postal_code_api'),
    path('api/place-order/', views.place_order_api, name='place_order_api'),
    path('confirm/', TemplateView.as_view(template_name='order_confirm.html'), name='order_confirm'),

    path('order-history/', views.order_history, name='order_history'),
    path('order-history/<int:order_id>/rate/<int:item_id>/', views.rate_order_item, name='rate_order_item'),
    path('my-account/', views.my_account, name='my_account'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/payments/', views.vendor_payment_dashboard, name='vendor_payment_dashboard'),
    path('vendor/orders/', views.vendor_order_management_dashboard, name='vendor_order_management_dashboard'),
    path('delivery/dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/orders/<int:order_id>/payment/', views.delivery_collect_payment, name='delivery_collect_payment'),
    path('vendor/products/new/<str:catalog>/', views.vendor_product_create, name='vendor_product_create'),
    path('vendor/products/<str:catalog>/<int:product_id>/edit/', views.vendor_product_edit, name='vendor_product_edit'),
    path('vendor/products/<str:catalog>/<int:product_id>/delete/', views.vendor_product_delete, name='vendor_product_delete'),
    path('admin-control/', views.admin_control_center, name='admin_control_center'),
    path('admin-control/payments/', views.payment_management_dashboard, name='payment_management_dashboard'),
    path('admin-control/orders/manage/', views.admin_order_management_dashboard, name='admin_order_management_dashboard'),
    path('admin-control/orders/<int:order_id>/assign-delivery/', views.assign_delivery_partner, name='assign_delivery_partner'),
    path('admin-control/payments/<int:order_id>/update/', views.admin_update_payment_record, name='admin_update_payment_record'),
    path('order-items/<int:item_id>/update/', views.update_order_item_status, name='update_order_item_status'),
    path('admin-control/orders/<int:order_id>/delivered/', views.admin_mark_order_delivered, name='admin_mark_order_delivered'),
    path('admin-control/users/<int:user_id>/role/', views.admin_update_account_role, name='admin_update_account_role'),
    path('admin-control/reviews/<int:rating_id>/moderate/', views.admin_moderate_rating, name='admin_moderate_rating'),

    # ---------- INVOICE ----------
    path('invoice/<int:order_id>/', views.view_invoice, name='view_invoice'),

   

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

