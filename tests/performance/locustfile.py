"""Locust load scenarios for the <500 ms @ 20 concurrent users target."""
from locust import HttpUser, between, task

CREDENTIALS = {"email": "admin@eduflow.com", "password": "admin123"}


class EduFlowUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self):
        response = self.client.post("/api/v1/auth/login", json=CREDENTIALS)
        if response.status_code != 200:
            return
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def browse_courses(self):
        self.client.get("/api/v1/courses?limit=20", headers=self.headers, name="/courses")

    @task(2)
    def browse_enrollments(self):
        self.client.get("/api/v1/enrollments?limit=20", headers=self.headers, name="/enrollments")

    @task(1)
    def dashboard(self):
        self.client.get("/api/v1/dashboard", headers=self.headers, name="/dashboard")

    @task(1)
    def audit(self):
        self.client.get("/api/v1/audit?limit=20", headers=self.headers, name="/audit")
