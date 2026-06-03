from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from datetime import datetime

from restaurants.models import Restaurant, Table
from .models import Reservation, AIRecommendation, ReservationStatusHistory
from .ai_engine import recommend_table
from .forms import ReservationForm
from datetime import date as date_type, datetime
from .restaurant_recommender import recommend_restaurants


@login_required
def book_table(request, restaurant_slug):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, status=Restaurant.STATUS_ACTIVE)
    initial = {
        'reservation_date': request.GET.get('date', ''),
        'reservation_time': request.GET.get('time', ''),
        'guest_count': request.GET.get('guests', 2),
        'customer_name': request.user.get_full_name(),
        'customer_email': request.user.email,
        'customer_phone': request.user.phone or '',
    }
    try:
        initial['customer_whatsapp'] = request.user.customerprofile.whatsapp_number
    except Exception:
        pass

    form = ReservationForm(initial=initial)
    return render(request, 'reservations/book.html', {
        'restaurant': restaurant,
        'form': form,
        'primary_image': restaurant.primary_image,
        'tables': restaurant.tables.filter(is_active=True).order_by('table_number'),
        'min_date': timezone.localdate().isoformat(),
    })


@login_required
@require_GET
def get_ai_recommendation(request):
    """AJAX GET: return AI table recommendation."""
    try:
        slug       = request.GET.get('slug', '')
        guest_count= int(request.GET.get('guests', 2))
        date_str   = request.GET.get('date', '')
        time_str   = request.GET.get('time', '')

        if not all([slug, date_str, time_str]):
            return JsonResponse({'has_recommendation': False, 'error': 'Missing fields'})

        from datetime import date as dt_date, time as dt_time
        restaurant = get_object_or_404(Restaurant, slug=slug)
        res_date   = dt_date.fromisoformat(date_str)
        res_time   = dt_time.fromisoformat(time_str)

        result = recommend_table(
            restaurant=restaurant,
            guest_count=guest_count,
            reservation_date=res_date,
            reservation_time=res_time,
            customer=request.user,
        )

        if result['has_recommendation']:
            t = result['recommended_table']
            return JsonResponse({
                'has_recommendation': True,
                'recommended_table': {
                    'id': t.id,
                    'number': t.table_number,
                    'type': t.get_table_type_display(),
                    'capacity': t.capacity,
                    'floor': str(t.floor),
                    'section': t.section,
                },
                'overall_score': float(result.get('overall_score', 0)),
                'reasoning': result.get('reasoning', {}),
                'alternative_slots': result.get('alternative_slots', []),
            })
        return JsonResponse({
            'has_recommendation': False,
            'alternative_slots': result.get('alternative_slots', []),
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return JsonResponse({'has_recommendation': False, 'error': str(e)})


@login_required
@transaction.atomic
def create_reservation(request, restaurant_slug):
    if request.method != 'POST':
        return redirect('book_table', restaurant_slug=restaurant_slug)

    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, status=Restaurant.STATUS_ACTIVE)
    form = ReservationForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'Please correct the errors below.')
        return render(request, 'reservations/book.html', {
            'restaurant': restaurant,
            'form': form,
            'primary_image': restaurant.primary_image,
            'tables': restaurant.tables.filter(is_active=True).order_by('table_number'),
            'min_date': timezone.localdate().isoformat(),
        })

    data = form.cleaned_data
    res_date    = data['reservation_date']
    res_time    = data['reservation_time']
    guest_count = data['guest_count']

    # Determine table
    table_id = request.POST.get('selected_table_id')
    selected_table = None
    ai_result = None
    ai_table_assigned = False

    if table_id:
        try:
            t = Table.objects.get(pk=table_id, restaurant=restaurant, is_active=True)
            if t.is_available(res_date, res_time):
                selected_table = t
        except Table.DoesNotExist:
            pass

    if not selected_table:
        ai_result = recommend_table(
            restaurant=restaurant, guest_count=guest_count,
            reservation_date=res_date, reservation_time=res_time,
            customer=request.user,
        )
        if ai_result['has_recommendation']:
            selected_table = ai_result['recommended_table']
            ai_table_assigned = True
        else:
            messages.error(request, 'No tables available for this slot. Please try a different time.')
            return render(request, 'reservations/book.html', {
                'restaurant': restaurant, 'form': form,
                'primary_image': restaurant.primary_image,
                'tables': restaurant.tables.filter(is_active=True),
                'min_date': timezone.localdate().isoformat(),
                'alternative_slots': ai_result.get('alternative_slots', []),
            })

    reservation = Reservation(
        customer=request.user,
        restaurant=restaurant,
        table=selected_table,
        customer_name=data['customer_name'],
        customer_phone=data['customer_phone'],
        customer_whatsapp=data.get('customer_whatsapp', ''),
        customer_email=data['customer_email'],
        reservation_date=res_date,
        reservation_time=res_time,
        guest_count=guest_count,
        special_requests=data.get('special_requests', ''),
        occasion=data.get('occasion', ''),
        ai_table_assigned=ai_table_assigned,
        status=Reservation.STATUS_CONFIRMED,
        source=Reservation.SOURCE_WEB,
    )
    if ai_result:
        reservation.ai_confidence_score = ai_result.get('overall_score', 0)

    print("ai_confidence_score:", reservation.ai_confidence_score)
    reservation.save()

    ReservationStatusHistory.objects.create(
        reservation=reservation,
        status=Reservation.STATUS_CONFIRMED,
        changed_by=request.user,
        notes='Created via web',
    )

    if ai_result and ai_result.get('has_recommendation'):
        AIRecommendation.objects.create(
            reservation=reservation,
            recommended_table=selected_table,
            overall_score=ai_result.get('overall_score', 0),
            capacity_score=ai_result.get('capacity_score', 0),
            preference_score=ai_result.get('preference_score', 0),
            utilization_score=ai_result.get('utilization_score', 0),
            historical_score=ai_result.get('historical_score', 0),
            reasoning=ai_result.get('reasoning', {}),
            algorithm_version='v2.0',
            processing_time_ms=ai_result.get('processing_time_ms', 0),
        )

    # Update loyalty
    try:
        profile = request.user.customerprofile
        profile.total_reservations = profile.total_reservations + 1
        profile.loyalty_points = profile.loyalty_points + 10
        profile.save(update_fields=['total_reservations', 'loyalty_points'])
    except Exception:
        pass

    from accounts.models import Notification
    Notification.objects.create(
        user=request.user,
        notification_type=Notification.TYPE_BOOKING_CONFIRMED,
        title='Reservation Confirmed! 🎉',
        message=f'Your table at {restaurant.name} on {res_date.strftime("%B %d, %Y")} at {res_time.strftime("%I:%M %p")} is confirmed.',
        link=f'/reservations/{reservation.reservation_id}/',
    )

    messages.success(request, f'Reservation confirmed! ID: {reservation.reservation_id}')
    return redirect('reservation_confirmation', reservation_id=reservation.reservation_id)


@login_required
def reservation_confirmation(request, reservation_id):
    reservation = get_object_or_404(Reservation, reservation_id=reservation_id, customer=request.user)
    ai_rec = None
    try:
        ai_rec = reservation.ai_recommendation
    except Exception:
        pass
    return render(request, 'reservations/confirmation.html', {
        'reservation': reservation,
        'ai_recommendation': ai_rec,
    })


@login_required
def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, reservation_id=reservation_id, customer=request.user)
    ai_rec = None
    try:
        ai_rec = reservation.ai_recommendation
    except Exception:
        pass
    return render(request, 'reservations/detail.html', {
        'reservation': reservation,
        'ai_recommendation': ai_rec,
        'status_history': reservation.status_history.all()[:10],
    })


@login_required
@require_POST
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, reservation_id=reservation_id, customer=request.user)
    if not reservation.can_cancel:
        messages.error(request, 'This reservation cannot be cancelled at this time.')
        return redirect('reservation_detail', reservation_id=reservation_id)

    reason = request.POST.get('reason', 'Cancelled by customer')
    reservation.cancel(reason=reason, by_user=request.user)

    try:
        profile = request.user.customerprofile
        profile.total_cancellations = profile.total_cancellations + 1
        profile.save(update_fields=['total_cancellations'])
    except Exception:
        pass

    from accounts.models import Notification
    Notification.objects.create(
        user=request.user,
        notification_type=Notification.TYPE_BOOKING_CANCELLED,
        title='Reservation Cancelled',
        message=f'Reservation {reservation.reservation_id} at {reservation.restaurant.name} cancelled.',
        link='/dashboard/',
    )
    messages.success(request, f'Reservation {reservation.reservation_id} cancelled.')
    return redirect('customer_dashboard')


def ai_recommend(request):
    """
    POST handler for the hero AI recommendation form.
    Renders a dedicated results page.
    """
    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("home")

    occasion = request.POST.get("occasion", "casual")
    date_str = request.POST.get("date", "")
    members  = max(1, min(20, int(request.POST.get("members", 2))))
    city     = request.POST.get("city", "").strip() or None

    # Parse date safely
    try:
        reservation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        reservation_date = date_type.today()

    # Prevent past dates
    if reservation_date < date_type.today():
        reservation_date = date_type.today()

    customer = request.user if request.user.is_authenticated else None

    recommendations = recommend_restaurants(
        occasion=occasion,
        reservation_date=reservation_date,
        members=members,
        city=city,
        customer=customer,
        limit=5,
    )

    from django.shortcuts import render
    return render(request, "ai_recommendations.html", {
        "recommendations": recommendations,
        "occasion": occasion,
        "reservation_date": reservation_date,
        "members": members,
        "city": city,
        "date_display": reservation_date.strftime("%A, %B %d %Y"),
    })