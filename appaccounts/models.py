from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class MyAccountManager(BaseUserManager):
    def create_user(self, email, username, password=None, account_type='customer', **extra_fields):
        if not email:
            raise ValueError("User must have an email address")
        if not username:
            raise ValueError("User must have a username")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, account_type=account_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        user = self.create_user(
            email=email,
            username=username,
            password=password,
            account_type=Account.AccountType.ADMIN,
            email_verified=True,
            **extra_fields,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, email):
        return self.get(email=email)

class Account(AbstractBaseUser, PermissionsMixin):
    class AccountType(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        VENDOR = 'vendor', 'Vendor'
        DELIVERY_PARTNER = 'delivery_partner', 'Delivery Partner'
        ADMIN = 'admin', 'Admin'

    email = models.EmailField(verbose_name="Email", max_length=60, unique=True)
    username = models.CharField(max_length=30, unique=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.CUSTOMER)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    email_verified = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = MyAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        if hasattr(self, 'vendor_profile') and self.vendor_profile.business_name:
            return self.vendor_profile.business_name
        return self.username or self.email.split('@')[0]

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.username

    @property
    def is_vendor_account(self):
        return self.account_type == self.AccountType.VENDOR

    @property
    def is_delivery_partner_account(self):
        return self.account_type == self.AccountType.DELIVERY_PARTNER

    @property
    def has_admin_access(self):
        return self.is_superuser or self.account_type == self.AccountType.ADMIN

    @property
    def dashboard_url_name(self):
        if self.has_admin_access:
            return 'admin_control_center'
        if self.is_vendor_account:
            return 'vendor_dashboard'
        if self.is_delivery_partner_account:
            return 'delivery_dashboard'
        return 'my_account'


class VendorProfile(models.Model):
    user = models.OneToOneField(Account, related_name='vendor_profile', on_delete=models.CASCADE)
    business_name = models.CharField(max_length=120)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.business_name
