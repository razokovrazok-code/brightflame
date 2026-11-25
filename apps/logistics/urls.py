from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # Suppliers
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/update/', views.SupplierUpdateView.as_view(), name='supplier_update'),

    # Inbound
    path('inbound/', views.InboundShipmentListView.as_view(), name='inbound_list'),
    path('inbound/create/', views.InboundShipmentCreateView.as_view(), name='inbound_create'),
    path('inbound/<int:pk>/', views.InboundShipmentDetailView.as_view(), name='inbound_detail'),
    path('inbound/<int:pk>/receive/', views.inbound_receive_view, name='inbound_receive'),
    path('inbound/<int:pk>/complete/', views.inbound_complete_view, name='inbound_complete'),
    path('inbound/<int:pk>/cancel/', views.inbound_cancel_view, name='inbound_cancel'),

    # Orders
    path('orders/', views.OutboundOrderListView.as_view(), name='order_list'),
    path('orders/create/', views.OutboundOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.OutboundOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/allocate/', views.order_allocate_view, name='order_allocate'),
    path('orders/<int:pk>/assign-picker/', views.order_assign_picker_view, name='order_assign_picker'),
    path('orders/<int:pk>/cancel/', views.order_cancel_view, name='order_cancel'),
    path('orders/<int:pk>/pack/', views.pack_order_view, name='order_pack'),
    path('orders/<int:pk>/ship/', views.ship_order_view, name='order_ship'),

    # Picking
    path('picking/', views.PickingListView.as_view(), name='picking_list'),
    path('picking/<int:pk>/', views.PickingDetailView.as_view(), name='picking_detail'),
    path('picking/<int:pk>/pick-item/', views.pick_item_view, name='pick_item'),

    # Packages
    path('packages/', views.PackageListView.as_view(), name='package_list'),

    # Returns
    path('returns/', views.ReturnRecordListView.as_view(), name='return_list'),
    path('returns/create/', views.ReturnRecordCreateView.as_view(), name='return_create'),
    path('returns/<int:pk>/process/', views.return_process_view, name='return_process'),

    # Reports
    path('reports/', views.reports_index, name='reports'),
    path('reports/inventory/', views.inventory_report_view, name='report_inventory'),
    path('reports/movements/', views.stock_movement_report_view, name='report_movements'),
    path('reports/inbound/', views.inbound_report_view, name='report_inbound'),
    path('reports/outbound/', views.outbound_report_view, name='report_outbound'),
    path('reports/returns/', views.returns_report_view, name='report_returns'),
]
