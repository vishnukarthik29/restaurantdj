from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Restaurant, CuisineType, Table, Review


class RestaurantListView(ListView):
    model = Restaurant
    template_name = 'restaurants/list.html'
    context_object_name = 'restaurants'
    paginate_by = 12

    def get_queryset(self):
        qs = Restaurant.objects.filter(
            status=Restaurant.STATUS_ACTIVE
        ).prefetch_related('cuisine_types', 'images')

        p = self.request.GET
        q = p.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(description__icontains=q) |
                Q(cuisine_types__name__icontains=q) | Q(city__icontains=q) |
                Q(neighborhood__icontains=q) | Q(tagline__icontains=q)
            ).distinct()

        city = p.get('city', '').strip()
        if city:
            qs = qs.filter(city__icontains=city)

        cuisine = p.get('cuisine', '').strip()
        if cuisine:
            qs = qs.filter(cuisine_types__slug=cuisine).distinct()

        try:
            min_rating = float(p.get('rating', '') or '0')
            if min_rating:
                qs = qs.filter(avg_rating__gte=min_rating)
        except ValueError:
            pass

        price = p.get('price', '').strip()
        if price:
            qs = qs.filter(price_range=price)

        if p.get('has_parking'):
            qs = qs.filter(has_parking=True)
        if p.get('has_wifi'):
            qs = qs.filter(has_wifi=True)
        if p.get('has_outdoor'):
            qs = qs.filter(has_outdoor_seating=True)
        if p.get('has_private'):
            qs = qs.filter(has_private_dining=True)
        if p.get('accessible'):
            qs = qs.filter(is_wheelchair_accessible=True)

        sort = p.get('sort', '-is_featured')
        sort_map = {
            '-rating':     ['-avg_rating'],
            'name':        ['name'],
            '-created_at': ['-created_at'],
            'price_range': ['price_range'],
            '-is_featured':['-is_featured', '-avg_rating'],
        }
        return qs.order_by(*sort_map.get(sort, ['-is_featured', '-avg_rating']))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cuisine_types'] = CuisineType.objects.filter(is_active=True)
        ctx['total_count'] = self.get_queryset().count()
        ctx['price_choices'] = Restaurant.PRICE_CHOICES
        ctx['features_list'] = [
            ('has_parking',  '🅿 Parking'),
            ('has_wifi',     '📶 WiFi'),
            ('has_outdoor',  '🌿 Outdoor Seating'),
            ('has_private',  '🚪 Private Dining'),
            ('accessible',   '♿ Wheelchair Accessible'),
        ]
        return ctx


class RestaurantDetailView(DetailView):
    model = Restaurant
    template_name = 'restaurants/detail.html'
    context_object_name = 'restaurant'

    def get_queryset(self):
        return Restaurant.objects.filter(status=Restaurant.STATUS_ACTIVE)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        restaurant = self.object

        ctx['all_images'] = restaurant.images.all()[:10]
        ctx['primary_image'] = restaurant.primary_image   # URL string

        ctx['tables'] = restaurant.tables.filter(is_active=True).order_by('table_number')
        ctx['reviews'] = restaurant.reviews.filter(is_published=True).select_related('customer')[:10]
        ctx['rating_breakdown'] = self._rating_breakdown(restaurant)
        ctx['operating_hours'] = restaurant.hours.all()
        ctx['time_slots'] = self._build_time_slots(restaurant)

        if self.request.user.is_authenticated:
            try:
                ctx['is_favourite'] = self.request.user.customerprofile.favorite_restaurants.filter(
                    pk=restaurant.pk).exists()
            except Exception:
                ctx['is_favourite'] = False

        return ctx

    def _rating_breakdown(self, restaurant):
        """Return list of (label, avg_score) tuples for the four sub-ratings."""
        reviews = restaurant.reviews.filter(is_published=True)
        if not reviews.exists():
            return []
        agg = reviews.aggregate(
            food=Avg('food_rating'),
            service=Avg('service_rating'),
            ambiance=Avg('ambiance_rating'),
            overall=Avg('overall_rating'),
        )
        results = []
        for label, key in [('Overall', 'overall'), ('Food', 'food'),
                            ('Service', 'service'), ('Ambiance', 'ambiance')]:
            val = agg.get(key)
            if val is not None:
                results.append((label, round(float(val), 1)))
        return results

    def _build_time_slots(self, restaurant):
        from datetime import time
        slots = []
        try:
            for h in range(restaurant.opening_time.hour, restaurant.closing_time.hour + 1):
                for m in (0, 30):
                    t = time(h, m)
                    if t >= restaurant.opening_time and t <= restaurant.closing_time:
                        slots.append(t.strftime('%H:%M'))
        except Exception:
            for h in range(11, 23):
                for m in (0, 30):
                    slots.append(f'{h:02d}:{m:02d}')
        return slots


@require_GET
def check_availability(request):
    slug      = request.GET.get('slug', '')
    date_str  = request.GET.get('date', '')
    time_str  = request.GET.get('time', '')
    guests    = request.GET.get('guests', 2)
    try:
        from datetime import date as dt_date, time as dt_time
        restaurant = Restaurant.objects.get(slug=slug, status=Restaurant.STATUS_ACTIVE)
        available  = restaurant.get_available_tables(
            dt_date.fromisoformat(date_str),
            dt_time.fromisoformat(time_str),
            int(guests),
        )
        return JsonResponse({'available': available.exists(), 'available_count': available.count()})
    except Exception as e:
        return JsonResponse({'available': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def toggle_favourite(request, slug):
    restaurant = get_object_or_404(Restaurant, slug=slug, status=Restaurant.STATUS_ACTIVE)
    try:
        profile = request.user.customerprofile
    except Exception:
        from accounts.models import CustomerProfile
        profile = CustomerProfile.objects.create(user=request.user)

    if profile.favorite_restaurants.filter(pk=restaurant.pk).exists():
        profile.favorite_restaurants.remove(restaurant)
        return JsonResponse({'favourited': False})
    else:
        profile.favorite_restaurants.add(restaurant)
        return JsonResponse({'favourited': True})


@require_GET
def get_time_slots(request):
    slug     = request.GET.get('slug', '')
    date_str = request.GET.get('date', '')
    guests   = int(request.GET.get('guests', 2))
    try:
        from datetime import date as dt_date, datetime, timedelta
        restaurant = Restaurant.objects.get(slug=slug)
        res_date   = dt_date.fromisoformat(date_str)
        slots = []
        t = datetime(res_date.year, res_date.month, res_date.day,
                     restaurant.opening_time.hour, restaurant.opening_time.minute)
        end = datetime(res_date.year, res_date.month, res_date.day,
                       restaurant.closing_time.hour, restaurant.closing_time.minute)
        while t <= end:
            avail = restaurant.get_available_tables(res_date, t.time(), guests)
            slots.append({
                'time': t.strftime('%H:%M'),
                'display': t.strftime('%I:%M %p'),
                'available': avail.exists(),
                'count': avail.count(),
            })
            t += timedelta(minutes=30)
        return JsonResponse({'slots': slots})
    except Exception as e:
        return JsonResponse({'slots': [], 'error': str(e)}, status=400)
