import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta

from accounts.models import User, CustomerProfile, Notification
from restaurants.models import Restaurant, Review, CuisineType
from reservations.models import Reservation, AIRecommendation


def is_admin(user):
    return user.is_authenticated and user.is_admin_user


@login_required
def customer_dashboard(request):
    user = request.user
    upcoming = Reservation.objects.filter(
        customer=user,
        reservation_date__gte=timezone.localdate(),
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
    ).select_related('restaurant', 'table').order_by('reservation_date', 'reservation_time')[:5]

    all_res = Reservation.objects.filter(customer=user)
    stats = {
        'total': all_res.count(),
        'completed': all_res.filter(status=Reservation.STATUS_COMPLETED).count(),
        'upcoming': upcoming.count(),
        'cancelled': all_res.filter(status=Reservation.STATUS_CANCELLED).count(),
    }
    try:
        profile = user.customerprofile
    except CustomerProfile.DoesNotExist:
        profile = CustomerProfile.objects.create(user=user)

    recent_notifications = user.notifications.all()[:5]

    return render(request, 'dashboard/customer.html', {
        'profile': profile,
        'upcoming': upcoming,
        'stats': stats,
        'recent_notifications': recent_notifications,
    })


@login_required
def reservation_history(request):
    qs = Reservation.objects.filter(
        customer=request.user
    ).select_related('restaurant', 'table').order_by('-reservation_date', '-created_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'dashboard/reservation_history.html', {
        'reservations': page_obj,
        'current_status': status_filter,
        'status_choices': Reservation.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_admin, login_url='/accounts/login/')
def admin_dashboard(request):
    today = timezone.localdate()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago  = today - timedelta(days=7)

    stats = {
        'total_restaurants':   Restaurant.objects.filter(status=Restaurant.STATUS_ACTIVE).count(),
        'active_restaurants':  Restaurant.objects.filter(status=Restaurant.STATUS_ACTIVE).count(),
        'total_users':         User.objects.filter(role=User.ROLE_CUSTOMER).count(),
        'new_users_week':      User.objects.filter(date_joined__date__gte=seven_days_ago).count(),
        'total_reservations':  Reservation.objects.count(),
        'today_reservations':  Reservation.objects.filter(reservation_date=today).count(),
        'pending_reservations':Reservation.objects.filter(status=Reservation.STATUS_PENDING).count(),
    }

    recent_reservations = Reservation.objects.select_related(
        'customer', 'restaurant', 'table'
    ).order_by('-created_at')[:15]

    top_restaurants = Restaurant.objects.filter(
        status=Restaurant.STATUS_ACTIVE
    ).annotate(reservation_count=Count('reservations')).order_by('-reservation_count')[:5]

    return render(request, 'dashboard/admin_dashboard.html', {
        'stats': stats,
        'recent_reservations': recent_reservations,
        'top_restaurants': top_restaurants,
    })


@login_required
@user_passes_test(is_admin)
def admin_restaurants(request):
    qs = Restaurant.objects.annotate(
        reservation_count=Count('reservations'),
    ).order_by('-created_at')

    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q))
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'dashboard/admin_restaurants.html', {
        'restaurants': page_obj,
        'total_count': qs.count(),
        'status_choices': Restaurant.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def admin_reservations(request):
    qs = Reservation.objects.select_related('customer', 'restaurant', 'table').order_by('-created_at')

    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    date_filter = request.GET.get('date', '')
    if date_filter:
        qs = qs.filter(reservation_date=date_filter)
    restaurant_filter = request.GET.get('restaurant', '')
    if restaurant_filter:
        qs = qs.filter(restaurant_id=restaurant_filter)
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(reservation_id__icontains=q) | Q(customer_name__icontains=q) |
            Q(customer_email__icontains=q) | Q(restaurant__name__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'dashboard/admin_reservations.html', {
        'reservations': page_obj,
        'total_count': qs.count(),
        'status_choices': Reservation.STATUS_CHOICES,
        'restaurant_list': Restaurant.objects.filter(status=Restaurant.STATUS_ACTIVE).values('id', 'name'),
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_update_reservation_status(request, reservation_id):
    """AJAX: update reservation status. Accepts JSON body."""
    reservation = get_object_or_404(Reservation, reservation_id=reservation_id)
    try:
        data = json.loads(request.body)
        new_status = data.get('status', '')
    except (json.JSONDecodeError, AttributeError):
        new_status = request.POST.get('status', '')

    valid_statuses = dict(Reservation.STATUS_CHOICES)
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

    old_status = reservation.status
    reservation.status = new_status
    if new_status == Reservation.STATUS_CONFIRMED:
        reservation.confirmed_at = timezone.now()
        reservation.confirmed_by = request.user
    elif new_status == Reservation.STATUS_CANCELLED:
        reservation.cancelled_at = timezone.now()
    reservation.save()

    from reservations.models import ReservationStatusHistory
    ReservationStatusHistory.objects.create(
        reservation=reservation,
        status=new_status,
        changed_by=request.user,
        notes=f'Status changed from {old_status} to {new_status} via admin',
    )

    type_map = {
        Reservation.STATUS_CONFIRMED: Notification.TYPE_BOOKING_CONFIRMED,
        Reservation.STATUS_CANCELLED: Notification.TYPE_BOOKING_CANCELLED,
    }
    if new_status in type_map and reservation.customer:
        Notification.objects.create(
            user=reservation.customer,
            notification_type=type_map[new_status],
            title=f'Reservation {new_status.title()}',
            message=f'Your reservation {reservation.reservation_id} has been {new_status}.',
            link=f'/reservations/{reservation.reservation_id}/',
        )

    return JsonResponse({'success': True, 'new_status': new_status})


@login_required
@user_passes_test(is_admin)
def admin_users(request):
    qs = User.objects.annotate(reservation_count=Count('reservations')).order_by('-date_joined')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    role_filter = request.GET.get('role', '')
    if role_filter:
        qs = qs.filter(role=role_filter)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'dashboard/admin_users.html', {
        'users': page_obj,
        'total_count': qs.count(),
        'role_choices': User.ROLE_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def admin_analytics(request):
    today = timezone.localdate()

    # Chart data: last 30 days
    labels, values = [], []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime('%b %d'))
        values.append(Reservation.objects.filter(reservation_date=day).count())

    # Cuisine breakdown
    cuisine_labels, cuisine_values = [], []
    for c in CuisineType.objects.annotate(n=Count('restaurant__reservations')).order_by('-n')[:8]:
        cuisine_labels.append(c.name)
        cuisine_values.append(c.n)

    # KPIs
    total = Reservation.objects.count() or 1
    completed = Reservation.objects.filter(status=Reservation.STATUS_COMPLETED).count()
    cancelled = Reservation.objects.filter(status=Reservation.STATUS_CANCELLED).count()
    ai_used   = AIRecommendation.objects.count()
    kpi = {
        'total_reservations': total,
        'completion_rate': round(completed / total * 100, 1),
        'cancellation_rate': round(cancelled / total * 100, 1),
        'ai_usage_rate': round(ai_used / total * 100, 1),
        'reservation_growth': 0,
    }

    # Peak hours
    peak_hours = []
    max_count = 1
    hour_counts = {}
    for h in range(10, 23):
        cnt = Reservation.objects.filter(reservation_time__hour=h).count()
        hour_counts[h] = cnt
        if cnt > max_count:
            max_count = cnt
    for h in range(10, 23):
        cnt = hour_counts[h]
        peak_hours.append({'label': f'{h:02d}', 'opacity': max(0.15, round(cnt / max_count, 2))})

    # Top restaurants
    top_restaurants = []
    max_res = 1
    for r in Restaurant.objects.annotate(count=Count('reservations')).order_by('-count')[:8]:
        if r.count > max_res:
            max_res = r.count
    for r in Restaurant.objects.annotate(count=Count('reservations')).order_by('-count')[:8]:
        top_restaurants.append({
            'name': r.name,
            'count': r.count,
            'pct': round(r.count / max_res * 100) if max_res else 0,
        })

    return render(request, 'dashboard/admin_analytics.html', {
        'chart_labels': json.dumps(labels),
        'chart_values': json.dumps(values),
        'cuisine_labels': json.dumps(cuisine_labels),
        'cuisine_values': json.dumps(cuisine_values),
        'kpi': kpi,
        'peak_hours': peak_hours,
        'top_restaurants': top_restaurants,
        'period_choices': [('30', 'Last 30 Days'), ('7', 'Last 7 Days'), ('90', 'Last 90 Days')],
        'current_period': request.GET.get('period', '30'),
    })
