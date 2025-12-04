from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User, Permission
from rest_framework.test import APIClient
from rest_framework import status
import hashlib
from django.conf import settings
from .models import Votacion, Opcion, Voto
from core.models import Perfil

# ==========================================
# 1. PRUEBAS UNITARIAS (Lógica pura)
# ==========================================
class VotacionModelTest(TestCase):
    def test_esta_abierta_retorna_true_si_es_futuro(self):
        """PU-01: Verifica que esta_abierta() sea True si la fecha es futura."""
        fecha_futura = timezone.now() + timedelta(days=1)
        votacion = Votacion(pregunta="Test", fecha_cierre=fecha_futura, activa=True)
        self.assertIs(votacion.esta_abierta(), True)

    def test_esta_abierta_retorna_false_si_es_pasado(self):
        """PU-02: Verifica que sea False si la fecha ya pasó."""
        fecha_pasada = timezone.now() - timedelta(days=1)
        votacion = Votacion(pregunta="Test", fecha_cierre=fecha_pasada, activa=True)
        self.assertIs(votacion.esta_abierta(), False)

# ==========================================
# 2. PRUEBAS DE INTEGRACIÓN (API y Web)
# ==========================================
class VotacionIntegracionTest(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.client = Client()
        self.user = User.objects.create_user(username='vecino_api', password='123')
        # Simulamos autenticación para la API
        self.api_client.force_authenticate(user=self.user) 
        
        self.votacion = Votacion.objects.create(
            pregunta="Integración API",
            fecha_cierre=timezone.now() + timedelta(days=1),
            activa=True
        )
        Opcion.objects.create(votacion=self.votacion, texto="A")

    def test_api_abiertas_status_200(self):
        """PI-01: La API debe responder JSON 200 OK a la App Móvil."""
        url = reverse('votaciones:api_abiertas')
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

# ==========================================
# 3. PRUEBAS DE SISTEMA (Casos de Tesis CP-VOT)
# ==========================================
class PruebasSistemaVotacion(TestCase):
    def setUp(self):
        self.client = Client()
        # Usuario Vecino (Votante legítimo)
        self.vecino = User.objects.create_user(username='vecino_sys', password='123')
        Perfil.objects.create(usuario=self.vecino, rol='vecino', rut='11.111.111-1', direccion='Test')

        # Usuario Hacker (Sin perfil/rol)
        self.hacker = User.objects.create_user(username='hacker', password='123')
        
        self.votacion = Votacion.objects.create(
            pregunta="Seguridad",
            fecha_cierre=timezone.now() + timedelta(days=1),
            activa=True
        )
        self.opcion_si = Opcion.objects.create(votacion=self.votacion, texto="Si")
        self.opcion_no = Opcion.objects.create(votacion=self.votacion, texto="No")

    def test_cp_vot_001_bloqueo_doble_voto(self):
        """CP-VOT-001: El sistema impide votar dos veces."""
        self.client.login(username='vecino_sys', password='123')
        url = reverse('votaciones:emitir_voto', args=[self.votacion.id])

        # Voto 1
        self.client.post(url, {'opcion': self.opcion_si.id})
        self.assertEqual(Voto.objects.count(), 1)

        # Voto 2 (Intento fraude)
        self.client.post(url, {'opcion': self.opcion_no.id})
        self.assertEqual(Voto.objects.count(), 1) # No debe subir a 2

    def test_cp_vot_002_integridad_criptografica(self):
        """CP-VOT-002: Detectar manipulación de BD mediante Hash."""
        # 1. Crear voto legítimo
        voto = Voto.objects.create(votante=self.vecino, opcion=self.opcion_si)
        
        # 2. Simular ataque directo a la BD (update sin save)
        Voto.objects.filter(id=voto.id).update(opcion=self.opcion_no)
        
        # 3. Verificar integridad
        voto_corrupto = Voto.objects.get(id=voto.id)
        datos_reales = f"{voto_corrupto.votante.id}-{voto_corrupto.opcion.id}-{settings.SECRET_KEY}"
        hash_recalculado = hashlib.sha256(datos_reales.encode()).hexdigest()
        
        # El hash guardado (viejo) NO debe coincidir con el recalculado (nuevo)
        self.assertNotEqual(voto_corrupto.hash_voto, hash_recalculado)

    def test_cp_vot_003_acceso_denegado(self):
        """CP-VOT-003: Usuario sin rol no puede crear votación."""
        self.client.login(username='hacker', password='123')
        url = reverse('votaciones:crear_votacion')
        response = self.client.get(url)
        # Esperamos redirección (302) o Prohibido (403), no éxito (200)
        self.assertNotEqual(response.status_code, 200)