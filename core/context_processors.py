from core.models import Currency
from core.utils.currency import get_user_currency
from wallet.models import Wallet

def currency_context(request):
    """
    Add currency data to all templates automatically.
    """
    # Use the same logic as get_user_currency
    currency = get_user_currency(request)
    
    return {
        'available_currencies': Currency.objects.filter(is_active=True),
        'current_currency': currency,
    }
    

def get_currency_context(user):
    """Get currency context for a user"""
    try:
        wallet = Wallet.objects.get(user=user)
        currency_code = wallet.currency or "USD"
    except Wallet.DoesNotExist:
        currency_code = "USD"
    
    current_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()

    currency_code = current_currency.code
    currency_symbol = current_currency.symbol  # FIX: Get symbol from currency object

    return wallet, currency_code, currency_symbol