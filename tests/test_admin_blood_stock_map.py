import sqlite3
import unittest
from contextlib import closing
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from main import app, _generate_jwt, DATABASE_PATH, AUTH_DATABASE_PATH
from admin_portal import (
    initialize_admin_and_notification_database,
    ALL_BLOOD_GROUPS,
    BANGLADESH_DIVISIONS_GEO,
)


class AdminBloodStockGeographicDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_admin_and_notification_database()

    def setUp(self):
        self.client = TestClient(app)
        initialize_admin_and_notification_database()
        self.admin_token = _generate_jwt("+8801745678901", "admin")
        self.donor_token = _generate_jwt("+8801712345678", "donor")
        self.seeker_token = _generate_jwt("+8801723456789", "seeker")
        self.admin_cookies = {"access_token": self.admin_token}
        self.donor_cookies = {"access_token": self.donor_token}
        self.seeker_cookies = {"access_token": self.seeker_token}

    def tearDown(self):
        self.client.close()

    # -------------------------------------------------------------------------
    # 1. Security & Access Control Tests
    # -------------------------------------------------------------------------
    def test_unauthenticated_requests_are_rejected_with_401(self):
        endpoints = [
            "/api/v1/admin/inventory/summary",
            "/api/v1/admin/inventory/heatmap",
            "/api/v1/admin/inventory/facilities",
            "/api/v1/admin/inventory/geo-availability",
        ]
        for ep in endpoints:
            with self.subTest(endpoint=ep):
                resp = self.client.get(ep)
                self.assertEqual(resp.status_code, 401, f"{ep} should require authentication")
                self.assertIn("detail", resp.json())

        # POST alert unauthenticated
        alert_resp = self.client.post(
            "/api/v1/admin/inventory/alert",
            json={"blood_group": "O-", "district": "Dhaka", "severity": "critical"},
        )
        self.assertEqual(alert_resp.status_code, 401)

    def test_donor_and_seeker_roles_are_forbidden_with_403(self):
        endpoints = [
            "/api/v1/admin/inventory/summary",
            "/api/v1/admin/inventory/heatmap",
            "/api/v1/admin/inventory/facilities",
            "/api/v1/admin/inventory/geo-availability",
        ]
        for cookies, role in [(self.donor_cookies, "donor"), (self.seeker_cookies, "seeker")]:
            for ep in endpoints:
                with self.subTest(role=role, endpoint=ep):
                    resp = self.client.get(ep, cookies=cookies)
                    self.assertEqual(
                        resp.status_code,
                        403,
                        f"{ep} should forbid role {role}",
                    )

    def test_authorized_admin_can_access_all_inventory_endpoints(self):
        endpoints = [
            "/api/v1/admin/inventory/summary",
            "/api/v1/admin/inventory/heatmap",
            "/api/v1/admin/inventory/facilities",
            "/api/v1/admin/inventory/geo-availability",
        ]
        for ep in endpoints:
            with self.subTest(endpoint=ep):
                resp = self.client.get(ep, cookies=self.admin_cookies)
                self.assertEqual(resp.status_code, 200, f"{ep} should allow admin")
                self.assertEqual(resp.json()["status"], "success")

    # -------------------------------------------------------------------------
    # 2. Facility Stock Overview & 8-Blood-Group Availability
    # -------------------------------------------------------------------------
    def test_inventory_summary_aggregates_all_eight_blood_groups(self):
        resp = self.client.get("/api/v1/admin/inventory/summary", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertGreater(data["total_units"], 0)
        self.assertGreater(data["facilities_reporting"], 0)
        self.assertIn("critical_shortage_alerts_count", data)

        groups = data["groups"]
        self.assertEqual(len(groups), 8)
        returned_groups = [g["blood_group"] for g in groups]
        self.assertEqual(returned_groups, ALL_BLOOD_GROUPS)

        for g in groups:
            self.assertIn(g["blood_group"], ALL_BLOOD_GROUPS)
            self.assertIsInstance(g["units"], int)
            self.assertIn(g["status"], ("adequate", "low", "critical"))
            self.assertIsInstance(g["critical_facilities_count"], int)
            self.assertIsInstance(g["low_facilities_count"], int)

    def test_facilities_endpoint_returns_eight_blood_group_matrix(self):
        resp = self.client.get("/api/v1/admin/inventory/facilities", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        facilities = data["facilities"]
        self.assertGreaterEqual(len(facilities), 10)

        for fac in facilities:
            self.assertIn("facility_name", fac)
            self.assertIn("facility_type", fac)
            self.assertIn("district", fac)
            self.assertIn("latitude", fac)
            self.assertIn("longitude", fac)
            self.assertIn("total_units", fac)
            self.assertIn("has_critical", fac)
            self.assertIn("status", fac)
            self.assertIn("maintenance_mode", fac)
            self.assertIn("network_active", fac)

            # Stock matrix must have all 8 ABO/Rh groups
            stock = fac["stock"]
            for bg in ALL_BLOOD_GROUPS:
                self.assertIn(bg, stock, f"{fac['facility_name']} missing {bg}")
                self.assertIsInstance(stock[bg], int)
                self.assertGreaterEqual(stock[bg], 0)

            self.assertEqual(fac["total_units"], sum(stock.values()))

    # -------------------------------------------------------------------------
    # 3. Geographic View & GIS Heatmap Tests
    # -------------------------------------------------------------------------
    def test_heatmap_endpoint_covers_all_eight_bangladesh_divisions(self):
        resp = self.client.get("/api/v1/admin/inventory/heatmap", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        heatmap = data["heatmap"]
        self.assertEqual(len(heatmap), 8)
        division_names = {d["division"] for d in heatmap}
        expected_divisions = set(BANGLADESH_DIVISIONS_GEO.keys())
        self.assertEqual(division_names, expected_divisions)

        for div in heatmap:
            self.assertIn("latitude", div)
            self.assertIn("longitude", div)
            self.assertGreaterEqual(div["latitude"], 20.0)
            self.assertLessEqual(div["latitude"], 27.0)
            self.assertGreaterEqual(div["longitude"], 88.0)
            self.assertLessEqual(div["longitude"], 93.5)

            self.assertIn("total_units", div)
            self.assertIn("facilities_count", div)
            self.assertIn("shortage_score", div)
            self.assertGreaterEqual(div["shortage_score"], 0)
            self.assertLessEqual(div["shortage_score"], 100)
            self.assertIn("severity", div)
            self.assertIn("color_code", div)
            self.assertIn("blood_groups", div)

            # Check rare groups breakdown
            self.assertIn("o_minus_units", div)
            self.assertIn("b_minus_units", div)

    def test_geo_availability_unified_payload_for_leaflet_map(self):
        resp = self.client.get("/api/v1/admin/inventory/geo-availability", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("map_center", data)
        self.assertAlmostEqual(data["map_center"]["lat"], 23.8103, places=2)
        self.assertAlmostEqual(data["map_center"]["lng"], 90.4125, places=2)

        self.assertIn("divisions", data)
        self.assertEqual(len(data["divisions"]), 8)

        self.assertIn("facilities", data)
        self.assertGreaterEqual(len(data["facilities"]), 10)

        # Validate facility GPS bounds for Bangladesh
        for f in data["facilities"]:
            self.assertTrue(20.0 <= f["latitude"] <= 27.5, f"Latitude {f['latitude']} outside BD")
            self.assertTrue(88.0 <= f["longitude"] <= 93.5, f"Longitude {f['longitude']} outside BD")
            self.assertIn(f["status"], ("adequate", "low", "critical", "maintenance"))
            self.assertIn("color_code", f)

        self.assertIn("thresholds", data)
        self.assertIn("summary", data)

    def test_facilities_filtering_by_district(self):
        resp = self.client.get("/api/v1/admin/inventory/facilities?district=Dhaka", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        facilities = resp.json()["facilities"]
        self.assertGreater(len(facilities), 0)
        for f in facilities:
            self.assertEqual(f["district"].lower(), "dhaka")

    def test_facilities_filtering_by_status(self):
        resp = self.client.get("/api/v1/admin/inventory/facilities?status=critical", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        facilities = resp.json()["facilities"]
        for f in facilities:
            self.assertEqual(f["status"], "critical")

    # -------------------------------------------------------------------------
    # 4. Facility Privacy Rules & Maintenance Mode
    # -------------------------------------------------------------------------
    def test_facility_maintenance_mode_and_privacy_rules_respected(self):
        test_phone = "+8801999990888"
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as conn:
            with conn:
                conn.execute(
                    """INSERT OR REPLACE INTO facility_settings
                       (phone, facility_name, facility_type, division, gps_coords, maintenance_mode, inter_facility_network, updated_at)
                       VALUES (?, 'Specialized Trauma Center', 'Hospital', 'Dhaka', '23.7500° N, 90.3900° E', 1, 0, ?)""",
                    (test_phone, int(datetime.now(timezone.utc).timestamp())),
                )
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            with conn:
                conn.execute(
                    """INSERT OR REPLACE INTO facility_blood_inventory
                       (facility_phone, blood_group, quantity, updated_at) VALUES (?, 'O-', 15, ?)""",
                    (test_phone, datetime.now(timezone.utc).isoformat()),
                )

        try:
            resp = self.client.get("/api/v1/admin/inventory/facilities", cookies=self.admin_cookies)
            self.assertEqual(resp.status_code, 200)
            facilities = resp.json()["facilities"]
            trauma = next((f for f in facilities if f["facility_name"] == "Specialized Trauma Center"), None)
            self.assertIsNotNone(trauma)
            self.assertTrue(trauma["maintenance_mode"])
            self.assertEqual(trauma["status"], "maintenance")
            self.assertFalse(trauma["network_active"])
            self.assertAlmostEqual(trauma["latitude"], 23.75, places=2)
            self.assertAlmostEqual(trauma["longitude"], 90.39, places=2)
        finally:
            with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as conn:
                with conn:
                    conn.execute("DELETE FROM facility_settings WHERE phone = ?", (test_phone,))
            with closing(sqlite3.connect(DATABASE_PATH)) as conn:
                with conn:
                    conn.execute("DELETE FROM facility_blood_inventory WHERE facility_phone = ?", (test_phone,))

    # -------------------------------------------------------------------------
    # 5. Emergency Inventory Shortage Alert Dispatch
    # -------------------------------------------------------------------------
    def test_admin_can_dispatch_inventory_shortage_alert(self):
        payload = {
            "blood_group": "O-",
            "district": "Sylhet",
            "severity": "critical",
            "message": "Immediate O- PRBC units required for surgery transfusion reserve.",
        }
        resp = self.client.post("/api/v1/admin/inventory/alert", json=payload, cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    # -------------------------------------------------------------------------
    # 6. UI Integration & Leaflet Resources in Template
    # -------------------------------------------------------------------------
    def test_admin_dashboard_template_renders_stock_and_map_elements(self):
        resp = self.client.get("/admin/dashboard", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        html = resp.text

        # Leaflet CDN assets included
        self.assertIn("leaflet@1.9.4/dist/leaflet.css", html)
        self.assertIn("leaflet@1.9.4/dist/leaflet.js", html)

        # Section & container IDs
        self.assertIn('id="section-stock"', html)
        self.assertIn('id="bloodStockMap"', html)
        self.assertIn('id="bloodGroupAvailabilityGrid"', html)
        self.assertIn('id="stockTotalUnitsVal"', html)
        self.assertIn('id="stockFacilitiesCountVal"', html)
        self.assertIn('id="stockCriticalGroupsVal"', html)
        self.assertIn('id="heatmapDivisionsGrid"', html)
        self.assertIn('id="facilitiesTableBody"', html)
        self.assertIn('id="adminStockAlertsTableBody"', html)

        # Blood group threshold save buttons
        for bg in ALL_BLOOD_GROUPS:
            self.assertIn(f'data-save-stock-threshold="{bg}"', html)
