from django.db import models

class Turno(models.Model):
    nombre = models.CharField(max_length=50, unique=True) # Matutino, Vespertino
    hora_entrada = models.TimeField()
    hora_limite_retardo = models.TimeField()
    
    def __str__(self):
        return self.nombre

class Carrera(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nombre

class Semestre(models.Model):
    nombre = models.CharField(max_length=50, unique=True) # 1er Semestre, etc.
    numero = models.IntegerField(unique=True) # 1, 2, 3...
    
    def __str__(self):
        return self.nombre

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True) # Estudiante, Docente, etc.
    
    def __str__(self):
        return self.nombre

class UsuarioRfid(models.Model):
    nombre = models.CharField(max_length=200)
    matricula = models.CharField(max_length=50, unique=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT)
    carrera = models.ForeignKey(Carrera, on_delete=models.SET_NULL, null=True, blank=True)
    semestre = models.ForeignKey(Semestre, on_delete=models.SET_NULL, null=True, blank=True)
    turno = models.ForeignKey(Turno, on_delete=models.SET_NULL, null=True, blank=True)
    
    correo = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    
    uidRfid = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)
    fechaAlta = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.matricula})"

class Acceso(models.Model):
    ESTADOS = [
        ('a_tiempo', 'A tiempo'),
        ('retardo', 'Retardo'),
        ('denegado', 'Denegado'),
    ]
    usuario = models.ForeignKey(UsuarioRfid, on_delete=models.SET_NULL, null=True, blank=True)
    uid_leido = models.CharField(max_length=50) 
    hora = models.DateTimeField(auto_now_add=True)
    puerta = models.CharField(max_length=100)
    estado = models.CharField(max_length=20, choices=ESTADOS)

    def __str__(self):
        return f"{self.uid_leido} - {self.puerta} - {self.estado}"

class Justificante(models.Model):
    usuario = models.ForeignKey(UsuarioRfid, on_delete=models.CASCADE)
    fecha = models.DateField()
    motivo = models.CharField(max_length=255)
    folio = models.CharField(max_length=50, null=True, blank=True)
    autorizado_por = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Justificante: {self.usuario.nombre} - {self.fecha}"

class TelemetriaESP32(models.Model):
    ip = models.CharField(max_length=50, default='192.168.1.145')
    rssi = models.IntegerField(default=-58)
    online = models.BooleanField(default=True)
    ultimo_uid_leido = models.CharField(max_length=50, null=True, blank=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ESP32 - {'Online' if self.online else 'Offline'}"
