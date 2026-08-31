from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class LighthouseSmokeTest(APITestCase):
    """Minimal regression check: list endpoints resolve, authenticate, and
    serialize without error. Not business-logic coverage."""

    def setUp(self):
        self.user = User.objects.create_user(username="smoketest", password="smoketest-pw-12345")

    def test_lighthouse_list_requires_authentication(self):
        response = self.client.get("/api/lighthouse/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_lighthouse_list_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/lighthouse/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_lighthouse_details_list_requires_authentication(self):
        response = self.client.get("/api/lighthouse_details/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_lighthouse_details_list_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/lighthouse_details/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
