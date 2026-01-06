# wallet/models.py - COMPLETE CORRECT VERSION
from django.db import models
from django.conf import settings
import uuid

User = settings.AUTH_USER_MODEL

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    available_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    locked_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus_claimed = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')  # Add this for currency preference

    def __str__(self):
        return f"{self.user.username} Wallet"

    def total_balance(self):
        return self.available_balance + self.locked_balance + self.bonus_balance


class Transaction(models.Model):
    # Transaction types
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    INVESTMENT = 'investment'
    PROFIT = 'profit'
    BONUS = 'bonus'
    ADJUSTMENT = 'adjustment'
    
    TRANSACTION_TYPE_CHOICES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
        (INVESTMENT, 'Investment'),
        (PROFIT, 'Profit'),
        (BONUS, 'Bonus'),
        (ADJUSTMENT, 'Adjustment'),
    ]
    
    # Payment methods
    MPESA = 'mpesa'
    CARD = 'card'
    BANK = 'bank'
    WALLET = 'wallet'
    
    PAYMENT_METHOD_CHOICES = [
        (MPESA, 'M-Pesa'),
        (CARD, 'Credit/Debit Card'),
        (BANK, 'Bank Transfer'),
        (WALLET, 'Wallet Balance'),
    ]
    
    # Status
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (COMPLETED, 'Completed'),
    ]

    # Fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_transactions')  # Changed
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='wallet_transactions') 
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default=DEPOSIT)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=MPESA)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    
    reference = models.CharField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} | {self.amount} | {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"TX{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)