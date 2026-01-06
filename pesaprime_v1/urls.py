from django import views
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='home'),
    path('core/', include('core.urls', namespace='core')),
    path('wallet/', include('wallet.urls', namespace='wallet')),
    path('investments/', include('investments.urls', namespace='investments')),

    path('accounts/', include('accounts.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
