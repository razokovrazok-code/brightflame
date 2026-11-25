import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.views.generic import TemplateView
from apps.warehouse.models import InventoryBatch, StockMovement
from apps.logistics.models import OutboundOrder, InboundShipment
from apps.catalog.models import Product, Category


class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        seven_days = today + timezone.timedelta(days=7)

        ctx['page_title'] = 'Asosiy panel'
        ctx['total_skus'] = Product.objects.filter(is_active=True).count()

        agg = InventoryBatch.objects.filter(condition='available').aggregate(
            total=Sum('quantity_on_hand'), reserved=Sum('quantity_reserved')
        )
        ctx['total_units'] = agg['total'] or 0
        ctx['reserved_units'] = agg['reserved'] or 0

        ctx['today_inbound'] = StockMovement.objects.filter(
            movement_type='inbound', created_at__date=today
        ).aggregate(t=Sum('quantity'))['t'] or 0
        ctx['today_outbound'] = StockMovement.objects.filter(
            movement_type='outbound', created_at__date=today
        ).aggregate(t=Sum('quantity'))['t'] or 0

        ctx['picking_orders'] = OutboundOrder.objects.filter(status='picking').count()
        ctx['low_stock_count'] = Product.objects.filter(
            is_active=True, min_stock_limit__gt=0
        ).count()

        ctx['expiring_batches'] = InventoryBatch.objects.filter(
            condition='available',
            expiry_date__isnull=False,
            expiry_date__lte=seven_days,
            expiry_date__gte=today,
        ).select_related('product', 'location').order_by('expiry_date')[:8]

        ctx['active_orders'] = OutboundOrder.objects.filter(
            status__in=['created', 'allocated', 'picking', 'picked', 'packed']
        ).select_related('seller', 'warehouse').order_by('-created_at')[:8]

        ctx['recent_inbound'] = InboundShipment.objects.filter(
            status__in=['expected', 'arrived', 'receiving']
        ).select_related('warehouse', 'supplier').order_by('-created_at')[:5]

        # Chart: last 14 days inbound/outbound
        labels, inbound_data, outbound_data = [], [], []
        for i in range(13, -1, -1):
            day = today - timezone.timedelta(days=i)
            labels.append(day.strftime('%d/%m'))
            ib = StockMovement.objects.filter(
                movement_type='inbound', created_at__date=day
            ).aggregate(t=Sum('quantity'))['t'] or 0
            ob = StockMovement.objects.filter(
                movement_type='outbound', created_at__date=day
            ).aggregate(t=Sum('quantity'))['t'] or 0
            inbound_data.append(int(ib))
            outbound_data.append(int(ob))

        ctx['chart_labels'] = json.dumps(labels)
        ctx['chart_inbound'] = json.dumps(inbound_data)
        ctx['chart_outbound'] = json.dumps(outbound_data)

        # Category donut
        cat_data = list(Category.objects.annotate(
            total=Sum('products__inventory_batches__quantity_on_hand',
                      filter=Q(products__inventory_batches__condition='available'))
        ).filter(total__gt=0).values('name', 'total')[:7])
        ctx['cat_labels'] = json.dumps([c['name'] for c in cat_data])
        ctx['cat_values'] = json.dumps([int(c['total'] or 0) for c in cat_data])

        return ctx
