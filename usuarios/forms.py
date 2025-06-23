from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import CustomUser

rut_validator = RegexValidator(
    regex=r'^\d{1,3}(?:\.\d{3}){2}-[\dkK]$',
    message="Formato inválido. Use: 12.345.678-9"
)

class RegistroForm(UserCreationForm):
    rut = forms.CharField(
            label='RUT',
            max_length=12,
            validators=[rut_validator],
            widget=forms.TextInput(attrs={'placeholder': '12.345.678-9'})
        )
    email = forms.EmailField(required=True)
    nombre_completo = forms.CharField(label='Nombre Completo')
    telefono = forms.CharField(
        label='Teléfono', 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '+56912345678'})
    )
    
    mfa_method = forms.ChoiceField(
        choices=CustomUser.MFA_CHOICES,
        widget=forms.RadioSelect,
        label="Método de verificación MFA"
    )

    class Meta:
        model = CustomUser
        fields = ['rut', 'email', 'nombre_completo', 'telefono', 'password1', 'password2', 'mfa_method']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password2'].error_messages = {
            'password_mismatch': 'Las contraseñas no coinciden.'
        }
        self.fields['email'].required = True
        self.fields['telefono'].required = True

class LoginForm(forms.Form):
    rut = forms.CharField(
        label='RUT',
        max_length=12,
        validators=[rut_validator],
        widget=forms.TextInput(attrs={
            'placeholder': '12.345.678-9',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ingresa tu contraseña',
            'class': 'form-control'
        })
    )
    
    
    
    
class RecuperarCuentaForm(forms.Form):
    rut = forms.CharField(
        label='RUT',
        max_length=12,
        validators=[rut_validator],
        widget=forms.TextInput(attrs={
            'placeholder': '12.345.678-9',
            'class': 'form-control'
        })
    )

class ActualizarPasswordForm(forms.Form):
    password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nueva contraseña'})
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden')
        return cleaned_data