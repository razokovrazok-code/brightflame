import uuid
from django.db import models
from django.core.exceptions import ValidationError
from apps.catalog.models import Product
from apps.accounts.models import User


class Warehouse(models.Model):
    TYPE_CHOICES = [
        ('FBW', 'Fulfillment by WMS (FBW)'),
        ('FBS', 'Fulfillment by Seller (FBS)'),
    ]
    code = models.CharField(max_length=50, unique=True, verbose_name='Kodi')
    name = models.CharField(max_length=200, verbose_name='Nomi')
    address = models.TextField(verbose_name='Manzili')
    warehouse_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default='FBW', verbose_name='Ombor turi'
    )
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ombor'
        verbose_name_plural = 'Omborlar'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class StorageLocation(models.Model):
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE,
        related_name='locations', verbose_name='Ombor'
    )
    zone = models.CharField(max_length=20, verbose_name='Zona')
    aisle = models.CharField(max_length=20, verbose_name='Yo\'lak')
    rack = models.CharField(max_length=20, verbose_name='Stellaj')
    shelf = models.CharField(max_length=20, verbose_name='Javon')
    position = models.CharField(max_length=20, verbose_name='Pozitsiya')
    barcode = models.CharField(max_length=100, unique=True, verbose_name='Shtrix-kod')
    max_weight_capacity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name='Maksimal yuklanish (kg)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Saqlash joyi'
        verbose_name_plural = 'Saqlash joylari'
        ordering = ['warehouse', 'zone', 'aisle', 'rack', 'shelf', 'position']

    def __str__(self):
        return f'{self.warehouse.code}-{self.zone}-{self.rack}-{self.shelf}-{self.position}'

    def get_display_name(self):
        return f'Zona {self.zone}, Stell. {self.rack}, Jav. {self.shelf}, Poz. {self.position}'


class InventoryBatch(models.Model):
    CONDITION_CHOICES = [
        ('available', 'Mavjud'),
        ('reserved', 'Band'),
        ('damaged', 'Shikastlangan'),
        ('quarantine', 'Karantin'),
        ('expired', 'Muddati o\'tgan'),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name='inventory_batches', verbose_name='Mahsulot'
    )
    location = models.ForeignKey(
        StorageLocation, on_delete=models.PROTECT,
        related_name='batches', verbose_name='Joylashuvi'
    )
    batch_number = models.CharField(max_length=100, verbose_name='Partiya raqami')
    quantity_on_hand = models.PositiveIntegerField(default=0, verbose_name='Qo\'ldagi miqdor')
    quantity_reserved = models.PositiveIntegerField(default=0, verbose_name='Band miqdor')
    manufacture_date = models.DateField(null=True, blank=True, verbose_name='Ishlab chiqarilgan sana')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='Yaroqlilik muddati')
    received_at = models.DateTimeField(verbose_name='Qabul qilingan vaqt')
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, default='available', verbose_name='Holati'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventar partiyasi'
        verbose_name_plural = 'Inventar partiyalari'
        ordering = ['product', 'received_at']
        indexes = [
            models.Index(fields=['product', 'condition']),
            models.Index(fields=['location']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['batch_number']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity_on_hand__gte=0),
                name='inventory_batch_quantity_on_hand_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(quantity_reserved__gte=0),
                name='inventory_batch_quantity_reserved_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(quantity_reserved__lte=models.F('quantity_on_hand')),
                name='inventory_batch_reserved_lte_on_hand'
            ),
        ]

    def __str__(self):
        return f'{self.product.name} - {self.batch_number} ({self.quantity_on_hand})'

    @property
    def available_quantity(self):
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    def clean(self):
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValidationError(
                'Band miqdor qo\'ldagi miqdordan ko\'p bo\'lishi mumkin emas.'
            )


class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('inbound', 'Kirim'),
        ('outbound', 'Chiqim'),
        ('transfer', 'Ko\'chirish'),
        ('adjustment', 'Tuzatish'),
        ('return', 'Qaytarish'),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT,
        related_name='stock_movements', verbose_name='Mahsulot'
    )
    batch = models.ForeignKey(
        InventoryBatch, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movements', verbose_name='Partiya'
    )
    from_location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movements_from', verbose_name='Kimdan'
    )
    to_location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movements_to', verbose_name='Kimga'
    )
    quantity = models.PositiveIntegerField(verbose_name='Miqdor')
    movement_type = models.CharField(
        max_length=20, choices=MOVEMENT_TYPE_CHOICES, verbose_name='Harakat turi'
    )
    reference = models.CharField(max_length=200, blank=True, verbose_name='Havola')
    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stock_movements', verbose_name='Bajaruvchi'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.CharField(
        max_length=100, unique=True,
        default=uuid.uuid4,
        verbose_name='Idempotentlik kaliti'
    )

    class Meta:
        verbose_name = 'Zaxira harakati'
        verbose_name_plural = 'Zaxira harakatlari'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'movement_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['reference']),
        ]

    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.product.name} x{self.quantity}'
