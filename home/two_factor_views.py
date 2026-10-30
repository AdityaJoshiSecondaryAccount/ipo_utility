import pyotp
import qrcode
import base64
import secrets
from io import BytesIO
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .models import CustomUser

def generate_backup_codes(count=3):
    codes = []
    for _ in range(count):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        codes.append(f"{part1}-{part2}")
    return codes

def verify_2fa(request):
    user_id = request.session.get('pre_auth_user_id')
    if not user_id:
        return redirect('login')
        
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect('login')

    if request.method == "POST":
        attempts = request.session.get('2fa_attempts', 0)
        if attempts >= 5:
            messages.error(request, 'Too many invalid attempts. Please log in again.')
            request.session.pop('pre_auth_user_id', None)
            request.session.pop('2fa_attempts', None)
            return redirect('login')
            
        token = request.POST.get("totp_token")
        totp = pyotp.TOTP(user.two_factor_secret)
        
        if totp.verify(token):
            request.session.pop('pre_auth_user_id', None)
            request.session.pop('2fa_attempts', None)
            login(request, user)
            return redirect('/')
        else:
            request.session['2fa_attempts'] = attempts + 1
            messages.error(request, 'Invalid 2FA code.')
            
    return render(request, 'verify_2fa.html')

def verify_backup_code(request):
    user_id = request.session.get('pre_auth_user_id')
    if not user_id:
        return redirect('login')
        
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect('login')
        
    if request.method == "POST":
        attempts = request.session.get('2fa_attempts', 0)
        if attempts >= 5:
            messages.error(request, 'Too many invalid attempts. Please log in again.')
            request.session.pop('pre_auth_user_id', None)
            request.session.pop('2fa_attempts', None)
            return redirect('login')

        code = request.POST.get("backup_code", "").strip().upper()
        if code in user.backup_codes:
            user.backup_codes.remove(code)
            request.session.pop('pre_auth_user_id', None)
            request.session.pop('2fa_attempts', None)
            
            if len(user.backup_codes) == 0:
                user.two_factor_enabled = False
                user.two_factor_secret = None
                user.backup_codes = []
                user.save()
                login(request, user)
                messages.warning(request, 'You used your last backup code. 2FA has been automatically disabled to prevent lockout. Please re-enable 2FA in your Profile.')
                return redirect('user_profile')
                
            user.save()
            login(request, user)
            messages.info(request, f'Backup code verified. You have {len(user.backup_codes)} backup code(s) remaining.')
            return redirect('/')
        else:
            request.session['2fa_attempts'] = attempts + 1
            messages.error(request, 'Invalid backup code.')
            
    return render(request, 'verify_backup_code.html')

from django.http import JsonResponse

def verify_password_for_2fa(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Authentication required."}, status=401)
        
    if request.method == "POST":
        password = request.POST.get("password", "")
        if not password:
            return JsonResponse({"status": "error", "message": "Please enter your password."})
            
        if request.user.check_password(password):
            request.session['2fa_password_verified'] = True
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse({"status": "error", "message": "Incorrect password. Please try again."})
            
    return JsonResponse({"status": "error", "message": "Invalid request method."})

def setup_2fa(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    user = request.user
    
    if request.method == "POST":
        if not request.session.get('2fa_password_verified'):
            messages.error(request, 'Password confirmation is required to setup 2FA.')
            return redirect('user_profile')

        token = request.POST.get("totp_token")
        temp_secret = request.session.get('temp_2fa_secret')
        temp_backup_codes = request.session.get('temp_backup_codes')
        
        if temp_secret and temp_backup_codes:
            totp = pyotp.TOTP(temp_secret)
            if totp.verify(token):
                user.two_factor_secret = temp_secret
                user.backup_codes = temp_backup_codes
                user.two_factor_enabled = True
                user.save()
                
                request.session.pop('temp_2fa_secret', None)
                request.session.pop('temp_backup_codes', None)
                request.session.pop('2fa_password_verified', None)
                messages.success(request, '2FA has been successfully enabled.')
                return redirect('user_profile')
            else:
                messages.error(request, 'Invalid authenticator code. 2FA setup failed.')
        else:
            messages.error(request, '2FA setup session expired. Please try again.')
            
    return redirect('user_profile')

def disable_2fa(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    user = request.user
    if request.method == "POST":
        code = request.POST.get("verification_code", "").strip()
        is_valid = False
        
        # Check TOTP code
        if user.two_factor_secret and code:
            totp = pyotp.TOTP(user.two_factor_secret)
            if totp.verify(code):
                is_valid = True
                
        # Check backup code
        if not is_valid and user.backup_codes and code:
            code_upper = code.upper()
            if code_upper in user.backup_codes:
                is_valid = True
                
        if is_valid:
            user.two_factor_enabled = False
            user.two_factor_secret = None
            user.backup_codes = []
            user.save()
            messages.success(request, 'Two-factor authentication has been successfully disabled.')
        else:
            messages.error(request, 'Invalid 2FA code or backup code. Could not disable 2FA.')
            
    return redirect('user_profile')
