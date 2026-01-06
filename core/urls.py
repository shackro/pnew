from django.urls import path
from . import views
from investments.views import asset_detail

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('wallet', views.wallet, name='wallet'),
    path('bonus', views.bonus_list, name='bonus'),
    path('assets', views.assets_view, name='assets'),
    path('assets/<uuid:asset_id>/', asset_detail, name='asset_detail'),
    path('profile/', views.profile, name='profile'),
    path('assets/', views.assets_view, name='assets'),
    path('profile/', views.profile, name='profile'),
    path("switch-currency/", views.switch_currency, name="switch_currency"),
    path('number-carousel/', views.number_carousel_view, name='number_carousel'),
    path('newsletter/', views.newsletter_view, name='newsletter'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('contact/success/', views.contact_success_view, name='contact_success'),
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('faq/', views.faq_view, name='faq'),
]
