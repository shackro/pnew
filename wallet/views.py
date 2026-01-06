from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Transaction, Wallet
from core.utils.currency import convert_from_usd, get_user_currency
from wallet.forms import DepositForm, WithdrawalForm

# Helper function to get or create wallet
def get_user_wallet(user):
    """Get or create wallet for user"""
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={
            'available_balance': Decimal('0.00'),
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    return wallet

@login_required
def wallet_view(request):
    """Main wallet dashboard"""
    wallet = get_user_wallet(request.user)
    currency = get_user_currency(request)

    
    # Convert wallet balances to user's currency
    wallet_data = {
        'available': convert_from_usd(wallet.available_balance, currency),
        'locked': convert_from_usd(wallet.locked_balance, currency),
        'bonus': convert_from_usd(wallet.bonus_balance, currency),
        'total': convert_from_usd(wallet.total_balance(), currency),
        'bonus_claimed': wallet.bonus_claimed,
    }
    
    # Get transactions
    recent_deposits = Transaction.objects.filter(
        user=request.user,
        transaction_type='deposit'
    ).order_by('-created_at')[:5]
    
    recent_withdrawals = Transaction.objects.filter(
        user=request.user,
        transaction_type='withdrawal'
    ).order_by('-created_at')[:5]
    
    recent_activity = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Convert transaction amounts for display
    def convert_transaction_amounts(transactions):
        for transaction in transactions:
            # transaction.amount is in USD, convert to user's currency
            transaction.display_amount = convert_from_usd(abs(transaction.amount), currency)
            
            # Add sign
            if transaction.transaction_type in ['deposit', 'profit', 'bonus']:
                transaction.display_sign = '+'
            else:
                transaction.display_sign = '-'
        return transactions
    
    recent_deposits = convert_transaction_amounts(recent_deposits)
    recent_withdrawals = convert_transaction_amounts(recent_withdrawals)
    recent_activity = convert_transaction_amounts(recent_activity)
    
    # Handle quick actions
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        action = request.POST.get('action')
        
        
        if amount <= 0:
            messages.error(request, "Please enter a valid amount")
        elif action == 'deposit':
            # User enters amount in their currency, convert to USD for storage
            amount_usd = amount / currency.exchange_rate
            
            wallet.available_balance += amount_usd
            wallet.save()
            
            # Create transaction
            Transaction.objects.create(
                user=request.user,
                wallet=wallet,
                transaction_type='deposit',
                payment_method='wallet',
                amount=amount_usd,  # Store in USD
                status='completed',
                description=f"Quick deposit of {currency.symbol}{amount:.2f}"
            )
            
            messages.success(request, f"Deposited {currency.symbol}{amount:.2f} successfully!")
            return redirect('wallet:wallet_view')  # Redirect to self
            
        elif action == 'withdraw':
            # User enters amount in their currency, convert to USD for check
            amount_usd = amount / currency.exchange_rate
            
            if wallet.available_balance >= amount_usd:
                wallet.available_balance -= amount_usd
                wallet.save()
                
                # Create transaction
                Transaction.objects.create(
                    user=request.user,
                    wallet=wallet,
                    transaction_type='withdrawal',
                    payment_method='wallet',
                    amount=-amount_usd,  # Negative for withdrawal
                    status='completed',
                    description=f"Quick withdrawal of {currency.symbol}{amount:.2f}"
                )
                
                messages.success(request, f"Withdrew {currency.symbol}{amount:.2f} successfully!")
                return redirect('wallet:wallet_view')
            else:
                messages.error(request, "Insufficient balance")
        else:
            messages.error(request, "Invalid action")
    
    context = {
        'wallet': wallet_data,
        'wallet_obj': wallet,
        'recent_deposits': recent_deposits,
        'recent_withdrawals': recent_withdrawals,
        'recent_activity': recent_activity,
        'recent_transactions': recent_activity,
        'currency': currency,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
    }
    
    return render(request, 'wallet.html', context)

@login_required
def deposit(request):
    """Deposit page with form"""
    wallet = get_user_wallet(request.user)
    currency = get_user_currency(request)
    
    form = DepositForm(currency=currency)
    
    if request.method == 'POST':
        form = DepositForm(request.POST, currency=currency)
        
        if form.is_valid():
            amount_display = form.cleaned_data['amount']  # In user's currency
            payment_method = form.cleaned_data['payment_method']
            
            # Convert to USD for storage
            amount_usd = amount_display / currency.exchange_rate
            
            # Update wallet
            wallet.available_balance += amount_usd
            wallet.save()
            
            # Create transaction
            Transaction.objects.create(
                user=request.user,
                wallet=wallet,
                transaction_type='deposit',
                payment_method=payment_method,
                amount=amount_usd,
                status='completed',
                description=f"Deposit of {currency.symbol}{amount_display:.2f} via {payment_method}"
            )
            
            messages.success(request, f"Deposit of {currency.symbol}{amount_display:.2f} successful!")
            return redirect('wallet:wallet_view')  # Change to your actual URL
    
    context = {
        'form': form,
        'wallet_balance': convert_from_usd(wallet.available_balance, currency),
        'currency_symbol': currency.symbol,
        'current_currency': currency,
    }
    
    return render(request, 'deposit.html', context)

@login_required
def withdraw(request):
    """Withdraw page with form"""
    wallet = get_user_wallet(request.user)
    currency = get_user_currency(request)
    
    # Get recent withdrawals
    withdrawals = Transaction.objects.filter(
        user=request.user,
        transaction_type='withdrawal'
    ).order_by('-created_at')[:5]
    
    # Create quick amounts
    wallet_balance_display = convert_from_usd(wallet.available_balance, currency)
    quick_amounts = []
    
    if wallet_balance_display > 0:
        percentages = [0.25, 0.5, 0.75, 1.0]
        for perc in percentages:
            amount = (wallet_balance_display * Decimal(str(perc))).quantize(Decimal('0.01'))
            if amount >= Decimal('1.00'):
                quick_amounts.append(amount)
    
    if not quick_amounts:
        quick_amounts = [Decimal('10.00'), Decimal('50.00'), Decimal('100.00'), 
                        Decimal('200.00'), Decimal('500.00'), Decimal('1000.00')]
    
    form = WithdrawalForm(currency=currency)
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST, currency=currency)
        
        if form.is_valid():
            amount_display = form.cleaned_data['amount']  # In user's currency
            payment_method = form.cleaned_data['payment_method']
            
            # Convert to USD for storage
            amount_usd = amount_display / currency.exchange_rate
            
            if 0 < amount_usd <= wallet.available_balance:
                wallet.available_balance -= amount_usd
                wallet.save()
                
                Transaction.objects.create(
                    user=request.user,
                    wallet=wallet,
                    transaction_type='withdrawal',
                    payment_method=payment_method,
                    amount=-amount_usd,
                    status='pending',
                    description=f"Withdrawal of {currency.symbol}{amount_display:.2f} via {payment_method}"
                )
                
                messages.success(request, f"Withdrawal request of {currency.symbol}{amount_display:.2f} submitted!")
                return redirect('wallet:wallet_view')  # Change to your actual URL
            else:
                messages.error(request, "Insufficient balance")
    
    # Convert withdrawals for display
    for w in withdrawals:
        w.display_amount = convert_from_usd(abs(w.amount), currency)
    
    context = {
        'form': form,
        'wallet': wallet,
        'wallet_balance': wallet_balance_display,
        'currency_symbol': currency.symbol,
        'current_currency': currency,
        'available_balance': wallet_balance_display,
        'quick_amounts': quick_amounts,
        'withdrawals': withdrawals,
    }
    
    return render(request, 'withdraw.html', context)

@login_required
def claim_bonus(request):
    wallet = get_user_wallet(request.user)
    
    if not wallet.bonus_claimed:
        wallet.bonus_balance += Decimal('500.00')
        wallet.bonus_claimed = True
        wallet.save()
        
        # Create bonus transaction
        Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            transaction_type='bonus',
            payment_method='system',
            amount=Decimal('500.00'),
            status='completed',
            description="Welcome bonus claimed"
        )
        
        messages.success(request, "Bonus claimed successfully!")
    else:
        messages.warning(request, "Bonus already claimed")
    
    return redirect('wallet:wallet_view')  # Change to your actual URL