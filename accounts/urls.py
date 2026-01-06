from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),

    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='auth/login.html'
        ),
        name='login'
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),
    
    path('My-profile', views.profile, name='profile'),
    path('profile/password/', views.change_password_view, name='change_password'),
    
    path('settings/', views.account_settings, name='settings'),
    path('update-theme/', views.update_theme, name='update-theme'),
]
