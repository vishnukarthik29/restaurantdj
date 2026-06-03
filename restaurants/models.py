from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import os


class CuisineType(models.Model):
    """Cuisine categories for restaurants."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='🍽️')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'restaurants_cuisine_type'
        ordering = ['order', 'name']
        verbose_name = 'Cuisine Type'
        verbose_name_plural = 'Cuisine Types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Restaurant(models.Model):
    """Core restaurant model."""

    PRICE_BUDGET = 'budget'
    PRICE_MID = 'mid'
    PRICE_FINE = 'fine'
    PRICE_LUXURY = 'luxury'

    PRICE_CHOICES = [
        (PRICE_BUDGET, '₹ Budget'),
        (PRICE_MID, '₹ Mid-Range'),
        (PRICE_FINE, '₹ Fine Dining'),
        (PRICE_LUXURY, '₹ Luxury'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_PENDING = 'pending'
    STATUS_SUSPENDED = 'suspended'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_SUSPENDED, 'Suspended'),
    ]

    # Basic info
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='owned_restaurants'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    tagline = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    cuisine_types = models.ManyToManyField(CuisineType, blank=True)
    price_range = models.CharField(max_length=10, choices=PRICE_CHOICES, default=PRICE_MID)

    # Location
    address = models.TextField()
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    google_maps_url = models.URLField(blank=True)
    neighborhood = models.CharField(max_length=200, blank=True)

    # Contact
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Operations
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_open_24h = models.BooleanField(default=False)
    reservation_required = models.BooleanField(default=True)
    accepts_walkins = models.BooleanField(default=True)
    min_advance_booking_hours = models.IntegerField(default=1)
    max_advance_booking_days = models.IntegerField(default=60)
    max_party_size = models.IntegerField(default=20)
    min_party_size = models.IntegerField(default=1)
    reservation_duration_minutes = models.IntegerField(default=90)

    # Ratings (auto-computed)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.IntegerField(default=0)
    food_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    service_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    ambiance_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    # Features
    has_parking = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    has_outdoor_seating = models.BooleanField(default=False)
    has_private_dining = models.BooleanField(default=False)
    has_bar = models.BooleanField(default=False)
    has_valet = models.BooleanField(default=False)
    is_wheelchair_accessible = models.BooleanField(default=False)
    is_kid_friendly = models.BooleanField(default=False)
    accepts_large_groups = models.BooleanField(default=False)

    # Dress code and ambiance
    DRESS_CASUAL = 'casual'
    DRESS_SMART = 'smart'
    DRESS_FORMAL = 'formal'
    DRESS_CHOICES = [
        (DRESS_CASUAL, 'Casual'),
        (DRESS_SMART, 'Smart Casual'),
        (DRESS_FORMAL, 'Formal'),
    ]
    dress_code = models.CharField(max_length=10, choices=DRESS_CHOICES, default=DRESS_CASUAL)

    # Status
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # SEO / metadata
    meta_description = models.TextField(blank=True, max_length=300)

    # Cover image (primary photo)
    cover_image = models.ImageField(upload_to='restaurant_images/', blank=True, null=True)
    cover_image_url = models.URLField(blank=True,
        default='https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'restaurants_restaurant'
        ordering = ['-is_featured', '-avg_rating', 'name']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['avg_rating']),
        ]
        verbose_name = 'Restaurant'
        verbose_name_plural = 'Restaurants'

    def __str__(self):
        return f"{self.name} - {self.city}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if img and img.image:
            return img.image.url
        if img and img.image_url:
            return img.image_url
        return self.cover_image_url or 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800'

    @property
    def price_symbol(self):
        return {'budget': '₹', 'mid': '₹', 'fine': '₹', 'luxury': '₹'}.get(self.price_range, '₹')

    @property
    def is_currently_open(self):
        from django.utils import timezone
        now = timezone.localtime().time()
        if self.is_open_24h:
            return True
        return self.opening_time <= now <= self.closing_time

    @property
    def total_tables(self):
        return self.tables.filter(is_active=True).count()

    @property
    def total_capacity(self):
        return sum(t.capacity for t in self.tables.filter(is_active=True))

    @property
    def star_display(self):
        """Returns integer star count for display."""
        return round(float(self.avg_rating))

    def get_available_tables(self, date, time, guest_count):
        """Get available tables for given date/time/guests."""
        from reservations.models import Reservation
        from datetime import datetime, timedelta

        # Find conflicting reservations
        duration = self.reservation_duration_minutes
        check_start = datetime.combine(date, time) - timedelta(minutes=duration)
        check_end = datetime.combine(date, time) + timedelta(minutes=duration)

        reserved_ids = Reservation.objects.filter(
            restaurant=self,
            reservation_date=date,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            reservation_time__gte=check_start.time(),
            reservation_time__lte=check_end.time(),
        ).values_list('table_id', flat=True)

        return self.tables.filter(
            is_active=True,
            capacity__gte=guest_count
        ).exclude(id__in=reserved_ids)


class RestaurantImage(models.Model):
    """Multiple images for a restaurant."""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='restaurant_images/', blank=True, null=True)
    image_url = models.URLField(blank=True)
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restaurants_image'
        ordering = ['-is_primary', 'order']

    def __str__(self):
        return f"Image for {self.restaurant.name}"

    @property
    def url(self):
        if self.image:
            return self.image.url
        return self.image_url or 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800'


class RestaurantHours(models.Model):
    """Operating hours per day of week."""
    DAYS = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='hours')
    day_of_week = models.IntegerField(choices=DAYS)
    is_open = models.BooleanField(default=True)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_special = models.BooleanField(default=False)
    special_note = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'restaurants_hours'
        unique_together = ['restaurant', 'day_of_week']
        ordering = ['day_of_week']

    def __str__(self):
        return f"{self.restaurant.name} - {self.get_day_of_week_display()}"


class Table(models.Model):
    """Individual table configuration."""

    TYPE_STANDARD = 'standard'
    TYPE_BOOTH = 'booth'
    TYPE_WINDOW = 'window'
    TYPE_PRIVATE = 'private'
    TYPE_OUTDOOR = 'outdoor'
    TYPE_BAR = 'bar'
    TYPE_HIGH_TOP = 'high_top'
    TYPE_ROUND = 'round'

    TABLE_TYPES = [
        (TYPE_STANDARD, 'Standard Table'),
        (TYPE_BOOTH, 'Booth'),
        (TYPE_WINDOW, 'Window Table'),
        (TYPE_PRIVATE, 'Private Dining Room'),
        (TYPE_OUTDOOR, 'Outdoor Table'),
        (TYPE_BAR, 'Bar Seating'),
        (TYPE_HIGH_TOP, 'High-Top Table'),
        (TYPE_ROUND, 'Round Table'),
    ]

    TYPE_ICONS = {
        TYPE_STANDARD: '🪑',
        TYPE_BOOTH: '🛋️',
        TYPE_WINDOW: '🪟',
        TYPE_PRIVATE: '🚪',
        TYPE_OUTDOOR: '🌿',
        TYPE_BAR: '🍸',
        TYPE_HIGH_TOP: '🪑',
        TYPE_ROUND: '⭕',
    }

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=20)
    capacity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)])
    min_capacity = models.IntegerField(default=1)
    table_type = models.CharField(max_length=20, choices=TABLE_TYPES, default=TYPE_STANDARD)

    # Features
    has_window_view = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    is_outdoor = models.BooleanField(default=False)
    is_accessible = models.BooleanField(default=False)
    has_power_outlet = models.BooleanField(default=False)
    is_round = models.BooleanField(default=False)

    # Location in restaurant
    floor = models.IntegerField(default=1)
    section = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    # Floor plan position (for visual map)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'restaurants_table'
        unique_together = ['restaurant', 'table_number']
        ordering = ['restaurant', 'table_number']
        indexes = [
            models.Index(fields=['restaurant', 'is_active']),
            models.Index(fields=['capacity']),
        ]

    def __str__(self):
        return f"Table {self.table_number} ({self.capacity} seats) - {self.restaurant.name}"

    @property
    def type_icon(self):
        return self.TYPE_ICONS.get(self.table_type, '🪑')

    @property
    def display_features(self):
        features = []
        if self.has_window_view:
            features.append('Window View')
        if self.is_private:
            features.append('Private')
        if self.is_outdoor:
            features.append('Outdoor')
        if self.is_accessible:
            features.append('Accessible')
        return features

    def is_available(self, date, time):
        """Check if this table is available at given date/time."""
        from reservations.models import Reservation
        from datetime import datetime, timedelta

        duration = self.restaurant.reservation_duration_minutes
        check_start = datetime.combine(date, time) - timedelta(minutes=duration)
        check_end = datetime.combine(date, time) + timedelta(minutes=duration)

        conflict = Reservation.objects.filter(
            table=self,
            reservation_date=date,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            reservation_time__gte=check_start.time(),
            reservation_time__lte=check_end.time(),
        ).exists()
        return not conflict


class Review(models.Model):
    """Customer reviews and ratings."""
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='review'
    )

    # Ratings
    overall_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    food_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    service_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    ambiance_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    value_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)

    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField(max_length=2000)
    is_verified = models.BooleanField(default=False)  # Verified reservation
    is_published = models.BooleanField(default=True)
    admin_reply = models.TextField(blank=True)
    admin_reply_at = models.DateTimeField(null=True, blank=True)

    helpful_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'restaurants_review'
        ordering = ['-created_at']
        unique_together = ['customer', 'restaurant', 'reservation']
        indexes = [
            models.Index(fields=['restaurant', 'is_published']),
            models.Index(fields=['overall_rating']),
        ]

    def __str__(self):
        return f"Review by {self.customer.full_name} for {self.restaurant.name} ({self.overall_rating}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update restaurant ratings
        self._update_restaurant_ratings()

    def _update_restaurant_ratings(self):
        from django.db.models import Avg
        reviews = Review.objects.filter(restaurant=self.restaurant, is_published=True)
        agg = reviews.aggregate(
            avg=Avg('overall_rating'),
            food=Avg('food_rating'),
            service=Avg('service_rating'),
            ambiance=Avg('ambiance_rating'),
        )
        Restaurant.objects.filter(pk=self.restaurant.pk).update(
            avg_rating=round(agg['avg'] or 0, 2),
            total_reviews=reviews.count(),
            food_rating=round(agg['food'] or 0, 2),
            service_rating=round(agg['service'] or 0, 2),
            ambiance_rating=round(agg['ambiance'] or 0, 2),
        )

    @property
    def star_range(self):
        return range(1, 6)


class RestaurantAnalytics(models.Model):
    """Daily analytics per restaurant."""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()
    total_reservations = models.IntegerField(default=0)
    confirmed_reservations = models.IntegerField(default=0)
    cancelled_reservations = models.IntegerField(default=0)
    no_shows = models.IntegerField(default=0)
    completed_reservations = models.IntegerField(default=0)
    total_guests = models.IntegerField(default=0)
    avg_party_size = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    peak_hour = models.TimeField(null=True, blank=True)
    revenue_estimate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'restaurants_analytics'
        unique_together = ['restaurant', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"Analytics: {self.restaurant.name} on {self.date}"
