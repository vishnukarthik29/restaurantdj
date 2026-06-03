from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import random

User = get_user_model()

CUISINES = [
    ('South Indian', '🥘', 1), ('North Indian', '🍛', 2), ('Chinese', '🥡', 3),
    ('Italian', '🍝', 4), ('Continental', '🥗', 5), ('Japanese', '🍣', 6),
    ('Mexican', '🌮', 7), ('Seafood', '🦞', 8),
]

RESTAURANTS = [
    {
        'name': 'The Madras Kitchen', 'city': 'Chennai', 'neighborhood': 'Anna Nagar',
        'address': '42, 6th Avenue, Anna Nagar', 'state': 'Tamil Nadu', 'pincode': '600040',
        'description': 'Authentic South Indian cuisine celebrating the flavours of Tamil Nadu.',
        'price_range': 'mid', 'cuisines': ['South Indian', 'Seafood'],
        'features': {'has_parking': True, 'has_wifi': True, 'is_wheelchair_accessible': True},
        'tables': [
            ('1', 4, 'standard', 1, 'A'), ('2', 2, 'window', 1, 'A'),
            ('3', 6, 'booth', 1, 'B'), ('4', 4, 'standard', 1, 'B'), ('5', 8, 'private', 2, 'P'),
        ],
    },
    {
        'name': 'Bukhara Garden', 'city': 'Bengaluru', 'neighborhood': 'Indiranagar',
        'address': '100 Feet Road, Indiranagar', 'state': 'Karnataka', 'pincode': '560038',
        'description': 'Robust North Indian cuisine. Our tandoor burns through the night.',
        'price_range': 'fine', 'cuisines': ['North Indian'],
        'features': {'has_parking': True, 'has_outdoor_seating': True, 'has_bar': True},
        'tables': [
            ('1', 2, 'window', 1, 'A'), ('2', 4, 'standard', 1, 'A'),
            ('3', 4, 'standard', 1, 'B'), ('4', 8, 'private', 2, 'P'), ('5', 6, 'outdoor', 1, 'O'),
        ],
    },
    {
        'name': 'Sakura House', 'city': 'Mumbai', 'neighborhood': 'Bandra West',
        'address': 'Linking Road, Bandra West', 'state': 'Maharashtra', 'pincode': '400050',
        'description': 'Tokyo-trained chefs bring Japanese cuisine to Mumbai.',
        'price_range': 'luxury', 'cuisines': ['Japanese'],
        'features': {'has_wifi': True, 'has_bar': True, 'has_private_dining': True},
        'tables': [
            ('1', 2, 'bar', 1, 'Bar'), ('2', 2, 'window', 1, 'A'),
            ('3', 4, 'standard', 1, 'A'), ('4', 6, 'private', 2, 'P'), ('5', 2, 'window', 1, 'B'),
        ],
    },
    {
        'name': 'Trattoria Roma', 'city': 'Delhi', 'neighborhood': 'Connaught Place',
        'address': 'Block F, Connaught Place', 'state': 'Delhi', 'pincode': '110001',
        'description': 'Rustic Italian warmth. Fresh pasta made daily.',
        'price_range': 'fine', 'cuisines': ['Italian', 'Continental'],
        'features': {'has_wifi': True, 'has_outdoor_seating': True},
        'tables': [
            ('1', 4, 'standard', 1, 'A'), ('2', 2, 'window', 1, 'A'),
            ('3', 4, 'outdoor', 1, 'O'), ('4', 6, 'booth', 1, 'B'), ('5', 4, 'standard', 1, 'B'),
        ],
    },
    {
        'name': 'Dragon Palace', 'city': 'Hyderabad', 'neighborhood': 'Jubilee Hills',
        'address': '17, Road No. 1, Jubilee Hills', 'state': 'Telangana', 'pincode': '500033',
        'description': 'Dim sum carts, Peking duck and fiery Schezwan in Hyderabad.',
        'price_range': 'mid', 'cuisines': ['Chinese'],
        'features': {'has_parking': True, 'has_wifi': True},
        'tables': [
            ('1', 4, 'standard', 1, 'A'), ('2', 4, 'standard', 1, 'A'),
            ('3', 8, 'round', 1, 'B'), ('4', 6, 'standard', 1, 'B'), ('5', 4, 'private', 2, 'P'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed sample data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **options):
        if options['clear']:
            from restaurants.models import Restaurant, Table
            from reservations.models import Reservation
            Reservation.objects.all().delete()
            Table.objects.all().delete()
            Restaurant.objects.all().delete()
            self.stdout.write('Cleared existing data.')

        self._cuisines()
        self._admin()
        self._customers()
        self._restaurants()
        self.stdout.write(self.style.SUCCESS(
            '\n✓ Seeded! Admin: admin@tablemaster.in / admin123  |  Customer: priya@example.com / test1234'
        ))

    def _cuisines(self):
        from restaurants.models import CuisineType
        from django.utils.text import slugify
        n = 0
        for name, icon, order in CUISINES:
            _, created = CuisineType.objects.get_or_create(
                name=name, defaults={'slug': slugify(name), 'icon': icon, 'order': order}
            )
            if created: n += 1
        self.stdout.write(f'  Cuisines: {n} new')

    def _admin(self):
        if not User.objects.filter(email='admin@tablemaster.in').exists():
            User.objects.create_superuser(
                username='admin', email='admin@tablemaster.in', password='admin123',
                first_name='Admin', last_name='TableMaster', role='admin',
            )
            self.stdout.write('  Admin created')

    def _customers(self):
        from accounts.models import CustomerProfile
        for d in [
            {'username': 'priya', 'email': 'priya@example.com', 'first_name': 'Priya', 'last_name': 'Sharma'},
            {'username': 'rahul', 'email': 'rahul@example.com', 'first_name': 'Rahul', 'last_name': 'Gupta'},
        ]:
            if not User.objects.filter(email=d['email']).exists():
                u = User.objects.create_user(role='customer', **d, password='test1234')
                CustomerProfile.objects.get_or_create(user=u, defaults={'loyalty_points': random.randint(0, 200)})
        self.stdout.write('  Customers OK')

    def _restaurants(self):
        from restaurants.models import Restaurant, CuisineType, Table, RestaurantHours
        from django.utils.text import slugify
        from datetime import time as t

        owner = User.objects.filter(role='admin').first()
        n = 0

        for d in RESTAURANTS:
            slug = slugify(d['name'])
            if Restaurant.objects.filter(slug=slug).exists():
                continue

            rest = Restaurant.objects.create(
                name=d['name'], slug=slug, owner=owner,
                description=d['description'],
                address=d['address'], city=d['city'],
                neighborhood=d.get('neighborhood', ''),
                state=d['state'], pincode=d['pincode'],
                phone=f'+91 9{random.randint(100000000,999999999)}',
                price_range=d['price_range'],
                status='active',
                is_featured=random.choice([True, False]),
                opening_time=t(11, 0), closing_time=t(23, 0),
                **d.get('features', {}),
            )

            for cname in d['cuisines']:
                try:
                    rest.cuisine_types.add(CuisineType.objects.get(name=cname))
                except CuisineType.DoesNotExist:
                    pass

            for num, cap, ttype, floor, section in d['tables']:
                Table.objects.create(
                    restaurant=rest, table_number=num, capacity=cap,
                    table_type=ttype, floor=floor, section=section, is_active=True,
                )

            # Operating hours (integers 0=Mon … 6=Sun)
            for day_int in range(7):
                RestaurantHours.objects.get_or_create(
                    restaurant=rest, day_of_week=day_int,
                    defaults={'open_time': t(11, 0), 'close_time': t(23, 0), 'is_open': day_int != 6},
                )
            n += 1

        self.stdout.write(f'  Restaurants: {n} created')
