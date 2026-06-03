"""
TableMaster AI Recommendation Engine v2.0
=========================================
Intelligent table recommendation using multi-factor scoring algorithm.

Factors analyzed:
  - Capacity optimization (guest count vs table capacity)
  - Historical preference learning (past booking patterns)
  - Real-time availability (conflict detection)
  - Peak hour management (load balancing)
  - Customer seating preferences (profile data)
  - Table feature matching (window, private, outdoor)
  - Utilization optimization (reduce unused capacity)
  - Temporal patterns (day of week, time of year)
"""

import time
import logging
from datetime import datetime, timedelta, date as date_type, time as time_type
from decimal import Decimal
from collections import defaultdict

logger = logging.getLogger('tablemaster')


class ScoringWeights:
    """Configurable weights for the recommendation algorithm."""
    CAPACITY_MATCH = 0.30
    CUSTOMER_PREFERENCE = 0.22
    UTILIZATION = 0.18
    HISTORICAL_PATTERN = 0.15
    PEAK_OPTIMIZATION = 0.10
    FEATURE_BONUS = 0.05


class TableRecommendationEngine:
    """
    Core AI engine for table recommendations.

    Algorithm Overview:
    1. Fetch all active, available tables for given slot
    2. Score each table across 6 dimensions
    3. Apply weighted sum to get composite score
    4. Rank and return top recommendation + alternatives
    5. If no tables available, generate smart alternative slots
    """

    VERSION = 'v2.0'
    WEIGHTS = ScoringWeights()
    CONFLICT_BUFFER_MINUTES = 90  # Buffer on either side of reservation

    def __init__(self):
        self._cache = {}

    def recommend(self, restaurant, guest_count, reservation_date,
                  reservation_time, customer=None, preferences=None):
        """
        Main entry point for AI recommendations.

        Args:
            restaurant: Restaurant model instance
            guest_count: Number of guests
            reservation_date: date object
            reservation_time: time object
            customer: User model instance (optional, for personalization)
            preferences: dict of explicit preferences

        Returns:
            dict with keys:
                recommended_table: Table instance or None
                overall_score: float 0-100
                reasoning: dict explaining scores
                alternatives: list of alternative table dicts
                alternative_slots: list of alternative date/time dicts
                has_recommendation: bool
        """
        start_time = time.time()
        preferences = preferences or {}

        logger.info(f"AI Recommendation: {restaurant.name}, {guest_count} guests, {reservation_date} {reservation_time}")

        # Step 1: Get available tables
        available_tables = self._get_available_tables(restaurant, reservation_date, reservation_time, guest_count)

        if not available_tables:
            logger.info("No available tables - generating alternatives")
            alt_slots = self._generate_alternative_slots(restaurant, guest_count, reservation_date, reservation_time)
            return {
                'recommended_table': None,
                'overall_score': 0,
                'reasoning': {'error': 'No tables available for this slot', 'capacity_available': False},
                'alternatives': [],
                'alternative_slots': alt_slots,
                'has_recommendation': False,
                'processing_time_ms': int((time.time() - start_time) * 1000),
            }

        # Step 2: Score all available tables
        customer_profile = self._get_customer_profile(customer)
        historical_prefs = self._get_historical_preferences(customer, restaurant)
        peak_factor = self._is_peak_hour(reservation_time)
        daily_stats = self._get_daily_stats(restaurant, reservation_date)

        scored_tables = []
        for table in available_tables:
            score_breakdown = self._score_table(
                table=table,
                guest_count=guest_count,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                customer_profile=customer_profile,
                preferences=preferences,
                historical_prefs=historical_prefs,
                peak_factor=peak_factor,
                daily_stats=daily_stats,
            )
            scored_tables.append({
                'table': table,
                'overall_score': score_breakdown['weighted_total'],
                'breakdown': score_breakdown,
            })

        # Step 3: Sort by score descending
        scored_tables.sort(key=lambda x: x['overall_score'], reverse=True)

        best = scored_tables[0]
        alternatives = scored_tables[1:4]  # Up to 3 alternatives

        # Step 4: Build reasoning explanation
        reasoning = self._build_reasoning(best['breakdown'], best['table'], guest_count)

        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"Recommendation complete in {processing_time}ms: Table {best['table'].table_number} (score: {best['overall_score']:.2f})")

        return {
            'recommended_table': best['table'],
            'overall_score': round(best['overall_score'], 4),
            'reasoning': reasoning,
            'alternatives': [
                {
                    'table': alt['table'],
                    'score': round(alt['overall_score'], 4),
                    'reason': self._short_reason(alt['breakdown'], alt['table'])
                }
                for alt in alternatives
            ],
            'alternative_slots': [],
            'has_recommendation': True,
            'processing_time_ms': processing_time,

            # Individual score components
            'capacity_score': round(best['breakdown']['capacity_score'], 4),
            'preference_score': round(best['breakdown']['preference_score'], 4),
            'utilization_score': round(best['breakdown']['utilization_score'], 4),
            'historical_score': round(best['breakdown']['historical_score'], 4),
        }

    def _get_available_tables(self, restaurant, reservation_date, reservation_time, guest_count):
        """Get tables that can accommodate guests and are not conflicting."""
        from restaurants.models import Table
        from reservations.models import Reservation

        buffer = self.CONFLICT_BUFFER_MINUTES
        res_dt = datetime.combine(reservation_date, reservation_time)
        window_start = (res_dt - timedelta(minutes=buffer)).time()
        window_end = (res_dt + timedelta(minutes=buffer)).time()

        # Find all conflicting reservations
        conflicting_table_ids = Reservation.objects.filter(
            restaurant=restaurant,
            reservation_date=reservation_date,
            status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
            reservation_time__gte=window_start,
            reservation_time__lte=window_end,
        ).values_list('table_id', flat=True)

        return list(
            Table.objects.filter(
                restaurant=restaurant,
                is_active=True,
                capacity__gte=guest_count,
            ).exclude(id__in=conflicting_table_ids).select_related('restaurant')
        )

    def _score_table(self, table, guest_count, reservation_date, reservation_time,
                     customer_profile, preferences, historical_prefs, peak_factor, daily_stats):
        """
        Compute multi-dimensional score for a table.
        Returns dict with individual scores and weighted total.
        """
        # --- 1. Capacity Match Score (0-100) ---
        capacity_score = self._capacity_score(table.capacity, guest_count)

        # --- 2. Customer Preference Score (0-100) ---
        preference_score = self._preference_score(table, customer_profile, preferences)

        # --- 3. Utilization Optimization Score (0-100) ---
        utilization_score = self._utilization_score(table, daily_stats)

        # --- 4. Historical Pattern Score (0-100) ---
        historical_score = self._historical_score(table, historical_prefs)

        # --- 5. Peak Hour Optimization Score (0-100) ---
        peak_score = self._peak_score(table, reservation_time, peak_factor, daily_stats)

        # --- 6. Feature Bonus (0-100) ---
        feature_score = self._feature_bonus_score(table, preferences)

        # Weighted composite
        W = self.WEIGHTS
        weighted_total = (
            W.CAPACITY_MATCH * capacity_score +
            W.CUSTOMER_PREFERENCE * preference_score +
            W.UTILIZATION * utilization_score +
            W.HISTORICAL_PATTERN * historical_score +
            W.PEAK_OPTIMIZATION * peak_score +
            W.FEATURE_BONUS * feature_score
        )

        # Scale to 0-100
        weighted_total = min(100.0, max(0.0, weighted_total))

        return {
            'capacity_score': capacity_score,
            'preference_score': preference_score,
            'utilization_score': utilization_score,
            'historical_score': historical_score,
            'peak_score': peak_score,
            'feature_score': feature_score,
            'weighted_total': weighted_total,
        }

    def _capacity_score(self, table_capacity, guest_count):
        """
        Reward tables that fit snugly.
        Perfect score for exact match, decreasing for larger tables.
        Zero if table can't fit guests.
        """
        if table_capacity < guest_count:
            return 0.0

        overflow = table_capacity - guest_count
        if overflow == 0:
            return 100.0
        elif overflow == 1:
            return 93.0
        elif overflow == 2:
            return 85.0
        elif overflow == 3:
            return 75.0
        elif overflow <= 5:
            return 60.0
        elif overflow <= 8:
            return 40.0
        else:
            return max(15.0, 100.0 - (overflow * 7))

    def _preference_score(self, table, customer_profile, preferences):
        """
        Score based on customer seating preferences from profile and explicit request.
        """
        score = 50.0  # Neutral baseline

        # Profile-based preferences
        if customer_profile:
            if customer_profile.get('prefers_window') and table.has_window_view:
                score += 20.0
            elif customer_profile.get('prefers_window') and not table.has_window_view:
                score -= 10.0

            if customer_profile.get('prefers_private') and table.is_private:
                score += 20.0
            elif customer_profile.get('prefers_private') and not table.is_private:
                score -= 8.0

            if customer_profile.get('prefers_outdoor') and table.is_outdoor:
                score += 15.0
            elif customer_profile.get('prefers_outdoor') and not table.is_outdoor:
                score -= 5.0

            if customer_profile.get('needs_accessible') and table.is_accessible:
                score += 30.0  # Strong boost for accessibility need
            elif customer_profile.get('needs_accessible') and not table.is_accessible:
                score -= 40.0  # Heavy penalty

            if customer_profile.get('prefers_quiet') and table.section == 'quiet':
                score += 10.0

        # Explicit preferences override
        if preferences.get('window_view') and table.has_window_view:
            score += 15.0
        if preferences.get('private') and table.is_private:
            score += 15.0
        if preferences.get('outdoor') and table.is_outdoor:
            score += 15.0
        if preferences.get('accessible') and table.is_accessible:
            score += 25.0

        return min(100.0, max(0.0, score))

    def _utilization_score(self, table, daily_stats):
        """
        Prefer tables that maximize overall restaurant utilization.
        Spread bookings evenly; avoid clustering reservations.
        """
        table_id = table.id
        bookings_today = daily_stats.get('table_bookings', {}).get(table_id, 0)

        # Fewer existing bookings = higher score (spread load)
        if bookings_today == 0:
            return 85.0
        elif bookings_today == 1:
            return 75.0
        elif bookings_today == 2:
            return 60.0
        elif bookings_today == 3:
            return 45.0
        else:
            return max(20.0, 85.0 - bookings_today * 12)

    def _historical_score(self, table, historical_prefs):
        """
        Learn from customer's past reservations at this restaurant.
        Boost tables similar to ones they've enjoyed before.
        """
        if not historical_prefs:
            return 70.0  # Neutral for new customers

        preferred_types = historical_prefs.get('preferred_types', [])
        avoided_types = historical_prefs.get('avoided_types', [])

        score = 70.0

        if table.table_type in preferred_types:
            score += 20.0
        if table.table_type in avoided_types:
            score -= 25.0
        if table.is_private and historical_prefs.get('likes_private', False):
            score += 15.0
        if table.has_window_view and historical_prefs.get('likes_window', False):
            score += 15.0

        # Repeat table bonus (customer liked this exact table before)
        if table.id in historical_prefs.get('past_table_ids', []):
            score += 10.0

        return min(100.0, max(0.0, score))

    def _peak_score(self, table, reservation_time, is_peak, daily_stats):
        """
        During peak hours: prefer smaller/standard tables for better turnover.
        Off-peak: premium tables available without rush.
        """
        hour = reservation_time.hour

        if is_peak:
            # During peak, prefer standard/window over large private rooms
            if table.table_type in ('standard', 'window', 'booth'):
                return 80.0
            elif table.table_type in ('private',):
                return 50.0  # Save private rooms for non-peak
            else:
                return 65.0
        else:
            # Off-peak: premium tables are fine
            if table.is_private:
                return 85.0  # Private rooms feel more special off-peak
            elif table.has_window_view:
                return 80.0
            else:
                return 70.0

    def _feature_bonus_score(self, table, preferences):
        """
        Small bonus for having desirable features regardless of preference.
        """
        score = 50.0
        if table.has_window_view:
            score += 10.0
        if table.is_accessible:
            score += 5.0
        if table.has_power_outlet:
            score += 5.0
        if table.is_private:
            score += 8.0
        return min(100.0, score)

    def _is_peak_hour(self, reservation_time):
        """Check if time falls in peak dining hours."""
        hour = reservation_time.hour
        peak_ranges = getattr(
            __import__('django.conf', fromlist=['settings']).settings,
            'TABLEMASTER', {}
        ).get('PEAK_HOURS', [(12, 14), (19, 22)])

        for start, end in peak_ranges:
            if start <= hour < end:
                return True
        return False

    def _get_customer_profile(self, customer):
        """Extract preference flags from customer profile."""
        if not customer:
            return {}
        try:
            profile = customer.customerprofile
            return {
                'prefers_window': profile.prefers_window_seat,
                'prefers_private': profile.prefers_private_dining,
                'prefers_outdoor': profile.prefers_outdoor,
                'needs_accessible': profile.requires_accessibility,
                'prefers_quiet': profile.prefers_quiet_section,
            }
        except Exception:
            return {}

    def _get_historical_preferences(self, customer, restaurant):
        """Analyze customer's past reservations to infer preferences."""
        if not customer:
            return {}

        try:
            from reservations.models import Reservation
            past = Reservation.objects.filter(
                customer=customer,
                restaurant=restaurant,
                status__in=[Reservation.STATUS_COMPLETED],
                table__isnull=False,
            ).select_related('table').order_by('-created_at')[:20]

            if not past.exists():
                # Try any restaurant
                past = Reservation.objects.filter(
                    customer=customer,
                    status=Reservation.STATUS_COMPLETED,
                    table__isnull=False,
                ).select_related('table').order_by('-created_at')[:20]

            if not past.exists():
                return {}

            type_counter = defaultdict(int)
            table_ids = []
            likes_private = 0
            likes_window = 0

            for r in past:
                if r.table:
                    type_counter[r.table.table_type] += 1
                    table_ids.append(r.table.id)
                    if r.table.is_private:
                        likes_private += 1
                    if r.table.has_window_view:
                        likes_window += 1

            total = len(table_ids)
            preferred_types = [t for t, c in type_counter.items() if c / total > 0.3]
            avoided_types = [t for t, c in type_counter.items() if c / total < 0.1]

            return {
                'preferred_types': preferred_types,
                'avoided_types': avoided_types,
                'past_table_ids': table_ids[:5],
                'likes_private': likes_private / total > 0.4,
                'likes_window': likes_window / total > 0.4,
            }
        except Exception as e:
            logger.warning(f"Error loading historical prefs: {e}")
            return {}

    def _get_daily_stats(self, restaurant, reservation_date):
        """Get today's booking stats per table for utilization scoring."""
        try:
            from reservations.models import Reservation
            today_reservations = Reservation.objects.filter(
                restaurant=restaurant,
                reservation_date=reservation_date,
                status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED],
                table__isnull=False,
            ).values_list('table_id', flat=True)

            table_bookings = defaultdict(int)
            for tid in today_reservations:
                table_bookings[tid] += 1

            return {'table_bookings': dict(table_bookings)}
        except Exception:
            return {'table_bookings': {}}

    def _generate_alternative_slots(self, restaurant, guest_count, requested_date, requested_time):
        """
        When no tables available, suggest smart alternative slots.
        Checks same day at different times + upcoming days.
        """
        alternatives = []
        checked = set()

        def check_slot(check_date, check_time):
            key = (check_date, check_time)
            if key in checked:
                return
            checked.add(key)

            # Must be future
            slot_dt = datetime.combine(check_date, check_time)
            if slot_dt <= datetime.now():
                return

            # Must be within restaurant hours
            if not (restaurant.opening_time <= check_time <= restaurant.closing_time):
                return

            available = self._get_available_tables(restaurant, check_date, check_time, guest_count)
            if available:
                alternatives.append({
                    'date': check_date.isoformat(),
                    'time': check_time.strftime('%H:%M'),
                    'display_date': check_date.strftime('%A, %B %d'),
                    'display_time': check_time.strftime('%I:%M %p'),
                    'available_count': len(available),
                    'is_same_day': check_date == requested_date,
                })

        # Same day: ±1h, ±2h, ±3h
        req_hour = requested_time.hour
        req_minute = requested_time.minute
        for delta_hours in [-3, -2, -1, 1, 2, 3]:
            new_hour = req_hour + delta_hours
            if 10 <= new_hour <= 22:
                try:
                    alt_time = time_type(new_hour, req_minute)
                    check_slot(requested_date, alt_time)
                except ValueError:
                    pass

        # Same time, next 7 days
        for days_ahead in [1, 2, 3, 4, 5, 6, 7]:
            alt_date = requested_date + timedelta(days=days_ahead)
            check_slot(alt_date, requested_time)

        # Sort: same day first, then by date
        alternatives.sort(key=lambda x: (not x['is_same_day'], x['date'], x['time']))

        return alternatives[:6]

    def _build_reasoning(self, breakdown, table, guest_count):
        """Build human-readable reasoning for the recommendation."""
        reasons = []

        cap_score = breakdown['capacity_score']
        overflow = table.capacity - guest_count
        if overflow == 0:
            reasons.append(f"Perfect capacity match: Table seats exactly {guest_count} guest{'s' if guest_count > 1 else ''}")
        elif overflow <= 2:
            reasons.append(f"Excellent capacity fit: Table seats {table.capacity} for your party of {guest_count}")
        else:
            reasons.append(f"Available capacity: Table seats {table.capacity}, accommodating your party of {guest_count}")

        if table.has_window_view:
            reasons.append("Scenic window view for an enhanced dining experience")
        if table.is_private:
            reasons.append("Private dining room for an intimate experience")
        if table.is_outdoor:
            reasons.append("Outdoor seating in a pleasant environment")
        if table.is_accessible:
            reasons.append("Wheelchair accessible table for comfortable seating")

        util_score = breakdown['utilization_score']
        if util_score >= 80:
            reasons.append("Table is fresh with minimal bookings today")

        peak_score = breakdown['peak_score']
        if peak_score >= 75:
            reasons.append("Optimal table type for your dining time slot")

        return {
            'summary': reasons[0] if reasons else 'Best available table for your requirements',
            'details': reasons,
            'capacity_score': round(cap_score, 1),
            'preference_score': round(breakdown['preference_score'], 1),
            'utilization_score': round(util_score, 1),
            'historical_score': round(breakdown['historical_score'], 1),
            'overall': round(breakdown['weighted_total'], 1),
            'table_features': table.display_features,
        }

    def _short_reason(self, breakdown, table):
        """One-line reason for alternative table."""
        if table.is_private:
            return "Private dining room"
        if table.has_window_view:
            return f"Window table, seats {table.capacity}"
        if table.is_outdoor:
            return f"Outdoor seating, seats {table.capacity}"
        overflow = table.capacity
        return f"Standard table, seats {overflow}"


# Module-level singleton
_engine = None

def get_engine():
    """Get or create the recommendation engine singleton."""
    global _engine
    if _engine is None:
        _engine = TableRecommendationEngine()
    return _engine


def recommend_table(restaurant, guest_count, reservation_date, reservation_time,
                    customer=None, preferences=None):
    """
    Convenience function for getting a table recommendation.

    Returns: recommendation dict (see TableRecommendationEngine.recommend)
    """
    engine = get_engine()
    return engine.recommend(
        restaurant=restaurant,
        guest_count=guest_count,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        customer=customer,
        preferences=preferences,
    )
