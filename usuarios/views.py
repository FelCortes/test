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

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.username = user.email  # Usar email como username temporal
                user.save()
                
                # Crear dispositivo solo si elige Google Authenticator
                if user.mfa_method == 'totp':
                    TOTPDevice.objects.create(user=user, name='default', confirmed=False)
                
                login(request, user)
                messages.success(request, '¡Cuenta creada con éxito! Configura MFA ahora')

                if user.mfa_method == 'email':
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
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data['rut']
            password = form.cleaned_data['password']
            user = authenticate(request, rut=rut, password=password)
            
            if user is not None:
                # Verificar MFA si está activado
                if user.mfa_enabled:
                    request.session['mfa_user_id'] = user.id
                    return render(request, 'verify_mfa.html')  # Página para ingresar código
                
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'RUT o contraseña incorrectos.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

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
    device, created = TOTPDevice.objects.get_or_create(
        user=request.user,
        defaults={'name': 'default', 'confirmed': False}
    )
    
    if request.method == 'POST':
        if device.verify_token(request.POST.get('code')):
            device.confirmed = True
            device.save()
            request.user.mfa_enabled = True
            request.user.save()
            messages.success(request, 'MFA configurado correctamente')
            return redirect('dashboard')
        else:
            messages.error(request, 'Código inválido')
    
    # Generar QR solo si no está confirmado
    if not device.confirmed:
        img = qrcode.make(device.config_url)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()
        return render(request, 'setup_mfa.html', {'qr_code': qr_code})
    
    return redirect('dashboard')


from django.utils import timezone
import datetime
from datetime import timedelta
from django.utils.dateparse import parse_datetime

@login_required
def setup_mfa_email(request):
    user = request.user

    def enviar_codigo():
        code = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=5)

        request.session['email_mfa_code'] = code
        request.session['email_mfa_expiry'] = expiry.isoformat()

        send_mail(
            subject='Código MFA',
            message=f'Tu código de verificación es: {code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email]
        )

    # Generar solo si no existe
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
                request.session.pop('email_mfa_code', None)
                request.session.pop('email_mfa_expiry', None)
                messages.success(request, 'MFA por correo configurado correctamente.')
                return redirect('dashboard')

    return render(request, 'setup_mfa_email.html')