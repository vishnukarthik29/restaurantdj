from google import genai
from django.conf import settings
import json

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def recommend_restaurants_with_gemini(
    occasion,
    members,
    reservation_date,
    restaurants
):
    restaurant_data = []

    for r in restaurants:
        restaurant_data.append({
            "id": r["id"],
            "name": r["name"],
            "rating": r["rating"],
            "reviews": r["reviews"],
            "cuisines": r["cuisines"],
            "available_time": r["available_time"],
            "features": r["features"],
            "price_range": r["price_range"]
        })

    prompt = f"""
You are a restaurant recommendation expert.

Customer Details:
- Occasion: {occasion}
- Guests: {members}
- Reservation Date: {reservation_date}

Available Restaurants:

{json.dumps(restaurant_data, indent=2)}

Return ONLY JSON:

[
  {{
    "restaurant_id": 1,
    "score": 95,
    "reason": "Excellent private dining and highly rated"
  }}
]

Rank best restaurants first.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text

    text = text.replace("```json", "").replace("```", "")

    return json.loads(text)