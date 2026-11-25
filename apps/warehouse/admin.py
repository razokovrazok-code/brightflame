from django.contrib import admin
from .models import Warehouse, StorageLocation, InventoryBatch, StockMovement


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'warehouse_type', 'is_active', 'created_at')
    list_filter = ('warehouse_type', 'is_active')
    search_fields = ('name', 'code', 'address')
    ordering = ('name',)


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ('barcode', 'warehouse', 'zone', 'aisle', 'rack', 'shelf', 'position', 'is_active')
    list_filter = ('warehouse', 'zone', 'is_active')
    search_fields = ('barcode', 'zone', 'aisle', 'rack', 'shelf', 'position')
    list_select_related = ('warehouse',)
    ordering = ('warehouse', 'zone', 'aisle', 'rack', 'shelf', 'position')


@admin.register(InventoryBatch)
class InventoryBatchAdmin(admin.ModelAdmin):
    list_display = (
        'batch_number',
        'product',
        'location',
        'quantity_on_hand',
        'quantity_reserved',
        'available_quantity',
        'condition',
        'expiry_date',
        'received_at'
    )
    list_filter = ('condition', 'location__warehouse', 'expiry_date')
    search_fields = ('batch_number', 'product__name', 'product__sku', 'location__barcode')
    list_select_related = ('product', 'location', 'location__warehouse')
    readonly_fields = ('received_at', 'available_quantity')

    @admin.display(description='Mavjud miqdor')
    def available_quantity(self, obj):
        return obj.available_quantity


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'idempotency_key',
        'movement_type',
        'product',
        'quantity',
        'from_location',
        'to_location',
        'reference',
        'performed_by',
        'created_at'
    )
    list_filter = ('movement_type', 'created_at')
    search_fields = ('reference', 'idempotency_key', 'product__name', 'product__sku')
    list_select_related = ('product', 'from_location', 'to_location', 'performed_by')
    readonly_fields = ('idempotency_key', 'created_at')
