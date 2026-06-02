import unittest
from unittest.mock import patch

from app import create_app


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_ANON_KEY="public-anon-key",
            SUPABASE_SERVICE_ROLE_KEY="private-service-role-key",
        )

    def test_reset_confirm_exposes_only_public_supabase_config(self):
        with patch("routes.auth_routes.Config.SUPABASE_URL", "https://example.supabase.co"), patch(
            "routes.auth_routes.Config.SUPABASE_ANON_KEY", "public-anon-key"
        ), patch("routes.auth_routes.Config.SUPABASE_SERVICE_ROLE_KEY", "private-service-role-key"):
            response = self.app.test_client().get("/reset-password/confirm")

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("https://example.supabase.co", html)
        self.assertIn("public-anon-key", html)
        self.assertNotIn("private-service-role-key", html)
        self.assertIn("updateUser", html)
