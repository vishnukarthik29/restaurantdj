from django.contrib import admin
from .models import Reservation, ReservationStatusHistory, AIRecommendation, WaitlistEntry


class ReservationStatusHistoryInline(admin.TabularInline):
    model = ReservationStatusHistory
    extra = 0
    readonly_fields = ('status', 'changed_by', 'changed_at', 'notes')
    can_delete = False


class AIRecommendationInline(admin.StackedInline):
    model = AIRecommendation
    extra = 0
    readonly_fields = (
        'recommended_table',
        'overall_score', 'capacity_score', 'preference_score',
        'utilization_score', 'historical_score',
        'algorithm_version', 'processing_time_ms', 'created_at',
    )
    can_delete = False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display   = ('reservation_id', 'customer_name', 'restaurant', 'reservation_date',
                      'reservation_time', 'guest_count', 'status', 'created_at')
    list_filter    = ('status', 'restaurant', 'reservation_date')
    search_fields  = ('reservation_id', 'customer_name', 'customer_email', 'customer_phone')
    date_hierarchy = 'reservation_date'
    ordering       = ('-created_at',)
    readonly_fields = ('reservation_id', 'created_at', 'updated_at')
    inlines        = [ReservationStatusHistoryInline, AIRecommendationInline]
    list_editable  = ('status',)

    fieldsets = (
        ('Reservation', {
            'fields': ('reservation_id', 'restaurant', 'table', 'status'),
        }),
        ('Timing', {
            'fields': ('reservation_date', 'reservation_time', 'guest_count'),
        }),
        ('Customer', {
            'fields': ('customer', 'customer_name', 'customer_email', 'customer_phone', 'customer_whatsapp'),
        }),
        ('Requests & Notes', {
            'fields': ('special_requests', 'admin_notes'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if change:
            old = Reservation.objects.get(pk=obj.pk)
            if old.status != obj.status:
                ReservationStatusHistory.objects.create(
                    reservation=obj,
                    status=obj.status,
                    changed_by=request.user,
                    notes=f'Changed via admin by {request.user.username}',
                )
        super().save_model(request, obj, form, change)


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display   = ('reservation', 'recommended_table', 'overall_score', 'get_confidence', 'created_at')
    list_filter    = ('algorithm_version',)
    readonly_fields = ('created_at',)
    ordering       = ('-created_at',)

    def get_confidence(self, obj):
        return obj.confidence_label
    get_confidence.short_description = 'Confidence'


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display  = ('customer', 'restaurant', 'requested_date', 'requested_time',
                     'guest_count', 'is_notified', 'created_at')
    list_filter   = ('restaurant', 'is_notified')
    search_fields = ('customer__username', 'customer__email')
    ordering      = ('-created_at',)
