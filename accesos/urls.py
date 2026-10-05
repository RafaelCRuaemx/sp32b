from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'accesos', views.AccesoViewSet)
router.register(r'usuarios-rfid', views.UsuarioRfidViewSet)

urlpatterns = [
    path('catalogos/', views.catalogos),
    path('dashboard/resumen/', views.get_dashboard_resumen),
    path('accesos/simular-lectura/', views.simular_lectura),
    path('inasistencias/', views.listar_inasistencias_al_vuelo),
    # FIX 5: Ruta que el frontend llama para justificar una falta
    path('inasistencias/<int:usuario_id>/justificar/', views.justificar_inasistencia),
    path('justificantes/', views.crear_justificante),
    path('esp32/ultimo-uid-leido/', views.get_ultimo_uid_leido),
    path('auth/setup-2fa/', views.setup_2fa),
    path('auth/login/', views.login_2fa),
    path('auth/verify-2fa/', views.verify_2fa),
    path('', include(router.urls)),
]
