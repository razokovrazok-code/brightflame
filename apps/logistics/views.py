import csv
import uuid
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from apps.accounts.views import RoleRequiredMixin
from apps.accounts.models import User
from apps.warehouse.services import (
    allocate_stock, process_return, cancel_order, process_pick,
    receive_inbound_item, ALREADY_DONE_MESSAGES,
)
from .models import (
    Supplier, InboundShipment, InboundItem,
    OutboundOrder, StockAllocation,
    Package, ReturnRecord
)
from .forms import (
    InboundShipmentForm, InboundItemForm,
    OutboundOrderForm, OrderItemForm, ReturnRecordForm
)


# ── Suppliers ──────────────────────────────────────────────────────────────────

class SupplierListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver']
    model = Supplier
    template_name = 'logistics/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20

    def get_queryset(self):
        qs = Supplier.objects.all().order_by('name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(tax_number__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class SupplierCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'warehouse_manager']
    model = Supplier
    fields = ['name', 'tax_number', 'contact_person', 'phone', 'address']
    template_name = 'logistics/supplier_form.html'
    success_url = reverse_lazy('logistics:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, "Yetkazib beruvchi muvaffaqiyatli yaratildi.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Yangi yetkazib beruvchi'
        ctx['action'] = 'Yaratish'
        return ctx


class SupplierUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['admin', 'warehouse_manager']
    model = Supplier
    fields = ['name', 'tax_number', 'contact_person', 'phone', 'address', 'is_active']
    template_name = 'logistics/supplier_form.html'
    success_url = reverse_lazy('logistics:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, "Yetkazib beruvchi muvaffaqiyatli yangilandi.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Yetkazib beruvchini tahrirlash'
        ctx['action'] = 'Saqlash'
        return ctx


# ── Inbound Shipments ──────────────────────────────────────────────────────────

class InboundShipmentListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver']
    model = InboundShipment
    template_name = 'logistics/inbound_list.html'
    context_object_name = 'shipments'
    paginate_by = 20

    def get_queryset(self):
        qs = InboundShipment.objects.select_related('warehouse', 'supplier', 'receiver').order_by('-created_at')
        status = self.request.GET.get('status', '').strip()
        warehouse_id = self.request.GET.get('warehouse', '').strip()
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        if q:
            qs = qs.filter(Q(shipment_number__icontains=q) | Q(supplier__name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        from apps.warehouse.models import Warehouse
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['status_choices'] = InboundShipment.STATUS_CHOICES
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        return ctx


class InboundShipmentCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver']
    model = InboundShipment
    form_class = InboundShipmentForm
    template_name = 'logistics/inbound_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.shipment_number = f'SHP-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}'
        form.instance.status = 'draft'
        messages.success(self.request, "Kirim yetkazmasi muvaffaqiyatli yaratildi.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('logistics:inbound_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Yangi kirim'
        return ctx


class InboundShipmentDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver']
    model = InboundShipment
    template_name = 'logistics/inbound_detail.html'
    context_object_name = 'shipment'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('product', 'target_location').all()
        ctx['item_form'] = InboundItemForm(initial={'shipment': self.object})
        from apps.warehouse.models import StorageLocation
        ctx['locations'] = StorageLocation.objects.filter(
            warehouse=self.object.warehouse, is_active=True
        ).order_by('zone', 'rack', 'shelf')
        # Har render uchun yangi token: bir xil formani ikki marta yuborish
        # (ikki marta bosish, qayta yuborish) zaxirani ikki marta o'zgartirmaydi
        ctx['idempotency_token'] = uuid.uuid4().hex
        return ctx


@login_required
def inbound_receive_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'receiver'):
        raise PermissionDenied
    shipment = get_object_or_404(InboundShipment, pk=pk)
    if request.method == 'POST':
        from apps.warehouse.models import StorageLocation, StockMovement

        item_id = request.POST.get('item_id')
        received_qty = _post_int(request, 'received_qty')
        damaged_qty = _post_int(request, 'damaged_qty')
        location_id = request.POST.get('location_id')
        batch_number = request.POST.get('batch_number', '').strip()
        expiry_date = request.POST.get('expiry_date') or None

        get_object_or_404(InboundItem, pk=item_id, shipment=shipment)

        if received_qty is None or received_qty <= 0 or damaged_qty is None or damaged_qty < 0:
            messages.error(request, "Qabul qilingan miqdor 0 dan katta, shikastlangan esa manfiy bo'lmasligi kerak.")
            return redirect('logistics:inbound_detail', pk=pk)

        idempotency_key = f'receive-{item_id}-{_idempotency_token(request)}'
        if StockMovement.objects.filter(idempotency_key=idempotency_key).exists():
            messages.info(request, "Bu qabul allaqachon bajarilgan.")
            return redirect('logistics:inbound_detail', pk=pk)

        location = None
        if location_id:
            location = StorageLocation.objects.filter(pk=location_id, is_active=True).first()

        # Element yangilanishi va qabul bitta tranzaksiyada: takroriy so'rovda
        # damaged_quantity ikki marta qo'shilmaydi
        with transaction.atomic():
            item = InboundItem.objects.select_for_update().get(pk=item_id, shipment=shipment)
            item.target_location = location or item.target_location
            item.batch_number = batch_number or item.batch_number
            item.expiry_date = expiry_date or item.expiry_date
            item.damaged_quantity += damaged_qty
            item.save()

            success, msg = receive_inbound_item(item, received_qty, request.user, idempotency_key)
            if success and msg not in ALREADY_DONE_MESSAGES:
                InboundShipment.objects.filter(pk=shipment.pk).exclude(
                    status__in=['completed', 'cancelled']
                ).update(status='receiving')
            else:
                transaction.set_rollback(True)

        if not success:
            messages.error(request, f"Xato: {msg}")
        elif msg in ALREADY_DONE_MESSAGES:
            messages.info(request, "Bu qabul allaqachon bajarilgan.")
        else:
            messages.success(request, f"{received_qty} dona muvaffaqiyatli qabul qilindi.")

    return redirect('logistics:inbound_detail', pk=pk)


def _post_int(request, name, default=0):
    """POST qiymatini butun songa aylantiradi; noto'g'ri bo'lsa None."""
    raw = request.POST.get(name, '')
    if raw in ('', None):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _idempotency_token(request):
    """Formadagi idempotentlik tokeni; bo'lmasa yangi (takrorlanmaydigan) token."""
    token = request.POST.get('idempotency_token', '').strip()
    if token and len(token) <= 64 and token.isalnum():
        return token
    return uuid.uuid4().hex


@login_required
def inbound_complete_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'receiver'):
        raise PermissionDenied
    shipment = get_object_or_404(InboundShipment, pk=pk)
    if request.method == 'POST':
        shipment.status = 'completed'
        shipment.received_at = timezone.now()
        shipment.save(update_fields=['status', 'received_at'])
        messages.success(request, "Kirim yetkazmasi yakunlandi.")
    return redirect('logistics:inbound_detail', pk=pk)


@login_required
def inbound_cancel_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager'):
        raise PermissionDenied
    shipment = get_object_or_404(InboundShipment, pk=pk)
    if request.method == 'POST':
        if shipment.status == 'completed':
            messages.error(request, "Yakunlangan yetkazmani bekor qilib bo'lmaydi.")
        else:
            shipment.status = 'cancelled'
            shipment.save(update_fields=['status'])
            messages.success(request, "Kirim yetkazmasi bekor qilindi.")
    return redirect('logistics:inbound_detail', pk=pk)


# ── Outbound Orders ────────────────────────────────────────────────────────────

class OutboundOrderListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'dispatcher', 'picker', 'seller']
    model = OutboundOrder
    template_name = 'logistics/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = OutboundOrder.objects.select_related('seller', 'warehouse', 'assigned_picker').order_by('-created_at')
        # Seller isolation
        if self.request.user.role == 'seller' and hasattr(self.request.user, 'seller_profile'):
            qs = qs.filter(seller=self.request.user.seller_profile)
        # Picker sees only assigned orders
        if self.request.user.role == 'picker':
            qs = qs.filter(assigned_picker=self.request.user)

        status = self.request.GET.get('status', '').strip()
        model_filter = self.request.GET.get('sales_model', '').strip()
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if model_filter:
            qs = qs.filter(sales_model=model_filter)
        if q:
            qs = qs.filter(Q(order_number__icontains=q) | Q(destination__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_model'] = self.request.GET.get('sales_model', '')
        ctx['status_choices'] = OutboundOrder.STATUS_CHOICES
        ctx['sales_models'] = OutboundOrder.SALES_MODEL_CHOICES
        return ctx


class OutboundOrderCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'warehouse_manager', 'dispatcher']
    model = OutboundOrder
    form_class = OutboundOrderForm
    template_name = 'logistics/order_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.order_number = f'ORD-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:8].upper()}'
        form.instance.status = 'created'
        messages.success(self.request, "Buyurtma muvaffaqiyatli yaratildi.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('logistics:order_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Yangi buyurtma'
        return ctx


class OutboundOrderDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['admin', 'warehouse_manager', 'dispatcher', 'picker', 'seller']
    model = OutboundOrder
    template_name = 'logistics/order_detail.html'
    context_object_name = 'order'

    def get_object(self):
        obj = super().get_object()
        # Seller isolation
        if self.request.user.role == 'seller':
            if not hasattr(self.request.user, 'seller_profile') or obj.seller != self.request.user.seller_profile:
                raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('product').prefetch_related('allocations__inventory_batch').all()
        ctx['packages'] = self.object.packages.all()
        ctx['pickers'] = User.objects.filter(role='picker', is_active=True)
        ctx['item_form'] = OrderItemForm()
        return ctx


@login_required
def order_allocate_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'dispatcher'):
        raise PermissionDenied
    get_object_or_404(OutboundOrder, pk=pk)
    if request.method == 'POST':
        errors = []
        with transaction.atomic():
            # Buyurtma qulflanadi: ikkinchi parallel so'rov birinchisi tugashini
            # kutadi va yangilangan holatni ko'radi
            order = OutboundOrder.objects.select_for_update().get(pk=pk)
            if order.status not in ('created', 'needs_stock'):
                messages.info(request, "Bu buyurtmaga zaxira allaqachon ajratilgan yoki ajratib bo'lmaydi.")
                return redirect('logistics:order_detail', pk=pk)
            for item in order.items.select_related('product'):
                success, msg = allocate_stock(item, performed_by=request.user)
                if not success:
                    errors.append(f'{item.product.name}: {msg}')
            order.status = 'needs_stock' if errors else 'allocated'
            order.save(update_fields=['status'])
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            messages.success(request, "Zaxira muvaffaqiyatli ajratildi.")
    return redirect('logistics:order_detail', pk=pk)


@login_required
def order_assign_picker_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'dispatcher'):
        raise PermissionDenied
    get_object_or_404(OutboundOrder, pk=pk)
    if request.method == 'POST':
        picker = get_object_or_404(User, pk=request.POST.get('picker_id'), role='picker', is_active=True)
        with transaction.atomic():
            order = OutboundOrder.objects.select_for_update().get(pk=pk)
            if order.status != 'allocated':
                messages.error(request, "Faqat zaxirasi ajratilgan buyurtmaga yig'uvchi tayinlash mumkin.")
                return redirect('logistics:order_detail', pk=pk)
            order.assigned_picker = picker
            order.status = 'picking'
            order.save(update_fields=['assigned_picker', 'status'])
        messages.success(request, f"Buyurtma {picker.get_full_name() or picker.username} ga tayinlandi.")
    return redirect('logistics:order_detail', pk=pk)


@login_required
def order_cancel_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager'):
        raise PermissionDenied
    order = get_object_or_404(OutboundOrder, pk=pk)
    if request.method == 'POST':
        success, msg = cancel_order(order, performed_by=request.user)
        if success:
            messages.success(request, "Buyurtma bekor qilindi va zaxira bo'shatildi.")
        else:
            messages.error(request, msg)
    return redirect('logistics:order_detail', pk=pk)


@login_required
def pack_order_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'dispatcher'):
        raise PermissionDenied
    get_object_or_404(OutboundOrder, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            order = OutboundOrder.objects.select_for_update().get(pk=pk)
            # Holat qulfdan keyin tekshiriladi — ikki marta bosish ikkita qadoq yaratmaydi
            if order.status != 'picked':
                if order.status in ('packed', 'shipped', 'completed'):
                    messages.info(request, "Buyurtma allaqachon qadoqlangan.")
                else:
                    messages.error(request, "Faqat yig'ilgan buyurtmani qadoqlash mumkin.")
                return redirect('logistics:order_detail', pk=pk)
            pkg_number = f'PKG-{uuid.uuid4().hex[:10].upper()}'
            Package.objects.create(
                package_number=pkg_number,
                order=order,
                barcode=pkg_number,
                status='packed',
                packed_at=timezone.now(),
                destination=order.destination,
            )
            order.status = 'packed'
            order.save(update_fields=['status'])
        messages.success(request, f"Qadoq {pkg_number} yaratildi.")
    return redirect('logistics:order_detail', pk=pk)


@login_required
def ship_order_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'dispatcher'):
        raise PermissionDenied
    get_object_or_404(OutboundOrder, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            order = OutboundOrder.objects.select_for_update().get(pk=pk)
            if order.status != 'packed':
                if order.status in ('shipped', 'completed'):
                    messages.info(request, "Buyurtma allaqachon jo'natilgan.")
                else:
                    messages.error(request, "Faqat qadoqlangan buyurtmani jo'natish mumkin.")
                return redirect('logistics:order_detail', pk=pk)
            order.packages.filter(status='packed').update(status='shipped', shipped_at=timezone.now())
            order.status = 'shipped'
            order.save(update_fields=['status'])
        messages.success(request, "Buyurtma jo'natildi.")
    return redirect('logistics:order_detail', pk=pk)


# ── Picking ─────────────────────────────────────────────────────────────────────

class PickingListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'picker', 'dispatcher']
    model = OutboundOrder
    template_name = 'logistics/picking_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = OutboundOrder.objects.filter(status__in=['picking', 'allocated']).select_related(
            'seller', 'warehouse', 'assigned_picker'
        ).order_by('-priority', 'deadline', 'created_at')
        if self.request.user.role == 'picker':
            qs = qs.filter(assigned_picker=self.request.user)
        return qs


class PickingDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['admin', 'warehouse_manager', 'picker', 'dispatcher']
    model = OutboundOrder
    template_name = 'logistics/picking_detail.html'
    context_object_name = 'order'

    def get_object(self):
        obj = super().get_object()
        if self.request.user.role == 'picker' and obj.assigned_picker != self.request.user:
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = self.object.items.select_related('product').prefetch_related(
            'allocations__inventory_batch__location'
        ).all()
        ctx['items'] = items
        ctx['progress'] = self.object.get_picking_progress()
        ctx['idempotency_token'] = uuid.uuid4().hex
        return ctx


@login_required
def pick_item_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'picker', 'dispatcher'):
        raise PermissionDenied
    order = get_object_or_404(OutboundOrder, pk=pk)
    if request.user.role == 'picker' and order.assigned_picker != request.user:
        raise PermissionDenied
    if request.method == 'POST':
        allocation = get_object_or_404(
            StockAllocation, pk=request.POST.get('allocation_id'), order_item__order=order
        )
        picked_qty = _post_int(request, 'picked_qty')
        if picked_qty is None or picked_qty <= 0:
            messages.error(request, "Yig'ilgan miqdor 0 dan katta bo'lishi kerak.")
            return redirect('logistics:picking_detail', pk=pk)
        idempotency_key = f'pick-{allocation.pk}-{_idempotency_token(request)}'

        with transaction.atomic():
            order = OutboundOrder.objects.select_for_update().get(pk=pk)
            if order.status not in ('allocated', 'picking'):
                messages.error(request, "Buyurtma yig'ish holatida emas.")
                return redirect('logistics:picking_detail', pk=pk)
            success, msg = process_pick(allocation, picked_qty, request.user, idempotency_key)
            if success and all(item.is_picked for item in order.items.all()):
                order.status = 'picked'
                order.save(update_fields=['status'])

        if not success:
            messages.error(request, msg)
        elif msg in ALREADY_DONE_MESSAGES:
            messages.info(request, "Bu yig'ish allaqachon qayd etilgan.")
        else:
            messages.success(request, f"{picked_qty} dona muvaffaqiyatli yig'ildi.")
    return redirect('logistics:picking_detail', pk=pk)


# ── Packages ──────────────────────────────────────────────────────────────────

class PackageListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'dispatcher']
    model = Package
    template_name = 'logistics/package_list.html'
    context_object_name = 'packages'
    paginate_by = 20

    def get_queryset(self):
        qs = Package.objects.select_related('order__seller').order_by('-packed_at')
        status = self.request.GET.get('status', '').strip()
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(Q(package_number__icontains=q) | Q(order__order_number__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['status_choices'] = Package.STATUS_CHOICES
        return ctx


# ── Returns ───────────────────────────────────────────────────────────────────

class ReturnRecordListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'returns_operator']
    model = ReturnRecord
    template_name = 'logistics/return_list.html'
    context_object_name = 'returns'
    paginate_by = 20

    def get_queryset(self):
        qs = ReturnRecord.objects.select_related('product', 'original_order', 'received_by').order_by('-created_at')
        condition = self.request.GET.get('condition', '').strip()
        processed = self.request.GET.get('processed', '').strip()
        if condition:
            qs = qs.filter(condition=condition)
        if processed == '1':
            qs = qs.filter(processed=True)
        elif processed == '0':
            qs = qs.filter(processed=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['condition_choices'] = ReturnRecord.CONDITION_CHOICES
        ctx['selected_condition'] = self.request.GET.get('condition', '')
        ctx['selected_processed'] = self.request.GET.get('processed', '')
        return ctx


class ReturnRecordCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['admin', 'warehouse_manager', 'returns_operator']
    model = ReturnRecord
    form_class = ReturnRecordForm
    template_name = 'logistics/return_form.html'
    success_url = reverse_lazy('logistics:return_list')

    def form_valid(self, form):
        form.instance.received_by = self.request.user
        messages.success(self.request, "Qaytarish muvaffaqiyatli ro'yxatga olindi.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Yangi qaytarish'
        return ctx


@login_required
def return_process_view(request, pk):
    if request.user.role not in ('admin', 'warehouse_manager', 'returns_operator'):
        raise PermissionDenied
    ret = get_object_or_404(ReturnRecord, pk=pk)
    if request.method == 'POST':
        success, msg = process_return(ret, request.user)
        if success and msg in ALREADY_DONE_MESSAGES:
            messages.info(request, "Bu qaytarish allaqachon qayta ishlangan.")
        elif success:
            messages.success(request, "Qaytarish muvaffaqiyatli qayta ishlandi.")
        else:
            messages.error(request, msg)
    return redirect('logistics:return_list')


# ── Reports ───────────────────────────────────────────────────────────────────

@login_required
def reports_index(request):
    if request.user.role not in ('admin', 'warehouse_manager', 'dispatcher'):
        raise PermissionDenied
    return render(request, 'logistics/reports.html', {'page_title': 'Hisobotlar'})


@login_required
def inventory_report_view(request):
    if request.user.role not in ('admin', 'warehouse_manager'):
        raise PermissionDenied
    from apps.warehouse.models import InventoryBatch
    qs = InventoryBatch.objects.select_related('product__seller', 'product__category', 'location__warehouse').filter(
        condition='available', quantity_on_hand__gt=0
    ).order_by('product__name')
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
        response.write('\ufeff')
        w = csv.writer(response)
        w.writerow(['Mahsulot', 'SKU', 'Sotuvchi', 'Partiya', 'Ombor', 'Joy', "Qo'ldagi", 'Band', 'Erkin'])
        for b in qs:
            w.writerow([
                b.product.name, b.product.sku, str(b.product.seller),
                b.batch_number, b.location.warehouse.name, str(b.location),
                b.quantity_on_hand, b.quantity_reserved, b.available_quantity
            ])
        return response
    return render(request, 'logistics/report_inventory.html', {'batches': qs, 'page_title': 'Zaxira hisoboti'})


@login_required
def stock_movement_report_view(request):
    if request.user.role not in ('admin', 'warehouse_manager'):
        raise PermissionDenied
    from apps.warehouse.models import StockMovement
    qs = StockMovement.objects.select_related('product', 'performed_by').order_by('-created_at')[:500]
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="movements.csv"'
        response.write('\ufeff')
        w = csv.writer(response)
        w.writerow(['Vaqt', 'Tur', 'Mahsulot', 'Miqdor', 'Havola', 'Bajaruvchi'])
        for m in qs:
            w.writerow([
                m.created_at.strftime('%Y-%m-%d %H:%M'),
                m.get_movement_type_display(), m.product.name,
                m.quantity, m.reference,
                m.performed_by.username if m.performed_by else '-'
            ])
        return response
    return render(request, 'logistics/report_movements.html', {'movements': qs, 'page_title': 'Harakat hisoboti'})


@login_required
def inbound_report_view(request):
    if request.user.role not in ('admin', 'warehouse_manager', 'receiver'):
        raise PermissionDenied
    qs = InboundShipment.objects.select_related('warehouse', 'supplier').order_by('-created_at')[:200]
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="inbound.csv"'
        response.write('\ufeff')
        w = csv.writer(response)
        w.writerow(['Raqam', 'Ombor', 'Yetkazib beruvchi', 'Holat', 'Kutilgan', 'Qabul qilingan'])
        for s in qs:
            w.writerow([
                s.shipment_number, s.warehouse.name,
                s.supplier.name if s.supplier else '-',
                s.get_status_display(),
                s.expected_arrival.strftime('%Y-%m-%d') if s.expected_arrival else '-',
                s.received_at.strftime('%Y-%m-%d') if s.received_at else '-'
            ])
        return response
    return render(request, 'logistics/report_inbound.html', {'shipments': qs, 'page_title': 'Kirim hisoboti'})


@login_required
def outbound_report_view(request):
    if request.user.role not in ('admin', 'warehouse_manager', 'dispatcher'):
        raise PermissionDenied
    qs = OutboundOrder.objects.select_related('seller', 'warehouse').order_by('-created_at')[:200]
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="outbound.csv"'
        response.write('\ufeff')
        w = csv.writer(response)
        w.writerow(['Raqam', 'Sotuvchi', 'Ombor', 'Holat', 'Ustuvorlik', 'Yaratildi'])
        for o in qs:
            w.writerow([
                o.order_number, str(o.seller), o.warehouse.name,
                o.get_status_display(), o.get_priority_display(),
                o.created_at.strftime('%Y-%m-%d')
            ])
        return response
    return render(request, 'logistics/report_outbound.html', {'orders': qs, 'page_title': 'Chiqim hisoboti'})


@login_required
def returns_report_view(request):
    if request.user.role not in ('admin', 'warehouse_manager', 'returns_operator'):
        raise PermissionDenied
    qs = ReturnRecord.objects.select_related('product', 'received_by').order_by('-created_at')[:200]
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="returns.csv"'
        response.write('\ufeff')
        w = csv.writer(response)
        w.writerow(['Mahsulot', 'Miqdor', 'Sabab', 'Holati', 'Sana'])
        for r in qs:
            w.writerow([
                r.product.name, r.quantity, r.reason,
                r.get_condition_display(), r.created_at.strftime('%Y-%m-%d')
            ])
        return response
    return render(request, 'logistics/report_returns.html', {'returns': qs, 'page_title': 'Qaytarish hisoboti'})
