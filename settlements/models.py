from django.db import models
from django.contrib.auth.models import User
from groups.models import Group
from payments.models import Payment

class Settlement(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    debtor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settlements_owed')
    creditor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settlements_received')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='settlement')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.debtor.username} paid {self.creditor.username} ₹{self.amount} ({self.status})"
