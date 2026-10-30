import unittest
from _client import TestClient

from main import app, _generate_jwt


class AdminAnalyticsDashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_token = _generate_jwt("+8801745678901", "admin")
        self.donor_token = _generate_jwt("+8801712345678", "donor")

    def test_unauthenticated_admin_dashboard_redirects_to_login(self):
        response = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/login", response.headers.get("location"))

    def test_donor_accessing_admin_dashboard_redirects_to_login_console(self):
        response = self.client.get(
            "/admin/dashboard",
            cookies={"access_token": self.donor_token},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("/login", response.headers.get("location"))

    def test_admin_dashboard_page_renders_master_analytics(self):
        response = self.client.get(
            "/admin/dashboard",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("section-analytics", html)
        self.assertIn("section-users", html)
        self.assertIn("section-kyc", html)

    def test_admin_analytics_summary_api_default(self):
        response = self.client.get(
            "/api/v1/admin/analytics/summary",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["time_range"], "7d")

        # KPI Metrics validation
        kpi = data["kpi_metrics"]
        self.assertIn("total_users", kpi)
        self.assertIn("total_donors", kpi)
        self.assertIn("total_requests", kpi)
        self.assertIn("critical_requests", kpi)
        self.assertIn("fulfilled_donations", kpi)
        self.assertIn("monitored_facilities", kpi)
        self.assertIn("cold_storage_temp", kpi)
        self.assertIn("apheresis_units", kpi)
        self.assertIn("verified_donor_percent", kpi)

        # Supply vs Demand Matrix validation
        balances = data["blood_group_balance"]
        self.assertIsInstance(balances, list)
        self.assertGreaterEqual(len(balances), 8)
        groups = {b["blood_group"] for b in balances}
        self.assertIn("A+", groups)
        self.assertIn("O-", groups)

        # Regional distribution validation
        regions = data["regional_distribution"]
        self.assertIsInstance(regions, list)
        division_names = {r["division"] for r in regions}
        self.assertIn("Dhaka", division_names)
        self.assertIn("Chittagong", division_names)
        self.assertIn("Sylhet", division_names)

        # Trend & activity stream validation
        self.assertIsInstance(data["weekly_trend"], list)
        self.assertIsInstance(data["activity_stream"], list)
        self.assertGreaterEqual(len(data["activity_stream"]), 3)

    def test_admin_analytics_summary_time_ranges(self):
        for tr in ["24h", "7d", "30d", "all"]:
            response = self.client.get(
                f"/api/v1/admin/analytics/summary?time_range={tr}",
                cookies={"access_token": self.admin_token},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["time_range"], tr)
            self.assertIsInstance(data["weekly_trend"], list)
            self.assertGreater(len(data["weekly_trend"]), 0)
