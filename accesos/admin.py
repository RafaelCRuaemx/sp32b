from django.contrib import admin
from .models import Turno, Carrera, Semestre, Rol, UsuarioRfid, Acceso, Justificante, TelemetriaESP32

admin.site.register(Turno)
admin.site.register(Carrera)
admin.site.register(Semestre)
admin.site.register(Rol)

@admin.register(Justificante)
class JustificanteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha', 'motivo', 'autorizado_por')
    list_filter = ('fecha',)
    search_fields = ('usuario__nombre', 'autorizado_por')

@admin.register(UsuarioRfid)
class UsuarioRfidAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'matricula', 'rol', 'carrera', 'semestre', 'turno', 'activo')
    list_filter = ('rol', 'carrera', 'semestre', 'turno', 'activo')
    search_fields = ('nombre', 'matricula', 'uidRfid')

@admin.register(Acceso)
class AccesoAdmin(admin.ModelAdmin):
    list_display = ('uid_leido', 'usuario', 'puerta', 'estado', 'hora')
    list_filter = ('estado', 'puerta', 'hora')
    search_fields = ('uid_leido', 'usuario__nombre')

@admin.register(TelemetriaESP32)
class TelemetriaESP32Admin(admin.ModelAdmin):
    list_display = ('ip', 'online', 'ultimo_uid_leido', 'ultima_actualizacion')
