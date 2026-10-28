"""
Automated Feature Test Suite for Employee Attendance Management System
"""
import unittest
import os
from datetime import date
from pathlib import Path

from validators import (
    validate_employee_id,
    validate_name,
    validate_department,
    validate_designation,
    validate_date,
    validate_status,
    validate_time,
    validate_checkin_checkout,
    VALID_STATUSES
)
from database import LocalClient, LocalCollection, DuplicateKeyError

class TestValidators(unittest.TestCase):
    def test_employee_id_validation(self):
        # Valid cases
        valid, val = validate_employee_id("EMP101")
        self.assertTrue(valid)
        self.assertEqual(val, "EMP101")

        valid, val = validate_employee_id("emp-002")
        self.assertTrue(valid)
        self.assertEqual(val, "EMP-002")

        # Invalid cases
        valid, _ = validate_employee_id("")
        self.assertFalse(valid)

        valid, _ = validate_employee_id("A") # too short
        self.assertFalse(valid)

        valid, _ = validate_employee_id("EMP 123") # spaces not allowed
        self.assertFalse(valid)

    def test_name_validation(self):
        valid, val = validate_name("Aarav Sharma")
        self.assertTrue(valid)
        self.assertEqual(val, "Aarav Sharma")

        valid, _ = validate_name("")
        self.assertFalse(valid)

        valid, _ = validate_name("A")
        self.assertFalse(valid)

        valid, _ = validate_name("John123")
        self.assertFalse(valid)

    def test_department_validation(self):
        valid, val = validate_department("engineering")
        self.assertTrue(valid)
        self.assertEqual(val, "Engineering")

        valid, _ = validate_department("")
        self.assertFalse(valid)

    def test_designation_validation(self):
        valid, val = validate_designation("software engineer")
        self.assertTrue(valid)
        self.assertEqual(val, "Software Engineer")

    def test_date_validation(self):
        valid, val = validate_date("2026-10-28")
        self.assertTrue(valid)
        self.assertEqual(val, "2026-10-28")

        # Empty defaults to today
        valid, val = validate_date("")
        self.assertTrue(valid)
        self.assertEqual(val, date.today().strftime("%Y-%m-%d"))

        # Invalid format
        valid, _ = validate_date("28-10-2026")
        self.assertFalse(valid)

    def test_status_validation(self):
        for status in VALID_STATUSES:
            valid, val = validate_status(status.lower())
            self.assertTrue(valid)
            self.assertEqual(val, status)

        valid, _ = validate_status("UnknownStatus")
        self.assertFalse(valid)

    def test_time_and_checkout_validation(self):
        valid, val = validate_time("09:30")
        self.assertTrue(valid)
        self.assertEqual(val, "09:30")

        valid, _ = validate_time("25:00")
        self.assertFalse(valid)

        # Checkout after checkin
        valid, _ = validate_checkin_checkout("09:00", "18:00")
        self.assertTrue(valid)

        # Checkout before checkin
        valid, err = validate_checkin_checkout("18:00", "09:00")
        self.assertFalse(valid)
        self.assertIn("must be after", err)

class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        self.test_file = Path("test_db.json")
        if self.test_file.exists():
            self.test_file.unlink()
        self.client = LocalClient(self.test_file)
        self.emp_col = LocalCollection("employees", self.test_file)
        self.att_col = LocalCollection("attendance", self.test_file)
        self.emp_col.create_index("employee_id", unique=True)
        self.att_col.create_index([("employee_id", 1), ("date", 1)], unique=True)

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()

    def test_employee_crud_and_uniqueness(self):
        # Insert employee
        res = self.emp_col.insert_one({"employee_id": "EMP101", "name": "Test User", "department": "IT"})
        self.assertIsNotNone(res.inserted_id)

        # Duplicate ID must raise DuplicateKeyError
        with self.assertRaises(DuplicateKeyError):
            self.emp_col.insert_one({"employee_id": "EMP101", "name": "Second User", "department": "HR"})

        # Read employee
        doc = self.emp_col.find_one({"employee_id": "EMP101"})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["name"], "Test User")

        # Update employee
        self.emp_col.update_one({"employee_id": "EMP101"}, {"$set": {"department": "Engineering"}})
        updated = self.emp_col.find_one({"employee_id": "EMP101"})
        self.assertEqual(updated["department"], "Engineering")

        # Delete employee
        del_res = self.emp_col.delete_one({"employee_id": "EMP101"})
        self.assertEqual(del_res.deleted_count, 1)
        self.assertIsNone(self.emp_col.find_one({"employee_id": "EMP101"}))

    def test_attendance_crud_and_uniqueness(self):
        today = "2026-10-28"
        self.att_col.insert_one({
            "employee_id": "EMP101",
            "date": today,
            "status": "Present",
            "checkin_time": "09:00"
        })

        # Duplicate attendance for same employee on same date must raise DuplicateKeyError
        with self.assertRaises(DuplicateKeyError):
            self.att_col.insert_one({
                "employee_id": "EMP101",
                "date": today,
                "status": "Late"
            })

        # Different date or different employee is allowed
        self.att_col.insert_one({
            "employee_id": "EMP102",
            "date": today,
            "status": "Present"
        })
        self.assertEqual(self.att_col.count_documents(), 2)

if __name__ == "__main__":
    unittest.main()

