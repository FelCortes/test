from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator

#google auth
from django_otp.plugins.otp_totp.models import TOTPDevice

validar_rut_chileno = RegexValidator(
    regex=r'^\d{1,3}(?:\.\d{3}){2}-[\dkK]$',
    message="Formato inválido. Use: 12.345.678-9"
)

class CustomUser(AbstractUser):
    username = None
    
    mfa_enabled = models.BooleanField(default=False)

    MFA_CHOICES = [
        ('totp', 'Google Authenticator - ¡Descarga la aplicación! (Recomendado para mayor seguridad)'),
        ('email', 'Código por correo'),
    ]
    
    mfa_method = models.CharField(
        max_length=10,
        choices=MFA_CHOICES,
        default='totp'
    )
    
    
    rut = models.CharField(
        _('RUT'),
        max_length=12,
        unique=True,
        validators=[validar_rut_chileno],
        help_text="Formato: 12.345.678-9",
        error_messages={
            'unique': 'Este RUT ya está registrado.'
        }
    )
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': 'Este correo electrónico ya está en uso.'
        }
    )
    telefono = models.CharField(
        _('Teléfono'),
        max_length=15,
        unique=True,
        error_messages={
            'unique': 'Este número de teléfono ya está registrado.'
        }
    )
    nombre_completo = models.CharField(
        _('Nombre completo'), 
        max_length=100,
        blank=True
    )
    
    saldo = models.IntegerField(
        _('Saldo'), 
        default=0,
        validators=[MinValueValidator(0)]
    )
    inversiones = models.IntegerField(
        _('Inversiones'), 
        default=0,
        validators=[MinValueValidator(0)]
    )
    tarjetas = models.IntegerField(
        _('Tarjetas'), 
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    USERNAME_FIELD = 'rut'  # pk login
    REQUIRED_FIELDS = ['nombre_completo', 'email']  # createsuperuser

    def __str__(self):
        return f"{self.nombre_completo} ({self.rut})"
    
    def setup_mfa(self):
        """Crea dispositivo TOTP y devuelve URL para QR"""
        device, created = TOTPDevice.objects.get_or_create(
            user=self, 
            name='default',
            confirmed=False  # requiere verificacion
        )
        if created:
            return device.config_url    # url para qr
        return None