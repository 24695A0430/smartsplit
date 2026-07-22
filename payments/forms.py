from django import forms
from .models import Payment
from django.contrib.auth.models import User

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'paid_to', 'payment_method', 'date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'paid_to': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional remarks/reference'}),
        }

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if group and user:
            # Payer is request.user, so paid_to must be other members of the group
            members = group.members.exclude(user=user)
            self.fields['paid_to'].queryset = User.objects.filter(id__in=[m.user.id for m in members])
