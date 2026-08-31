from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class YakeSmokeTest(APITestCase):
    """Minimal regression check: list endpoint resolves, authenticates, and
    serializes without error. Not business-logic coverage."""

    def setUp(self):
        self.user = User.objects.create_user(username="smoketest", password="smoketest-pw-12345")

    def test_list_requires_authentication(self):
        response = self.client.get("/api/keywords/yake/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_list_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/keywords/yake/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
