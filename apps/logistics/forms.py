from django import forms
from .models import InboundShipment, InboundItem, OutboundOrder, OrderItem, ReturnRecord


class InboundShipmentForm(forms.ModelForm):
    class Meta:
        model = InboundShipment
        fields = ['supplier', 'seller', 'warehouse', 'expected_arrival', 'notes']
        widgets = {
            'expected_arrival': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_arrival'].input_formats = ['%Y-%m-%dT%H:%M']
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent')


class InboundItemForm(forms.ModelForm):
    class Meta:
        model = InboundItem
        fields = ['product', 'expected_quantity', 'batch_number', 'expiry_date', 'target_location']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500')


class OutboundOrderForm(forms.ModelForm):
    class Meta:
        model = OutboundOrder
        fields = ['seller', 'warehouse', 'sales_model', 'destination', 'priority', 'deadline']
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'destination': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['deadline'].input_formats = ['%Y-%m-%dT%H:%M']
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500')


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'requested_quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500')


class ReturnRecordForm(forms.ModelForm):
    class Meta:
        model = ReturnRecord
        fields = ['original_order', 'product', 'quantity', 'reason', 'condition', 'disposition']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-purple-500')
