from datetime import date, datetime, time
from .db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False, default="Andy")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Day(db.Model):
    """
    One row per user per date. This is the "planner page" everything attaches to.
    """
    __tablename__ = "days"
    __table_args__ = (db.UniqueConstraint("user_id", "day_date", name="uq_user_day"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    day_date = db.Column(db.Date, nullable=False)

    focus = db.Column(db.String(200), nullable=True)
    wins = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("days", lazy=True))


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)

    # store as time-of-day; rendering uses the Day's date + this time
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=True)

    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    day = db.relationship("Day", backref=db.backref("appointments", lazy=True, cascade="all, delete-orphan"))


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Optional: link to a day for "today's tasks"
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=True)

    priority = db.Column(db.String(1), nullable=False, default="B")  # A/B/C
    text = db.Column(db.String(300), nullable=False)

    status = db.Column(db.String(20), nullable=False, default="open")  # open/done
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    done_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("tasks", lazy=True))
    day = db.relationship("Day", backref=db.backref("tasks", lazy=True))


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)

    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    day = db.relationship("Day", backref=db.backref("notes", lazy=True, cascade="all, delete-orphan"))



# --------------------------
# NEW: Weekly items
# --------------------------
class WeeklyItem(db.Model):
    __tablename__ = "weekly_items"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    week_start = db.Column(db.Date, nullable=False)  # Monday

    category = db.Column(db.String(50), nullable=False)
    text = db.Column(db.String(300), nullable=False)

    status = db.Column(db.String(20), nullable=False, default="open")  # open|done

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
