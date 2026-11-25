from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'barcode', 'seller', 'category', 'unit', 'is_active', 'created_at')
    list_filter = ('is_active', 'unit', 'seller', 'category')
    search_fields = ('name', 'sku', 'barcode', 'wb_article', 'nm_id', 'brand')
    list_select_related = ('seller', 'category')
    ordering = ('name',)
