import csv
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Q, F
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from apps.accounts.views import RoleRequiredMixin
from apps.catalog.models import Product
from .models import Warehouse, StorageLocation, InventoryBatch, StockMovement
from .forms import WarehouseForm, StorageLocationForm, InventoryBatchForm


class WarehouseListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'dispatcher']
    model = Warehouse
    template_name = 'warehouse/warehouse_list.html'
    context_object_name = 'warehouses'
    paginate_by = 20

    def get_queryset(self):
        qs = Warehouse.objects.all().order_by('name')
        q = self.request.GET.get('q', '').strip()
        is_active = self.request.GET.get('is_active', '').strip()
        wh_type = self.request.GET.get('type', '').strip()

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(address__icontains=q))
        if wh_type:
            qs = qs.filter(warehouse_type=wh_type)
        if is_active in ['true', '1']:
            qs = qs.filter(is_active=True)
        elif is_active in ['false', '0']:
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['selected_active'] = self.request.GET.get('is_active', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['warehouse_types'] = Warehouse.TYPE_CHOICES
        return context


class WarehouseCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['warehouse_manager', 'admin']
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'warehouse/warehouse_form.html'
    success_url = reverse_lazy('warehouse:warehouse_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Ombor '{self.object.name}' muvaffaqiyatli yaratildi.")
        return response


class WarehouseUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['warehouse_manager', 'admin']
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'warehouse/warehouse_form.html'
    success_url = reverse_lazy('warehouse:warehouse_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Ombor '{self.object.name}' muvaffaqiyatli yangilandi.")
        return response


class WarehouseDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'dispatcher']
    model = Warehouse
    template_name = 'warehouse/warehouse_detail.html'
    context_object_name = 'warehouse'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        locations = self.object.locations.all()
        batches = InventoryBatch.objects.filter(location__warehouse=self.object)

        total_units = batches.aggregate(total=Sum('quantity_on_hand'))['total'] or 0
        total_reserved = batches.aggregate(total=Sum('quantity_reserved'))['total'] or 0

        context['locations_count'] = locations.count()
        context['batches_count'] = batches.count()
        context['total_units'] = total_units
        context['total_reserved'] = total_reserved
        context['available_units'] = total_units - total_reserved
        context['zones'] = locations.values_list('zone', flat=True).distinct().order_by('zone')
        return context


class StorageLocationListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'picker', 'dispatcher']
    model = StorageLocation
    template_name = 'warehouse/location_list.html'
    context_object_name = 'locations'
    paginate_by = 30

    def get_queryset(self):
        qs = StorageLocation.objects.select_related('warehouse').all()
        wh_id = self.request.GET.get('warehouse', '').strip()
        zone = self.request.GET.get('zone', '').strip()
        q = self.request.GET.get('q', '').strip()
        is_active = self.request.GET.get('is_active', '').strip()

        if wh_id:
            qs = qs.filter(warehouse_id=wh_id)
        if zone:
            qs = qs.filter(zone__iexact=zone)
        if q:
            qs = qs.filter(
                Q(barcode__icontains=q) |
                Q(zone__icontains=q) |
                Q(aisle__icontains=q) |
                Q(rack__icontains=q) |
                Q(shelf__icontains=q) |
                Q(position__icontains=q)
            )
        if is_active in ['true', '1']:
            qs = qs.filter(is_active=True)
        elif is_active in ['false', '0']:
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouses'] = Warehouse.objects.filter(is_active=True).order_by('name')
        context['selected_warehouse'] = self.request.GET.get('warehouse', '')
        context['selected_zone'] = self.request.GET.get('zone', '')
        context['selected_active'] = self.request.GET.get('is_active', '')
        context['q'] = self.request.GET.get('q', '')

        if context['selected_warehouse']:
            context['zones'] = StorageLocation.objects.filter(
                warehouse_id=context['selected_warehouse']
            ).values_list('zone', flat=True).distinct().order_by('zone')
        else:
            context['zones'] = StorageLocation.objects.values_list('zone', flat=True).distinct().order_by('zone')

        return context


class StorageLocationCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['warehouse_manager', 'admin']
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'warehouse/location_form.html'
    success_url = reverse_lazy('warehouse:location_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Saqlash joyi '{self.object.barcode}' muvaffaqiyatli yaratildi.")
        return response


class StorageLocationUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['warehouse_manager', 'admin']
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'warehouse/location_form.html'
    success_url = reverse_lazy('warehouse:location_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Saqlash joyi '{self.object.barcode}' muvaffaqiyatli yangilandi.")
        return response


class InventoryBatchListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'picker', 'dispatcher', 'returns_operator', 'seller']
    model = InventoryBatch
    template_name = 'warehouse/inventory_list.html'
    context_object_name = 'batches'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = InventoryBatch.objects.select_related(
            'product', 'product__category', 'product__seller', 'location', 'location__warehouse'
        ).all().order_by('-received_at')

        # Seller isolation
        if user.role == 'seller':
            if hasattr(user, 'seller_profile'):
                qs = qs.filter(product__seller=user.seller_profile)
            else:
                qs = qs.none()

        q = self.request.GET.get('q', '').strip()
        product_id = self.request.GET.get('product', '').strip()
        location_id = self.request.GET.get('location', '').strip()
        warehouse_id = self.request.GET.get('warehouse', '').strip()
        condition = self.request.GET.get('condition', '').strip()

        if q:
            qs = qs.filter(
                Q(batch_number__icontains=q) |
                Q(product__name__icontains=q) |
                Q(product__sku__icontains=q) |
                Q(product__barcode__icontains=q) |
                Q(location__barcode__icontains=q)
            )
        if product_id:
            qs = qs.filter(product_id=product_id)
        if location_id:
            qs = qs.filter(location_id=location_id)
        if warehouse_id:
            qs = qs.filter(location__warehouse_id=warehouse_id)
        if condition:
            qs = qs.filter(condition=condition)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['selected_product'] = self.request.GET.get('product', '')
        context['selected_location'] = self.request.GET.get('location', '')
        context['selected_warehouse'] = self.request.GET.get('warehouse', '')
        context['selected_condition'] = self.request.GET.get('condition', '')
        context['condition_choices'] = InventoryBatch.CONDITION_CHOICES
        context['warehouses'] = Warehouse.objects.filter(is_active=True).order_by('name')
        return context


class InventoryBatchDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'picker', 'dispatcher', 'returns_operator', 'seller']
    model = InventoryBatch
    template_name = 'warehouse/inventory_detail.html'
    context_object_name = 'batch'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.role == 'seller':
            if not hasattr(user, 'seller_profile') or obj.product.seller != user.seller_profile:
                raise PermissionDenied("Siz faqat o'zingizning tovarlaringiz partiyalarini ko'ra olasiz.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['movements'] = self.object.movements.select_related(
            'performed_by', 'from_location', 'to_location'
        ).order_by('-created_at')[:50]
        return context


class StockMovementListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'picker', 'dispatcher', 'returns_operator', 'seller']
    model = StockMovement
    template_name = 'warehouse/movement_list.html'
    context_object_name = 'movements'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = StockMovement.objects.select_related(
            'product', 'batch', 'from_location', 'to_location', 'performed_by'
        ).all().order_by('-created_at')

        # Seller isolation
        if user.role == 'seller':
            if hasattr(user, 'seller_profile'):
                qs = qs.filter(product__seller=user.seller_profile)
            else:
                qs = qs.none()

        movement_type = self.request.GET.get('movement_type', '').strip()
        product_id = self.request.GET.get('product', '').strip()
        start_date = self.request.GET.get('start_date', '').strip()
        end_date = self.request.GET.get('end_date', '').strip()
        q = self.request.GET.get('q', '').strip()

        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        if product_id:
            qs = qs.filter(product_id=product_id)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        if q:
            qs = qs.filter(
                Q(reference__icontains=q) |
                Q(product__name__icontains=q) |
                Q(product__sku__icontains=q) |
                Q(batch__batch_number__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['selected_type'] = self.request.GET.get('movement_type', '')
        context['selected_product'] = self.request.GET.get('product', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['movement_types'] = StockMovement.MOVEMENT_TYPE_CHOICES
        return context


@login_required
def inventory_summary_view(request):
    """Summary of stock by product and warehouse with CSV export option."""
    user = request.user
    role = getattr(user, 'role', '')

    batches = InventoryBatch.objects.select_related('product', 'location__warehouse', 'product__category')

    if role == 'seller':
        if hasattr(user, 'seller_profile'):
            batches = batches.filter(product__seller=user.seller_profile)
        else:
            batches = batches.none()

    warehouse_id = request.GET.get('warehouse', '').strip()
    category_id = request.GET.get('category', '').strip()
    q = request.GET.get('q', '').strip()

    if warehouse_id:
        batches = batches.filter(location__warehouse_id=warehouse_id)
    if category_id:
        batches = batches.filter(product__category_id=category_id)
    if q:
        batches = batches.filter(
            Q(product__name__icontains=q) |
            Q(product__sku__icontains=q) |
            Q(product__barcode__icontains=q)
        )

    # Group summary by product and warehouse
    summary = (
        batches.values(
            'product_id',
            'product__name',
            'product__sku',
            'product__barcode',
            'product__category__name',
            'location__warehouse_id',
            'location__warehouse__name',
            'location__warehouse__code',
        )
        .annotate(
            total_on_hand=Sum('quantity_on_hand'),
            total_reserved=Sum('quantity_reserved'),
        )
        .order_by('product__name')
    )

    # Calculate available stock for each line
    summary_data = []
    for item in summary:
        on_hand = item['total_on_hand'] or 0
        reserved = item['total_reserved'] or 0
        avail = on_hand - reserved
        item['available_quantity'] = avail
        summary_data.append(item)

    # Handle CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f"inventory_summary_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['SKU', 'Mahsulot nomi', 'Shtrix-kod', 'Kategoriya', 'Ombor kodi', 'Ombor nomi', 'Jami qoldiq', 'Band qilingan', 'Mavjud qoldiq'])

        for row in summary_data:
            writer.writerow([
                row['product__sku'],
                row['product__name'],
                row['product__barcode'],
                row['product__category__name'] or '',
                row['location__warehouse__code'],
                row['location__warehouse__name'],
                row['total_on_hand'],
                row['total_reserved'],
                row['available_quantity']
            ])

        return response

    context = {
        'summary_data': summary_data,
        'warehouses': Warehouse.objects.filter(is_active=True).order_by('name'),
        'selected_warehouse': warehouse_id,
        'selected_category': category_id,
        'q': q,
    }
    return render(request, 'warehouse/inventory_summary.html', context)
