# votaciones/tests.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class AdminAccessVotacionesTests(TestCase):
    """
    Pruebas de control de acceso al admin de Votaciones.
    Relacionado con el caso de prueba CP-VOT-003.
    """

    def setUp(self):
        # Usuario vecino (sin permisos de administración)
        self.vecino = User.objects.create_user(
            username="vecino_test",
            email="vecino@test.com",
            password="123456",
            is_staff=False,
            is_superuser=False,
        )

        # Usuario administrador (con acceso al admin)
        self.admin = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="123456",
            is_staff=True,
            is_superuser=True,
        )

        # URL del admin para crear votaciones:
        #   app: votaciones
        #   modelo: votacion
        #   acción: add
        self.admin_url = reverse("admin:votaciones_votacion_add")

    def test_vecino_no_puede_acceder_admin_votaciones(self):
        """
        CP-VOT-003 (parte negativa):
        Verificar que un usuario sin rol de administrador
        NO pueda acceder a la pantalla de creación de votaciones.
        """
        # Login como vecino
        logged = self.client.login(username="vecino_test", password="123456")
        self.assertTrue(logged)

        # Intentar acceder al admin de votaciones
        resp = self.client.get(self.admin_url, follow=True)

        # No debería devolver 200 mostrando el formulario
        self.assertNotEqual(resp.status_code, 200)

        # Aceptamos 302 (redirige a login) o 403 (forbidden)
        self.assertIn(resp.status_code, (302, 403))

        # Si hubo redirecciones, verificamos que en alguna aparezca /admin/login/
        if hasattr(resp, "redirect_chain"):
            self.assertTrue(
                any("/admin/login/" in url for url, code in resp.redirect_chain),
                msg="El usuario vecino no debería poder acceder al admin de votaciones.",
            )

    def test_admin_si_puede_acceder_admin_votaciones(self):
        """
        CP-VOT-003 (parte positiva):
        Verificar que un usuario administrador SÍ pueda acceder
        al formulario de creación de votaciones.
        """
        # Login como admin
        logged = self.client.login(username="admin_test", password="123456")
        self.assertTrue(logged)

        resp = self.client.get(self.admin_url)

        # El admin debe ver la página sin problemas
        self.assertEqual(resp.status_code, 200)

        # Texto que suele aparecer en el admin al crear un objeto.
        # Ajusta si en tu admin sale "Añadir votación" u otro texto.
        self.assertContains(resp, "votación", ignore_case=True)
