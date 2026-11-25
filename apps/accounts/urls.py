from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('sellers/', views.SellerListView.as_view(), name='seller_list'),
    path('sellers/create/', views.SellerCreateView.as_view(), name='seller_create'),
    path('sellers/<int:pk>/update/', views.SellerUpdateView.as_view(), name='seller_update'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
