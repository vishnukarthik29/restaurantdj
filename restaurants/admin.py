from django.contrib import admin
from django.db.models import Avg
from .models import CuisineType, Restaurant, RestaurantImage, RestaurantHours, Table, Review, RestaurantAnalytics


class RestaurantImageInline(admin.TabularInline):
    model = RestaurantImage
    extra = 1
    fields = ('image', 'image_url', 'caption', 'is_primary', 'order')


class RestaurantHoursInline(admin.TabularInline):
    model = RestaurantHours
    extra = 7
    fields = ('day_of_week', 'open_time', 'close_time', 'is_open')


class TableInline(admin.TabularInline):
    model = Table
    extra = 1
    fields = ('table_number', 'capacity', 'table_type', 'floor', 'section', 'is_active')


@admin.register(CuisineType)
class CuisineTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'is_active', 'order')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display   = ('name', 'city', 'status', 'is_featured', 'avg_rating', 'total_reviews', 'created_at')
    list_filter    = ('status', 'is_featured', 'price_range', 'city')
    search_fields  = ('name', 'slug', 'city', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('cuisine_types',)
    list_editable  = ('status', 'is_featured')
    date_hierarchy = 'created_at'
    ordering       = ('-created_at',)
    readonly_fields = ('avg_rating', 'total_reviews', 'created_at', 'updated_at')
    inlines = [RestaurantImageInline, RestaurantHoursInline, TableInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'owner', 'description', 'tagline', 'cuisine_types',
                       'price_range', 'status', 'is_featured', 'is_verified'),
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'pincode', 'neighborhood',
                       'latitude', 'longitude', 'google_maps_url'),
        }),
        ('Contact', {
            'fields': ('phone', 'whatsapp', 'email', 'website'),
        }),
        ('Operations', {
            'fields': ('opening_time', 'closing_time', 'is_open_24h',
                       'min_party_size', 'max_party_size',
                       'reservation_duration_minutes', 'max_advance_booking_days'),
        }),
        ('Features', {
            'fields': ('has_parking', 'has_wifi', 'has_outdoor_seating', 'has_private_dining',
                       'has_bar', 'has_valet', 'is_wheelchair_accessible', 'is_kid_friendly'),
        }),
        ('Images', {
            'fields': ('cover_image', 'cover_image_url'),
        }),
        ('Stats (auto-computed)', {
            'fields': ('avg_rating', 'total_reviews'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display  = ('restaurant', 'table_number', 'table_type', 'capacity', 'floor', 'section', 'is_active')
    list_filter   = ('restaurant', 'table_type', 'is_active')
    search_fields = ('restaurant__name', 'table_number')
    ordering      = ('restaurant', 'table_number')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display   = ('restaurant', 'customer', 'overall_rating', 'title', 'is_published', 'created_at')
    list_filter    = ('is_published', 'overall_rating')
    search_fields  = ('restaurant__name', 'customer__username', 'comment')
    list_editable  = ('is_published',)
    date_hierarchy = 'created_at'
    ordering       = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(RestaurantAnalytics)
class RestaurantAnalyticsAdmin(admin.ModelAdmin):
    list_display  = ('restaurant', 'date', 'total_reservations', 'completed_reservations', 'cancelled_reservations')
    list_filter   = ('restaurant',)
    date_hierarchy = 'date'
    ordering      = ('-date',)
