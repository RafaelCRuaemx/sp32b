from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Turno, Carrera, Semestre, Rol, UsuarioRfid, Acceso, Justificante, TelemetriaESP32
from .serializers import UsuarioRfidSerializer, AccesoSerializer, JustificanteSerializer

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

@api_view(['POST'])
def simular_lectura(request):
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
    
    # Inasistencias calculadas al vuelo
    usuarios_activos = UsuarioRfid.objects.filter(activo=True)
    justificantes_hoy = Justificante.objects.filter(fecha=hoy).values_list('usuario_id', flat=True)
    accesos_hoy_ids = accesos_hoy.values_list('usuario_id', flat=True)
    inasistencias = usuarios_activos.exclude(id__in=accesos_hoy_ids).exclude(id__in=justificantes_hoy).count()

    tele = TelemetriaESP32.objects.first()
    
    return Response({
        'kpis': {
            'accesos_hoy': accesos_hoy.filter(estado='a_tiempo').count(),
            'retardos_hoy': accesos_hoy.filter(estado='retardo').count(),
            'inasistencias_hoy': inasistencias,
            'alertas_hoy': accesos_hoy.filter(estado='denegado').count(),
        },
        'esp32_status': {
            'online': tele.online if tele else False,
            'ip': tele.ip if tele else '0.0.0.0',
            'rssi': tele.rssi if tele else 0,
            'last_update': tele.ultima_actualizacion if tele else timezone.now(),
        }
    })

@api_view(['GET'])
def listar_inasistencias_al_vuelo(request):
    hoy = timezone.now().date()
    fecha_req = request.query_params.get('fecha', hoy)
    
    usuarios_activos = UsuarioRfid.objects.filter(activo=True)
    accesos_hoy = Acceso.objects.filter(hora__date=fecha_req).values_list('usuario_id', flat=True)
    usuarios_ausentes = usuarios_activos.exclude(id__in=accesos_hoy)
    
    justificantes = Justificante.objects.filter(fecha=fecha_req)
    justificados_ids = justificantes.values_list('usuario_id', flat=True)
    justificantes_dict = {j.usuario_id: j for j in justificantes}
    
    resultados = []
    for u in usuarios_ausentes:
        tiene_just = u.id in justificados_ids
        j = justificantes_dict.get(u.id)
        
        resultados.append({
            'id': u.id,
            'nombre': u.nombre,
            'matricula': u.matricula,
            'grupo': u.carrera.nombre if u.carrera else 'Sin carrera',
            'fecha': fecha_req,
            'estado': 'justificada' if tiene_just else 'injustificada',
            'motivoJustificacion': j.motivo if tiene_just else '',
            'folio': j.folio if tiene_just else '',
            'tutorTelefono': '55-0000-0000',
        })
        
    return Response(resultados)

@api_view(['POST'])
def crear_justificante(request):
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
