import uuid
from django.db import models
from apps.catalog.models import Product
from apps.accounts.models import User, SellerProfile
from apps.warehouse.models import Warehouse, StorageLocation


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nomi')
    tax_number = models.CharField(max_length=50, blank=True, verbose_name='INN/STIR')
    contact_person = models.CharField(max_length=100, blank=True, verbose_name='Aloqa shaxsi')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefon')
    address = models.TextField(blank=True, verbose_name='Manzil')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Yetkazib beruvchi'
        verbose_name_plural = 'Yetkazib beruvchilar'
        ordering = ['name']

    def __str__(self):
        return self.name


class InboundShipment(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Qoralama'),
        ('expected', 'Kutilmoqda'),
        ('arrived', 'Yetib keldi'),
        ('receiving', 'Qabul qilinmoqda'),
        ('received', 'Qabul qilindi'),
        ('putaway', 'Joylashtirilyapti'),
        ('completed', 'Yakunlandi'),
        ('cancelled', 'Bekor qilindi'),
    ]

    shipment_number = models.CharField(max_length=100, unique=True, verbose_name='Yetkazma raqami')
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shipments', verbose_name='Yetkazib beruvchi'
    )
    seller = models.ForeignKey(
        SellerProfile, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='inbound_shipments', verbose_name='Sotuvchi'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT,
        related_name='inbound_shipments', verbose_name='Ombor'
    )
    receiver = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='received_shipments', verbose_name='Qabul qiluvchi'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Holati'
    )
    expected_arrival = models.DateTimeField(null=True, blank=True, verbose_name='Kutilayotgan vaqt')
    arrived_at = models.DateTimeField(null=True, blank=True, verbose_name='Yetib kelgan vaqt')
    received_at = models.DateTimeField(null=True, blank=True, verbose_name='Qabul qilingan vaqt')
    notes = models.TextField(blank=True, verbose_name='Izohlar')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_shipments', verbose_name='Yaratuvchi'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kirim yetkazmasi'
        verbose_name_plural = 'Kirim yetkazmalari'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['warehouse']),
        ]

    def __str__(self):
        return f'{self.shipment_number} ({self.get_status_display()})'

    def get_total_expected(self):
        return sum(item.expected_quantity for item in self.items.all())

    def get_total_received(self):
        return sum(item.received_quantity for item in self.items.all())


class InboundItem(models.Model):
    shipment = models.ForeignKey(
        InboundShipment, on_delete=models.CASCADE,
        related_name='items', verbose_name='Yetkazma'
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name='inbound_items', verbose_name='Mahsulot'
    )
    expected_quantity = models.PositiveIntegerField(verbose_name='Kutilgan miqdor')
    received_quantity = models.PositiveIntegerField(default=0, verbose_name='Qabul qilingan miqdor')
    damaged_quantity = models.PositiveIntegerField(default=0, verbose_name='Shikastlangan miqdor')
    batch_number = models.CharField(max_length=100, blank=True, verbose_name='Partiya raqami')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='Yaroqlilik muddati')
    target_location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='inbound_items', verbose_name='Maqsad joyi'
    )

    class Meta:
        verbose_name = 'Kirim elementi'
        verbose_name_plural = 'Kirim elementlari'
        constraints = [
            models.CheckConstraint(
                check=models.Q(received_quantity__gte=0),
                name='inbound_item_received_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(damaged_quantity__gte=0),
                name='inbound_item_damaged_gte_0'
            ),
        ]

    def __str__(self):
        return f'{self.product.name} ({self.received_quantity}/{self.expected_quantity})'

    @property
    def missing_quantity(self):
        return max(0, self.expected_quantity - self.received_quantity - self.damaged_quantity)


class OutboundOrder(models.Model):
    STATUS_CHOICES = [
        ('created', 'Yaratildi'),
        ('allocated', 'Ajratildi'),
        ('picking', "Yig'ilmoqda"),
        ('picked', "Yig'ildi"),
        ('packed', 'Qadoqlandi'),
        ('shipped', "Jo'natildi"),
        ('completed', 'Yakunlandi'),
        ('needs_stock', 'Zaxira kerak'),
        ('cancelled', 'Bekor qilindi'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Past'),
        ('normal', 'Oddiy'),
        ('high', 'Yuqori'),
        ('urgent', 'Shoshilinch'),
    ]
    SALES_MODEL_CHOICES = [
        ('FBW', 'FBW'),
        ('FBS', 'FBS'),
    ]

    order_number = models.CharField(max_length=100, unique=True, verbose_name='Buyurtma raqami')
    sales_model = models.CharField(
        max_length=10, choices=SALES_MODEL_CHOICES, default='FBW', verbose_name='Savdo modeli'
    )
    seller = models.ForeignKey(
        SellerProfile, on_delete=models.PROTECT,
        related_name='orders', verbose_name='Sotuvchi'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT,
        related_name='orders', verbose_name='Ombor'
    )
    assigned_picker = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_orders', verbose_name='Tayinlangan yig\'uvchi'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Holati'
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='normal', verbose_name='Ustuvorlik'
    )
    destination = models.CharField(max_length=500, verbose_name='Manzil')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_orders', verbose_name='Yaratuvchi'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Muddat')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Chiqim buyurtmasi'
        verbose_name_plural = 'Chiqim buyurtmalari'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['seller']),
            models.Index(fields=['created_at']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f'{self.order_number} ({self.get_status_display()})'

    def is_cancellable(self):
        return self.status not in ('shipped', 'completed', 'cancelled')

    def get_picking_progress(self):
        items = self.items.all()
        if not items:
            return 0
        picked = sum(1 for i in items if i.is_picked)
        return int(picked / len(items) * 100)


class OrderItem(models.Model):
    order = models.ForeignKey(
        OutboundOrder, on_delete=models.CASCADE,
        related_name='items', verbose_name='Buyurtma'
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name='order_items', verbose_name='Mahsulot'
    )
    requested_quantity = models.PositiveIntegerField(verbose_name='So\'ralgan miqdor')
    picked_quantity = models.PositiveIntegerField(default=0, verbose_name='Yig\'ilgan miqdor')
    is_picked = models.BooleanField(default=False, verbose_name="Yig'ildi")

    class Meta:
        verbose_name = 'Buyurtma elementi'
        verbose_name_plural = 'Buyurtma elementlari'
        constraints = [
            models.CheckConstraint(
                check=models.Q(requested_quantity__gt=0),
                name='order_item_requested_quantity_gt_0'
            ),
            models.CheckConstraint(
                check=models.Q(picked_quantity__gte=0),
                name='order_item_picked_quantity_gte_0'
            ),
        ]

    def __str__(self):
        return f'{self.product.name} x{self.requested_quantity}'

    def get_allocated_quantity(self):
        return self.allocations.aggregate(
            total=models.Sum('reserved_quantity')
        )['total'] or 0


class StockAllocation(models.Model):
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE,
        related_name='allocations', verbose_name='Buyurtma elementi'
    )
    inventory_batch = models.ForeignKey(
        'warehouse.InventoryBatch', on_delete=models.PROTECT,
        related_name='allocations', verbose_name='Inventar partiyasi'
    )
    reserved_quantity = models.PositiveIntegerField(verbose_name='Band miqdor')
    picked_quantity = models.PositiveIntegerField(default=0, verbose_name="Yig'ilgan miqdor")

    class Meta:
        verbose_name = 'Zaxira ajratma'
        verbose_name_plural = 'Zaxira ajratmalar'
        unique_together = [['order_item', 'inventory_batch']]

    def __str__(self):
        return f'{self.order_item} -> {self.inventory_batch.batch_number} x{self.reserved_quantity}'

    @property
    def remaining_to_pick(self):
        return self.reserved_quantity - self.picked_quantity


class Package(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('packed', 'Qadoqlandi'),
        ('shipped', "Jo'natildi"),
    ]

    package_number = models.CharField(max_length=100, unique=True, verbose_name='Qadoq raqami')
    order = models.ForeignKey(
        OutboundOrder, on_delete=models.CASCADE,
        related_name='packages', verbose_name='Buyurtma'
    )
    barcode = models.CharField(max_length=100, verbose_name='Shtrix-kod')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Holati'
    )
    packed_at = models.DateTimeField(null=True, blank=True, verbose_name='Qadoqlangan vaqt')
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name="Jo'natilgan vaqt")
    destination = models.CharField(max_length=500, verbose_name='Manzil')
    notes = models.TextField(blank=True, verbose_name='Izohlar')

    class Meta:
        verbose_name = 'Qadoq'
        verbose_name_plural = 'Qadoqlar'
        ordering = ['-packed_at']

    def __str__(self):
        return f'{self.package_number} ({self.get_status_display()})'


class ReturnRecord(models.Model):
    CONDITION_CHOICES = [
        ('sellable', 'Sotishga yaroqli'),
        ('damaged', 'Shikastlangan'),
        ('quarantine', 'Karantin'),
    ]
    DISPOSITION_CHOICES = [
        ('restock', 'Zaxiraga qaytarish'),
        ('dispose', 'Utilizatsiya'),
        ('quarantine', 'Karantinga'),
    ]

    original_order = models.ForeignKey(
        OutboundOrder, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='returns', verbose_name='Asl buyurtma'
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name='returns', verbose_name='Mahsulot'
    )
    quantity = models.PositiveIntegerField(verbose_name='Miqdor')
    reason = models.CharField(max_length=500, verbose_name='Sabab')
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, verbose_name='Holati'
    )
    disposition = models.CharField(
        max_length=20, choices=DISPOSITION_CHOICES, default='restock', verbose_name='Chora'
    )
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='received_returns', verbose_name='Qabul qiluvchi'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False, verbose_name='Qayta ishlandi')
    idempotency_key = models.CharField(
        max_length=100, unique=True,
        default=uuid.uuid4,
        verbose_name='Idempotentlik kaliti'
    )

    class Meta:
        verbose_name = 'Qaytarish'
        verbose_name_plural = 'Qaytarishlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'Qaytarish: {self.product.name} x{self.quantity} ({self.get_condition_display()})'
