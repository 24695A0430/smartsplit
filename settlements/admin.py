from django.contrib import admin
from .models import Settlement

@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ('group', 'debtor', 'creditor', 'amount', 'status', 'updated_at')
    search_fields = ('group__name', 'debtor__username', 'creditor__username')
    list_filter = ('status', 'updated_at')
