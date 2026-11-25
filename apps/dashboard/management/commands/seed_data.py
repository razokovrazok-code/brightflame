import decimal
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import SellerProfile
from apps.catalog.models import Category, Product
from apps.warehouse.models import Warehouse, StorageLocation, InventoryBatch
from apps.logistics.models import Supplier, InboundShipment, InboundItem, OutboundOrder, OrderItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds demo data into the database'

    def handle(self, *args, **options):
        self.stdout.write("Demo ma'lumotlar yuklanmoqda...")

        # Create superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@wms.uz',
                password='Admin1234!',
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS('Admin user yaratildi: admin/Admin1234!'))

        # Create demo users for each role
        demo_users = [
            ('manager1', 'warehouse_manager', 'Alibek', 'Toshmatov'),
            ('receiver1', 'receiver', 'Bobur', 'Rahimov'),
            ('picker1', 'picker', 'Jasur', 'Karimov'),
            ('dispatcher1', 'dispatcher', 'Dilnoza', 'Yusupova'),
            ('returns1', 'returns_operator', 'Nodira', 'Hamidova'),
            ('seller1', 'seller', 'Sardor', 'Ergashev'),
            ('seller2', 'seller', 'Malika', 'Nazarova'),
        ]

        for username, role, first, last in demo_users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(role=role, first_name=first, last_name=last, email=f'{username}@wms.uz')
            )
            if created:
                user.set_password('Demo1234!')
                user.save()

        # Create seller profiles
        seller1_user = User.objects.get(username='seller1')
        seller2_user = User.objects.get(username='seller2')

        sp1, _ = SellerProfile.objects.get_or_create(
            user=seller1_user,
            defaults={'seller_name': 'TechMart Store', 'seller_code': 'TMS001'}
        )
        sp2, _ = SellerProfile.objects.get_or_create(
            user=seller2_user,
            defaults={'seller_name': 'Fashion Hub', 'seller_code': 'FHS002'}
        )

        # Create categories
        categories = [
            ('Elektronika', 'ELEC'),
            ('Kiyim', 'CLOTH'),
            ('Oziq-ovqat', 'FOOD'),
            ('Maishiy texnika', 'HOME'),
            ("O'yinchoqlar", 'TOYS'),
            ('Kitoblar', 'BOOKS'),
        ]
        cat_objs = {}
        for name, code in categories:
            cat, _ = Category.objects.get_or_create(code=code, defaults={'name': name})
            cat_objs[code] = cat

        # Create products
        products_data = [
            (sp1, 'ELEC', 'Samsung Galaxy A55', 'SKU-SA55-001', '8801643845729', False),
            (sp1, 'ELEC', 'Apple AirPods Pro', 'SKU-APP-002', '194253376057', False),
            (sp1, 'ELEC', 'Xiaomi Redmi Note 13', 'SKU-XRN13-003', '6941812701232', False),
            (sp2, 'CLOTH', "Erkaklar ko'ylagi L", 'SKU-EKL-004', '4901780198405', False),
            (sp2, 'CLOTH', "Ayollar ko'ylagi M", 'SKU-AKM-005', '4901780198412', False),
            (sp1, 'FOOD', 'Albatta Shokolad 100g', 'SKU-CHOC-006', '4607087101048', True),
            (sp2, 'HOME', "Tovoq to'plami", 'SKU-TP-007', '4901780198429', False),
            (sp2, 'TOYS', "Lego Creator 500 detal", 'SKU-LEG-008', '5702017424279', False),
        ]

        product_objs = []
        for sp, cat_code, name, sku, barcode, perishable in products_data:
            p, _ = Product.objects.get_or_create(
                seller=sp, sku=sku,
                defaults={
                    'category': cat_objs[cat_code],
                    'name': name,
                    'barcode': barcode,
                    'is_perishable': perishable,
                    'min_stock_limit': random.randint(5, 20),
                    'weight': decimal.Decimal(str(round(random.uniform(0.1, 2.0), 2))),
                }
            )
            product_objs.append(p)

        # Create warehouses
        wh1, _ = Warehouse.objects.get_or_create(
            code='WH-TAS-001',
            defaults={'name': 'Toshkent Asosiy Ombori', 'warehouse_type': 'FBW', 'address': 'Toshkent, Yunusobod tumani'}
        )
        wh2, _ = Warehouse.objects.get_or_create(
            code='WH-TAS-002',
            defaults={'name': 'Toshkent FBS Ombori', 'warehouse_type': 'FBS', 'address': 'Toshkent, Mirzo Ulugbek tumani'}
        )

        # Create storage locations
        locations = []
        for zone in ['A', 'B', 'C']:
            for rack in range(1, 4):
                for shelf in range(1, 4):
                    loc_barcode = f'{wh1.code}-{zone}-R{rack:02d}-S{shelf:02d}'
                    loc, _ = StorageLocation.objects.get_or_create(
                        barcode=loc_barcode,
                        defaults={
                            'warehouse': wh1,
                            'zone': zone,
                            'aisle': '1',
                            'rack': f'R{rack:02d}',
                            'shelf': f'S{shelf:02d}',
                            'position': '1',
                            'max_weight_capacity': decimal.Decimal('500.00'),
                        }
                    )
                    locations.append(loc)

        # Create inventory batches
        today = date.today()

        for i, product in enumerate(product_objs[:6]):
            batch_number = f'BATCH-{product.sku}-{today.strftime("%Y%m%d")}-001'
            location = locations[i % len(locations)]
            expiry = (today + timedelta(days=random.randint(30, 365))) if product.is_perishable else None

            InventoryBatch.objects.get_or_create(
                product=product,
                batch_number=batch_number,
                defaults={
                    'location': location,
                    'quantity_on_hand': random.randint(20, 100),
                    'quantity_reserved': 0,
                    'expiry_date': expiry,
                    'condition': 'available',
                }
            )

        # Create supplier
        sup, _ = Supplier.objects.get_or_create(
            name='Samsung Uzbekistan',
            defaults={
                'tax_number': '302345678',
                'contact_person': 'Kim Jong',
                'phone': '+998712345678',
                'address': 'Toshkent, Shayxontohur',
            }
        )

        # Create sample inbound shipment
        manager = User.objects.get(username='manager1')
        if not InboundShipment.objects.filter(shipment_number='SHP-20241001-001').exists():
            shipment = InboundShipment.objects.create(
                shipment_number='SHP-20241001-001',
                supplier=sup,
                warehouse=wh1,
                status='expected',
                expected_arrival=timezone.now() + timezone.timedelta(days=1),
                created_by=manager,
            )
            InboundItem.objects.create(
                shipment=shipment,
                product=product_objs[0],
                expected_quantity=50,
                received_quantity=0,
            )

        # Create sample order
        if not OutboundOrder.objects.filter(order_number='ORD-20241001-001').exists():
            order = OutboundOrder.objects.create(
                order_number='ORD-20241001-001',
                sales_model='FBW',
                seller=sp1,
                warehouse=wh1,
                status='created',
                priority='normal',
                destination='Samarqand, mijoz manzili',
                created_by=manager,
            )
            OrderItem.objects.create(
                order=order,
                product=product_objs[0],
                requested_quantity=3,
            )

        self.stdout.write(self.style.SUCCESS('Demo ma\'lumotlar muvaffaqiyatli yuklandi!'))
        self.stdout.write(self.style.SUCCESS('Login: admin / Admin1234!'))
        self.stdout.write(self.style.SUCCESS('Demo users password: Demo1234!'))
