from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import string
import random


def generate_reservation_id():
    """Generate unique reservation ID like TM-2024-XXXX."""
    year = timezone.now().year
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f"TM-{year}-{suffix}"


class Reservation(models.Model):
    """Core reservation model with full booking lifecycle."""

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_NO_SHOW = 'no_show'
    STATUS_MODIFIED = 'modified'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Confirmation'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_NO_SHOW, 'No Show'),
        (STATUS_MODIFIED, 'Modified'),
    ]

    STATUS_COLORS = {
        STATUS_PENDING: 'warning',
        STATUS_CONFIRMED: 'success',
        STATUS_CANCELLED: 'danger',
        STATUS_COMPLETED: 'info',
        STATUS_NO_SHOW: 'secondary',
        STATUS_MODIFIED: 'primary',
    }

    SOURCE_WEB = 'web'
    SOURCE_MOBILE = 'mobile'
    SOURCE_PHONE = 'phone'
    SOURCE_ADMIN = 'admin'

    SOURCE_CHOICES = [
        (SOURCE_WEB, 'Web'),
        (SOURCE_MOBILE, 'Mobile App'),
        (SOURCE_PHONE, 'Phone'),
        (SOURCE_ADMIN, 'Admin Panel'),
    ]

    # Unique identifier
    reservation_id = models.CharField(
        max_length=20, unique=True,
        default=generate_reservation_id,
        editable=False
    )

    # Relations
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    table = models.ForeignKey(
        'restaurants.Table',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reservations'
    )

    # Guest info (denormalized for history integrity)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_whatsapp = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField()

    # Booking details
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    guest_count = models.IntegerField(validators=[MinValueValidator(1)])
    special_requests = models.TextField(blank=True, max_length=1000)
    occasion = models.CharField(max_length=200, blank=True)

    # Status
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_WEB)

    # Admin notes
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    # Confirmation
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='confirmed_reservations'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # AI fields
    ai_table_assigned = models.BooleanField(default=False)
    ai_confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    # Notification flags
    confirmation_sent = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reservations_reservation'
        ordering = ['-reservation_date', '-reservation_time']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['restaurant', 'reservation_date', 'status']),
            models.Index(fields=['reservation_id']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Reservation'
        verbose_name_plural = 'Reservations'

    def __str__(self):
        return f"[{self.reservation_id}] {self.customer_name} at {self.restaurant.name} on {self.reservation_date}"

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'secondary')

    @property
    def is_upcoming(self):
        from datetime import datetime
        now = timezone.localtime()
        reservation_dt = timezone.make_aware(
            datetime.combine(self.reservation_date, self.reservation_time)
        )
        return reservation_dt > now and self.status in [self.STATUS_PENDING, self.STATUS_CONFIRMED]

    @property
    def can_cancel(self):
        """Check if reservation can be cancelled (respecting business rules)."""
        if self.status not in [self.STATUS_PENDING, self.STATUS_CONFIRMED]:
            return False
        from datetime import datetime, timedelta
        now = timezone.localtime()
        reservation_dt = timezone.make_aware(
            datetime.combine(self.reservation_date, self.reservation_time)
        )
        cancel_window = getattr(settings, 'TABLEMASTER', {}).get('CANCELLATION_HOURS', 2)
        return (reservation_dt - now).total_seconds() > cancel_window * 3600

    @property
    def can_modify(self):
        return self.status in [self.STATUS_PENDING, self.STATUS_CONFIRMED] and self.is_upcoming

    def confirm(self, by_user=None):
        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = timezone.now()
        self.confirmed_by = by_user
        self.save(update_fields=['status', 'confirmed_at', 'confirmed_by'])
        self._create_status_history(self.STATUS_CONFIRMED, by_user)
        self._send_confirmation_notification()

    def cancel(self, reason='', by_user=None):
        self.status = self.STATUS_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancellation_reason'])
        self._create_status_history(self.STATUS_CANCELLED, by_user, reason)

    def complete(self):
        self.status = self.STATUS_COMPLETED
        self.save(update_fields=['status'])
        self._create_status_history(self.STATUS_COMPLETED)
        # Update customer stats
        try:
            profile = self.customer.customerprofile
            profile.total_completed += 1
            profile.loyalty_points += 10
            profile.save(update_fields=['total_completed', 'loyalty_points'])
        except Exception:
            pass

    def _create_status_history(self, status, by_user=None, notes=''):
        ReservationStatusHistory.objects.create(
            reservation=self,
            status=status,
            changed_by=by_user or self.customer,
            notes=notes
        )

    def _send_confirmation_notification(self):
        from accounts.models import Notification
        Notification.objects.create(
            user=self.customer,
            notification_type=Notification.TYPE_BOOKING_CONFIRMED,
            title='Reservation Confirmed! 🎉',
            message=f'Your reservation at {self.restaurant.name} on {self.reservation_date.strftime("%B %d, %Y")} at {self.reservation_time.strftime("%I:%M %p")} has been confirmed.',
            link=f'/reservations/{self.reservation_id}/'
        )


class ReservationStatusHistory(models.Model):
    """Audit trail for reservation status changes."""
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=15, choices=Reservation.STATUS_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='reservation_status_changes'
    )
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reservations_status_history'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.reservation.reservation_id} -> {self.status} at {self.changed_at}"


class AIRecommendation(models.Model):
    """Detailed AI recommendation record for each reservation."""
    reservation = models.OneToOneField(
        Reservation, on_delete=models.CASCADE,
        related_name='ai_recommendation'
    )
    recommended_table = models.ForeignKey(
        'restaurants.Table', on_delete=models.SET_NULL, null=True,
        related_name='ai_recommendations'
    )

    # Scores (0-100 scale)
    overall_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    capacity_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    preference_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    utilization_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    historical_score = models.DecimalField(max_digits=6, decimal_places=4, default=0)

    # Reasoning details (JSON)
    reasoning = models.JSONField(default=dict)
    alternatives_data = models.JSONField(default=list)
    alternative_slots = models.JSONField(default=list)

    # Algorithm info
    algorithm_version = models.CharField(max_length=20, default='v2.0')
    processing_time_ms = models.IntegerField(default=0)
    was_overridden = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reservations_ai_recommendation'
        verbose_name = 'AI Recommendation'

    def __str__(self):
        return f"AI Rec for {self.reservation.reservation_id}"

    @property
    def confidence_label(self):
        score = float(self.overall_score)
        if score >= 80:
            return ('Excellent Match', 'success')
        elif score >= 60:
            return ('Good Match', 'info')
        elif score >= 40:
            return ('Fair Match', 'warning')
        else:
            return ('Low Confidence', 'danger')

    @property
    def confidence_percent(self):
        return round(float(self.overall_score))


class WaitlistEntry(models.Model):
    """Waitlist when no tables available."""
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='waitlist')
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, related_name='waitlist')
    requested_date = models.DateField()
    requested_time = models.TimeField()
    guest_count = models.IntegerField()
    notes = models.TextField(blank=True)
    is_notified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'reservations_waitlist'
        ordering = ['created_at']

    def __str__(self):
        return f"Waitlist: {self.customer.email} at {self.restaurant.name}"
