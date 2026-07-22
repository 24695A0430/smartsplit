from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from groups.models import Group

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Shopping', 'Shopping'),
        ('Fuel', 'Fuel'),
        ('Rent', 'Rent'),
        ('Bills', 'Bills'),
        ('Entertainment', 'Entertainment'),
        ('Others', 'Others'),
    ]

    SPLIT_CHOICES = [
        ('EQUAL', 'Equal Split'),
        ('CUSTOM', 'Custom Split (Exact Amounts)'),
        ('PERCENT', 'Percentage Split'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Others')
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses_paid')
    split_type = models.CharField(max_length=10, choices=SPLIT_CHOICES, default='EQUAL')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount} in {self.group.name}"

class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_shares')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('expense', 'user')

    def __str__(self):
        return f"{self.user.username}'s share of {self.expense.title}: {self.amount}"
