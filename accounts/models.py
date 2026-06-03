from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Extended User model with role-based access control."""

    ROLE_CUSTOMER = 'customer'
    ROLE_ADMIN = 'admin'
    ROLE_RESTAURANT_OWNER = 'owner'
    ROLE_STAFF = 'staff'

    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_ADMIN, 'Administrator'),
        (ROLE_RESTAURANT_OWNER, 'Restaurant Owner'),
        (ROLE_STAFF, 'Staff'),
    ]

    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    avatar = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    @property
    def is_customer(self):
        return self.role == self.ROLE_CUSTOMER

    @property
    def is_restaurant_owner(self):
        return self.role == self.ROLE_RESTAURANT_OWNER

    @property
    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN or self.is_staff

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return f"https://ui-avatars.com/api/?name={self.full_name}&background=C9922A&color=fff&size=200"


class CustomerProfile(models.Model):
    """Extended profile for customer users."""

    DIETARY_CHOICES = [
        ('none', 'No Restrictions'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('halal', 'Halal'),
        ('kosher', 'Kosher'),
        ('gluten_free', 'Gluten Free'),
        ('dairy_free', 'Dairy Free'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customerprofile')
    whatsapp_number = models.CharField(max_length=20, blank=True)
    dietary_preference = models.CharField(max_length=30, choices=DIETARY_CHOICES, default='none')
    cuisine_preferences = models.ManyToManyField('restaurants.CuisineType', blank=True)
    favorite_restaurants = models.ManyToManyField('restaurants.Restaurant', blank=True, related_name='favorited_by')

    # Seating preferences
    prefers_window_seat = models.BooleanField(default=False)
    prefers_private_dining = models.BooleanField(default=False)
    prefers_outdoor = models.BooleanField(default=False)
    requires_accessibility = models.BooleanField(default=False)
    prefers_quiet_section = models.BooleanField(default=False)

    # Notification preferences
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    notify_whatsapp = models.BooleanField(default=True)

    # Stats (updated via signals)
    total_reservations = models.IntegerField(default=0)
    total_cancellations = models.IntegerField(default=0)
    total_completed = models.IntegerField(default=0)
    loyalty_points = models.IntegerField(default=0)

    bio = models.TextField(blank=True, max_length=500)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_customer_profile'
        verbose_name = 'Customer Profile'

    def __str__(self):
        return f"Profile: {self.user.full_name}"

    @property
    def preference_flags(self):
        """Returns dict of all seating preferences."""
        return {
            'window_seat': self.prefers_window_seat,
            'private': self.prefers_private_dining,
            'outdoor': self.prefers_outdoor,
            'accessible': self.requires_accessibility,
            'quiet': self.prefers_quiet_section,
        }


class Notification(models.Model):
    """User notification system."""

    TYPE_BOOKING_CONFIRMED = 'booking_confirmed'
    TYPE_BOOKING_CANCELLED = 'booking_cancelled'
    TYPE_BOOKING_REMINDER = 'booking_reminder'
    TYPE_BOOKING_MODIFIED = 'booking_modified'
    TYPE_REVIEW_REQUEST = 'review_request'
    TYPE_PROMO = 'promotion'
    TYPE_SYSTEM = 'system'

    TYPE_CHOICES = [
        (TYPE_BOOKING_CONFIRMED, 'Booking Confirmed'),
        (TYPE_BOOKING_CANCELLED, 'Booking Cancelled'),
        (TYPE_BOOKING_REMINDER, 'Booking Reminder'),
        (TYPE_BOOKING_MODIFIED, 'Booking Modified'),
        (TYPE_REVIEW_REQUEST, 'Review Request'),
        (TYPE_PROMO, 'Promotion'),
        (TYPE_SYSTEM, 'System'),
    ]

    ICON_MAP = {
        TYPE_BOOKING_CONFIRMED: 'bi-check-circle-fill',
        TYPE_BOOKING_CANCELLED: 'bi-x-circle-fill',
        TYPE_BOOKING_REMINDER: 'bi-clock-fill',
        TYPE_BOOKING_MODIFIED: 'bi-pencil-fill',
        TYPE_REVIEW_REQUEST: 'bi-star-fill',
        TYPE_PROMO: 'bi-gift-fill',
        TYPE_SYSTEM: 'bi-info-circle-fill',
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} -> {self.user.email}"

    @property
    def icon(self):
        return self.ICON_MAP.get(self.notification_type, 'bi-bell-fill')

    def mark_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
