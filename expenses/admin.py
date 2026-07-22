from django.contrib import admin
from .models import Expense, ExpenseSplit

class ExpenseSplitInline(admin.TabularInline):
    model = ExpenseSplit
    extra = 1

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'amount', 'paid_by', 'category', 'split_type', 'date')
    search_fields = ('title', 'group__name', 'paid_by__username', 'category')
    list_filter = ('category', 'split_type', 'date')
    inlines = [ExpenseSplitInline]

@admin.register(ExpenseSplit)
class ExpenseSplitAdmin(admin.ModelAdmin):
    list_display = ('expense', 'user', 'amount', 'percentage')
    search_fields = ('expense__title', 'user__username')
