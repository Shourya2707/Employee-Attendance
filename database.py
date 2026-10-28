"""Storage: MongoDB if one is reachable, otherwise a local JSON file with the same small API."""
import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).parent
DB_FILE = HERE / "attendance_db.json"
_lock = threading.Lock()  # one writer at a time; collections share one file


class DuplicateKeyError(Exception):
    pass


def _matches(doc, query):
    return all(doc.get(k) == v for k, v in (query or {}).items())


class LocalCollection:
    """The subset of pymongo's Collection this app uses, stored under one key of a JSON file.
    The file is re-read on every call, so the CLI and the web server see each other's changes."""

    def __init__(self, name, path=DB_FILE, unique=()):
        self.name, self.path, self.unique = name, Path(path), unique

    def _read(self):
        try:
            return json.loads(self.path.read_text("utf-8"))
        except FileNotFoundError:
            return {}

    def _docs(self):
        return self._read().get(self.name, [])

    def _save(self, docs):
        data = self._read()
        data[self.name] = docs
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), "utf-8")
        os.replace(tmp, self.path)  # atomic: readers never see a half-written file

    def find(self, query=None, projection=None, sort=()):
        docs = [d for d in self._docs() if _matches(d, query)]
        for field, direction in reversed(sort):
            docs.sort(key=lambda d: d.get(field, ""), reverse=direction < 0)
        return docs

    def find_one(self, query=None, projection=None):
        return next(iter(self.find(query)), None)

    def insert_one(self, doc):
        self.insert_many([doc])

    def insert_many(self, new_docs):
        with _lock:
            docs = self._docs()
            for doc in new_docs:
                for keys in self.unique:
                    if any(all(d.get(k) == doc.get(k) for k in keys) for d in docs):
                        raise DuplicateKeyError(f"Duplicate {'/'.join(keys)} in {self.name}")
                docs.append(dict(doc))
            self._save(docs)

    def update_one(self, query, update, upsert=False):
        with _lock:
            docs = self._docs()
            match = next((d for d in docs if _matches(d, query)), None)
            if match:
                match.update(update["$set"])
            elif upsert:
                docs.append({**query, **update["$set"]})
            self._save(docs)

    def delete_one(self, query):
        with _lock:
            docs = self._docs()
            match = next((d for d in docs if _matches(d, query)), None)
            if match:
                docs.remove(match)
                self._save(docs)
            return SimpleNamespace(deleted_count=int(match is not None))


def local_collections(path=DB_FILE):
    return (LocalCollection("employees", path, [("employee_id",)]),
            LocalCollection("attendance", path, [("employee_id", "date")]))


def connect():
    """Return (employees, attendance) collections: MongoDB if reachable, else attendance_db.json."""
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    try:
        import pymongo
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        db = client["employee_attendance_db"]
        db.employees.create_index("employee_id", unique=True)
        db.attendance.create_index([("employee_id", 1), ("date", 1)], unique=True)
        print("Using MongoDB at", uri)
        return db.employees, db.attendance
    except Exception:  # pymongo missing or server down
        print(f"MongoDB not reachable, using {DB_FILE.name}")
        return local_collections()
