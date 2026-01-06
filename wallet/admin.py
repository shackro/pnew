from django.contrib import admin
from .models import Wallet

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'available_balance', 'bonus_balance', 'bonus_claimed')
    search_fields = ('user__username',)
