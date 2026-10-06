from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Turno, Carrera, Semestre, Rol, UsuarioRfid, Acceso, Justificante, TelemetriaESP32
from .serializers import UsuarioRfidSerializer, AccesoSerializer, JustificanteSerializer
import pyotp
import qrcode
import base64
from io import BytesIO
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import SeguridadAdministrador

class UsuarioRfidViewSet(viewsets.ModelViewSet):
    queryset = UsuarioRfid.objects.all()
    serializer_class = UsuarioRfidSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) | 
                Q(matricula__icontains=search) | 
                Q(uidRfid__icontains=search)
            )
        return qs

class AccesoViewSet(viewsets.ModelViewSet):
    queryset = Acceso.objects.all().order_by('-hora')
    serializer_class = AccesoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get('estado', None)
        search = self.request.query_params.get('search', None)
        if estado and estado != 'todos':
            qs = qs.filter(estado=estado)
        if search:
            qs = qs.filter(
                Q(uid_leido__icontains=search) | 
                Q(usuario__nombre__icontains=search) | 
                Q(usuario__matricula__icontains=search)
            )
            
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            qs = qs.filter(hora__date__gte=start_date)
        if end_date:
            qs = qs.filter(hora__date__lte=end_date)
            
        return qs

from django.conf import settings

@api_view(['POST'])
@permission_classes([AllowAny])
def simular_lectura(request):
    api_key = request.headers.get('X-Hardware-Key')
    if settings.ESP32_API_KEY and api_key != settings.ESP32_API_KEY:
        return Response({'detail': 'Hardware Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    uid = request.data.get('uid', '00:00:00:00')
    puerta = request.data.get('puerta', 'Torniquete 01')
    
    tele = TelemetriaESP32.objects.first()
    if tele:
        tele.ultimo_uid_leido = uid
        tele.save()

    if puerta == 'Mesa de Registro':
        return Response({'detail': 'UID capturado para alta', 'uid': uid}, status=status.HTTP_200_OK)
    
    usuario = UsuarioRfid.objects.filter(uidRfid=uid, activo=True).first()
    estado = 'a_tiempo' 
    
    if not usuario:
        estado = 'denegado'
        
    acceso = Acceso.objects.create(
        usuario=usuario,
        uid_leido=uid,
        puerta=puerta,
        estado=estado
    )
        
    return Response(AccesoSerializer(acceso).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_ultimo_uid_leido(request):
    tele = TelemetriaESP32.objects.first()
    if tele and tele.ultimo_uid_leido:
        return Response({'uid': tele.ultimo_uid_leido, 'timestamp': tele.ultima_actualizacion})
    return Response({'uid': 'Ninguno', 'timestamp': timezone.now()})

@api_view(['GET'])
def get_dashboard_resumen(request):
    hoy = timezone.now().date()
    accesos_hoy = Acceso.objects.filter(hora__date=hoy)

    total_padron = UsuarioRfid.objects.filter(activo=True).count()
    asistencias = accesos_hoy.filter(estado='a_tiempo').count()
    retardos = accesos_hoy.filter(estado='retardo').count()

    # Inasistencias calculadas al vuelo (sin acceso y sin justificante)
    usuarios_activos = UsuarioRfid.objects.filter(activo=True, fechaAlta__lte=hoy)
    justificantes_hoy = Justificante.objects.filter(fecha=hoy).values_list('usuario_id', flat=True)
    accesos_hoy_ids = accesos_hoy.values_list('usuario_id', flat=True)
    inasistencias = usuarios_activos.exclude(id__in=accesos_hoy_ids).exclude(id__in=justificantes_hoy).count()

    total_accesos = asistencias + retardos
    porcentaje_asistencia = round((asistencias / total_padron * 100), 1) if total_padron > 0 else 0
    porcentaje_retardos   = round((retardos / total_padron * 100), 1) if total_padron > 0 else 0
    porcentaje_inasistencias = round((inasistencias / total_padron * 100), 1) if total_padron > 0 else 0

    tele = TelemetriaESP32.objects.first()

    # FIX 3: Respuesta con campos planos que coinciden exactamente con lo que lee el frontend
    return Response({
        'totalPadron': total_padron,
        'asistencias': asistencias,
        'porcentajeAsistencia': porcentaje_asistencia,
        'retardos': retardos,
        'porcentajeRetardos': porcentaje_retardos,
        'inasistencias': inasistencias,
        'porcentajeInasistencias': porcentaje_inasistencias,
        'flujoHorario': [],  # Por ahora vacío; se puede implementar con anotaciones
        'esp32Status': {
            'online': tele.online if tele else False,
            'ip': tele.ip if tele else '0.0.0.0',
            'rssi': tele.rssi if tele else 0,
            'lastUpdate': str(tele.ultima_actualizacion) if tele else str(timezone.now()),
        },
    })

@api_view(['GET'])
def listar_inasistencias_al_vuelo(request):
    hoy = timezone.now().date()

    # FIX 4: Soporte de rango de fechas (start_date / end_date) que manda el frontend
    start_date = request.query_params.get('start_date')
    end_date   = request.query_params.get('end_date')
    fecha_req  = request.query_params.get('fecha', str(hoy))

    usuarios_activos = UsuarioRfid.objects.filter(activo=True)

    if start_date and end_date:
        # Modo rango: usuarios ausentes en ALGÚN día del rango
        from datetime import date, timedelta
        try:
            inicio = date.fromisoformat(start_date)
            fin    = date.fromisoformat(end_date)
        except ValueError:
            inicio = fin = hoy

        resultados = []
        dia = inicio
        while dia <= fin:
            accesos_dia = Acceso.objects.filter(hora__date=dia).values_list('usuario_id', flat=True)
            ausentes_dia = usuarios_activos.filter(fechaAlta__lte=dia).exclude(id__in=accesos_dia)

            justificantes = Justificante.objects.filter(fecha=dia)
            justificados_ids = list(justificantes.values_list('usuario_id', flat=True))
            justificantes_dict = {j.usuario_id: j for j in justificantes}

            for u in ausentes_dia:
                tiene_just = u.id in justificados_ids
                j = justificantes_dict.get(u.id)
                resultados.append({
                    'id': f"{u.id}_{dia}",
                    'usuario_id': u.id,
                    'nombre': u.nombre,
                    'matricula': u.matricula,
                    'grupo': u.carrera.nombre if u.carrera else 'Sin carrera',
                    'fecha': str(dia),
                    'estado': 'justificada' if tiene_just else 'injustificada',
                    'motivoJustificacion': j.motivo if tiene_just else '',
                    'folio': j.folio if tiene_just else '',
                    # FIX 2: Teléfono real del usuario en lugar del valor hardcodeado
                    'tutorTelefono': u.telefono or 'No especificado',
                })
            dia += timedelta(days=1)

        return Response(resultados)

    # Modo fecha única (compatibilidad con el parámetro ?fecha=)
    accesos_dia = Acceso.objects.filter(hora__date=fecha_req).values_list('usuario_id', flat=True)
    usuarios_ausentes = usuarios_activos.filter(fechaAlta__lte=fecha_req).exclude(id__in=accesos_dia)

    justificantes = Justificante.objects.filter(fecha=fecha_req)
    justificados_ids = list(justificantes.values_list('usuario_id', flat=True))
    justificantes_dict = {j.usuario_id: j for j in justificantes}

    resultados = []
    for u in usuarios_ausentes:
        tiene_just = u.id in justificados_ids
        j = justificantes_dict.get(u.id)
        resultados.append({
            'id': f"{u.id}_{fecha_req}",
            'usuario_id': u.id,
            'nombre': u.nombre,
            'matricula': u.matricula,
            'grupo': u.carrera.nombre if u.carrera else 'Sin carrera',
            'fecha': fecha_req,
            'estado': 'justificada' if tiene_just else 'injustificada',
            'motivoJustificacion': j.motivo if tiene_just else '',
            'folio': j.folio if tiene_just else '',
            # FIX 2: Teléfono real del usuario
            'tutorTelefono': u.telefono or 'No especificado',
        })

    return Response(resultados)

@api_view(['POST'])
def crear_justificante(request):
    """Endpoint original: POST /api/justificantes/ con usuario_id en el body."""
    usuario_id = request.data.get('usuario_id')
    fecha = request.data.get('fecha')
    
    try:
        usuario = UsuarioRfid.objects.get(id=usuario_id)
        j = Justificante.objects.create(
            usuario=usuario,
            fecha=fecha,
            motivo=request.data.get('motivo', ''),
            folio=request.data.get('folio', ''),
            autorizado_por=request.data.get('autorizado_por', 'Admin')
        )
        return Response(JustificanteSerializer(j).data, status=status.HTTP_201_CREATED)
    except UsuarioRfid.DoesNotExist:
        return Response({'detail': 'Usuario no existe'}, status=status.HTTP_404_NOT_FOUND)

# FIX 5: Endpoint que el frontend llama con la ruta /api/inasistencias/{usuario_id}/justificar/
@api_view(['POST'])
def justificar_inasistencia(request, usuario_id):
    """
    POST /api/inasistencias/{usuario_id}/justificar/
    Body: { motivo, folio, observaciones, autorizado_por, fecha }
    """
    try:
        usuario = UsuarioRfid.objects.get(id=usuario_id)
    except UsuarioRfid.DoesNotExist:
        return Response({'detail': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    fecha = request.data.get('fecha', str(timezone.now().date()))
    motivo = request.data.get('motivo', '')
    folio = request.data.get('folio', 'S/F')
    observaciones = request.data.get('observaciones', '')
    autorizado_por = request.data.get('autorizado_por', 'Administrador Web')

    # Si ya existe un justificante para ese usuario y fecha, lo actualiza
    j, created = Justificante.objects.update_or_create(
        usuario=usuario,
        fecha=fecha,
        defaults={
            'motivo': f"{motivo}. {observaciones}".strip('. ') if observaciones else motivo,
            'folio': folio,
            'autorizado_por': autorizado_por,
        }
    )

    return Response(JustificanteSerializer(j).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@api_view(['GET'])
def catalogos(request):
    roles = [{'id': r.id, 'nombre': r.nombre} for r in Rol.objects.all()]
    carreras = [{'id': c.id, 'nombre': c.nombre} for c in Carrera.objects.all()]
    semestres = [{'id': s.id, 'nombre': s.nombre} for s in Semestre.objects.order_by('numero')]
    turnos = [{'id': t.id, 'nombre': t.nombre} for t in Turno.objects.all()]
    return Response({'roles': roles, 'carreras': carreras, 'semestres': semestres, 'turnos': turnos})




import uuid
from django.core.cache import cache
import pyotp
import qrcode
import base64
from io import BytesIO
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([AllowAny])
def login_2fa(request):
    """Paso 1: Valida usuario y contraseña."""
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
    """Genera el QR para el usuario autenticado temporalmente"""
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
    """Paso 2: Valida el código TOTP usando el token temporal."""
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
            
            # Generar JWT real
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            user_data = {"email": user.username, "name": user.get_full_name() or user.username, "role": "Administrador"}
            return Response({
                "status": "success",
                "detail": "Verificación 2FA exitosa",
                "token": access_token,
                "user": user_data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Código 2FA incorrecto"}, status=status.HTTP_401_UNAUTHORIZED)
            
    except (User.DoesNotExist, SeguridadAdministrador.DoesNotExist):
        return Response({"detail": "Error en la validación"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token(request):
    """Verifica si el token JWT enviado en el header es válido."""
    return Response({"detail": "Token válido"}, status=status.HTTP_200_OK)
