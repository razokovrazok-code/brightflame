from django import forms
from django.core.exceptions import ValidationError
from .models import Category, Product
from apps.accounts.models import SellerProfile


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'code': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        qs = Category.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ushbu kategoriya kodi allaqachon mavjud.")
        return code


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'seller', 'category', 'name', 'sku', 'barcode', 'wb_article',
            'nm_id', 'brand', 'unit', 'size', 'color', 'weight',
            'length', 'width', 'height', 'min_stock_limit',
            'image', 'is_perishable', 'is_active'
        ]
        widgets = {
            'seller': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'category': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'sku': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'barcode': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'wb_article': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'nm_id': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'brand': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'unit': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'size': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'color': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'weight': forms.NumberInput(attrs={'step': '0.001', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'length': forms.NumberInput(attrs={'step': '0.01', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'width': forms.NumberInput(attrs={'step': '0.01', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'height': forms.NumberInput(attrs={'step': '0.01', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'min_stock_limit': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*', 'class': 'block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-purple-50 file:text-purple-700'}),
            'is_perishable': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and hasattr(self.user, 'role') and self.user.role == 'seller':
            if hasattr(self.user, 'seller_profile'):
                self.fields['seller'].initial = self.user.seller_profile
                self.fields['seller'].widget = forms.HiddenInput()
                self.fields['seller'].required = False
        else:
            self.fields['seller'].queryset = SellerProfile.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        seller = cleaned_data.get('seller')
        if not seller and self.user and hasattr(self.user, 'role') and self.user.role == 'seller':
            if hasattr(self.user, 'seller_profile'):
                seller = self.user.seller_profile
                cleaned_data['seller'] = seller

        sku = cleaned_data.get('sku')
        barcode = cleaned_data.get('barcode')

        if seller and sku:
            qs = Product.objects.filter(seller=seller, sku__iexact=sku)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('sku', "Ushbu SKU (artikul) mazkur sotuvchida allaqachon mavjud.")

        if seller and barcode:
            qs = Product.objects.filter(seller=seller, barcode__iexact=barcode)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('barcode', "Ushbu shtrix-kod mazkur sotuvchida allaqachon mavjud.")

        return cleaned_data
