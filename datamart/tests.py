"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Pruebas unitarias y de integración para validar el Datamart, 
               incluyendo pruebas de rendimiento (SLA), lógica de KPIs, 
               seguridad y concurrencia.
--------------------------------------------------------------------------------
"""
import time
import threading
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datamart.models import DimVecino, DimTaller, DimActa, FactConsultaActa
from datamart.views import construir_datos_panel_bi

# -------------------------------------------------------------------------
# 1. PRUEBA DE RENDIMIENTO (SLA) - Carga del Dashboard
# -------------------------------------------------------------------------
class DashboardSLATest(TestCase):
    def setUp(self):
        # Preparación: Creamos usuario admin y lo logueamos
        self.user = User.objects.create_user(username='admin_bi', password='123')
        self.client = Client()
        self.client.force_login(self.user)
        
        # Carga de Datos Simulada (Volumen masivo)
        talleres = [
            DimTaller(taller_id_oltp=i, nombre=f"Taller {i}", cupos_totales=20)
            for i in range(100)
        ]
        DimTaller.objects.bulk_create(talleres)
        
        vecinos = [
            DimVecino(vecino_id_oltp=i, nombre_completo=f"Vecino {i}") 
            for i in range(200)
        ]
        DimVecino.objects.bulk_create(vecinos)

    def test_carga_dashboard_menos_8_segundos(self):
        """
        CP-BI-003: Verificar que el dashboard carga en menos de 8 segundos.
        """
        print("\nEjecutando CP-BI-003: Prueba de rendimiento SLA Dashboard...")
        
        start_time = time.time()
        
        # Petición GET a la vista del panel
        response = self.client.get(reverse('panel_bi')) 
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f" -> Tiempo de respuesta obtenido: {duration:.4f} segundos")
        
        # Validaciones de éxito y tiempo
        self.assertEqual(response.status_code, 200, "El panel debe cargar correctamente (HTTP 200)")
        self.assertLess(duration, 8.0, f"Fallo SLA: Tardó {duration}s, límite es 8s")


# -------------------------------------------------------------------------
# 2. PRUEBA DE LÓGICA DE NEGOCIO - Cálculo de KPIs
# -------------------------------------------------------------------------
class KpiLogicTest(TestCase):
    def setUp(self):
        # Preparación de datos de prueba
        self.vecino = DimVecino.objects.create(vecino_id_oltp=999, nombre_completo="Juan Perez")
        
        # Creación de actas simuladas
        self.acta_popular = DimActa.objects.create(
            acta_id_oltp=10, 
            titulo="Acta Muy Leída", 
            fecha_reunion="2024-01-01", 
            precision_transcripcion=100
        )
        self.acta_impopular = DimActa.objects.create(
            acta_id_oltp=11, 
            titulo="Acta Poco Leída", 
            fecha_reunion="2024-01-02", 
            precision_transcripcion=90
        )

        # Simulación de consultas (Hechos)
        # 3 consultas para el acta popular
        for _ in range(3):
            FactConsultaActa.objects.create(
                vecino=self.vecino, 
                acta=self.acta_popular, 
                fecha_consulta=timezone.now()
            )
        
        # 1 consulta para el acta impopular
        FactConsultaActa.objects.create(
            vecino=self.vecino, 
            acta=self.acta_impopular, 
            fecha_consulta=timezone.now()
        )

    def test_calculo_ranking_actas(self):
        """
        CP-BI-004: Validar que el algoritmo ordena correctamente las actas más leídas.
        """
        print("\nEjecutando CP-BI-004: Prueba de Lógica KPI (Ranking)...")

        # Llama a la lógica de construcción de datos (Caja Blanca)
        datos = construir_datos_panel_bi()
        ranking = datos['consulta_actas']
        
        # Validaciones del ordenamiento
        self.assertEqual(ranking[0]['acta__titulo'], "Acta Muy Leída")
        self.assertEqual(ranking[0]['consultas'], 3)
        self.assertEqual(ranking[1]['acta__titulo'], "Acta Poco Leída")
        self.assertEqual(ranking[1]['consultas'], 1)


# -------------------------------------------------------------------------
# 3. PRUEBAS DE SEGURIDAD - Inyección SQL y XSS
# -------------------------------------------------------------------------
class SecurityTest(TestCase):
    def setUp(self):
        # Usuario autenticado malintencionado
        self.user = User.objects.create_user(username='hacker', password='123')
        self.client = Client()
        self.client.force_login(self.user)

    def test_sql_injection_attempt(self):
        """
        CP-SEC-001: Verificar resistencia a Inyección SQL en filtros de fecha.
        """
        print("\nEjecutando CP-SEC-001: Prueba de Seguridad (SQL Injection)...")
        
        malicious_payload = "2024 OR 1=1"
        url = reverse('panel_bi') + f"?anio={malicious_payload}"
        
        response = self.client.get(url)
        
        # El sistema no debe fallar (500) ni ejecutar la inyección
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "OR 1=1")

    def test_xss_attempt(self):
        """
        CP-SEC-002: Verificar protección contra Cross-Site Scripting (XSS).
        """
        print("\nEjecutando CP-SEC-002: Prueba de Seguridad (XSS)...")
        
        script = "<script>alert('HACKED')</script>"
        url = reverse('panel_bi') + f"?mes={script}"
        
        response = self.client.get(url)
        
        # El script debe estar escapado y no presente tal cual en la respuesta
        self.assertNotContains(response, script)


# -------------------------------------------------------------------------
# 4. PRUEBA DE ESTRÉS Y CONCURRENCIA
# -------------------------------------------------------------------------
class ConcurrencyTest(TransactionTestCase):
    reset_sequences = True 

    def setUp(self):
        self.user = User.objects.create_user(username='stress_user', password='123')
        self.url = reverse('panel_bi')
        
        # Login inicial en el hilo principal
        self.master_client = Client()
        self.master_client.force_login(self.user)
        self.session_cookie = self.master_client.cookies.get('sessionid')

    def _make_request(self, results, index):
        """Función auxiliar que ejecutará cada hilo"""
        client = Client()
        # Inyecta la sesión compartida
        if self.session_cookie:
            client.cookies['sessionid'] = self.session_cookie.value
            
        try:
            response = client.get(self.url)
            results[index] = response.status_code
        except Exception as e:
            results[index] = str(e)

    def test_acceso_concurrente_15_usuarios(self):
        """
        CP-PERF-001: Simular 15 usuarios accediendo simultáneamente al Dashboard.
        """
        print("\nEjecutando CP-PERF-001: Prueba de Carga Concurrente (15 hilos)...")
        
        cantidad_usuarios = 15
        threads = []
        resultados = [None] * cantidad_usuarios

        # Crear e iniciar hilos
        for i in range(cantidad_usuarios):
            t = threading.Thread(target=self._make_request, args=(resultados, i))
            threads.append(t)
            t.start()

        # Esperar terminación
        for t in threads:
            t.join()

        # Análisis de resultados
        exitos = resultados.count(200)
        fallos = cantidad_usuarios - exitos
        
        print(f" -> Peticiones lanzadas: {cantidad_usuarios}")
        print(f" -> Éxitos (HTTP 200): {exitos}")
        
        if fallos > 0:
            errores = [r for r in resultados if r != 200]
            print(f" -> Detalle del error: {errores[0]}")

        self.assertEqual(exitos, cantidad_usuarios, f"Hubo {fallos} fallos bajo carga concurrente.")