# TableMaster 🍽️

**AI-Powered Restaurant Reservation System**

A full-stack Django application that combines intelligent table recommendations with a luxury dark-themed UI. TableMaster helps diners discover restaurants, make reservations, and experience AI-guided table selection.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Table Recommendation** | Six-dimension scoring engine (capacity, preference, utilization, historical, peak-hour, feature) selects the optimal table per booking |
| 🍽️ **Restaurant Discovery** | Search by city, cuisine type, price range, features; paginated results with availability indicators |
| 📅 **Real-time Availability** | AJAX availability check updates instantly as date/time/guests change |
| 👤 **Customer Dashboard** | Upcoming reservations, notification centre, loyalty points, booking history |
| 🛠️ **Admin Panel** | Reservation management with inline status updates, user management, restaurant CRUD |
| 📊 **Analytics** | Reservation trends, peak-hour heatmaps, cuisine breakdown, top restaurants |
| 🔔 **Notifications** | 7 notification types with in-app bell + mark-as-read |
| 🎨 **Luxury Dark Theme** | Mahogany + gold palette, Cormorant Garamond + Jost typography |
| 📱 **Responsive** | Mobile-first Bootstrap 5 grid, sticky booking sidebar, collapsible filters |

---

## 🛠️ Tech Stack

- **Backend**: Django 4.2+, Python 3.10+
- **Database**: SQLite (dev) / MySQL (prod)
- **Frontend**: Bootstrap 5.3, Bootstrap Icons, Vanilla JS
- **Static Files**: WhiteNoise
- **AI Engine**: Pure Python scoring algorithm (no external ML dependencies)

---

## 🚀 Quick Start

### 1. Clone / Extract the project

```bash
unzip tablemaster.zip
cd tablemaster
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the example env file (or edit `settings.py` directly):

```bash
cp .env.example .env   # if provided
```

Key settings to review in `tablemaster/settings.py`:
- `SECRET_KEY` — change before deploying
- `DEBUG` — set to `False` in production
- `ALLOWED_HOSTS` — add your domain
- MySQL config (commented out by default; SQLite is used for dev)

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Seed sample data (optional but recommended)

```bash
python manage.py seed_data
```

This creates:
- **Admin user**: `admin@tablemaster.in` / `admin123`
- **Test customer**: `priya@example.com` / `test1234`
- 5 sample restaurants with tables, operating hours, and cuisine types

To reset and re-seed:
```bash
python manage.py seed_data --clear
```

### 7. Collect static files

```bash
python manage.py collectstatic --no-input
```

### 8. Run the development server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000**

---

## 📁 Project Structure

```
tablemaster/
├── manage.py
├── requirements.txt
├── tablemaster/               # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── accounts/                  # Custom user model + profiles + notifications
│   ├── models.py              # User, CustomerProfile, Notification
│   ├── views.py               # Register, login, profile, notifications
│   ├── forms.py
│   ├── admin.py
│   └── urls.py
│
├── restaurants/               # Restaurants, tables, reviews
│   ├── models.py              # Restaurant, Table, CuisineType, Review, ...
│   ├── views.py               # List, detail, AJAX availability check
│   ├── forms.py               # ReviewForm
│   ├── admin.py
│   └── urls.py
│
├── reservations/              # Booking flow + AI engine
│   ├── models.py              # Reservation, AIRecommendation, Waitlist
│   ├── views.py               # book_table, create_reservation, confirmation
│   ├── forms.py               # ReservationForm
│   ├── ai_engine.py           # TableRecommendationEngine
│   ├── admin.py
│   └── urls.py
│
├── dashboard/                 # Customer + admin dashboards
│   ├── views.py
│   └── urls.py
│
├── core/                      # Home, about, contact
│   ├── views.py
│   ├── urls.py
│   ├── context_processors.py
│   └── management/
│       └── commands/
│           └── seed_data.py
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── contact.html
│   ├── accounts/              # login, register, profile, notifications
│   ├── restaurants/           # list, detail
│   ├── reservations/          # book, confirmation, detail
│   └── dashboard/             # customer, admin views
│
├── static/
│   ├── css/tablemaster.css    # Complete luxury theme CSS
│   └── js/tablemaster.js      # AJAX, AI panel, toasts, animations
│
└── media/                     # User uploads (created at runtime)
    ├── restaurant_images/
    └── profile_photos/
```

---

## 🤖 AI Engine

The `TableRecommendationEngine` in `reservations/ai_engine.py` scores every available table on six dimensions:

| Dimension | Weight | Logic |
|-----------|--------|-------|
| **Capacity Match** | 30% | Rewards exact fit; penalises waste |
| **Customer Preference** | 22% | Matches stored seating preferences (window, private, outdoor, accessible) |
| **Utilisation Optimisation** | 18% | Spreads bookings evenly across tables |
| **Historical Pattern** | 15% | Learns from previous completed reservations |
| **Peak-Hour Optimisation** | 10% | Favours standard tables at peak hours (12–14h, 19–22h); premium at off-peak |
| **Feature Bonus** | 5% | Small bonus for desirable table features |

The engine also generates **alternative time slots** (±1–3 hours and next 7 days) when no tables are available.

---

## 🔑 Key URLs

| URL | Description |
|-----|-------------|
| `/` | Home page |
| `/restaurants/` | Search & browse restaurants |
| `/restaurants/<slug>/` | Restaurant detail page |
| `/restaurants/<slug>/book/` | Booking form with AI panel |
| `/reservations/<id>/confirmation/` | Booking confirmation |
| `/dashboard/` | Customer dashboard |
| `/dashboard/admin/` | Admin overview |
| `/accounts/login/` | Sign in |
| `/accounts/register/` | Sign up |
| `/admin/` | Django admin |

---

## 🌐 AJAX Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/restaurants/api/check-availability/` | GET | Check table availability |
| `/restaurants/api/time-slots/` | GET | Get available time slots |
| `/restaurants/<slug>/favourite/` | POST | Toggle restaurant favourite |
| `/reservations/api/ai-recommend/` | GET | Get AI table recommendation |
| `/dashboard/admin/reservations/<id>/status/` | POST | Update reservation status inline |
| `/accounts/notifications/<id>/read/` | POST | Mark notification as read |
| `/accounts/notifications/read-all/` | POST | Mark all notifications as read |

---

## 🛠️ Configuration

Key settings in `tablemaster/settings.py`:

```python
TABLEMASTER = {
    'RESERVATION_WINDOW_HOURS':    2,    # Minimum advance booking
    'MAX_ADVANCE_DAYS':           60,    # Max days ahead for booking
    'CANCELLATION_WINDOW_HOURS':   2,    # Cancel up to X hours before
    'PEAK_HOURS':         [(12,14), (19,22)],
    'AI_CONFIDENCE_THRESHOLD':   0.6,   # Min score to show AI recommendation
}
```

---

## 📦 Requirements

```
django>=4.2
Pillow>=10.0
whitenoise>=6.6
django-environ>=0.11
mysqlclient>=2.2       # Only needed for MySQL
```

---

## 🚢 Production Deployment

1. Set `DEBUG = False` and `ALLOWED_HOSTS = ['yourdomain.com']`
2. Switch to MySQL in `settings.py` (uncomment the MySQL config block)
3. Set a strong `SECRET_KEY` via environment variable
4. Run `collectstatic`
5. Use Gunicorn + Nginx (or any WSGI server)

```bash
gunicorn tablemaster.wsgi:application --bind 0.0.0.0:8000
```

---

## 📝 License

MIT — free to use, modify, and distribute.

---

*Built with ❤️ and Django*
