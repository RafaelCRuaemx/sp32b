from rest_framework import serializers
from .models import UsuarioRfid, Acceso, Justificante, TelemetriaESP32
from django.utils.timezone import localtime

class UsuarioRfidSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    carrera_nombre = serializers.CharField(source='carrera.nombre', read_only=True)
    semestre_nombre = serializers.CharField(source='semestre.nombre', read_only=True)
    turno_nombre = serializers.CharField(source='turno.nombre', read_only=True)

    class Meta:
        model = UsuarioRfid
        fields = '__all__'

class AccesoSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    matricula = serializers.SerializerMethodField()
    uid = serializers.CharField(source='uid_leido')
    # FIX 1: Renombrado de hora_str → hora para coincidir con accessorKey del frontend
    hora = serializers.SerializerMethodField()

    class Meta:
        model = Acceso
        fields = ['id', 'nombre', 'matricula', 'uid', 'hora', 'puerta', 'estado']

    def get_nombre(self, obj):
        return obj.usuario.nombre if obj.usuario else 'Tarjeta No Registrada'

    def get_matricula(self, obj):
        return obj.usuario.matricula if obj.usuario else 'N/A'

    def get_hora(self, obj):
        # El frontend espera '21/09/2026 07:44:12 AM'
        if obj.hora:
            local_time = localtime(obj.hora)
            return local_time.strftime('%d/%m/%Y %I:%M:%S %p')
        return ''

class JustificanteSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    matricula = serializers.SerializerMethodField()

    class Meta:
        model = Justificante
        fields = ['id', 'nombre', 'matricula', 'fecha', 'motivo', 'folio', 'autorizado_por']

    def get_nombre(self, obj):
        return obj.usuario.nombre

    def get_matricula(self, obj):
        return obj.usuario.matricula
