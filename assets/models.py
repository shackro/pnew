from datetime import datetime,timedelta
from decimal import Decimal
import uuid
from django.db import models


class Asset(models.Model):
    CATEGORY_CHOICES = [
        ('crypto', 'Cryptocurrency'),
        ('forex', 'Forex'),
        ('futures', 'Futures'),
        ('stock', 'Stock'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Price data
    current_price = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    previous_price = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    change_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Investment settings
    min_investment = models.DecimalField(max_digits=20, decimal_places=2, default=10)
    max_investment = models.DecimalField(max_digits=20, decimal_places=2, default=100000)
    
    # Last updated timestamp
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Display ordering
    display_order = models.PositiveIntegerField(default=0)
    
    icon = models.ImageField(upload_to='assets/icons/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    return_rate_1h = models.DecimalField(max_digits=5, decimal_places=2, default=0.5)  # 0.5% per hour
    return_rate_3h = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)  # 1.5% per 3 hours
    return_rate_6h = models.DecimalField(max_digits=5, decimal_places=2, default=3.0)  # 3.0% per 6 hours
    return_rate_12h = models.DecimalField(max_digits=5, decimal_places=2, default=6.0)  # 6.0% per 12 hours
    return_rate_24h = models.DecimalField(max_digits=5, decimal_places=2, default=12.0)  # 12.0% per 24 hours
    
    # Risk level
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('very_high', 'Very High Risk'),
    ]
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='medium')
    
    # Allowed investment durations (in hours)
    allowed_durations = models.JSONField(default=list)  # Store as list: [1, 3, 6, 12, 24]
    
    def get_return_rate(self, duration_hours):
        """Get return rate for a specific duration"""
        rates = {
            1: self.return_rate_1h,
            3: self.return_rate_3h,
            6: self.return_rate_6h,
            12: self.return_rate_12h,
            24: self.return_rate_24h,
        }
        return rates.get(duration_hours, Decimal('0.0'))
    
    def calculate_profit(self, invested_amount, duration_hours):
        """Calculate potential profit for an investment"""
        return_rate = self.get_return_rate(duration_hours)
        return (invested_amount * return_rate) / 100
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"
    
    def update_price(self, new_price):
        """Update price and calculate changes"""
        if self.current_price and new_price:
            self.previous_price = self.current_price
            self.current_price = new_price
            self.change_percentage = ((self.current_price - self.previous_price) / self.previous_price) * 100
        elif new_price:
            self.current_price = new_price
        self.save()
    
    def needs_update(self):
        """Check if price needs update (older than 5 minutes)"""
        if not self.last_updated:
            return True
        update_threshold = datetime.now() - timedelta(minutes=5)  # FIXED: Use timedelta
        return self.last_updated < update_threshold
    
    def get_icon_url(self):
        """Get icon URL or default"""
        if self.icon:
            return self.icon.url
        # Default icons based on category
        defaults = {
            'crypto': '/static/assets/crypto.png',
            'forex': '/static/assets/forex.png',
            'futures': '/static/assets/futures.png',
            'stock': '/static/assets/stock.png',
        }
        return defaults.get(self.category, '/static/assets/default.png')
    