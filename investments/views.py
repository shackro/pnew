from datetime import datetime,timedelta, timezone
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal

from assets.models import Asset
from wallet.models import Transaction, Wallet
from core.utils.currency import get_user_currency, convert_from_usd
from .models import Investment

@login_required
def asset_detail(request, asset_id):  # asset_id is UUID
    """View asset details for potential investment"""
    import random
    from decimal import Decimal
    from django.utils import timezone
    
    asset = get_object_or_404(Asset, id=asset_id)
    currency = get_user_currency(request)
    
    # Get user's wallet for balance display
    try:
        wallet = Wallet.objects.get(user=request.user)
        wallet_balance_display = convert_from_usd(wallet.available_balance, currency)
    except Wallet.DoesNotExist:
        wallet_balance_display = Decimal('0.00')
    
    # Convert prices to user's currency
    current_price = getattr(asset, 'current_price', Decimal('100.00'))
    min_investment = getattr(asset, 'min_investment', Decimal('10.00'))
    max_investment = getattr(asset, 'max_investment', Decimal('10000.00'))
    
    asset.display_price = convert_from_usd(current_price, currency)
    asset.display_min_investment = convert_from_usd(min_investment, currency)
    asset.display_max_investment = convert_from_usd(max_investment, currency)
    
    # Get allowed durations and calculate expected returns
    # Use default durations if none specified
    if hasattr(asset, 'allowed_durations') and asset.allowed_durations:
        allowed_hours = asset.allowed_durations
    else:
        allowed_hours = [1, 3, 6, 12, 24]
    
    # Create duration options with returns
    duration_options = []
    for hours in allowed_hours:
        # Get return rate for this duration
        if hasattr(asset, f'return_rate_{hours}h'):
            return_rate = getattr(asset, f'return_rate_{hours}h')
        else:
            # Fallback rates based on hours
            fallback_rates = {
                1: Decimal('0.5'),
                3: Decimal('1.5'),
                6: Decimal('3.0'),
                12: Decimal('6.0'),
                24: Decimal('12.0')
            }
            return_rate = fallback_rates.get(hours, Decimal('1.0'))
        
        # Create label
        if hours == 1:
            label = "1 hour"
        elif hours < 24:
            label = f"{hours} hours"
        else:
            days = hours // 24
            label = f"{days} day{'s' if days > 1 else ''}"
        
        duration_options.append({
            'hours': hours,
            'label': label,
            'return_rate': return_rate,
            'return_percentage': return_rate,
        })
    
    # Sort by hours
    duration_options = sorted(duration_options, key=lambda x: x['hours'])
    
    # Add example calculations for minimum investment
    for option in duration_options:
        if hasattr(asset, 'calculate_profit'):
            profit_usd = asset.calculate_profit(min_investment, option['hours'])
        else:
            # Manual calculation (using Decimal)
            profit_usd = (min_investment * option['return_rate']) / Decimal('100')
        
        option['example_profit'] = {
            'usd': profit_usd,
            'display': convert_from_usd(profit_usd, currency),
            'total_usd': min_investment + profit_usd,
            'total_display': convert_from_usd(min_investment + profit_usd, currency),
        }
    
    # Get asset performance history (simulated)
    performance_history = []
    for i in range(30, 0, -1):
        # Simulate price fluctuations (convert float to Decimal)
        base_price = current_price
        fluctuation = Decimal(str(random.uniform(-0.05, 0.05)))  # Convert float to Decimal
        simulated_price = base_price * (Decimal('1') + fluctuation)
        
        performance_history.append({
            'date': timezone.now() - timezone.timedelta(days=i),
            'price': convert_from_usd(simulated_price, currency),
            'change': float(fluctuation * Decimal('100'))  # Convert to float for template
        })
    
    # Get similar assets
    similar_assets = Asset.objects.filter(
        category=asset.category,
        is_active=True
    ).exclude(id=asset.id).order_by('?')[:4]
    
    # Convert prices for similar assets
    for similar_asset in similar_assets:
        similar_asset.display_price = convert_from_usd(
            getattr(similar_asset, 'current_price', Decimal('100.00')),
            currency
        )
        similar_asset.display_min_investment = convert_from_usd(
            getattr(similar_asset, 'min_investment', Decimal('10.00')),
            currency
        )
    
    context = {
        'asset': asset,
        'currency_symbol': currency.symbol,
        'current_currency': currency,
        'wallet_balance': wallet_balance_display,
        'duration_options': duration_options,
        'performance_history': performance_history,
        'similar_assets': similar_assets,
        'default_duration': 3,  # Default selection
    }
    
    return render(request, 'investments/asset_detail.html', context)


@login_required
def invest_asset(request, asset_id):
    """Invest in a specific asset with duration"""
    if request.method == 'POST':
        asset = get_object_or_404(Asset, id=asset_id)
        currency = get_user_currency(request)
        
        try:
            # Get amount from form
            amount_display = Decimal(request.POST.get('amount', '0'))
            duration_hours = int(request.POST.get('duration_hours', 3))
            
            if amount_display <= 0:
                messages.error(request, 'Please enter a valid amount')
                return redirect('investments:asset_detail', asset_id=asset_id)
            
            # Get user's wallet
            wallet = Wallet.objects.get(user=request.user)
            
            # Convert amount from user's currency to USD for storage
            amount_usd = amount_display / currency.exchange_rate
            
            # Check minimum investment (in USD)
            min_investment_usd = getattr(asset, 'min_investment', 10)
            if amount_usd < min_investment_usd:
                min_investment_display = convert_from_usd(min_investment_usd, currency)
                messages.error(request, f'Minimum investment is {currency.symbol}{min_investment_display:.2f}')
                return redirect('investments:asset_detail', asset_id=asset_id)
            
            # Check if user has enough balance (compare USD to USD)
            if wallet.available_balance >= amount_usd:
                # Create investment with duration
                investment = Investment.objects.create(
                    user=request.user,
                    asset=asset,
                    invested_amount=amount_usd,
                    duration_hours=duration_hours,
                    status='active',
                    end_time=datetime.now() + timedelta(hours=duration_hours)
                )
                
                # Update wallet
                wallet.available_balance -= amount_usd
                wallet.locked_balance += amount_usd
                wallet.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=request.user,
                    wallet=wallet,
                    transaction_type='investment',
                    payment_method='wallet',
                    amount=-amount_usd,  # Negative for investment
                    status='completed',
                    description=f"Invested in {asset.name} for {duration_hours} hours"
                )
                
                messages.success(request, f'Successfully invested {currency.symbol}{amount_display:.2f} in {asset.name} for {duration_hours} hours')
                return redirect('core:assets')
            else:
                # Show helpful error message with both currencies
                available_display = convert_from_usd(wallet.available_balance, currency)
                messages.error(request, f'Insufficient balance. You have {currency.symbol}{available_display:.2f} available, trying to invest {currency.symbol}{amount_display:.2f}')
                
        except (ValueError, TypeError) as e:
            messages.error(request, f'Invalid amount specified: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('investments:asset_detail', asset_id=asset_id)

@login_required
def withdraw_investment(request, investment_id):  # investment_id is UUID
    """Withdraw from an investment"""
    investment = get_object_or_404(Investment, id=investment_id, user=request.user)
    
    if investment.status != 'active':
        messages.error(request, 'This investment is not active')
        return redirect('investments:active_investments')
    
    # Get user's wallet
    wallet = Wallet.objects.get(user=request.user)
    currency = get_user_currency(request)
    
    # Calculate total to withdraw (invested amount + profit)
    total_withdraw_usd = investment.invested_amount + investment.profit_loss
    
    # Update investment status
    investment.status = 'completed'
    investment.save()
    
    # Update wallet
    wallet.locked_balance -= investment.invested_amount
    wallet.balance += total_withdraw_usd
    wallet.save()
    
    total_withdraw_display = convert_from_usd(total_withdraw_usd, currency)
    messages.success(request, f'Successfully withdrew {currency.symbol}{total_withdraw_display:.2f}')
    
    return redirect('investments:history')


@login_required
def active_investments(request):
    """View all active investments"""
    investments = Investment.objects.filter(
        user=request.user,
        status='active'
    ).select_related('asset')
    
    currency = get_user_currency(request)
    
    # Convert amounts for display
    for investment in investments:
        investment.display_invested = convert_from_usd(investment.invested_amount, currency)
        investment.display_profit = convert_from_usd(investment.profit_loss, currency)
    
    context = {
        'investments': investments,
        'currency_symbol': currency.symbol,
    }
    
    return render(request, 'investments/active.html', context)

@login_required
def investment_history(request):
    """View investment history"""
    investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active').select_related('asset')
    
    currency = get_user_currency(request)
    
    # Convert amounts for display
    for investment in investments:
        investment.display_invested = convert_from_usd(investment.invested_amount, currency)
        investment.display_profit = convert_from_usd(investment.profit_loss, currency)
    
    context = {
        'investments': investments,
        'currency_symbol': currency.symbol,
    }
    
    return render(request, 'investments/history.html', context)