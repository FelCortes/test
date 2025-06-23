from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.custom_logout, name='logout'),
    path('', views.user_login, name='home'),
    
    path('setup-mfa/', views.setup_mfa, name='setup_mfa'),
    path('verify-mfa/', views.verify_mfa, name='verify_mfa'),
    path('setup-mfa-email/', views.setup_mfa_email, name='setup_mfa_email'),
    path('configurar-totp/', views.setup_mfa, name='setup_mfa'),
    path('mfa/choose/', views.choose_mfa_method, name='choose_mfa_method'),

    path('recuperar-cuenta/', views.recuperar_cuenta_rut, name='recuperar_cuenta'),
    path('recuperar/verificar/', views.choose_mfa_recuperar, name='choose_mfa_recuperar'),
    path('recuperar/verificar/email/', views.setup_mfa_email_recuperar, name='setup_mfa_email_recuperar'),
    path('recuperar/verificar/totp/', views.verify_mfa_recuperar, name='verify_mfa_recuperar'),
    path('recuperar/cambiar-clave/', views.actualizar_password, name='actualizar_password'),
]