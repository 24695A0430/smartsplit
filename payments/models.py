from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from groups.models import Group

class Payment(models.Model):
    METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI (Generic)'),
        ('PHONEPE', 'PhonePe'),
        ('GPAY', 'Google Pay'),
        ('PAYTM', 'Paytm'),
        ('DEBIT', 'Debit Card'),
        ('CREDIT', 'Credit Card'),
        ('BANK', 'Bank Transfer'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REJECTED', 'Rejected'),
    ]

    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_sent')
    paid_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='payments_received')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='CASH')
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        payee = self.paid_to.username if self.paid_to else "Merchant"
        return f"₹{self.amount} from {self.paid_by.username} to {payee} ({self.status})"
