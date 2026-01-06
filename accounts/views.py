from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from accounts.models import UserProfile
from core.models import Investment
from core.utils.currency import convert_from_usd, get_user_currency
from wallet.models import Wallet
from .forms import PasswordChangeForm, ProfileUpdateForm, RegisterForm, UserUpdateForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(request, 'Account created successfully.')
            return redirect('core:home')

    return render(request, 'auth/register.html', {'form': form})


@login_required
def profile(request):
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Get user's currency
    currency = get_user_currency(request)
    
    # Get user's wallet
    try:
        wallet = Wallet.objects.get(user=request.user)
        wallet_balance = convert_from_usd(wallet.available_balance, currency)
        wallet_equity = convert_from_usd(wallet.locked_balance, currency)
    except Wallet.DoesNotExist:
        wallet_balance = Decimal('0')
        wallet_equity = Decimal('0')
    
    # Get investment stats
    investments = Investment.objects.filter(user=request.user)
    
    # Calculate total invested
    total_invested_usd = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    total_invested = convert_from_usd(total_invested_usd, currency)
    
    # Calculate total profit/loss
    total_profit_loss_usd = investments.aggregate(
        total=Sum('profit_loss')
    )['total'] or Decimal('0')
    total_profit_loss = convert_from_usd(total_profit_loss_usd, currency)
    
    # Handle form submissions
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'wallet': wallet if 'wallet' in locals() else None,
        'wallet_balance': wallet_balance,
        'wallet_equity': wallet_equity,
        'total_invested': total_invested,
        'total_profit_loss': total_profit_loss,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'current_currency': currency,
        'profile': profile,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def account_settings(request):
    """
    Reserved for future:
    - Change password
    - Update email
    - KYC
    """
    return render(request, 'auth/settings.html')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            
            if user.check_password(current_password):
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('accounts:profile')
            else:
                form.add_error('current_password', 'Current password is incorrect.')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})


@csrf_exempt
def update_theme(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        theme = data.get('theme')
        request.user.profile.theme = theme  # assuming user has profile with theme field
        request.user.profile.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)

