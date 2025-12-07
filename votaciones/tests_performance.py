import time
from django.test import TestCase
from django.contrib.auth.models import User
from votaciones.models import Votacion, Opcion, Voto


class RendimientoVotacionesTests(TestCase):
    """
    CP-VOT-004 – Verificar que registrar 500 votos tarda menos de 5 segundos.
    """

    def setUp(self):
        # Crear votación y opción
        self.votacion = Votacion.objects.create(
            pregunta="Prueba de rendimiento",
            fecha_cierre="2099-01-01 00:00:00",
            activa=True,
        )
        self.opcion = Opcion.objects.create(
            votacion=self.votacion,
            texto="Sí"
        )

        # Crear 500 usuarios
        self.usuarios = [
            User.objects.create_user(
                username=f"user{i}", password="123456"
            )
            for i in range(500)
        ]

    def test_registrar_500_votos_en_menos_de_5_segundos(self):
        inicio = time.time()

        for user in self.usuarios:
            Voto.objects.create(opcion=self.opcion, votante=user)

        fin = time.time()
        duracion = fin - inicio

        print("\n============================")
        print(f" TIEMPO TOTAL: {duracion:.4f} segundos")
        print("============================\n")

        # El requisito de rendimiento: < 5 segundos
        self.assertLess(duracion, 5.0, f"El sistema tardó {duracion} segundos en registrar 500 votos.")
