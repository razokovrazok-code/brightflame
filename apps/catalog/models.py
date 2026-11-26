from django.db import models
from apps.accounts.models import SellerProfile


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nomi')
    code = models.CharField(max_length=50, unique=True, verbose_name='Kodi')
    description = models.TextField(blank=True, verbose_name='Tavsif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class Product(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Dona'),
        ('kg', 'Kilogramm'),
        ('g', 'Gramm'),
        ('l', 'Litr'),
        ('m', 'Metr'),
        ('box', 'Quti'),
        ('pack', 'Paket'),
    ]

    seller = models.ForeignKey(
        SellerProfile, on_delete=models.PROTECT,
        related_name='products', verbose_name='Sotuvchi'
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='products', verbose_name='Kategoriya'
    )
    name = models.CharField(max_length=300, verbose_name='Nomi')
    sku = models.CharField(max_length=100, verbose_name='SKU')
    barcode = models.CharField(max_length=100, verbose_name='Shtrix-kod')
    wb_article = models.CharField(max_length=100, blank=True, verbose_name='WB maqola')
    nm_id = models.CharField(max_length=50, blank=True, verbose_name='NM ID')
    brand = models.CharField(max_length=100, blank=True, verbose_name='Brend')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pcs', verbose_name='O\'lchov birligi')
    size = models.CharField(max_length=50, blank=True, verbose_name='O\'lchami')
    color = models.CharField(max_length=50, blank=True, verbose_name='Rangi')
    weight = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='Vazni (kg)'
    )
    length = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Uzunligi (sm)'
    )
    width = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Kengligi (sm)'
    )
    height = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Balandligi (sm)'
    )
    # Productionda Amazon S3'da saqlanadi (settings.STORAGES['default'])
    image = models.ImageField(upload_to='products/%Y/%m/', blank=True, verbose_name='Rasm')
    min_stock_limit = models.PositiveIntegerField(default=0, verbose_name='Minimal zaxira')
    is_perishable = models.BooleanField(default=False, verbose_name='Muddat nazorati')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        unique_together = [
            ['seller', 'sku'],
            ['seller', 'barcode'],
        ]
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['seller', 'is_active']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def get_total_stock(self):
        from apps.warehouse.models import InventoryBatch
        from django.db.models import Sum
        result = InventoryBatch.objects.filter(
            product=self, condition='available'
        ).aggregate(total=Sum('quantity_on_hand'))
        return result['total'] or 0

    def get_available_stock(self):
        from apps.warehouse.models import InventoryBatch
        batches = InventoryBatch.objects.filter(product=self, condition='available')
        total = sum(b.quantity_on_hand - b.quantity_reserved for b in batches)
        return max(0, total)
