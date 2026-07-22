from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'group', 'amount', 'paid_by', 'paid_to', 'payment_method', 'status', 'date')
    search_fields = ('transaction_id', 'paid_by__username', 'paid_to__username', 'group__name')
    list_filter = ('payment_method', 'status', 'date')
