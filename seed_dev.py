#!/usr/bin/env python
"""Quick seed script for dev SQLite database."""
import os
import sys
import decimal
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_dev')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import SellerProfile
from apps.catalog.models import Category, Product
from apps.warehouse.models import Warehouse, StorageLocation, InventoryBatch
from apps.logistics.models import Supplier, InboundShipment, InboundItem, OutboundOrder, OrderItem

User = get_user_model()

print("=== Demo ma'lumotlar yuklanmoqda ===")

# Admin
admin, created = User.objects.get_or_create(username='admin', defaults={
    'role': 'admin', 'first_name': 'Admin', 'last_name': 'User',
    'email': 'admin@wms.uz', 'is_staff': True, 'is_superuser': True
})
if created:
    admin.set_password('Admin1234!')
    admin.save()
    print("Admin yaratildi: admin / Admin1234!")
else:
    admin.role = 'admin'
    admin.save()
    print("Admin mavjud")

# Demo users
demo_users = [
    ('manager1', 'warehouse_manager', 'Alibek', 'Toshmatov'),
    ('receiver1', 'receiver', 'Bobur', 'Rahimov'),
    ('picker1', 'picker', 'Jasur', 'Karimov'),
    ('dispatcher1', 'dispatcher', 'Dilnoza', 'Yusupova'),
    ('returns1', 'returns_operator', 'Nodira', 'Hamidova'),
    ('seller1', 'seller', 'Sardor', 'Ergashev'),
    ('seller2', 'seller', 'Malika', 'Nazarova'),
]
for uname, role, fn, ln in demo_users:
    u, created = User.objects.get_or_create(username=uname, defaults={
        'role': role, 'first_name': fn, 'last_name': ln,
        'email': f'{uname}@wms.uz'
    })
    if created:
        u.set_password('Demo1234!')
        u.save()
print("Demo foydalanuvchilar yaratildi (parol: Demo1234!)")

# Seller profiles
sp1, _ = SellerProfile.objects.get_or_create(
    user=User.objects.get(username='seller1'),
    defaults={'seller_name': 'TechMart Store', 'seller_code': 'TMS001'}
)
sp2, _ = SellerProfile.objects.get_or_create(
    user=User.objects.get(username='seller2'),
    defaults={'seller_name': 'Fashion Hub', 'seller_code': 'FHS002'}
)

# Categories
cats = [('Elektronika', 'ELEC'), ('Kiyim', 'CLOTH'), ('Oziq-ovqat', 'FOOD'), ('Maishiy texnika', 'HOME')]
cat_objs = {}
for name, code in cats:
    c, _ = Category.objects.get_or_create(code=code, defaults={'name': name})
    cat_objs[code] = c
print(f"Kategoriyalar: {Category.objects.count()} ta")

# Products
prods_data = [
    (sp1, 'ELEC', 'Samsung Galaxy A55', 'SKU-SA55-001', '8801643845729', False),
    (sp1, 'ELEC', 'Apple AirPods Pro', 'SKU-APP-002', '194253376057', False),
    (sp1, 'ELEC', 'Xiaomi Redmi Note 13', 'SKU-XRN13-003', '6941812701232', False),
    (sp2, 'CLOTH', "Erkaklar ko'ylagi L", 'SKU-EKL-004', '4901780198405', False),
    (sp2, 'CLOTH', "Ayollar ko'ylagi M", 'SKU-AKM-005', '4901780198412', False),
    (sp1, 'FOOD', 'Shokolad 100g', 'SKU-CHOC-006', '4607087101048', True),
    (sp2, 'HOME', "Tovoq to'plami", 'SKU-TP-007', '4901780198429', False),
]
product_objs = []
for sp, cat_code, name, sku, barcode, perishable in prods_data:
    p, _ = Product.objects.get_or_create(seller=sp, sku=sku, defaults={
        'category': cat_objs[cat_code], 'name': name, 'barcode': barcode,
        'is_perishable': perishable, 'min_stock_limit': 10,
        'weight': decimal.Decimal('0.5'),
    })
    product_objs.append(p)
print(f"Mahsulotlar: {Product.objects.count()} ta")

# Warehouses
wh1, _ = Warehouse.objects.get_or_create(code='WH-TAS-001', defaults={
    'name': 'Toshkent Asosiy Ombori', 'warehouse_type': 'FBW', 'address': 'Toshkent, Yunusobod'
})
wh2, _ = Warehouse.objects.get_or_create(code='WH-TAS-002', defaults={
    'name': 'Toshkent FBS Ombori', 'warehouse_type': 'FBS', 'address': 'Toshkent, Mirzo Ulugbek'
})

# Storage Locations
locations = []
for zone in ['A', 'B', 'C']:
    for rack in range(1, 4):
        for shelf in range(1, 4):
            barcode = f'{wh1.code}-{zone}-R{rack:02d}-S{shelf:02d}'
            loc, _ = StorageLocation.objects.get_or_create(barcode=barcode, defaults={
                'warehouse': wh1, 'zone': zone, 'aisle': '1',
                'rack': f'R{rack:02d}', 'shelf': f'S{shelf:02d}', 'position': '1',
                'max_weight_capacity': decimal.Decimal('500')
            })
            locations.append(loc)
print(f"Saqlash joylari: {StorageLocation.objects.count()} ta")

# Inventory Batches
today = date.today()
for i, product in enumerate(product_objs):
    bn = f'BATCH-{product.sku}-{today.strftime("%Y%m%d")}'
    loc = locations[i % len(locations)]
    expiry = (today + timedelta(days=60)) if product.is_perishable else None
    InventoryBatch.objects.get_or_create(product=product, batch_number=bn, defaults={
        'location': loc, 'quantity_on_hand': random.randint(30, 100),
        'quantity_reserved': 0, 'received_at': timezone.now(),
        'expiry_date': expiry, 'condition': 'available'
    })
    # Add second batch for some
    if i < 3:
        bn2 = f'BATCH-{product.sku}-{today.strftime("%Y%m%d")}-B'
        loc2 = locations[(i + 3) % len(locations)]
        InventoryBatch.objects.get_or_create(product=product, batch_number=bn2, defaults={
            'location': loc2, 'quantity_on_hand': random.randint(10, 50),
            'quantity_reserved': 0, 'received_at': timezone.now() - timezone.timedelta(days=30),
            'condition': 'available'
        })
print(f"Inventar partiyalari: {InventoryBatch.objects.count()} ta")

# Supplier
sup, _ = Supplier.objects.get_or_create(name='Samsung Uzbekistan', defaults={
    'tax_number': '302345678', 'contact_person': 'Kim Jong',
    'phone': '+998712345678', 'address': 'Toshkent'
})

# Sample inbound shipment
manager = User.objects.get(username='manager1')
if not InboundShipment.objects.filter(shipment_number='SHP-20241101-001').exists():
    shipment = InboundShipment.objects.create(
        shipment_number='SHP-20241101-001', supplier=sup, warehouse=wh1,
        status='expected',
        expected_arrival=timezone.now() + timezone.timedelta(days=2),
        created_by=manager,
    )
    InboundItem.objects.create(
        shipment=shipment, product=product_objs[0],
        expected_quantity=50, received_quantity=0,
        batch_number='BATCH-INCOMING-001', target_location=locations[0]
    )

# Sample order
if not OutboundOrder.objects.filter(order_number='ORD-20241101-001').exists():
    order = OutboundOrder.objects.create(
        order_number='ORD-20241101-001', sales_model='FBW', seller=sp1,
        warehouse=wh1, status='created', priority='normal',
        destination='Samarqand shahar, Registon ko\'chasi 5',
        created_by=manager,
    )
    OrderItem.objects.create(order=order, product=product_objs[0], requested_quantity=5)
    OrderItem.objects.create(order=order, product=product_objs[1], requested_quantity=2)

print("\n=== Muvaffaqiyatli yuklandi! ===")
print("Login: admin / Admin1234!")
print("Demo users: manager1, receiver1, picker1, dispatcher1, seller1, seller2")
print("Parol: Demo1234!")
print("\nSayt: http://127.0.0.1:8000")
