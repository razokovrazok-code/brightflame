from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum, ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from apps.accounts.views import RoleRequiredMixin
from apps.accounts.models import SellerProfile
from .models import Category, Product
from .forms import CategoryForm, ProductForm


class CategoryListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'dispatcher', 'seller']
    model = Category
    template_name = 'catalog/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20

    def get_queryset(self):
        qs = Category.objects.all().order_by('name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class CategoryCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['warehouse_manager', 'admin']
    model = Category
    form_class = CategoryForm
    template_name = 'catalog/category_form.html'
    success_url = reverse_lazy('catalog:category_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Kategoriya '{self.object.name}' muvaffaqiyatli yaratildi.")
        return response


class CategoryUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['warehouse_manager', 'admin']
    model = Category
    form_class = CategoryForm
    template_name = 'catalog/category_form.html'
    success_url = reverse_lazy('catalog:category_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Kategoriya '{self.object.name}' muvaffaqiyatli yangilandi.")
        return response


class CategoryDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = ['warehouse_manager', 'admin']
    model = Category
    template_name = 'catalog/category_confirm_delete.html'
    success_url = reverse_lazy('catalog:category_list')
    context_object_name = 'category'

    # Django 4.0+: DeleteView POST'da delete() emas, form_valid() chaqiradi
    def form_valid(self, form):
        if self.object.products.exists():
            messages.error(self.request, "Bu kategoriyada mahsulotlar mavjud, o'chirish mumkin emas!")
            return redirect('catalog:category_list')
        name = self.object.name
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Kategoriya boshqa yozuvlarga bog'langan, o'chirish mumkin emas!")
            return redirect('catalog:category_list')
        messages.success(self.request, f"Kategoriya '{name}' muvaffaqiyatli o'chirildi.")
        return response


class ProductListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'picker', 'dispatcher', 'returns_operator', 'seller']
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Product.objects.select_related('category', 'seller').all().order_by('-created_at')

        # Seller isolation
        if user.role == 'seller':
            if hasattr(user, 'seller_profile'):
                qs = qs.filter(seller=user.seller_profile)
            else:
                qs = qs.none()

        q = self.request.GET.get('q', '').strip()
        category_id = self.request.GET.get('category', '').strip()
        seller_id = self.request.GET.get('seller', '').strip()
        is_active = self.request.GET.get('is_active', '').strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(sku__icontains=q) |
                Q(barcode__icontains=q) |
                Q(brand__icontains=q) |
                Q(wb_article__icontains=q)
            )
        if category_id:
            qs = qs.filter(category_id=category_id)
        if seller_id and user.role != 'seller':
            qs = qs.filter(seller_id=seller_id)
        if is_active in ['true', '1']:
            qs = qs.filter(is_active=True)
        elif is_active in ['false', '0']:
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_seller'] = self.request.GET.get('seller', '')
        context['selected_active'] = self.request.GET.get('is_active', '')
        context['categories'] = Category.objects.all().order_by('name')
        if self.request.user.role != 'seller':
            context['sellers'] = SellerProfile.objects.filter(is_active=True).order_by('seller_name')
        return context


class ProductDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['admin', 'warehouse_manager', 'receiver', 'picker', 'dispatcher', 'returns_operator', 'seller']
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.role == 'seller':
            if not hasattr(user, 'seller_profile') or obj.seller != user.seller_profile:
                raise PermissionDenied("Siz faqat o'zingizning mahsulotlaringizni ko'ra olasiz.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch batches and stock info
        batches = self.object.inventory_batches.select_related('location__warehouse').all().order_by('-received_at')
        total_on_hand = batches.aggregate(total=Sum('quantity_on_hand'))['total'] or 0
        total_reserved = batches.aggregate(total=Sum('quantity_reserved'))['total'] or 0
        context['batches'] = batches
        context['total_on_hand'] = total_on_hand
        context['total_reserved'] = total_reserved
        context['available_stock'] = total_on_hand - total_reserved
        return context


class ProductCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['warehouse_manager', 'admin', 'seller']
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if self.request.user.role == 'seller':
            if not hasattr(self.request.user, 'seller_profile'):
                messages.error(self.request, "Sotuvchi profili biriktirilmagan!")
                return redirect('catalog:product_list')
            form.instance.seller = self.request.user.seller_profile

        response = super().form_valid(form)
        messages.success(self.request, f"Mahsulot '{self.object.name}' muvaffaqiyatli yaratildi.")
        return response


class ProductUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['warehouse_manager', 'admin', 'seller']
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.role == 'seller':
            if not hasattr(user, 'seller_profile') or obj.seller != user.seller_profile:
                raise PermissionDenied("Siz faqat o'zingizning mahsulotlaringizni o'zgartira olasiz.")
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if self.request.user.role == 'seller':
            form.instance.seller = self.request.user.seller_profile

        response = super().form_valid(form)
        messages.success(self.request, f"Mahsulot '{self.object.name}' muvaffaqiyatli yangilandi.")
        return response


class ProductDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = ['warehouse_manager', 'admin', 'seller']
    model = Product
    template_name = 'catalog/product_confirm_delete.html'
    success_url = reverse_lazy('catalog:product_list')
    context_object_name = 'product'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.role == 'seller':
            if not hasattr(user, 'seller_profile') or obj.seller != user.seller_profile:
                raise PermissionDenied("Siz faqat o'zingizning mahsulotlaringizni o'chira olasiz.")
        return obj

    def form_valid(self, form):
        if self.object.inventory_batches.filter(quantity_on_hand__gt=0).exists():
            messages.error(self.request, "Ushbu mahsulot omborda mavjud, uni o'chirish mumkin emas!")
            return redirect('catalog:product_list')
        name = self.object.name
        try:
            response = super().form_valid(form)
        except ProtectedError:
            # Partiyalar, harakatlar yoki buyurtmalar tarixi mavjud
            messages.error(self.request, "Mahsulotning ombor/buyurtma tarixi bor, o'chirish mumkin emas!")
            return redirect('catalog:product_list')
        messages.success(self.request, f"Mahsulot '{name}' muvaffaqiyatli o'chirildi.")
        return response
