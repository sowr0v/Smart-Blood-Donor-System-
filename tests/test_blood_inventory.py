import sqlite3
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from main import (
    BLOOD_GROUPS,
    DATABASE_PATH,
    _generate_jwt,
    app,
    initialize_urgent_database,
)


class FacilityBloodInventoryTests(unittest.TestCase):
    hospital_phone = "+8801999990001"
    bank_phone = "+8801999990002"

    def setUp(self):
        self.client = TestClient(app)
        initialize_urgent_database()
        self._clear_inventory(self.hospital_phone)
        self._clear_inventory(self.bank_phone)
        self.hospital_cookies = {
            "access_token": _generate_jwt(self.hospital_phone, "hospital")
        }
        self.bank_cookies = {"access_token": _generate_jwt(self.bank_phone, "bank")}

    def tearDown(self):
        self._clear_inventory(self.hospital_phone)
        self._clear_inventory(self.bank_phone)
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

        for cookies in (self.hospital_cookies, self.bank_cookies):
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
            self.assertIn('id="inventoryLowStockGroups">8</strong>', dashboard.text)
            self.assertIn('id="inventoryLastMatrixSync"', dashboard.text)
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
