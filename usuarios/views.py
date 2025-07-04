from datetime import timedelta, timezone
import random
from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages

from banco_mgti import settings
from .forms import RegistroForm, LoginForm
from .models import CustomUser

#google auth
from django_otp.plugins.otp_totp.models import TOTPDevice

import qrcode
from io import BytesIO
import base64
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required

from django.utils import timezone
import datetime
from datetime import timedelta
from django.utils.dateparse import parse_datetime

from .forms import LoginForm

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.username = user.email  # email como username temporal
                user.save()
                
                # solo si elige google authenticator
                if user.mfa_method == 'totp':
                    TOTPDevice.objects.create(user=user, name='default', confirmed=False)
                
                login(request, user)
                
                messages.success(request, '¡Cuenta creada con éxito! Configura MFA ahora')

                if user.mfa_method == 'email':
                    request.session['pre_2fa_user_id'] = user.id
                    return redirect('setup_mfa_email')
                else:
                    return redirect('setup_mfa')
                
            except Exception as e:
                messages.error(request, f'Error al crear la cuenta: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = RegistroForm()
    
    return render(request, 'registro.html', {'form': form})

def user_login(request):
    form = LoginForm(request.POST or None)
    otp_required = False

    if request.method == 'POST':
        if form.is_valid():
            rut = form.cleaned_data['rut']
            password = form.cleaned_data['password']
            user = authenticate(request, rut=rut, password=password)

            if user:
                totp_device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

                if totp_device:
                    login(request, user)  # autentica para seleccionar metod de verificacion
                    return redirect('choose_mfa_method')
                else:
                    request.session['pre_2fa_user_id'] = user.id
                    return redirect('setup_mfa_email')
            else:
                messages.error(request, 'RUT o contraseña incorrectos.')

    return render(request, 'login.html', {
        'form': form,
        'otp_required': otp_required
    })
    
    

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'dashboard.html')

def custom_logout(request):
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('login')





@login_required
def verify_mfa(request):
    if request.method == 'POST':
        user = CustomUser.objects.get(id=request.session.get('mfa_user_id'))
        device = TOTPDevice.objects.get(user=user)
        
        if device.verify_token(request.POST.get('code')):
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Código MFA inválido')
    
    return render(request, 'verify_mfa.html')





@login_required
def setup_mfa(request):
    user = request.user
    existing_devices = TOTPDevice.objects.filter(user=user)

    if request.method == 'POST':
        code = request.POST.get('code')
        device = TOTPDevice.objects.filter(user=user).last()
        if device.verify_token(code):
            device.confirmed = True
            device.save()
            messages.success(request, 'Google Authenticator configurado correctamente.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Código incorrecto. Intenta de nuevo.')

    # eliminar totp anteriores
    existing_devices.delete()

    # crear nuevo
    device = TOTPDevice.objects.create(user=user, name='default', confirmed=False)

    # generar QR
    otp_uri = device.config_url
    qr = qrcode.make(otp_uri)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'setup_mfa.html', {
        'qr_code': qr_base64,
    })
    
    
    


def setup_mfa_email(request):

    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        messages.error(request, 'Sesión inválida. Intenta ingresar nuevamente.')
        return redirect('login')

    user = CustomUser.objects.get(id=user_id)

    def enviar_codigo():
        code = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=5)

        request.session['email_mfa_code'] = code
        request.session['email_mfa_expiry'] = expiry.isoformat()

        send_mail(
            subject='Tu código de verificación',
            message=f'Tu código es: {code}',
            from_email='Banco MGTI <{}>'.format(settings.DEFAULT_FROM_EMAIL),
            recipient_list=[user.email]
        )


    # generar solo si no existe
    if not request.session.get('email_mfa_code'):
        enviar_codigo()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'resend':
            enviar_codigo()
            messages.success(request, 'Se ha enviado un nuevo código a tu correo.')
            return redirect('setup_mfa_email')

        elif action == 'verify':
            entered = request.POST.get('code')
            code_session = request.session.get('email_mfa_code')
            expiry_str = request.session.get('email_mfa_expiry')
            expiry = parse_datetime(expiry_str)
            if expiry is None:
                messages.error(request, 'Error interno al verificar el código. Intenta reenviar.')
                return render(request, 'setup_mfa_email.html')

            now = timezone.now()
            if now > expiry:
                messages.error(request, 'El código ha expirado. Por favor, solicita uno nuevo.')
            elif entered != code_session:
                messages.error(request, 'El código ingresado es incorrecto.')
            else:
                user.mfa_enabled = True
                user.save()
                
                # iniciar sesion ahora que paso MFA
                login(request, user)
                
                # limpiar variables de sesion
                request.session.pop('email_mfa_code', None)
                request.session.pop('email_mfa_expiry', None)
                request.session.pop('pre_2fa_user_id', None)
                
                messages.success(request, '¡Correo confirmado!')
                return redirect('dashboard')

    return render(request, 'setup_mfa_email.html')


@login_required
def choose_mfa_method(request):
    user = request.user
    totp_device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

    if not totp_device:
        return redirect('setup_mfa_email')

    if request.method == 'POST':
        choice = request.POST.get('method')
        if choice == 'totp':
            request.session['mfa_user_id'] = user.id
            return redirect('verify_mfa')
        elif choice == 'email':
            request.session['pre_2fa_user_id'] = user.id
            return redirect('setup_mfa_email')

    return render(request, 'choose_mfa_method.html', {
        'user_email': user.email
    })
    
    
    
    
    
    
    
    
    
    
# RECUPERACIÓN DE CUENTA

from django.shortcuts import render, redirect
from django.contrib import messages
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.dateparse import parse_datetime
from datetime import timedelta
import random

from banco_mgti import settings
from .models import CustomUser
from .forms import RecuperarCuentaForm, ActualizarPasswordForm

def recuperar_cuenta_rut(request): 
    if request.method == 'POST':
        form = RecuperarCuentaForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data['rut']
            try:
                user = CustomUser.objects.get(rut=rut)
                request.session['rut_para_recuperar'] = rut

                # metodos MFA habilitados
                tiene_email = bool(user.email)
                tiene_totp = TOTPDevice.objects.filter(user=user, confirmed=True).exists()


                if tiene_totp and tiene_email:
                    return redirect('choose_mfa_recuperar')
                elif tiene_totp:
                    request.session['mfa_user_id'] = user.id
                    return redirect('choose_mfa_recuperar')
                elif tiene_email:
                    request.session['pre_2fa_user_id'] = user.id
                    return redirect('setup_mfa_email_recuperar')
                
                else:
                    messages.error(request, 'Tu cuenta no tiene métodos MFA configurados.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'No se encontró una cuenta con ese RUT.')
    else:
        form = RecuperarCuentaForm()
    return render(request, 'recuperar_cuenta.html', {'form': form})


def choose_mfa_recuperar(request):
    rut = request.session.get('rut_para_recuperar')
    if not rut:
        return redirect('recuperar_cuenta')

    user = CustomUser.objects.get(rut=rut)

    # variables template
    tiene_email = bool(user.email)
    tiene_totp = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
    if tiene_totp:
        if request.method == 'POST':
            choice = request.POST.get('method')
            if choice == 'totp':
                request.session['mfa_user_id'] = user.id
                return redirect('verify_mfa_recuperar')
            elif choice == 'email':
                request.session['pre_2fa_user_id'] = user.id
                return redirect('setup_mfa_email_recuperar')

        return render(request, 'choose_mfa_recovery.html', {
            'user_email': user.email,
            'tiene_totp': tiene_totp,
        })
    else:
        if request.method == 'POST':
            choice = request.POST.get('method')
            if choice == 'totp':
                request.session['mfa_user_id'] = user.id
                return redirect('verify_mfa_recuperar')
            elif choice == 'email':
                request.session['pre_2fa_user_id'] = user.id
                return redirect('setup_mfa_email_recuperar')

        return render(request, 'choose_mfa_recovery.html', {
            'user_email': user.email,
            'tiene_email': tiene_email,
        })
        


def verify_mfa_recuperar(request):
    user = CustomUser.objects.get(id=request.session.get('mfa_user_id'))
    if request.method == 'POST':
        code = request.POST.get('code')
        device = TOTPDevice.objects.get(user=user)
        if device.verify_token(code):
            request.session['permitido_recuperar_password'] = True
            return redirect('actualizar_password')
        else:
            messages.error(request, 'Código incorrecto.')
    return render(request, 'verify_mfa_recovery.html')


def setup_mfa_email_recuperar(request):
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        return redirect('recuperar_cuenta')

    user = CustomUser.objects.get(id=user_id)

    def enviar_codigo():
        code = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=5)

        request.session['email_mfa_code'] = code
        request.session['email_mfa_expiry'] = expiry.isoformat()

        send_mail(
            'Código de recuperación de cuenta',
            f'Tu código es: {code}',
            'Banco MGTI <{}>'.format(settings.DEFAULT_FROM_EMAIL),
            [user.email]
        )

    expiry_str = request.session.get('email_mfa_expiry')
    code = request.session.get('email_mfa_code')

    expired = False
    if expiry_str:
        expiry = parse_datetime(expiry_str)
        expired = timezone.now() > expiry

    if not code or expired:
        enviar_codigo()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'resend':
            enviar_codigo()
            messages.success(request, 'Código reenviado.')
        elif action == 'verify':
            entered = request.POST.get('code')
            code_session = request.session.get('email_mfa_code')
            expiry = parse_datetime(request.session.get('email_mfa_expiry'))

            if not code_session or not expiry:
                messages.error(request, 'Error interno.')
            elif timezone.now() > expiry:
                messages.error(request, 'Código expirado.')
            elif entered != code_session:
                messages.error(request, 'Código incorrecto.')
            else:
                request.session['permitido_recuperar_password'] = True
                return redirect('actualizar_password')

    return render(request, 'setup_mfa_email_recovery.html')


from django.contrib.auth.forms import SetPasswordForm

def actualizar_password(request):
    if not request.session.get('permitido_recuperar_password'):
        messages.error(request, 'Sesión no válida.')
        return redirect('recuperar_cuenta')

    rut = request.session.get('rut_para_recuperar')
    user = CustomUser.objects.get(rut=rut)

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()  # guarda la nueva password
            request.session.flush()  # limpia toda la sesion
            messages.success(request, 'Contraseña actualizada correctamente.')
            return redirect('login')
    else:
        form = SetPasswordForm(user)
    return render(request, 'reset_password.html', {'form': form})