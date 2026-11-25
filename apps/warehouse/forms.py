from django import forms
from django.core.exceptions import ValidationError
from .models import Warehouse, StorageLocation, InventoryBatch
from apps.catalog.models import Product


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['code', 'name', 'warehouse_type', 'address', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'warehouse_type': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        qs = Warehouse.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ushbu ombor kodi allaqachon mavjud.")
        return code


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = [
            'warehouse', 'zone', 'aisle', 'rack', 'shelf', 'position',
            'barcode', 'max_weight_capacity', 'is_active'
        ]
        widgets = {
            'warehouse': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'zone': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'aisle': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'rack': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'shelf': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'position': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'barcode': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'max_weight_capacity': forms.NumberInput(attrs={'step': '0.01', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        warehouse = cleaned_data.get('warehouse')
        zone = cleaned_data.get('zone', '').strip().upper()
        aisle = cleaned_data.get('aisle', '').strip().upper()
        rack = cleaned_data.get('rack', '').strip().upper()
        shelf = cleaned_data.get('shelf', '').strip().upper()
        position = cleaned_data.get('position', '').strip().upper()
        barcode = cleaned_data.get('barcode', '').strip()

        if warehouse and zone and aisle and rack and shelf and position:
            qs = StorageLocation.objects.filter(
                warehouse=warehouse, zone=zone, aisle=aisle,
                rack=rack, shelf=shelf, position=position
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Bu omborda ushbu koordinatadagi saqlash joyi allaqachon mavjud.")

        # If barcode is empty, auto-generate from coordinates
        if not barcode and warehouse and zone and aisle and rack and shelf and position:
            barcode = f"{warehouse.code}-{zone}-{aisle}-{rack}-{shelf}-{position}"
            cleaned_data['barcode'] = barcode

        if barcode:
            qs_b = StorageLocation.objects.filter(barcode=barcode)
            if self.instance.pk:
                qs_b = qs_b.exclude(pk=self.instance.pk)
            if qs_b.exists():
                self.add_error('barcode', "Ushbu shtrix-kodga ega saqlash joyi allaqachon mavjud.")

        return cleaned_data


class InventoryBatchForm(forms.ModelForm):
    class Meta:
        model = InventoryBatch
        fields = [
            'product', 'location', 'batch_number', 'quantity_on_hand',
            'quantity_reserved', 'condition', 'manufacture_date', 'expiry_date'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'location': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'batch_number': forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'quantity_on_hand': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'quantity_reserved': forms.NumberInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'condition': forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'manufacture_date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        quantity_on_hand = cleaned_data.get('quantity_on_hand') or 0
        quantity_reserved = cleaned_data.get('quantity_reserved') or 0

        if quantity_on_hand < 0:
            self.add_error('quantity_on_hand', "Ombordagi miqdor manfiy bo'lishi mumkin emas.")
        if quantity_reserved < 0:
            self.add_error('quantity_reserved', "Band qilingan miqdor manfiy bo'lishi mumkin emas.")
        if quantity_reserved > quantity_on_hand:
            self.add_error('quantity_reserved', "Band qilingan miqdor mavjud miqdordan ko'p bo'lishi mumkin emas.")

        return cleaned_data
