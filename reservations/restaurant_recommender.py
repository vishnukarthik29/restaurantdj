"""
TableMaster – Restaurant-Level AI Recommender
==============================================
Takes: occasion, date, members, city
Returns: ranked list of restaurants with best available time slot per restaurant
"""

import logging
from datetime import datetime, date as date_type, time as time_type, timedelta
from collections import defaultdict

from reservations.ai_engine import get_engine
from reservations.services.gemini_recommender import (
    recommend_restaurants_with_gemini
)

logger = logging.getLogger("tablemaster")


# ─── Occasion → preferred time windows & table preferences ───────────────────

OCCASION_CONFIG = {
    "date_night": {
        "preferred_hours": [19, 20, 21, 18],
        "preferences": {"window_view": True, "private": False},
        "label": "Date Night",
        "emoji": "💕",
        "boost_features": ["window_view", "is_private", "ambient_lighting"],
    },
    "birthday": {
        "preferred_hours": [19, 20, 18, 21],
        "preferences": {"private": True},
        "label": "Birthday",
        "emoji": "🎂",
        "boost_features": ["is_private", "event_space"],
    },
    "anniversary": {
        "preferred_hours": [20, 19, 21],
        "preferences": {"private": True, "window_view": True},
        "label": "Anniversary",
        "emoji": "💍",
        "boost_features": ["is_private", "window_view"],
    },
    "business": {
        "preferred_hours": [12, 13, 19, 18],
        "preferences": {"private": True},
        "label": "Business Lunch",
        "emoji": "💼",
        "boost_features": ["is_private", "quiet_section", "has_power_outlet"],
    },
    "family": {
        "preferred_hours": [13, 12, 19, 18],
        "preferences": {"accessible": True},
        "label": "Family Gathering",
        "emoji": "👨‍👩‍👧‍👦",
        "boost_features": ["is_accessible", "outdoor"],
    },
    "celebration": {
        "preferred_hours": [20, 19, 21, 18],
        "preferences": {"private": True},
        "label": "Celebration",
        "emoji": "🎉",
        "boost_features": ["is_private", "event_space"],
    },
    "casual": {
        "preferred_hours": [13, 19, 12, 20, 18],
        "preferences": {},
        "label": "Casual Dining",
        "emoji": "🍽️",
        "boost_features": [],
    },
    "brunch": {
        "preferred_hours": [10, 11, 12],
        "preferences": {"outdoor": True},
        "label": "Brunch",
        "emoji": "☕",
        "boost_features": ["outdoor", "window_view"],
    },
}

DEFAULT_OCCASION = {
    "preferred_hours": [19, 20, 13, 12],
    "preferences": {},
    "label": "Dining",
    "emoji": "🍽️",
    "boost_features": [],
}


def _score_restaurant(restaurant, occasion_config, available_tables, recommended_time):
    """
    Score a restaurant for a given occasion.
    Factors: rating, review count, feature match, price range.
    Returns float 0–100.
    """
    score = 0.0

    # 1. Rating (0–40 pts)
    rating = float(getattr(restaurant, "avg_rating", 0) or 0)
    score += (rating / 5.0) * 40.0

    # 2. Review count as social proof (0–10 pts)
    reviews = int(getattr(restaurant, "total_reviews", 0) or 0)
    review_score = min(10.0, reviews / 50.0 * 10.0)
    score += review_score

    # 3. Feature match for occasion (0–30 pts)
    boost_features = occasion_config.get("boost_features", [])
    if boost_features:
        matched = 0
        for table in available_tables:
            for feat in boost_features:
                if getattr(table, feat, False):
                    matched += 1
        feature_score = min(30.0, (matched / max(1, len(boost_features))) * 30.0)
        score += feature_score

    # 4. Is featured / verified (0–10 pts)
    if getattr(restaurant, "is_featured", False):
        score += 6.0
    if getattr(restaurant, "is_verified", False):
        score += 4.0

    # 5. Time quality bonus (0–10 pts) — prefer ideal hours
    preferred_hours = occasion_config.get("preferred_hours", [])
    if recommended_time and preferred_hours:
        try:
            hour = recommended_time.hour
            if hour in preferred_hours:
                idx = preferred_hours.index(hour)
                time_bonus = max(0, 10.0 - idx * 2.5)
                score += time_bonus
        except Exception:
            pass

    return min(100.0, score)


def _build_time_slots(occasion_config, restaurant, requested_date):
    """
    Build list of time objects to probe, ordered by occasion preference,
    filtered to restaurant hours.
    """
    preferred_hours = occasion_config.get("preferred_hours", [])
    opening = getattr(restaurant, "opening_time", time_type(10, 0))
    closing = getattr(restaurant, "closing_time", time_type(22, 0))

    slots = []
    seen_hours = set()

    # Preferred hours first
    for h in preferred_hours:
        if h not in seen_hours:
            t = time_type(h, 0)
            if opening <= t <= closing:
                slots.append(t)
            seen_hours.add(h)

    # Fill in every hour in operating window not yet covered
    current_hour = opening.hour
    while current_hour <= closing.hour:
        if current_hour not in seen_hours:
            slots.append(time_type(current_hour, 0))
            seen_hours.add(current_hour)
        current_hour += 1

    return slots


# def recommend_restaurants(occasion, reservation_date, members, city=None,
#                            customer=None, limit=5):
#     """
#     Main entry point.

#     Args:
#         occasion     : str key from OCCASION_CONFIG
#         reservation_date : date object
#         members      : int (guest count)
#         city         : str or None (filter by city)
#         customer     : User instance or None
#         limit        : max results to return

#     Returns:
#         list of dicts:
#           {
#             restaurant, recommended_time, available_table_count,
#             score, occasion_label, occasion_emoji,
#             ai_table_result, match_reasons
#           }
#     """
#     from restaurants.models import Restaurant

#     engine = get_engine()
#     occasion_config = OCCASION_CONFIG.get(occasion, DEFAULT_OCCASION)
#     preferences = occasion_config.get("preferences", {})

#     # Fetch candidate restaurants
#     qs = Restaurant.objects.filter(status=Restaurant.STATUS_ACTIVE).prefetch_related(
#         "cuisine_types", "tables"
#     ).select_related()

#     if city:
#         qs = qs.filter(city__icontains=city.strip())

#     results = []

#     for restaurant in qs:
#         time_slots = _build_time_slots(occasion_config, restaurant, reservation_date)

#         best_time = None
#         best_tables = []
#         best_ai_result = None

#         for slot in time_slots:
#             # Quick availability check
#             available = engine._get_available_tables(
#                 restaurant, reservation_date, slot, members
#             )
#             if not available:
#                 continue

#             # Run full AI engine for the best slot
#             ai_result = engine.recommend(
#                 restaurant=restaurant,
#                 guest_count=members,
#                 reservation_date=reservation_date,
#                 reservation_time=slot,
#                 customer=customer,
#                 preferences=preferences,
#             )

#             if ai_result.get("has_recommendation"):
#                 best_time = slot
#                 best_tables = available
#                 best_ai_result = ai_result
#                 break  # Found the best slot for this restaurant

#         if not best_time or not best_ai_result:
#             continue  # No availability at this restaurant

#         restaurant_score = _score_restaurant(
#             restaurant=restaurant,
#             occasion_config=occasion_config,
#             available_tables=best_tables,
#             recommended_time=best_time,
#         )

#         match_reasons = _build_match_reasons(
#             restaurant, occasion_config, best_time, best_tables, best_ai_result
#         )

#         results.append({
#             "restaurant": restaurant,
#             "recommended_time": best_time,
#             "recommended_time_display": best_time.strftime("%I:%M %p"),
#             "available_table_count": len(best_tables),
#             "score": round(restaurant_score, 2),
#             "occasion_label": occasion_config["label"],
#             "occasion_emoji": occasion_config["emoji"],
#             "ai_table_result": best_ai_result,
#             "match_reasons": match_reasons,
#         })

#     # Sort by score descending
#     results.sort(key=lambda x: x["score"], reverse=True)
#     return results[:limit]

def recommend_restaurants(
    occasion,
    reservation_date,
    members,
    city=None,
    customer=None,
    limit=5
):
    from restaurants.models import Restaurant

    engine = get_engine()

    occasion_config = OCCASION_CONFIG.get(
        occasion,
        DEFAULT_OCCASION
    )

    preferences = occasion_config.get(
        "preferences",
        {}
    )

    qs = (
        Restaurant.objects.filter(
            status=Restaurant.STATUS_ACTIVE
        )
        .prefetch_related(
            "cuisine_types",
            "tables"
        )
    )

    if city:
        qs = qs.filter(
            city__icontains=city.strip()
        )

    candidate_restaurants = []

    for restaurant in qs:

        time_slots = _build_time_slots(
            occasion_config,
            restaurant,
            reservation_date
        )

        best_time = None
        best_tables = []
        best_ai_result = None

        for slot in time_slots:

            available_tables = (
                engine._get_available_tables(
                    restaurant,
                    reservation_date,
                    slot,
                    members
                )
            )

            if not available_tables:
                continue

            # ai_result = engine.recommend(
            #     restaurant=restaurant,
            #     guest_count=members,
            #     reservation_date=reservation_date,
            #     reservation_time=slot,
            #     customer=customer,
            #     preferences=preferences,
            # )

            # if ai_result.get("has_recommendation"):
            #     best_time = slot
            #     best_tables = available_tables
            #     best_ai_result = ai_result
            #     break
            best_time = slot
            best_tables = available_tables
            break

        if not best_time:
            continue

        candidate_restaurants.append({
            "id": restaurant.id,
            "restaurant": restaurant,
            "name": restaurant.name,
            "rating": float(
                restaurant.avg_rating or 0
            ),
            "reviews": int(
                restaurant.total_reviews or 0
            ),
            "cuisines": [
                c.name
                for c in restaurant.cuisine_types.all()
            ],
            "available_time":
                best_time.strftime("%I:%M %p"),
            "price_range":
                getattr(
                    restaurant,
                    "price_range",
                    ""
                ),
            "features": {
                "private_dining": any(
                    getattr(t, "is_private", False)
                    for t in best_tables
                ),
                "window_view": any(
                    getattr(
                        t,
                        "has_window_view",
                        False
                    )
                    for t in best_tables
                ),
                "outdoor": any(
                    getattr(
                        t,
                        "is_outdoor",
                        False
                    )
                    for t in best_tables
                ),
            },
            "best_time": best_time,
            "available_table_count":
                len(best_tables),
            "ai_result": best_ai_result,
        })

    if not candidate_restaurants:
        return []

    gemini_rankings = (
        recommend_restaurants_with_gemini(
            occasion=occasion,
            members=members,
            reservation_date=str(
                reservation_date
            ),
            restaurants=[
                {
                    "id": r["id"],
                    "name": r["name"],
                    "rating": r["rating"],
                    "reviews": r["reviews"],
                    "cuisines": r["cuisines"],
                    "available_time":
                        r["available_time"],
                    "price_range":
                        r["price_range"],
                    "features":
                        r["features"],
                }
                for r in candidate_restaurants
            ],
        )
    )

    final_results = []

    for ranking in gemini_rankings:

        restaurant_data = next(
            (
                r
                for r in candidate_restaurants
                if r["id"]
                == ranking["restaurant_id"]
            ),
            None
        )

        if not restaurant_data:
            continue

        final_results.append({
            "restaurant":
                restaurant_data["restaurant"],
            "recommended_time":
                restaurant_data["best_time"],
            "recommended_time_display":
                restaurant_data[
                    "available_time"
                ],
            "available_table_count":
                restaurant_data[
                    "available_table_count"
                ],
            "score":
                ranking.get(
                    "score",
                    0
                ),
            "gemini_reason":
                ranking.get(
                    "reason",
                    ""
                ),
            "occasion_label":
                occasion_config["label"],
            "occasion_emoji":
                occasion_config["emoji"],
            "ai_table_result":
                restaurant_data[
                    "ai_result"
                ],
        })

    return final_results[:limit]

def _build_match_reasons(restaurant, occasion_config, best_time, available_tables, ai_result):
    """Human-readable reasons why this restaurant matches the occasion."""
    reasons = []
    occasion_label = occasion_config["label"]
    hour = best_time.hour

    # Time context
    if 18 <= hour <= 22:
        reasons.append(f"Perfect dinner timing at {best_time.strftime('%I:%M %p')}")
    elif 11 <= hour <= 15:
        reasons.append(f"Great lunch slot at {best_time.strftime('%I:%M %p')}")
    else:
        reasons.append(f"Available at {best_time.strftime('%I:%M %p')}")

    # Feature-driven reasons
    boost_features = occasion_config.get("boost_features", [])
    for table in available_tables[:3]:
        if "is_private" in boost_features and getattr(table, "is_private", False):
            reasons.append("Private dining room available")
            break
    for table in available_tables[:3]:
        if "window_view" in boost_features and getattr(table, "has_window_view", False):
            reasons.append("Window-view tables available")
            break
    for table in available_tables[:3]:
        if "outdoor" in boost_features and getattr(table, "is_outdoor", False):
            reasons.append("Outdoor seating available")
            break

    # AI engine reasoning
    ai_reasoning = ai_result.get("reasoning", {})
    if ai_reasoning.get("summary"):
        reasons.append(ai_reasoning["summary"])

    # Rating
    rating = getattr(restaurant, "avg_rating", None)
    if rating and float(rating) >= 4.5:
        reasons.append(f"Highly rated at {rating}★")

    return reasons[:4]  # Cap at 4 reasons