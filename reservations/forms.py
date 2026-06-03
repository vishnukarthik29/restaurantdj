from django import forms
from django.utils import timezone
from datetime import date, timedelta

from .models import Reservation


class ReservationForm(forms.Form):
    """Reservation booking form with full validation."""

    OCCASION_CHOICES = [
        ('', 'Select occasion (optional)'),
        ('birthday', '🎂 Birthday'),
        ('anniversary', '💕 Anniversary'),
        ('business', '💼 Business Dinner'),
        ('date', '🌹 Date Night'),
        ('family', '👨‍👩‍👧 Family Gathering'),
        ('celebration', '🥂 Celebration'),
        ('other', 'Other'),
    ]

    customer_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Your Full Name',
        })
    )
    customer_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '+91 XXXXX XXXXX',
            'type': 'tel',
        })
    )
    customer_whatsapp = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'WhatsApp number (if different)',
            'type': 'tel',
        })
    )
    customer_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'your@email.com',
        })
    )
    reservation_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-lg',
            'type': 'date',
        })
    )
    reservation_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control form-control-lg',
            'type': 'time',
        })
    )
    guest_count = forms.IntegerField(
        min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'min': 1,
            'max': 50,
        })
    )
    occasion = forms.ChoiceField(
        choices=OCCASION_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    special_requests = forms.CharField(
        required=False, max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special requests, dietary requirements, or accessibility needs...',
        })
    )

    def clean_reservation_date(self):
        res_date = self.cleaned_data['reservation_date']
        today = timezone.localdate()
        max_date = today + timedelta(days=60)

        if res_date < today:
            raise forms.ValidationError('Please select a future date.')
        if res_date > max_date:
            raise forms.ValidationError('Reservations can only be made up to 60 days in advance.')
        return res_date

    def clean_reservation_time(self):
        res_time = self.cleaned_data.get('reservation_time')
        if res_time:
            # Validate not too late or too early
            from datetime import time
            if res_time < time(10, 0):
                raise forms.ValidationError('Reservations are available from 10:00 AM.')
            if res_time > time(22, 30):
                raise forms.ValidationError('Last reservation time is 10:30 PM.')
        return res_time

    def clean(self):
        cleaned = super().clean()
        res_date = cleaned.get('reservation_date')
        res_time = cleaned.get('reservation_time')

        if res_date and res_time:
            from datetime import datetime
            now = timezone.localtime()
            slot_dt = timezone.make_aware(datetime.combine(res_date, res_time))
            if slot_dt <= now:
                raise forms.ValidationError('Please select a future date and time.')

        return cleaned
