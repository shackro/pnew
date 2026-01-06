# investments/models.py
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal


User = settings.AUTH_USER_MODEL

class Investment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE)
    
    invested_amount = models.DecimalField(max_digits=20, decimal_places=2)
    duration_hours = models.PositiveIntegerField(default=3)
    
    # Time tracking
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Returns
    expected_return_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    actual_profit_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0.0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.asset.name} - {self.invested_amount}"
    
    def save(self, *args, **kwargs):
        if not self.end_time and self.duration_hours:
            self.end_time = self.start_time + timezone.timedelta(hours=self.duration_hours)
        
        if not self.expected_return_rate and self.asset and self.duration_hours:
            self.expected_return_rate = self.asset.get_return_rate(self.duration_hours)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if investment has expired"""
        if self.status != 'active':
            return False
        return timezone.now() >= self.end_time
    
    @property
    def time_remaining(self):
        """Get time remaining in hours"""
        if self.status != 'active':
            return 0
        remaining = self.end_time - timezone.now()
        return max(0, remaining.total_seconds() / 3600)  # Convert to hours
    
    @property
    def expected_profit(self):
        """Calculate expected profit"""
        return (self.invested_amount * self.expected_return_rate) / 100
    
    def complete_investment(self):
        """Complete the investment and calculate actual profit"""
        if self.status != 'active':
            return
        
        # Simulate profit/loss based on market conditions
        import random
        from decimal import Decimal
        
        # Base profit based on expected return
        base_profit = self.expected_profit
        
        # Add some randomness (±20%)
        random_factor = Decimal(str(random.uniform(0.8, 1.2)))
        self.actual_profit_loss = base_profit * random_factor
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Update user's wallet
        wallet = self.user.wallet
        total_amount = self.invested_amount + self.actual_profit_loss
        
        wallet.locked_balance -= self.invested_amount
        wallet.available_balance += total_amount
        wallet.save()
        
        # Create transaction record
        from wallet.models import Transaction
        Transaction.objects.create(
            user=self.user,
            wallet=wallet,
            transaction_type='profit',
            payment_method='system',
            amount=self.actual_profit_loss,
            status='completed',
            description=f"Profit from {self.asset.name} investment"
        )
        
        return self.actual_profit_loss