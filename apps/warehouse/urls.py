from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    # Warehouses
    path('', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('create/', views.WarehouseCreateView.as_view(), name='warehouse_create'),
    path('<int:pk>/', views.WarehouseDetailView.as_view(), name='warehouse_detail'),
    path('<int:pk>/update/', views.WarehouseUpdateView.as_view(), name='warehouse_update'),

    # Storage Locations
    path('locations/', views.StorageLocationListView.as_view(), name='location_list'),
    path('locations/create/', views.StorageLocationCreateView.as_view(), name='location_create'),
    path('locations/<int:pk>/update/', views.StorageLocationUpdateView.as_view(), name='location_update'),

    # Inventory
    path('inventory/', views.InventoryBatchListView.as_view(), name='inventory_list'),
    path('inventory/<int:pk>/', views.InventoryBatchDetailView.as_view(), name='inventory_detail'),
    path('inventory/summary/', views.inventory_summary_view, name='inventory_summary'),

    # Stock Movements
    path('movements/', views.StockMovementListView.as_view(), name='movement_list'),
]
