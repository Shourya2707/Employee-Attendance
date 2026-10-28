"""Demo data: 35 employees and ~6 weeks of weekday attendance ending today.
Run `python seed_data.py` to rebuild attendance_db.json. The server calls seed() when the DB is empty."""
import random
from datetime import date, datetime, timedelta

from database import DB_FILE, local_collections

FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Rahul", "Pooja", "Karthik", "Divya",
         "Sandeep", "Kavita", "Arjun", "Meera", "Nikhil", "Tanvi", "Aditya", "Shreya", "Deepak", "Ishita"]
LAST = ["Sharma", "Patel", "Gupta", "Verma", "Singh", "Iyer", "Nair", "Reddy", "Joshi", "Kulkarni",
        "Menon", "Banerjee", "Mehta", "Kapoor", "Pillai", "Mishra"]
CITIES = ["Bengaluru", "Mumbai", "Pune", "Hyderabad", "Delhi NCR", "Chennai"]

# department: (chance of arriving late, designations). Finance/Operations are punctual, Sales/IT Support are not.
DEPARTMENTS = {
    "Engineering": (0.08, ["Senior Backend Engineer", "Frontend Developer", "DevOps Engineer", "QA Automation Lead"]),
    "Product": (0.07, ["Senior Product Manager", "UI/UX Designer", "Product Analyst"]),
    "Finance": (0.02, ["Financial Controller", "Senior Accountant", "Payroll Specialist"]),
    "HR": (0.04, ["HR Business Partner", "Talent Acquisition Lead"]),
    "Sales": (0.20, ["Enterprise Sales Manager", "Account Executive", "Business Development Lead"]),
    "Marketing": (0.10, ["Growth Marketing Lead", "Content Strategist"]),
    "Operations": (0.03, ["Operations Lead", "Logistics Coordinator"]),
    "IT Support": (0.15, ["Systems Administrator", "Network Engineer"]),
}
LATE_NOTES = ["Traffic delay on Silk Board junction", "Heavy jam on Western Express Highway",
              "Metro purple line delay", "Outer Ring Road waterlogging", "Heavy rain delay",
              "Traffic congestion near Cyber City", "Cab cancelled last minute"]
LEAVE_NOTES = ["Casual leave", "Sick leave - viral fever", "Earned leave - family function",
               "Personal emergency", "Medical appointment"]
HALF_DAY_NOTES = ["Doctor appointment in the afternoon", "Bank work", "Child's school event"]


def hhmm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def seed(emp_col, att_col, today=None):
    rng = random.Random(42)
    today = today or date.today()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    days = [today - timedelta(n) for n in range(41, -1, -1) if (today - timedelta(n)).weekday() < 5]

    employees = []
    for i, (first, last) in enumerate(rng.sample([(f, l) for f in FIRST for l in LAST], 35)):
        dept = list(DEPARTMENTS)[i % len(DEPARTMENTS)]
        employees.append({
            "employee_id": f"EMP{1001 + i}", "name": f"{first} {last}", "department": dept,
            "designation": rng.choice(DEPARTMENTS[dept][1]),
            "email": f"{first.lower()}.{last.lower()}@company.in",
            "phone": f"+91 {rng.randint(9700000000, 9999999999)}", "city": rng.choice(CITIES),
            "created_at": f"{days[0] - timedelta(rng.randint(30, 900))} 10:00:00", "status": "Active",
        })
    emp_col.insert_many([dict(e) for e in employees])

    unmarked_today = {e["employee_id"] for e in rng.sample(employees, 6)}
    records = []
    for emp in employees:
        late_rate = DEPARTMENTS[emp["department"]][0] * rng.uniform(0.6, 1.4)  # personal habit
        leave_left = 0
        for day in days:
            roll = rng.random()
            checkin, checkout, notes = hhmm(rng.randint(525, 569)), hhmm(rng.randint(1065, 1170)), ""  # 08:45-09:29, 17:45-19:30
            if leave_left or roll < 0.025:  # leave comes in streaks of 1-3 days
                leave_left = (leave_left or rng.randint(1, 3)) - 1
                status, checkin, checkout, notes = "On Leave", "", "", rng.choice(LEAVE_NOTES)
            elif roll < 0.04:
                status, checkin, checkout, notes = "Absent", "", "", "Uninformed absence"
            elif roll < 0.07:
                status, checkout, notes = "Half-Day", hhmm(rng.randint(780, 870)), rng.choice(HALF_DAY_NOTES)
            elif roll < 0.07 + late_rate:
                status, checkin, notes = "Late", hhmm(rng.randint(571, 645)), rng.choice(LATE_NOTES)  # 09:31-10:45
            else:
                status = "Present"
            marked_at = f"{day} {checkin or '09:00'}:00"
            if day == today:  # nothing may be in the future
                if emp["employee_id"] in unmarked_today or f"{day} {checkin}" > now:
                    continue  # not marked yet / not arrived yet
                if f"{day} {checkout}" > now:
                    checkout = ""  # still at work
                marked_at = min(marked_at, now)
            records.append({
                "employee_id": emp["employee_id"], "employee_name": emp["name"], "department": emp["department"],
                "date": day.isoformat(), "status": status, "checkin_time": checkin, "checkout_time": checkout,
                "notes": notes, "marked_at": marked_at,
            })
    att_col.insert_many(records)
    return len(employees), len(records)


if __name__ == "__main__":
    DB_FILE.unlink(missing_ok=True)
    n_emp, n_att = seed(*local_collections())
    print(f"Seeded {n_emp} employees and {n_att} attendance records into {DB_FILE.name}")
