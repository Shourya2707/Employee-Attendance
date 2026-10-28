"""
Database module for Employee Attendance Management System
Supports real MongoDB via pymongo with seamless local JSON/SQLite storage fallback.
"""
import os
import json
from datetime import datetime
from pathlib import Path

class DuplicateKeyError(Exception):
    """Raised when an operation would violate a unique index constraint."""
    pass

class LocalCollection:
    """A lightweight, MongoDB-compatible collection for local file-backed persistence."""
    def __init__(self, name: str, storage_file: Path):
        self.name = name
        self.storage_file = storage_file
        self.unique_keys = set()
        self._last_mtime = 0
        self._load()

    def _check_reload(self):
        if self.storage_file.exists():
            try:
                mtime = self.storage_file.stat().st_mtime
                if mtime > self._last_mtime:
                    self._load()
            except Exception:
                pass

    def _load(self):
        if self.storage_file.exists():
            try:
                self._last_mtime = self.storage_file.stat().st_mtime
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.docs = data.get(self.name, [])
            except Exception:
                self.docs = []
        else:
            self.docs = []

    def _save(self):
        data = {}
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[self.name] = self.docs
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        if self.storage_file.exists():
            self._last_mtime = self.storage_file.stat().st_mtime

    def create_index(self, keys, unique=False):
        if unique:
            if isinstance(keys, str):
                self.unique_keys.add(keys)
            elif isinstance(keys, (list, tuple)):
                key_names = tuple(k[0] if isinstance(k, (list, tuple)) else k for k in keys)
                self.unique_keys.add(key_names)

    def _matches(self, doc, query):
        if not query:
            return True
        for k, v in query.items():
            if k == "$or":
                if not any(self._matches(doc, q) for q in v):
                    return False
            elif isinstance(v, dict):
                doc_val = doc.get(k)
                for op, op_val in v.items():
                    if op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                        return False
                    elif op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                        return False
                    elif op == "$gt" and not (doc_val is not None and doc_val > op_val):
                        return False
                    elif op == "$lt" and not (doc_val is not None and doc_val < op_val):
                        return False
                    elif op == "$in" and not (doc_val in op_val):
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def insert_one(self, doc):
        self._check_reload()
        doc_copy = dict(doc)
        # Check unique constraints
        for u_key in self.unique_keys:
            if isinstance(u_key, tuple):
                query = {k: doc_copy.get(k) for k in u_key}
            else:
                query = {u_key: doc_copy.get(u_key)}
            if self.find_one(query):
                raise DuplicateKeyError(f"E11000 duplicate key error collection: {self.name} index on {u_key}")

        if "_id" not in doc_copy:
            doc_copy["_id"] = len(self.docs) + 1
        self.docs.append(doc_copy)
        self._save()
        class Result:
            inserted_id = doc_copy["_id"]
        return Result()

    def find_one(self, query=None):
        self._check_reload()
        for doc in self.docs:
            if self._matches(doc, query):
                return dict(doc)
        return None

    def find(self, query=None, sort=None):
        self._check_reload()
        results = [dict(doc) for doc in self.docs if self._matches(doc, query)]
        if sort:
            for field, direction in reversed(sort):
                results.sort(key=lambda d: d.get(field, ""), reverse=(direction < 0))
        return results

    def update_one(self, query, update):
        self._check_reload()
        for doc in self.docs:
            if self._matches(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                else:
                    doc.update(update)
                self._save()
                class Result:
                    modified_count = 1
                return Result()
        class Result:
            modified_count = 0
        return Result()

    def delete_one(self, query):
        self._check_reload()
        for i, doc in enumerate(self.docs):
            if self._matches(doc, query):
                self.docs.pop(i)
                self._save()
                class Result:
                    deleted_count = 1
                return Result()
        class Result:
            deleted_count = 0
        return Result()

    def count_documents(self, query=None):
        self._check_reload()
        return len(self.find(query))

class LocalDatabase:
    """Mock/local database."""
    def __init__(self, storage_file: Path):
        self.storage_file = storage_file

    def __getitem__(self, name: str):
        return LocalCollection(name, self.storage_file)

class LocalClient:
    """Mock/local MongoClient."""
    def __init__(self, uri="local"):
        self.uri = uri
        self.storage_file = Path("attendance_db.json")

    def __getitem__(self, db_name: str):
        return LocalDatabase(self.storage_file)

    def close(self):
        pass

def load_env():
    """Load variables from .env file if available."""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

def connect_and_setup():
    """
    Connect to MongoDB if available and running; otherwise fall back to persistent local storage.
    Returns: (client, db, employees_collection, attendance_collection)
    """
    load_env()
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    client = None
    db = None

    try:
        import pymongo
        # Short timeout to quickly detect if local MongoDB is up
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=1000)
        client.admin.command('ping')
        db = client["employee_attendance_db"]
        emp_col = db["employees"]
        att_col = db["attendance"]

        # Set up unique indexes
        emp_col.create_index("employee_id", unique=True)
        att_col.create_index([("employee_id", 1), ("date", 1)], unique=True)
        print("Connected to live MongoDB successfully!")
        return client, db, emp_col, att_col
    except Exception as e:
        print("Notice: Live MongoDB instance not found on localhost:27017.")
        print("Switching to persistent Local Database storage ('attendance_db.json').")
        local_client = LocalClient("attendance_db.json")
        db = local_client["employee_attendance_db"]
        emp_col = LocalCollection("employees", local_client.storage_file)
        att_col = LocalCollection("attendance", local_client.storage_file)

        emp_col.create_index("employee_id", unique=True)
        att_col.create_index([("employee_id", 1), ("date", 1)], unique=True)
        return local_client, db, emp_col, att_col

