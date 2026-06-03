from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, CustomerProfile, Notification


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    fk_name = 'user'
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (CustomerProfileInline,)
    list_display  = ('username', 'email', 'get_full_name', 'role', 'is_active', 'date_joined')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('TableMaster', {
            'fields': ('role', 'phone', 'avatar', 'is_email_verified'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('TableMaster', {
            'fields': ('role', 'email', 'phone'),
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name() or '—'
    get_full_name.short_description = 'Name'


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display   = ('user', 'dietary_preference', 'loyalty_points')
    list_filter    = ('dietary_preference',)
    search_fields  = ('user__username', 'user__email')
    raw_id_fields  = ('user',)
    filter_horizontal = ('cuisine_preferences', 'favorite_restaurants')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter   = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
