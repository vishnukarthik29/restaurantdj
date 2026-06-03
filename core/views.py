from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg, Count
from restaurants.models import Restaurant, CuisineType


def home(request):
    """Homepage with hero, search, featured restaurants, testimonials."""
    # Featured restaurants
    featured = Restaurant.objects.filter(
        status=Restaurant.STATUS_ACTIVE,
        is_featured=True
    ).prefetch_related('cuisine_types', 'images')[:6]

    # If not enough featured, fill with top-rated
    if featured.count() < 6:
        featured = Restaurant.objects.filter(
            status=Restaurant.STATUS_ACTIVE
        ).prefetch_related('cuisine_types', 'images').order_by('-avg_rating')[:6]

    # Popular cuisine types
    cuisine_types = CuisineType.objects.filter(is_active=True).annotate(
        restaurant_count=Count('restaurant')
    ).filter(restaurant_count__gt=0).order_by('order', '-restaurant_count')[:8]

    # Top cities
    cities = Restaurant.objects.filter(
        status=Restaurant.STATUS_ACTIVE
    ).values('city').annotate(
        count=Count('id')
    ).order_by('-count')[:8]

    # Stats
    stats = {
        'restaurants': Restaurant.objects.filter(status=Restaurant.STATUS_ACTIVE).count(),
        'cities': Restaurant.objects.filter(status=Restaurant.STATUS_ACTIVE).values('city').distinct().count(),
        'reservations': 0,
        'happy_customers': 0,
    }
    try:
        from reservations.models import Reservation
        stats['reservations'] = Reservation.objects.filter(status=Reservation.STATUS_COMPLETED).count()
        from accounts.models import User
        stats['happy_customers'] = User.objects.filter(role=User.ROLE_CUSTOMER).count()
    except Exception:
        pass

    # Testimonials (hardcoded for demo - in production from DB)
    testimonials = [
        {
            'name': 'Priya Sharma',
            'city': 'Mumbai',
            'avatar': 'https://randomuser.me/api/portraits/women/44.jpg',
            'rating': 5,
            'text': "TableMaster's AI recommended the perfect window table for our anniversary dinner. The entire experience was magical. I couldn't have planned it better myself!",
            'date': 'November 2024',
        },
        {
            'name': 'Rahul Mehta',
            'city': 'Bangalore',
            'avatar': 'https://randomuser.me/api/portraits/men/32.jpg',
            'rating': 5,
            'text': 'Booking for my team of 12 was effortless. The AI found us a private dining room that perfectly fit our group. The booking process took under 2 minutes.',
            'date': 'December 2024',
        },
        {
            'name': 'Ananya Krishnan',
            'city': 'Chennai',
            'avatar': 'https://randomuser.me/api/portraits/women/68.jpg',
            'rating': 5,
            'text': 'I loved how the system remembered my preference for outdoor seating. Every recommendation felt personal. This is the future of restaurant reservations.',
            'date': 'January 2025',
        },
    ]

    return render(request, 'home.html', {
        'featured_restaurants': featured,
        'cuisine_types': cuisine_types,
        'cities': cities,
        'stats': stats,
        'testimonials': testimonials,
    })


def about(request):
    """About page."""
    return render(request, 'about.html')


def contact(request):
    """Contact page with form handling."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if all([name, email, message]):
            # In production: send email via Django mail
            messages.success(request, "Thank you! We'll get back to you within 24 hours.")
        else:
            messages.error(request, 'Please fill in all required fields.')

    return render(request, 'contact.html')
