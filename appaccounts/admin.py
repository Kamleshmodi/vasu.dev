from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account, VendorProfile


class VendorProfileInline(admin.StackedInline):
    model = VendorProfile
    can_delete = False
    extra = 0

class AccountAdmin(UserAdmin):
    ordering = ['-date_joined']
    list_display = ['email', 'username', 'account_type', 'date_joined', 'last_login', 'is_admin']
    list_filter = ['account_type', 'is_admin', 'is_staff', 'is_superuser']
    readonly_fields = ['date_joined', 'last_login']
    inlines = [VendorProfileInline]

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Account Role', {'fields': ('account_type',)}),
        ('Permissions', {'fields': ('is_admin', 'is_staff', 'is_active', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Groups and Permissions', {'fields': ('groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'account_type', 'password1', 'password2'),
        }),
    )

admin.site.register(Account, AccountAdmin)
admin.site.register(VendorProfile)
