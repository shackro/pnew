import datetime
from django.db import models
from django.conf import settings
from assets.models import Asset
from django.utils import timezone
import uuid

User = settings.AUTH_USER_MODEL



class Bonus(models.Model):
    """Bonus system for users"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='bonuses'  # This creates user.bonuses
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    TYPE_CHOICES = [
        ('welcome', 'Welcome Bonus'),
        ('deposit', 'Deposit Bonus'),
        ('referral', 'Referral Bonus'),
        ('promotion', 'Promotional Bonus'),
    ]
    
    bonus_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='promotion')
    is_claimed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Bonuses'


# -------------------------
# Investment
# -------------------------
class Investment(models.Model):
    STATUS_CHOICES = [
        ('active','Active'),
        ('closed','Closed'),
        ('pending_close','Pending Admin Approval'),
        ('cancelled','Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='user_investments'   # <- change to a unique name
    )
    asset = models.ForeignKey(
        Asset, 
        on_delete=models.CASCADE, 
        related_name='asset_investments'  # <- unique
    )

    invested_amount = models.DecimalField(max_digits=20, decimal_places=2)
    entry_price = models.DecimalField(max_digits=20, decimal_places=4)
    units = models.DecimalField(max_digits=20, decimal_places=8)

    duration_hours = models.PositiveIntegerField(default=3)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    profit_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.asset.symbol}"

    @property
    def is_active(self):
        return self.status == 'active'


class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    currency_preference = models.CharField(max_length=10, default="USD")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.subject} - {self.name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'