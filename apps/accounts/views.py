from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from .forms import UserCreateForm, UserUpdateForm, SellerProfileForm
from .models import SellerProfile

User = get_user_model()


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in self.allowed_roles and request.user.role != 'admin':
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class LoginView(DjangoLoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard:index')


class LogoutView(DjangoLogoutView):
    next_page = reverse_lazy('login')


class UserListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin']
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_joined')
        q = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()
        is_active = self.request.GET.get('is_active', '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) | Q(first_name__icontains=q) |
                Q(last_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
            )
        if role:
            qs = qs.filter(role=role)
        if is_active in ['true', '1']:
            qs = qs.filter(is_active=True)
        elif is_active in ['false', '0']:
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['selected_role'] = self.request.GET.get('role', '')
        context['roles'] = User.ROLE_CHOICES
        return context


class UserCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['admin']
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Foydalanuvchi '{self.object.username}' muvaffaqiyatli yaratildi.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Yangi foydalanuvchi'
        ctx['action'] = 'Yaratish'
        return ctx


class UserUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['admin']
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Foydalanuvchi '{self.object.username}' muvaffaqiyatli yangilandi.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "Foydalanuvchini tahrirlash"
        ctx['action'] = 'Saqlash'
        return ctx


class UserDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = ['admin']
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')
    context_object_name = 'target_user'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object == request.user:
            messages.error(request, "O'z hisobingizni o'chira olmaysiz!")
            return redirect('accounts:user_list')
        username = self.object.username
        self.object.delete()
        messages.success(request, f"Foydalanuvchi '{username}' muvaffaqiyatli o'chirildi.")
        return redirect(self.success_url)


class SellerListView(RoleRequiredMixin, ListView):
    allowed_roles = ['admin', 'warehouse_manager']
    model = SellerProfile
    template_name = 'accounts/seller_list.html'
    context_object_name = 'sellers'
    paginate_by = 20

    def get_queryset(self):
        qs = SellerProfile.objects.select_related('user').order_by('seller_name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(seller_name__icontains=q) | Q(seller_code__icontains=q) |
                Q(user__username__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class SellerCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['admin']
    model = SellerProfile
    form_class = SellerProfileForm
    template_name = 'accounts/seller_form.html'
    success_url = reverse_lazy('accounts:seller_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Sotuvchi profili muvaffaqiyatli yaratildi.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Yangi sotuvchi'
        ctx['action'] = 'Yaratish'
        return ctx


class SellerUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ['admin']
    model = SellerProfile
    form_class = SellerProfileForm
    template_name = 'accounts/seller_form.html'
    success_url = reverse_lazy('accounts:seller_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Sotuvchi profili muvaffaqiyatli yangilandi.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Sotuvchini tahrirlash'
        ctx['action'] = 'Saqlash'
        return ctx


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user_form'] = UserUpdateForm(instance=self.request.user)
        if hasattr(self.request.user, 'seller_profile'):
            ctx['seller_form'] = SellerProfileForm(instance=self.request.user.seller_profile)
        return ctx

    def post(self, request, *args, **kwargs):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        seller_form = None
        seller_valid = True
        if hasattr(request.user, 'seller_profile'):
            seller_form = SellerProfileForm(request.POST, instance=request.user.seller_profile)
            seller_valid = seller_form.is_valid()
        if user_form.is_valid() and seller_valid:
            user_form.save()
            if seller_form:
                seller_form.save()
            messages.success(request, "Profilingiz muvaffaqiyatli yangilandi.")
            return redirect('accounts:profile')
        return render(request, self.template_name, {'user_form': user_form, 'seller_form': seller_form})
