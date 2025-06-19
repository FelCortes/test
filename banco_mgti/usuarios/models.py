from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator

validar_rut_chileno = RegexValidator(
    regex=r'^\d{1,3}(?:\.\d{3}){2}-[\dkK]$',
    message="Formato inválido. Use: 12.345.678-9"
)

class CustomUser(AbstractUser):
    rut = models.CharField(
        _('RUT'),
        max_length=12,
        unique=True,
        validators=[validar_rut_chileno],
        help_text="Formato: 12.345.678-9"
    )
    email = models.EmailField(_('email address'), blank=True)
    telefono = models.CharField(_('Teléfono'), max_length=15, blank=True)
    nombre_completo = models.CharField(_('Nombre completo'), max_length=100, blank=True)

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