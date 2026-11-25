from django.contrib import admin
from .models import (
    Supplier, InboundShipment, InboundItem,
    OutboundOrder, OrderItem, StockAllocation,
    Package, ReturnRecord
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_number', 'contact_person', 'phone', 'is_active')
    search_fields = ('name', 'tax_number', 'contact_person')
    list_filter = ('is_active',)


class InboundItemInline(admin.TabularInline):
    model = InboundItem
    extra = 0
    raw_id_fields = ('product', 'target_location')


@admin.register(InboundShipment)
class InboundShipmentAdmin(admin.ModelAdmin):
    list_display = ('shipment_number', 'warehouse', 'supplier', 'status', 'expected_arrival', 'created_at')
    list_filter = ('status', 'warehouse')
    search_fields = ('shipment_number',)
    raw_id_fields = ('supplier', 'seller', 'warehouse', 'receiver', 'created_by')
    inlines = [InboundItemInline]
    readonly_fields = ('created_at', 'updated_at')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ('product',)


@admin.register(OutboundOrder)
class OutboundOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'seller', 'warehouse', 'sales_model',
        'status', 'priority', 'created_at'
    )
    list_filter = ('status', 'sales_model', 'priority', 'warehouse')
    search_fields = ('order_number', 'destination')
    raw_id_fields = ('seller', 'warehouse', 'assigned_picker', 'created_by')
    inlines = [OrderItemInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StockAllocation)
class StockAllocationAdmin(admin.ModelAdmin):
    list_display = ('order_item', 'inventory_batch', 'reserved_quantity', 'picked_quantity')
    raw_id_fields = ('order_item', 'inventory_batch')


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('package_number', 'order', 'status', 'packed_at', 'shipped_at')
    list_filter = ('status',)
    search_fields = ('package_number', 'barcode')


@admin.register(ReturnRecord)
class ReturnRecordAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'condition', 'disposition', 'processed', 'created_at')
    list_filter = ('condition', 'disposition', 'processed')
    search_fields = ('product__name', 'reason')
    raw_id_fields = ('original_order', 'product', 'received_by')
    readonly_fields = ('created_at', 'idempotency_key')
