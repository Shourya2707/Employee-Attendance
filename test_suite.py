"""Tests. Run: python -m unittest test_suite -v  (uses temp files, never touches attendance_db.json)"""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path

import server
from database import DuplicateKeyError, local_collections
from validators import (VALID_STATUSES, validate_checkin_checkout, validate_date, validate_department,
                        validate_employee_id, validate_name, validate_status, validate_time)


class TestValidators(unittest.TestCase):
    def test_employee_id(self):
        self.assertEqual(validate_employee_id(" emp-002 "), (True, "EMP-002"))
        for bad in ("", "A", "EMP 123", None):
            self.assertFalse(validate_employee_id(bad)[0], bad)

    def test_name(self):
        self.assertEqual(validate_name("aarav sharma"), (True, "Aarav Sharma"))
        for bad in ("", "A", "John123"):
            self.assertFalse(validate_name(bad)[0], bad)

    def test_department_keeps_case(self):
        self.assertEqual(validate_department(" IT Support "), (True, "IT Support"))
        self.assertFalse(validate_department("")[0])

    def test_date(self):
        self.assertEqual(validate_date("2026-10-28"), (True, "2026-10-28"))
        self.assertEqual(validate_date(""), (True, date.today().isoformat()))
        self.assertFalse(validate_date("28-10-2026")[0])

    def test_status(self):
        for status in VALID_STATUSES:
            self.assertEqual(validate_status(status.upper()), (True, status))
        self.assertEqual(validate_status(""), (True, "Present"))
        self.assertFalse(validate_status("Sleeping")[0])

    def test_times(self):
        self.assertEqual(validate_time("9:30 AM"), (True, "09:30"))
        self.assertEqual(validate_time(""), (True, ""))
        self.assertFalse(validate_time("25:00")[0])
        self.assertTrue(validate_checkin_checkout("09:00", "18:00")[0])
        self.assertFalse(validate_checkin_checkout("18:00", "09:00")[0])


class TempDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.emp, self.att = local_collections(Path(self.tmp.name) / "db.json")

    def tearDown(self):
        self.tmp.cleanup()


class TestLocalCollection(TempDB):
    def test_crud(self):
        self.emp.insert_one({"employee_id": "EMP1", "name": "Test"})
        self.assertEqual(self.emp.find_one({"employee_id": "EMP1"})["name"], "Test")
        self.emp.update_one({"employee_id": "EMP1"}, {"$set": {"name": "New"}})
        self.assertEqual(self.emp.find_one()["name"], "New")
        self.emp.update_one({"employee_id": "EMP2"}, {"$set": {"name": "Upserted"}}, upsert=True)
        self.assertEqual([e["employee_id"] for e in self.emp.find(sort=[("employee_id", -1)])], ["EMP2", "EMP1"])
        self.assertEqual(self.emp.delete_one({"employee_id": "EMP1"}).deleted_count, 1)
        self.assertEqual(self.emp.delete_one({"employee_id": "EMP1"}).deleted_count, 0)

    def test_unique_constraints(self):
        self.emp.insert_one({"employee_id": "EMP1"})
        with self.assertRaises(DuplicateKeyError):
            self.emp.insert_one({"employee_id": "EMP1"})
        self.att.insert_one({"employee_id": "EMP1", "date": "2026-10-28"})
        self.att.insert_one({"employee_id": "EMP1", "date": "2026-10-27"})
        with self.assertRaises(DuplicateKeyError):
            self.att.insert_one({"employee_id": "EMP1", "date": "2026-10-28"})
        self.assertEqual(len(self.att.find()), 2)


class TestHTTP(TempDB):
    def setUp(self):
        super().setUp()
        self.emp.insert_one({"employee_id": "EMP1", "name": "Test", "department": "HR", "status": "Active"})
        server.emp_col, server.att_col = self.emp, self.att
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def post(self, body):
        url = f"http://127.0.0.1:{self.httpd.server_port}/api/attendance"
        req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_post_attendance(self):
        code, body = self.post({"employee_id": "EMP1", "status": "Sleeping"})
        self.assertEqual(code, 400)
        self.assertIn("Invalid status", body["error"])
        code, body = self.post({"employee_id": "emp1", "date": "2026-10-27", "status": "late", "checkin_time": "09:45"})
        self.assertEqual((code, body["status"], body["checkin_time"]), (200, "Late", "09:45"))
        self.assertEqual(len(self.att.find()), 1)


if __name__ == "__main__":
    unittest.main()
