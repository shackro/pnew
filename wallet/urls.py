from django.urls import path
from .views import deposit, wallet_view, withdraw, claim_bonus

app_name = 'wallet'   # ✅ THIS IS REQUIRED

urlpatterns = [
    path('', wallet_view, name='wallet_view'), 
    path('deposit/', deposit, name='deposit'),
    path('withdraw/', withdraw, name='withdraw'),
    path('claim-bonus/', claim_bonus, name='claim_bonus'),
]
