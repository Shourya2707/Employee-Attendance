"""Input validation. Every validator returns (True, cleaned_value) or (False, error_message)."""
import re
from datetime import date, datetime

VALID_STATUSES = ["Present", "Late", "Half-Day", "On Leave", "Absent"]


def _text(value, label, low, high):
    value = (value or "").strip()
    if not low <= len(value) <= high:
        return False, f"{label} must be between {low} and {high} characters."
    return True, value


def validate_employee_id(emp_id):
    ok, value = _text(emp_id, "Employee ID", 2, 20)
    if not ok:
        return ok, value
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return False, "Employee ID can only contain letters, numbers, hyphens and underscores."
    return True, value.upper()


def validate_name(name):
    ok, value = _text(name, "Name", 2, 60)
    if not ok:
        return ok, value
    if not re.fullmatch(r"[A-Za-z .'-]+", value):
        return False, "Name can only contain letters, spaces, hyphens, apostrophes and periods."
    return True, value.title()


def validate_department(department):
    return _text(department, "Department", 2, 40)


def validate_designation(designation):
    return _text(designation, "Designation", 2, 50)


def validate_date(date_str):
    """YYYY-MM-DD; empty means today."""
    if not (date_str or "").strip():
        return True, date.today().isoformat()
    try:
        return True, datetime.strptime(date_str.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return False, "Invalid date. Expected YYYY-MM-DD (e.g. 2026-10-28)."


def validate_status(status):
    """Case-insensitive; empty means Present."""
    status = (status or "Present").strip()
    match = next((s for s in VALID_STATUSES if s.lower() == status.lower()), None)
    if match:
        return True, match
    return False, f"Invalid status '{status}'. Valid options: {', '.join(VALID_STATUSES)}."


def validate_time(time_str):
    """Accepts 09:30, 9:30 AM or 09:30:00 and returns HH:MM; empty stays empty."""
    time_str = (time_str or "").strip()
    if not time_str:
        return True, ""
    for fmt in ("%H:%M", "%I:%M %p", "%H:%M:%S"):
        try:
            return True, datetime.strptime(time_str, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return False, f"Invalid time '{time_str}'. Expected HH:MM (e.g. 09:30)."


def validate_checkin_checkout(checkin, checkout):
    """Both HH:MM (already validated), so string comparison orders them correctly."""
    if checkin and checkout and checkout <= checkin:
        return False, f"Check-out time ({checkout}) must be after check-in time ({checkin})."
    return True, checkout
