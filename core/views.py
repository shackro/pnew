from datetime import datetime, timedelta
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from assets.models import Asset
from core.forms import ContactForm
from core.models import Currency, Investment
from core.services.price_fetcher import PriceFetcher
from core.utils.currency import convert_from_usd, get_user_currency
from wallet.models import Wallet, Transaction
from django.contrib import messages
from pyexpat.errors import messages as pyexpat_messages 


@login_required
def switch_currency(request):
    if request.method == "POST":
        code = request.POST.get("currency")
        try:
            currency = Currency.objects.get(code=code, is_active=True)
            
            # Update user's wallet currency preference
            wallet = Wallet.objects.get(user=request.user)
            wallet.currency = currency.code
            wallet.save()
            
            # Set cookie for consistency
            response = redirect(request.META.get("HTTP_REFERER", "/"))
            response.set_cookie('currency', currency.code, max_age=30*24*60*60)
            return response
            
        except Currency.DoesNotExist:
            # If currency doesn't exist, redirect without changes
            pass
    
    return redirect(request.META.get("HTTP_REFERER", "/"))

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


@login_required
def dashboard(request):
    """Main dashboard with assets preview"""
    # Get or create wallet
    wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={
            'available_balance': Decimal('0.00'),  # Give some starting balance
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    
    if created:
        messages.info(request, 'Welcome! Your wallet has been created')
    
    currency = get_user_currency(request)
    
    # =========================
    # WALLET CONVERSION (USD → selected currency)
    # =========================
    wallet_data = {
        'available': convert_from_usd(wallet.available_balance, currency),
        'locked': convert_from_usd(wallet.locked_balance, currency),
        'bonus': convert_from_usd(wallet.bonus_balance, currency),
        'total': convert_from_usd(wallet.total_balance(), currency),
    }
    

    # =========================
    # INVESTMENTS
    # =========================
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    )
    
    completed_investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active')
    
    # =========================
    # PnL CALCULATION (USD → currency)
    # =========================
    total_profit_usd = completed_investments.filter(
        profit_loss__gt=0
    ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
    
    total_loss_usd = completed_investments.filter(
        profit_loss__lt=0
    ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
    
    net_pl_usd = total_profit_usd + total_loss_usd
    
    invested_total_usd = completed_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    
    net_pl_percentage = (
        (net_pl_usd / invested_total_usd) * 100
        if invested_total_usd > 0 else 0
    )
    
    # =========================
    # CONVERT PnL TO USER'S CURRENCY
    # =========================
    investment_stats = {
        'total_profit': convert_from_usd(total_profit_usd, currency),
        'total_loss': convert_from_usd(total_loss_usd, currency),
        'net_pl': convert_from_usd(net_pl_usd, currency),
        'net_pl_percentage': round(net_pl_percentage, 2),
        'progress_width': min(abs(net_pl_percentage), 100),
        'active_investments': active_investments.count(),
    }
    
    # =========================
    # TRANSACTIONS - CRITICAL FIX
    # =========================
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Convert transaction amounts for display
    for transaction in recent_transactions:
        # Store both the original amount and converted amount
        transaction.original_amount = transaction.amount  # USD amount
        transaction.display_amount = convert_from_usd(transaction.amount, currency)  # Converted amount
        transaction.display_currency_symbol = currency.symbol
    
    # =========================
    # MARKET ASSETS FOR DASHBOARD (4-6 featured assets)
    # =========================
    from assets.models import Asset
    
    # Get top 6 active assets (mix of categories)
    market_assets = Asset.objects.filter(is_active=True).order_by('?')[:8]
    
    # Add display prices in user's currency
    for asset in market_assets:
        asset.display_price = convert_from_usd(asset.current_price, currency)
        asset.display_min_investment = convert_from_usd(asset.min_investment, currency)
        asset.display_max_investment = convert_from_usd(asset.max_investment, currency)
        asset.last_updated_str = asset.last_updated.strftime("%H:%M:%S") if asset.last_updated else "Never"
        
        # Add investment hours options with expected returns
        asset.ALLOWED_HOURS = [
            {'hours': 1, 'label': '1 hour', 'return_rate': asset.return_rate_1h},
            {'hours': 3, 'label': '3 hours', 'return_rate': asset.return_rate_3h},
            {'hours': 6, 'label': '6 hours', 'return_rate': asset.return_rate_6h},
            {'hours': 12, 'label': '12 hours', 'return_rate': asset.return_rate_12h},
            {'hours': 24, 'label': '24 hours', 'return_rate': asset.return_rate_24h},
        ]
        asset.duration_hours_default = 3
    
    # Calculate example returns for minimum investment
        example_investment = asset.min_investment
        asset.example_returns = {}
        for duration in asset.ALLOWED_HOURS:
            profit = asset.calculate_profit(example_investment, duration['hours'])
            asset.example_returns[duration['hours']] = {
                'profit_usd': profit,
                'profit_display': convert_from_usd(profit, currency),
                'total_usd': example_investment + profit,
                'total_display': convert_from_usd(example_investment + profit, currency),
            }
            
    # =========================
    # INVESTMENT FORM
    # =========================
    from django import forms
    
    class QuickInvestmentForm(forms.Form):
        """Quick investment form for dashboard"""
        amount = forms.DecimalField(
            max_digits=20,
            decimal_places=2,
            min_value=Decimal('10.00'),
            widget=forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm',
                'placeholder': f'Min: {currency.symbol}10.00',
                'step': '0.01'
            })
        )
        
        duration_hours = forms.ChoiceField(
            choices=[(1, '1 hour'), (3, '3 hours'), (6, '6 hours'), (12, '12 hours'), (24, '24 hours')],
            initial=3,
            widget=forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm'
            })
        )
    
    investment_form = QuickInvestmentForm()
    
    context = {
        'wallet': wallet_data,
        'investment_stats': investment_stats,
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'recent_transactions': recent_transactions,
        'market_assets': market_assets,
        'investment_form': investment_form,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'available_currencies': Currency.objects.filter(is_active=True),
        'current_currency': currency,
    }
    
    return render(request, 'home.html', context)



@login_required
def profile(request):
    """
    User profile page.
    NO financial logic here.
    """
    user = request.user

    context = {
        'user': user,
    }

    return render(request, 'accounts/profile.html', context)


@login_required
def home(request):
    """Main dashboard"""
    # FIX: Get or create wallet instead of just getting it
    wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={
            'available_balance': Decimal('0.00'),
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    
    currency = get_user_currency(request)
    
    # =========================
    # WALLET CONVERSION (USD → selected currency)
    # =========================
    wallet_data = {
        'available': convert_from_usd(wallet.available_balance, currency),
        'locked': convert_from_usd(wallet.locked_balance, currency),
        'bonus': convert_from_usd(wallet.bonus_balance, currency),
        'total': convert_from_usd(wallet.total_balance(), currency),
    }
    

    # =========================
    # INVESTMENTS
    # =========================
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    )
    
    completed_investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active')
    
    # =========================
    # PnL CALCULATION (USD → currency)
    # =========================
    total_profit_usd = completed_investments.filter(
        profit_loss__gt=0
    ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
    
    total_loss_usd = completed_investments.filter(
        profit_loss__lt=0
    ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
    
    net_pl_usd = total_profit_usd + total_loss_usd
    
    invested_total_usd = completed_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    
    net_pl_percentage = (
        (net_pl_usd / invested_total_usd) * 100
        if invested_total_usd > 0 else 0
    )
    
    # =========================
    # CONVERT PnL TO USER'S CURRENCY
    # =========================
    investment_stats = {
        'total_profit': convert_from_usd(total_profit_usd, currency),  # Converted!
        'total_loss': convert_from_usd(total_loss_usd, currency),      # Converted!
        'net_pl': convert_from_usd(net_pl_usd, currency),              # Converted!
        'net_pl_percentage': round(net_pl_percentage, 2),
        'progress_width': min(abs(net_pl_percentage), 100),
        'active_investments': active_investments.count(),
    }
    
    # =========================
    # TRANSACTIONS (If they store USD amounts)
    # =========================
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Convert transaction amounts if needed
    for transaction in recent_transactions:
        if hasattr(transaction, 'amount'):
            transaction.display_amount = convert_from_usd(transaction.amount, currency)
    
    context = {
        'wallet': wallet_data,  # ← This contains CONVERTED values
        'investment_stats': investment_stats,  # ← This contains CONVERTED values
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'recent_transactions': recent_transactions,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'available_currencies': Currency.objects.filter(is_active=True),
        'current_currency': currency,
    }
    
    return render(request, 'home.html', context)
    
    
@login_required
def wallet(request):
    # FIX: Get or create wallet
    user_wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={
            'available_balance': Decimal('0.00'),
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    
    currency = get_user_currency(request)
    
    # =========================
    # WALLET CONVERSION (USD → selected currency)
    # =========================
    # Use the SAME field names as in your dashboard view
    wallet_data = {
        'available': convert_from_usd(user_wallet.available_balance, currency),
        'locked': convert_from_usd(user_wallet.locked_balance, currency),
        'bonus': convert_from_usd(user_wallet.bonus_balance, currency),
        'total': convert_from_usd(user_wallet.total_balance(), currency),
    }
    
    # =========================
    # INVESTMENTS
    # =========================
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    )
    
    completed_investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active')
    
    # =========================
    # PnL CALCULATION (USD → currency)
    # =========================
    total_profit_usd = completed_investments.filter(
        profit_loss__gt=0
    ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
    
    total_loss_usd = completed_investments.filter(
        profit_loss__lt=0
    ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
    
    net_pl_usd = total_profit_usd + total_loss_usd
    
    invested_total_usd = completed_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    
    net_pl_percentage = (
        (net_pl_usd / invested_total_usd) * 100
        if invested_total_usd > 0 else 0
    )
    
    # =========================
    # CONVERT PnL TO USER'S CURRENCY
    # =========================
    investment_stats = {
        'total_profit': convert_from_usd(total_profit_usd, currency),
        'total_loss': convert_from_usd(total_loss_usd, currency),
        'net_pl': convert_from_usd(net_pl_usd, currency),
        'net_pl_percentage': round(net_pl_percentage, 2),
        'progress_width': min(abs(net_pl_percentage), 100),
        'active_investments': active_investments.count(),
    }
    
    # =========================
    # TRANSACTIONS
    # =========================
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]  # Show more transactions on wallet page
    
    # Convert transaction amounts
    for transaction in recent_transactions:
        if hasattr(transaction, 'amount'):
            transaction.display_amount = convert_from_usd(transaction.amount, currency)
    
    # =========================
    # CONTEXT (Use consistent naming with dashboard)
    # =========================
    context = {
        'wallet': wallet_data,  # Same key as dashboard for consistency
        'wallet_model': user_wallet,  # The actual model instance
        'investment_stats': investment_stats,
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'recent_transactions': recent_transactions,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'available_currencies': Currency.objects.filter(is_active=True),
        'current_currency': currency,
    }

    return render(request, "wallet.html", context)

@login_required
def assets_view(request):
    """Main assets page with manual price updates"""
    
    # FIX: Get or create wallet
    wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={
            'available_balance': Decimal('0.00'),
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    
    currency = get_user_currency(request)
    
    # Check if we should update prices
    refresh = request.GET.get('refresh', 'false').lower() == 'true'
    update_all = request.GET.get('update_all', 'false').lower() == 'true'
    
    if update_all:
        # Update all prices
        updated_count = PriceFetcher.update_all_prices()
        messages.success(request, f'Updated prices for {updated_count} assets')
        return redirect('core:assets')
    
    # =========================
    # WALLET SUMMARY
    # =========================
    wallet_balance = convert_from_usd(wallet.available_balance, currency)
    wallet_equity = convert_from_usd(wallet.locked_balance, currency)
    
    user_investments = Investment.objects.filter(user=request.user)
    
    total_invested_usd = user_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    total_invested = convert_from_usd(total_invested_usd, currency)
    
    total_profit_loss_usd = user_investments.aggregate(
        total=Sum('profit_loss')
    )['total'] or Decimal('0')
    total_profit_loss = convert_from_usd(total_profit_loss_usd, currency)
    
    # =========================
    # GET ASSETS WITH OPTIONAL UPDATE
    # =========================
    
    # Update stale prices (older than 5 minutes)
    stale_assets = Asset.objects.filter(
        is_active=True,
        last_updated__lt=datetime.now() - timedelta(minutes=5)  # FIXED: Use timedelta directly
    )[:10]  # Update max 10 at a time
    
    if stale_assets.exists() and refresh:
        for asset in stale_assets:
            PriceFetcher.update_asset_price(asset)
        messages.info(request, f'Refreshed {len(stale_assets)} stale prices')
    
    # Get all active assets
    market_assets = Asset.objects.filter(is_active=True).order_by('display_order', 'name')
    
    # Add display prices in user's currency
    for asset in market_assets:
        asset.display_price = convert_from_usd(asset.current_price, currency)
        asset.display_min_investment = convert_from_usd(asset.min_investment, currency)
        asset.display_max_investment = convert_from_usd(asset.max_investment, currency)
        asset.last_updated_str = asset.last_updated.strftime("%H:%M:%S") if asset.last_updated else "Never"
    
    # =========================
    # CATEGORY FILTERS
    # =========================
    category = request.GET.get('category', 'all')
    if category != 'all':
        market_assets = market_assets.filter(category=category)
    
    # Group by category for the category filter
    categories = [
        {'id': 'all', 'name': 'All Assets', 'count': Asset.objects.filter(is_active=True).count()},
        {'id': 'crypto', 'name': 'Cryptocurrency', 'count': Asset.objects.filter(category='crypto', is_active=True).count()},
        {'id': 'forex', 'name': 'Forex', 'count': Asset.objects.filter(category='forex', is_active=True).count()},
        {'id': 'futures', 'name': 'Futures', 'count': Asset.objects.filter(category='futures', is_active=True).count()},
        {'id': 'stock', 'name': 'Stocks', 'count': Asset.objects.filter(category='stock', is_active=True).count()},
    ]
    
    # =========================
    # TOP GAINERS & LOSERS
    # =========================
    sorted_assets = sorted(
        market_assets,
        key=lambda x: x.change_percentage,
        reverse=True
    )
    
    top_gainers = sorted_assets[:5]
    top_losers = sorted_assets[-5:]
    
    # =========================
    # EDUCATIONAL TIPS
    # =========================
    educational_tips = [
        {
            'title': 'Click Refresh for Latest Prices',
            'content': 'Prices update automatically every 5 minutes, or click refresh for immediate updates.'
        },
        {
            'title': 'Filter by Asset Type',
            'content': 'Use the category filter to focus on specific asset classes.'
        },
        {
            'title': 'Start with Minimum Investment',
            'content': 'Begin with the minimum amount to learn before investing more.'
        },
        {
            'title': 'Watch Top Gainers/Losers',
            'content': 'Monitor these sections for market trends and opportunities.'
        }
    ]
    
    context = {
        # Wallet Summary
        'wallet_balance': wallet_balance,
        'wallet_equity': wallet_equity,
        'total_invested': total_invested,
        'total_profit_loss': total_profit_loss,
        
        # Assets Data
        'market_assets': market_assets,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'categories': categories,
        'selected_category': category,
        
        # Educational
        'educational_tips': educational_tips,
        
        # Currency
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'current_currency': currency,
        'available_currencies': Currency.objects.filter(is_active=True),
        
        # Refresh info
        'last_refresh': datetime.now().strftime("%H:%M:%S"),
        'stale_count': stale_assets.count(),
    }
    
    return render(request, 'assets.html', context)



@login_required
def bonus_list(request):
    user = request.user
    
    # Get currency object
    currency = get_user_currency(request)
    
    # Get wallet
    try:
        wallet = Wallet.objects.get(user=user)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(
            user=user,
            available_balance=Decimal('0.00'),
            locked_balance=Decimal('0.00'),
            bonus_balance=Decimal('0.00'),
            bonus_claimed=Decimal('0.00'),
            currency='USD'
        )
    
    # Get investments - FIXED: Use the actual model name
    investments = Investment.objects.filter(user=user, status='active')
    
    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0.00')
    
    # Convert total invested to user's currency
    converted_total_invested = convert_from_usd(total_invested, currency)
    
    # Get available bonuses - FIXED: Check if Bonus model exists
    try:
        # Import Bonus model if needed
        from .models import Bonus
        
        available_bonuses = Bonus.objects.filter(user=user, is_claimed=False)
        
        # Get total bonuses earned
        total_bonuses = Bonus.objects.filter(user=user, is_claimed=True).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
    except ImportError:
        # If Bonus model doesn't exist, create dummy data
        available_bonuses = []
        total_bonuses = Decimal('0.00')
    
    # Convert bonuses for display
    converted_available = []
    for b in available_bonuses:
        converted_available.append({
            'id': b.id,
            'title': b.title,
            'amount': convert_from_usd(b.amount, currency),
            'description': b.description,
            'bonus_type': b.get_bonus_type_display(),
        })
    
    # Convert totals
    converted_total_bonuses = convert_from_usd(total_bonuses, currency)
    converted_wallet_balance = convert_from_usd(wallet.available_balance, currency)
    
    # Calculate available balance
    wallet_balance = converted_wallet_balance - converted_total_invested
    
    # Handle bonus claiming
    if request.method == 'POST':
        bonus_id = request.POST.get('bonus_id')
        try:
            # Import Bonus model
            from .models import Bonus
            from wallet.models import Transaction
            
            bonus = Bonus.objects.get(id=bonus_id, user=user, is_claimed=False)
            
            # Add bonus to wallet (in USD)
            wallet.available_balance += bonus.amount
            wallet.save()
            
            # Create transaction record
            Transaction.objects.create(
                user=user,
                wallet=wallet,
                transaction_type='bonus',
                payment_method='system',
                amount=bonus.amount,
                status='completed',
                description=f"Claimed bonus: {bonus.title}"
            )
            
            # Mark bonus as claimed
            bonus.is_claimed = True
            bonus.save()
            
            messages.success(request, f'Bonus "{bonus.title}" claimed successfully!')
            return redirect('core:bonus_list')
            
        except Exception as e:
            messages.error(request, f'Error claiming bonus: {str(e)}')
    
    context = {
        'wallet_balance': wallet_balance,
        'currency_symbol': currency.symbol,
        'available_bonuses': converted_available,
        'total_bonuses_earned': converted_total_bonuses,
        'currency': currency,
        'has_bonuses': len(converted_available) > 0,
    }
    
    return render(request, 'bonus.html', context)


def number_carousel_view(request):
    # Get user's currency
    currency = get_user_currency(request)
    
    # Generate random numbers for the carousel
    import random
    numbers = []
    
    # Generate amounts in USD first, then convert to user's currency
    for _ in range(20):
        # Generate amount in USD
        amount_usd = random.randint(50, 1000)  # USD amounts
        
        # Convert to user's currency
        amount_converted = convert_from_usd(amount_usd, currency)
        
        numbers.append({
            'phone': f"+254 7{random.randint(10, 99)} xxx {random.randint(10, 99)}",
            'profit': random.choice([25, 22, -3, -43, 50, 75, -15, -30, 10, 35, -5, 60, -2, -28, 2, 90, -45, 20, -10, 45, 5, -20, 30]),
            'amount': float(amount_converted),  # Convert to float for JSON serialization
            'amount_usd': amount_usd,
            'currency_symbol': currency.symbol,
            'currency_code': currency.code,
        })
    
    return JsonResponse({'numbers': numbers})


def newsletter_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # In production, save to database or send to email service
            messages.success(request, 'Thank you for subscribing to our newsletter!')
        else:
            messages.error(request, 'Please provide a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))

def about_view(request):
    return render(request, 'core/about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('core:contact_success')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})

def contact_success_view(request):
    return render(request, 'core/contact_success.html')

def terms_view(request):
    return render(request, 'core/terms.html')

def privacy_view(request):
    return render(request, 'core/privacy.html')

def faq_view(request):
    return render(request, 'core/faq.html')

