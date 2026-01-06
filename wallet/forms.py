# wallet/forms.py
from decimal import ROUND_HALF_UP, Decimal
from django import forms
from .models import Transaction
from core.utils.currency import convert_from_usd

class DepositForm(forms.Form):  # Changed from ModelForm to Form
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
    ]
    
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        self.currency = kwargs.pop('currency', None)
        self.base_min_amount_usd = kwargs.pop('base_min_amount_usd', Decimal('1.00'))
        super().__init__(*args, **kwargs)
        
        if self.currency:
            # Convert minimum amount from USD to user's currency
            min_amount_display = convert_from_usd(self.base_min_amount_usd, self.currency)
            
            self.fields['amount'].widget.attrs.update({
                'min': str(min_amount_display.quantize(Decimal('0.01'))),
                'step': '0.01',
                'placeholder': f'Minimum: {self.currency.symbol}{min_amount_display:.2f}'
            })
            self.fields['amount'].min_value = min_amount_display
            self.fields['amount'].label = f"Amount ({self.currency.symbol})"



class WithdrawalForm(forms.Form):
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('paypal', 'Paypal'),
    ]
    
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-transparent',
            'placeholder': 'Enter amount',
            'id': 'id_amount'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-transparent',
            'id': 'id_payment_method'
        })
    )
    
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-transparent',
            'placeholder': 'Phone number (for M-Pesa)',
            'id': 'id_phone_number'
        })
    )
    
    bank_account = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-transparent',
            'placeholder': 'Bank account details',
            'id': 'id_bank_account'
        })
    )

    def __init__(self, *args, **kwargs):
        self.currency = kwargs.pop('currency', None)
        self.user = kwargs.pop('user', None)
        self.base_min_amount_usd = kwargs.pop('base_min_amount_usd', Decimal('1.00'))
        super().__init__(*args, **kwargs)
        
        if self.currency:
            # Convert minimum amount from USD to user's currency
            min_amount_display = convert_from_usd(self.base_min_amount_usd, self.currency)
            
            self.fields['amount'].widget.attrs.update({
                'min': str(min_amount_display.quantize(Decimal('0.01'))),
                'step': '0.01',
                'placeholder': f'Minimum: {self.currency.symbol}{min_amount_display:.2f}'
            })
            self.fields['amount'].min_value = min_amount_display
            self.fields['amount'].label = f"Amount ({self.currency.symbol})"
        
        # Show phone field only for M-Pesa
        if 'payment_method' in self.data:
            payment_method = self.data.get('payment_method')
            if payment_method == 'mpesa':
                self.fields['phone_number'].required = True
            elif payment_method == 'bank':
                self.fields['bank_account'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        phone_number = cleaned_data.get('phone_number')
        bank_account = cleaned_data.get('bank_account')
        
        if payment_method == 'mpesa' and not phone_number:
            self.add_error('phone_number', 'Phone number is required for M-Pesa withdrawals.')
        
        if payment_method == 'bank' and not bank_account:
            self.add_error('bank_account', 'Bank account details are required for bank transfers.')
        
        return cleaned_data
    
    

ALLOWED_HOURS = [3, 4, 6, 8, 10, 12, 16, 18, 22]


class InvestmentForm(forms.Form):
    """
    Form that accepts amount in the user's selected currency (display currency).
    Amount is entered in display currency (e.g. KES, USD) and later converted to USD for storage.
    """

    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal('1.00'),
        error_messages={
            "required": "Enter an amount.",
            "min_value": "Amount must be at least %(limit_value)s."
        }
    )

    duration_hours = forms.ChoiceField(choices=[(h, f"{h} hours") for h in ALLOWED_HOURS])

    confirm = forms.BooleanField(required=True, label="I confirm this investment")

    def __init__(self, *args, **kwargs):
        """
        kwargs:
            currency: Currency object (for display conversion)
            min_investment_usd: Decimal (minimum in USD)
        """
        self.currency = kwargs.pop('currency', None)
        self.min_investment_usd = kwargs.pop('min_investment_usd', Decimal('10.00'))
        super().__init__(*args, **kwargs)

        if self.currency:
            # Convert minimum investment from USD to display currency
            min_display = convert_from_usd(self.min_investment_usd, self.currency)
            min_display = min_display.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Set widget attributes
            self.fields['amount'].widget = forms.NumberInput(attrs={
                'min': str(min_display),
                'step': '0.01',
                'class': 'form-control',
                'placeholder': f'{self.currency.symbol}{min_display:.2f}',
                'inputmode': 'decimal',
            })

            # Server-side validation
            self.fields['amount'].min_value = min_display

            # Update label with currency symbol
            self.fields['amount'].label = f"Investment Amount ({self.currency.symbol})"

        # Set default duration
        default_duration = kwargs.get('initial', {}).get('duration_hours', ALLOWED_HOURS[0])
        self.fields['duration_hours'].initial = str(default_duration)

        # Style the checkbox
        self.fields['confirm'].widget = forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })

    def clean_amount(self):
        """
        Validate amount in display currency
        """
        raw = self.cleaned_data.get('amount')
        if raw is None:
            raise forms.ValidationError("Enter an amount.")

        # Ensure Decimal
        amount = Decimal(str(raw))
        
        # Quantize to 2 decimal places
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Get minimum from field (already converted to display currency)
        min_allowed = self.fields['amount'].min_value
        
        if amount < min_allowed:
            if self.currency:
                raise forms.ValidationError(
                    f"Minimum investment is {self.currency.symbol}{min_allowed:.2f}"
                )
            else:
                raise forms.ValidationError(f"Minimum investment is {min_allowed}")

        return amount

    def clean_duration_hours(self):
        value = self.cleaned_data.get('duration_hours')
        try:
            hrs = int(value)
        except (TypeError, ValueError):
            raise forms.ValidationError("Invalid duration selected.")

        if hrs not in ALLOWED_HOURS:
            raise forms.ValidationError(f"Duration must be one of: {', '.join(map(str, ALLOWED_HOURS))}")
        return hrs

    def clean(self):
        """
        Additional validation: ensure confirmation is checked
        """
        cleaned_data = super().clean()
        confirm = cleaned_data.get('confirm')
        
        if not confirm:
            raise forms.ValidationError("You must confirm the investment.")
        
        return cleaned_data


class QuickInvestForm(forms.Form):
    quick_amount = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.currency = kwargs.pop('currency', None)
        super().__init__(*args, **kwargs)
        
        if self.currency:
            self.fields['quick_amount'].label = f"Amount ({self.currency.symbol})"


# class ContactForm(forms.ModelForm):
#     class Meta:
#         model = ContactMessage
#         fields = ['name', 'email', 'subject', 'message']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'email': forms.EmailInput(attrs={'class': 'form-control'}),
#             'subject': forms.TextInput(attrs={'class': 'form-control'}),
#             'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
#         }