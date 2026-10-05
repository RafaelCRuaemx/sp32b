import re

with open("/home/rafael/desarrollo/benitto_proyecto/backend/accesos/views.py", "r") as f:
    content = f.read()

# Split the content at "def setup_2fa"
parts = content.split("@api_view(['GET'])\n@permission_classes([IsAuthenticated])\ndef setup_2fa(request):")
if len(parts) == 1:
    # try another split in case
    parts = content.split("@api_view(['POST'])\n@permission_classes([AllowAny])\ndef login_2fa")

top = parts[0]

new_code = """
import uuid
from django.core.cache import cache
import pyotp
import qrcode
import base64
from io import BytesIO

@api_view(['POST'])
@permission_classes([AllowAny])
def login_2fa(request):
    \"\"\"Paso 1: Valida usuario y contraseña.\"\"\"
    email = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=email, password=password)
    if user is not None:
        seguridad, created = SeguridadAdministrador.objects.get_or_create(admin=user)
        user_data = {"email": user.username, "name": user.get_full_name() or user.username, "role": "Administrador"}
        
        # Generar un token temporal en cualquier caso
        temp_token = str(uuid.uuid4())
        cache.set(f"2fa_temp_{temp_token}", user.id, timeout=300)

        if seguridad.is_totp_enabled:
            return Response({
                "status": "2fa_required",
                "detail": "Se requiere código de Google Authenticator", 
                "tempToken": temp_token,
                "user": user_data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "setup_2fa_required",
                "detail": "Debes configurar Google Authenticator por primera vez", 
                "tempToken": temp_token,
                "user": user_data
            }, status=status.HTTP_200_OK)
    else:
        return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def setup_2fa(request):
    \"\"\"Genera el QR para el usuario autenticado temporalmente\"\"\"
    temp_token = request.data.get('temp_token')
    user_id = cache.get(f"2fa_temp_{temp_token}")
    if not user_id:
        return Response({"detail": "Sesión expirada o token inválido"}, status=status.HTTP_401_UNAUTHORIZED)
        
    user = User.objects.get(id=user_id)
    seguridad, created = SeguridadAdministrador.objects.get_or_create(admin=user)
    
    if not seguridad.totp_secret:
        seguridad.totp_secret = pyotp.random_base32()
        seguridad.save()
    
    totp = pyotp.TOTP(seguridad.totp_secret)
    uri = totp.provisioning_uri(name=user.username, issuer_name="Control Escolar RFID")

    qr = qrcode.make(uri)
    stream = BytesIO()
    qr.save(stream, format="PNG")
    qr_base64 = base64.b64encode(stream.getvalue()).decode('utf-8')
    
    return Response({
        "secret": seguridad.totp_secret,
        "qrImageUrl": f"data:image/png;base64,{qr_base64}"
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_2fa(request):
    \"\"\"Paso 2: Valida el código TOTP usando el token temporal.\"\"\"
    temp_token = request.data.get('temp_token')
    codigo = request.data.get('code')

    user_id = cache.get(f"2fa_temp_{temp_token}")
    if not user_id:
        return Response({"detail": "Sesión expirada o token inválido"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        user = User.objects.get(id=user_id)
        seguridad = SeguridadAdministrador.objects.get(admin=user)
        
        totp = pyotp.TOTP(seguridad.totp_secret)
        if totp.verify(codigo):
            if not seguridad.is_totp_enabled:
                seguridad.is_totp_enabled = True
                seguridad.save()
            
            cache.delete(f"2fa_temp_{temp_token}")
            user_data = {"email": user.username, "name": user.get_full_name() or user.username, "role": "Administrador"}
            return Response({
                "status": "success",
                "detail": "Verificación 2FA exitosa",
                "token": "token_jwt_generado_aqui",
                "user": user_data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Código 2FA incorrecto"}, status=status.HTTP_401_UNAUTHORIZED)
            
    except (User.DoesNotExist, SeguridadAdministrador.DoesNotExist):
        return Response({"detail": "Error en la validación"}, status=status.HTTP_401_UNAUTHORIZED)
"""

with open("/home/rafael/desarrollo/benitto_proyecto/backend/accesos/views.py", "w") as f:
    f.write(top + new_code)
print("Updated views.py")
