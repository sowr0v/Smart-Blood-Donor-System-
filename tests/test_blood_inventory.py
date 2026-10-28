import sqlite3
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import (
    AUTH_DATABASE_PATH,
    BLOOD_GROUPS,
    DATABASE_PATH,
    _generate_jwt,
    _get_blood_stock_thresholds,
    app,
    initialize_urgent_database,
)


class FacilityBloodInventoryTests(unittest.TestCase):
    hospital_phone = "+8801999990001"
    bank_phone = "+8801999990002"

    def setUp(self):
        self.client = TestClient(app)
        initialize_urgent_database()
        self.original_thresholds = _get_blood_stock_thresholds()
        self._clear_inventory(self.hospital_phone)
        self._clear_inventory(self.bank_phone)
        self.hospital_cookies = {
            "access_token": _generate_jwt(self.hospital_phone, "hospital")
        }
        self.bank_cookies = {"access_token": _generate_jwt(self.bank_phone, "bank")}
        self.admin_cookies = {
            "access_token": _generate_jwt("+8801745678901", "admin")
        }
        self.client.post(
            "/api/v1/facility/settings/reset",
            cookies=self.hospital_cookies,
        )
        self.client.post(
            "/api/v1/facility/settings/reset",
            cookies=self.bank_cookies,
        )

    def tearDown(self):
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
            with connection:
                connection.executemany(
                    "UPDATE blood_stock_thresholds SET threshold = ? WHERE blood_group = ?",
                    [
                        (threshold, group)
                        for group, threshold in self.original_thresholds.items()
                    ],
                )
        self._clear_inventory(self.hospital_phone)
        self._clear_inventory(self.bank_phone)
        self.client.post(
            "/api/v1/facility/settings/reset",
            cookies=self.hospital_cookies,
        )
        self.client.post(
            "/api/v1/facility/settings/reset",
            cookies=self.bank_cookies,
        )
        self.client.close()

    @staticmethod
    def _clear_inventory(phone):
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    "DELETE FROM facility_inventory_audit WHERE facility_phone = ?",
                    (phone,),
                )
                connection.execute(
                    "DELETE FROM facility_inventory_alerts WHERE facility_phone = ?",
                    (phone,),
                )
                connection.execute(
                    "DELETE FROM facility_blood_inventory WHERE facility_phone = ?",
                    (phone,),
                )

    def test_matrix_lists_all_blood_groups_and_available_quantities_for_facility_users(self):
        for cookies in (self.hospital_cookies, self.bank_cookies):
            response = self.client.get(
                "/api/v1/facility/inventory", cookies=cookies
            )
            self.assertEqual(response.status_code, 200)
            inventory = response.json()["inventory"]
            self.assertEqual(
                [item["blood_group"] for item in inventory], list(BLOOD_GROUPS)
            )
            self.assertTrue(all(item["quantity"] == 0 for item in inventory))
        for cookies in (
            self.hospital_cookies,
            self.bank_cookies,
        ):
        
            dashboard = self.client.get(
                "/hospital/dashboard", cookies=cookies
            )
            self.assertEqual(dashboard.status_code, 200)
            self.assertIn('id="section-stock-matrix"', dashboard.text)
            self.assertIn("Blood Stock Inventory Matrix Management", dashboard.text)
            self.assertIn("FACILITY BLOOD RESERVE", dashboard.text)
            self.assertIn(
                "Review available units by blood group and manage real-time inventory updates for this facility.",
                dashboard.text,
            )
            self.assertNotIn('class="inventory-hero-facility"', dashboard.text)
            self.assertIn('id="inventoryTotalUnits">0</strong>', dashboard.text)
            self.assertIn(
                'id="inventoryLowStockGroups" data-thresholds=',
                dashboard.text,
            )
            self.assertIn('id="inventoryLowStockGroups"', dashboard.text)
            self.assertIn('id="inventoryLastMatrixSync"', dashboard.text)
            self.assertIn('id="stockAlertsTableBody"', dashboard.text)
            self.assertIn('id="stockAlertsSummary"', dashboard.text)
            self.assertIn("administrator-defined minimum", dashboard.text)
            self.assertNotIn('id="facilityStockThreshold"', dashboard.text)
            self.assertNotIn("TOTAL UNITS IN STOCK", dashboard.text)
            self.assertNotIn("CRITICAL / LOW STOCK", dashboard.text)
            self.assertNotIn("LAST MATRIX SYNC", dashboard.text)
            self.assertIn(">Blood Group</th>", dashboard.text)
            self.assertIn(">Available Stock</th>", dashboard.text)
            self.assertIn(">Update Quantity</th>", dashboard.text)
            self.assertIn(">Last Updated</th>", dashboard.text)
            for group in BLOOD_GROUPS:
                self.assertIn(
                    f'data-inventory-quantity="{group}">0</strong>', dashboard.text
                )
                self.assertIn(f'data-blood-group="{group}"', dashboard.text)
                self.assertIn(f'data-inventory-save data-blood-group="{group}"', dashboard.text)
                self.assertIn('type="button" data-inventory-save', dashboard.text)
                self.assertIn(
                    f"onclick=\"window.saveFacilityInventory('{group}', 'inventory-input-",
                    dashboard.text,
                )
                self.assertIn("type=\"number\" min=\"0\" step=\"1\" required", dashboard.text)
            self.assertIn(
                '/static/js/hospital_dashboard.js?v=inventory-save-3',
                dashboard.text,
            )

    def test_update_persists_facility_stock_and_records_only_actual_changes(self):
        response = self.client.put(
            "/api/v1/facility/inventory/A%2B",
            json={"quantity": 7},
            cookies=self.hospital_cookies,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["item"]["quantity"], 7)
        self.assertTrue(response.json()["item"]["changed"])
        updated_at = response.json()["item"]["updated_at"]
        self.assertIsNotNone(updated_at)
        datetime.fromisoformat(updated_at)

        persisted = self.client.get(
            "/api/v1/facility/inventory", cookies=self.hospital_cookies
        ).json()["inventory"]
        self.assertEqual(
            next(item["quantity"] for item in persisted if item["blood_group"] == "A+"),
            7,
        )
        dashboard = self.client.get(
            "/hospital/dashboard", cookies=self.hospital_cookies
        )
        self.assertIn('data-inventory-quantity="A+">7</strong>', dashboard.text)
        self.assertIn(
            f'class="inventory-updated-at" data-timestamp="{updated_at}"',
            dashboard.text,
        )
        self.assertIn('data-inventory-save data-blood-group="A+"', dashboard.text)

        unchanged = self.client.put(
            "/api/v1/facility/inventory/A%2B",
            json={"quantity": 7},
            cookies=self.hospital_cookies,
        )
        self.assertEqual(unchanged.status_code, 200)
        self.assertFalse(unchanged.json()["item"]["changed"])
        self.assertEqual(unchanged.json()["item"]["updated_at"], updated_at)

        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            audit = connection.execute(
                """SELECT blood_group, previous_quantity, new_quantity, actor_phone
                   FROM facility_inventory_audit WHERE facility_phone = ?""",
                (self.hospital_phone,),
            ).fetchall()
        self.assertEqual(audit, [("A+", 0, 7, self.hospital_phone)])

    def test_save_button_sends_async_put_and_updates_quantity_and_timestamp(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "js"
            / "hospital_dashboard.js"
        ).read_text(encoding="utf-8")
        self.assertIn("window.saveFacilityInventory = async function", script)
        self.assertIn('form.addEventListener("submit"', script)
        self.assertIn("event.preventDefault();", script)
        self.assertIn('method: "PUT"', script)
        self.assertIn('`/api/v1/facility/inventory/${encodeURIComponent(bloodGroup)}`', script)
        self.assertIn("quantityDisplay.textContent = savedQuantity", script)
        self.assertIn("inventoryTotalDisplay.textContent = total", script)
        self.assertIn("lowStockDisplay.textContent = lowStockCount", script)
        self.assertIn("matrixSync.textContent = formatInventoryTimestamp(result.item.updated_at)", script)
        self.assertIn("parsedTimestamp.toLocaleString(\"en-US\"", script)
        self.assertIn("updatedAt.textContent = formatInventoryTimestamp(result.item.updated_at)", script)

    def test_stock_is_isolated_between_facilities_and_bank_users_can_update(self):
        updated = self.client.put(
            "/api/v1/facility/inventory/O-",
            json={"quantity": 4},
            cookies=self.bank_cookies,
        )
        self.assertEqual(updated.status_code, 200)

        hospital_stock = self.client.get(
            "/api/v1/facility/inventory", cookies=self.hospital_cookies
        ).json()["inventory"]
        bank_stock = self.client.get(
            "/api/v1/facility/inventory", cookies=self.bank_cookies
        ).json()["inventory"]
        hospital_o_negative = next(
            row["quantity"] for row in hospital_stock if row["blood_group"] == "O-"
        )
        bank_o_negative = next(
            row["quantity"] for row in bank_stock if row["blood_group"] == "O-"
        )
        self.assertEqual(hospital_o_negative, 0)
        self.assertEqual(bank_o_negative, 4)

    def test_low_stock_alerts_trigger_at_threshold_and_resolve_after_replenishment(self):
        for blood_group in BLOOD_GROUPS:
            response = self.client.put(
                f"/api/v1/facility/inventory/{blood_group.replace('+', '%2B')}",
                json={"quantity": 10},
                cookies=self.hospital_cookies,
            )
            self.assertEqual(response.status_code, 200)

        threshold_saved = self.client.put(
            "/api/v1/admin/blood-stock-thresholds/A%2B",
            json={"threshold": 5},
            cookies=self.admin_cookies,
        )
        self.assertEqual(threshold_saved.status_code, 200)

        update = self.client.put(
            "/api/v1/facility/inventory/A%2B",
            json={"quantity": 5},
            cookies=self.hospital_cookies,
        )
        self.assertEqual(update.status_code, 200)
        alerts = self.client.get(
            "/api/v1/facility/inventory/alerts",
            cookies=self.hospital_cookies,
        )
        self.assertEqual(alerts.status_code, 200)
        data = alerts.json()
        self.assertEqual(data["thresholds"]["A+"], 5)
        self.assertEqual(data["active_count"], 1)
        active_alert = next(item for item in data["alerts"] if item["blood_group"] == "A+")
        self.assertEqual(active_alert["status"], "active")
        self.assertEqual(active_alert["quantity"], 5)
        active_alert_id = active_alert["id"]

        repeated = self.client.get(
            "/api/v1/facility/inventory/alerts",
            cookies=self.hospital_cookies,
        ).json()
        self.assertEqual(repeated["active_count"], 1)
        self.assertEqual(
            next(item for item in repeated["alerts"] if item["blood_group"] == "A+")["id"],
            active_alert_id,
        )

        recovered = self.client.put(
            "/api/v1/facility/inventory/A%2B",
            json={"quantity": 6},
            cookies=self.hospital_cookies,
        )
        self.assertEqual(recovered.status_code, 200)
        history = self.client.get(
            "/api/v1/facility/inventory/alerts",
            cookies=self.hospital_cookies,
        ).json()
        resolved_alert = next(item for item in history["alerts"] if item["id"] == active_alert_id)
        self.assertEqual(resolved_alert["status"], "resolved")
        self.assertIsNotNone(resolved_alert["resolved_at"])
        self.assertEqual(history["active_count"], 0)

        threshold_update = self.client.put(
            "/api/v1/admin/blood-stock-thresholds/A%2B",
            json={"threshold": 6},
            cookies=self.admin_cookies,
        )
        self.assertEqual(threshold_update.status_code, 200)
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            active_after_threshold_change = connection.execute(
                """SELECT COUNT(*) FROM facility_inventory_alerts
                   WHERE facility_phone = ? AND blood_group = 'A+' AND status = 'active'""",
                (self.hospital_phone,),
            ).fetchone()[0]
        self.assertEqual(active_after_threshold_change, 1)
        threshold_alerts = self.client.get(
            "/api/v1/facility/inventory/alerts",
            cookies=self.hospital_cookies,
        ).json()
        self.assertEqual(threshold_alerts["thresholds"]["A+"], 6)
        self.assertEqual(threshold_alerts["active_count"], 1)
        self.assertEqual(
            next(
                item for item in threshold_alerts["alerts"]
                if item["blood_group"] == "A+"
            )["status"],
            "active",
        )

    def test_low_stock_alerts_and_threshold_changes_require_facility_authorization(self):
        for method in ("get", "put"):
            with self.subTest(method=method, access="anonymous"):
                response = (
                    self.client.get("/api/v1/facility/inventory/alerts")
                    if method == "get"
                    else self.client.post(
                        "/api/v1/hospital/settings",
                        json={"low_stock_threshold": 5},
                    )
                )
                self.assertEqual(response.status_code, 401)

        for role, phone in (
            ("donor", "+8801712345678"),
            ("admin", "+8801745678901"),
        ):
            with self.subTest(role=role):
                cookies = {"access_token": _generate_jwt(phone, role)}
                response = self.client.get(
                    "/api/v1/facility/inventory/alerts",
                    cookies=cookies,
                )
                self.assertEqual(response.status_code, 403)

        wrong_facility = self.client.post(
            "/api/v1/hospital/settings",
            json={"phone": self.bank_phone, "low_stock_threshold": 5},
            cookies=self.hospital_cookies,
        )
        self.assertEqual(wrong_facility.status_code, 403)

    def test_only_admins_can_read_or_update_blood_group_thresholds(self):
        anonymous_read = self.client.get("/api/v1/admin/blood-stock-thresholds")
        anonymous_update = self.client.put(
            "/api/v1/admin/blood-stock-thresholds/A%2B",
            json={"threshold": 7},
        )
        self.assertEqual(anonymous_read.status_code, 401)
        self.assertEqual(anonymous_update.status_code, 401)

        hospital_read = self.client.get(
            "/api/v1/admin/blood-stock-thresholds",
            cookies=self.hospital_cookies,
        )
        hospital_update = self.client.put(
            "/api/v1/admin/blood-stock-thresholds/A%2B",
            json={"threshold": 7},
            cookies=self.hospital_cookies,
        )
        self.assertEqual(hospital_read.status_code, 403)
        self.assertEqual(hospital_update.status_code, 403)

        thresholds = self.client.get(
            "/api/v1/admin/blood-stock-thresholds",
            cookies=self.admin_cookies,
        )
        self.assertEqual(thresholds.status_code, 200)
        self.assertEqual(set(thresholds.json()["thresholds"]), set(BLOOD_GROUPS))

    def test_admin_dashboard_shows_threshold_controls_and_facility_alerts(self):
        anonymous = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(anonymous.status_code, 303)

        admin = self.client.get("/admin/dashboard", cookies=self.admin_cookies)
        self.assertEqual(admin.status_code, 200)
        self.assertIn("Low Blood Stock Alerts &amp; Reorder Triggers", admin.text)
        self.assertIn('data-save-stock-threshold="A+"', admin.text)
        self.assertIn('id="adminStockAlertsTableBody"', admin.text)

    def test_admin_can_view_aggregated_facility_alerts(self):
        facility_phone = "+8801999990099"
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    """INSERT OR IGNORE INTO facility_blood_inventory
                       (facility_phone, blood_group, quantity) VALUES (?, 'O-', 2)""",
                    (facility_phone,),
                )
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    """INSERT OR IGNORE INTO facility_settings
                       (phone, facility_name, facility_type, updated_at)
                       VALUES (?, 'Test Hospital', 'Hospital', 1)""",
                    (facility_phone,),
                )

        try:
            with patch(
                "main._get_user_by_phone",
                return_value={"role": "hospital", "name": "Test Hospital"},
            ):
                admin_response = self.client.get(
                    "/api/v1/admin/facility/inventory/alerts",
                    cookies={"access_token": _generate_jwt("+8801745678901", "admin")},
                )
            self.assertEqual(admin_response.status_code, 200)
            data = admin_response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["thresholds"]["O-"], 5)
            facility = next(
                item for item in data["facilities"]
                if item["facility_name"] == "Test Hospital"
            )
            self.assertEqual(facility["thresholds"]["O-"], 5)
            self.assertEqual(facility["active_count"], 8)

            seeker_response = self.client.get(
                "/api/v1/admin/facility/inventory/alerts",
                cookies={"access_token": _generate_jwt("+8801723456789", "seeker")},
            )
            self.assertEqual(seeker_response.status_code, 403)
        finally:
            self._clear_inventory(facility_phone)
            with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
                with connection:
                    connection.execute(
                        "DELETE FROM facility_settings WHERE phone = ?",
                        (facility_phone,),
                    )

    def test_admin_inventory_overview_aggregates_authorized_facility_stock_and_locations(self):
        facility_phone = "+8801999990098"
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.executemany(
                    """INSERT OR REPLACE INTO facility_blood_inventory
                       (facility_phone, blood_group, quantity, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    [
                        (facility_phone, group, 12 if group == "A+" else 0, "2026-10-28T12:00:00+00:00")
                        for group in BLOOD_GROUPS
                    ],
                )
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    """INSERT OR REPLACE INTO facility_settings
                       (phone, facility_name, facility_type, division, gps_coords, updated_at)
                       VALUES (?, 'Overview Test Hospital', 'Hospital', 'Test Division',
                               '23.7257° N, 90.3980° E', 1)""",
                    (facility_phone,),
                )

        facility_user = {
            "phone": facility_phone,
            "role": "hospital",
            "name": "Overview Test Hospital",
        }
        try:
            with patch.dict("main.USERS", {facility_phone: facility_user}):
                summary = self.client.get(
                    "/api/v1/admin/inventory/summary",
                    cookies=self.admin_cookies,
                )
                heatmap = self.client.get(
                    "/api/v1/admin/inventory/heatmap",
                    cookies=self.admin_cookies,
                )
                facilities = self.client.get(
                    "/api/v1/admin/inventory/facilities?district=Test%20Division",
                    cookies=self.admin_cookies,
                )

                self.assertEqual(summary.status_code, 200)
                self.assertEqual(heatmap.status_code, 200)
                self.assertEqual(facilities.status_code, 200)
                summary_data = summary.json()
                self.assertEqual(
                    [item["blood_group"] for item in summary_data["groups"]],
                    list(BLOOD_GROUPS),
                )
                self.assertGreaterEqual(summary_data["total_units"], 12)

                facility = facilities.json()["facilities"][0]
                self.assertEqual(facility["facility_name"], "Overview Test Hospital")
                self.assertEqual(facility["stock"]["A+"], 12)
                self.assertEqual(facility["total_units"], 12)
                self.assertAlmostEqual(facility["latitude"], 23.7257)
                self.assertAlmostEqual(facility["longitude"], 90.398)
                self.assertNotIn("facility_phone", facility)
                self.assertNotIn("phone", facility)

                division = next(
                    item
                    for item in heatmap.json()["heatmap"]
                    if item["division"] == "Test Division"
                )
                self.assertEqual(division["total_units"], 12)
                self.assertEqual(division["facilities_count"], 1)
                self.assertEqual(division["groups"]["A+"], 12)

                for endpoint in (
                    "/api/v1/admin/inventory/summary",
                    "/api/v1/admin/inventory/heatmap",
                    "/api/v1/admin/inventory/facilities",
                ):
                    self.assertEqual(self.client.get(endpoint).status_code, 401)
                    self.assertEqual(
                        self.client.get(
                            endpoint,
                            cookies=self.hospital_cookies,
                        ).status_code,
                        403,
                    )
        finally:
            self._clear_inventory(facility_phone)
            with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
                with connection:
                    connection.execute(
                        "DELETE FROM facility_settings WHERE phone = ?",
                        (facility_phone,),
                    )

    def test_low_stock_threshold_is_validated(self):
        for invalid_threshold in (-1, 51, 1.5, "5"):
            with self.subTest(threshold=invalid_threshold):
                response = self.client.put(
                    "/api/v1/admin/blood-stock-thresholds/A%2B",
                    json={"threshold": invalid_threshold},
                    cookies=self.admin_cookies,
                )
                self.assertEqual(response.status_code, 422)

    def test_rejects_negative_empty_non_numeric_and_fractional_quantities(self):
        invalid_values = [-1, "", "not-a-number", 1.5, None]
        for quantity in invalid_values:
            with self.subTest(quantity=quantity):
                response = self.client.put(
                    "/api/v1/facility/inventory/A%2B",
                    json={"quantity": quantity},
                    cookies=self.hospital_cookies,
                )
                self.assertEqual(response.status_code, 422)

        invalid_group = self.client.put(
            "/api/v1/facility/inventory/X%2B",
            json={"quantity": 1},
            cookies=self.hospital_cookies,
        )
        self.assertEqual(invalid_group.status_code, 422)

    def test_inventory_access_and_modification_require_facility_user_role(self):
        for method in ("get", "put"):
            url = (
                "/api/v1/facility/inventory"
                if method == "get"
                else "/api/v1/facility/inventory/A%2B"
            )
            with self.subTest(method=method, access="anonymous"):
                response = (
                    self.client.get(url)
                    if method == "get"
                    else self.client.put(url, json={"quantity": 1})
                )
                self.assertEqual(response.status_code, 401)

            for role, phone in (
                ("donor", "+8801712345678"),
                ("admin", "+8801745678901"),
            ):
                with self.subTest(method=method, role=role):
                    cookies = {"access_token": _generate_jwt(phone, role)}
                    response = (
                        self.client.get(url, cookies=cookies)
                        if method == "get"
                        else self.client.put(url, json={"quantity": 1}, cookies=cookies)
                    )
                    self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
