from django.urls import path
from . import views

app_name = 'investments'

urlpatterns = [
    path('assets/<uuid:asset_id>/', views.asset_detail, name='asset_detail'),
    path('asset/<uuid:asset_id>/invest/', views.invest_asset, name='invest_asset'),  # UUID
    path('active/', views.active_investments, name='active_investments'),
    path('history/', views.investment_history, name='history'),
    path('withdraw/<uuid:investment_id>/', views.withdraw_investment, name='withdraw'),  # Also UUID
]