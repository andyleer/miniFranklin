from __future__ import annotations

from datetime import datetime, date, time, timedelta
import re

from flask import Blueprint, redirect, render_template, request, url_for, flash

from .db import db
from .models import User, Day, Appointment, Task, Note

bp = Blueprint("main", __name__)

# -----------------------------
# helpers
# -----------------------------
def get_or_create_default_user() -> User:
    user = db.session.query(User).first()
    if not user:
        user = User(display_name="Andy")
        db.session.add(user)
        db.session.commit()
    return user


def get_or_create_day(user_id: int, d: date) -> Day:
    day = db.session.query(Day).filter_by(user_id=user_id, day_date=d).first()
    if not day:
        day = Day(user_id=user_id, day_date=d)
        db.session.add(day)
        db.session.commit()
    return day


def parse_time_token(token: str) -> time | None:
    """
    Accepts: 9, 9:30, 09:30, 930, 14:05
    """
    token = token.strip().lower()
    m = re.fullmatch(r"(\d{1,2})(?::?(\d{2}))?", token)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2) or "00")
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return time(hour=hh, minute=mm)


def week_strip(center: date) -> list[date]:
    # Monday-start week
    start = center - timedelta(days=center.weekday())
    return [start + timedelta(days=i) for i in range(7)]


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


# -----------------------------
# ladder helper (appointment positioning)
# -----------------------------
LADDER_START_HOUR = 6
PX_PER_HOUR = 60  # tweak this to stretch/compress the ladder


def appt_top(t: time) -> int:
    """
    Convert a time-of-day into a pixel offset from the ladder top.
    """
    minutes_from_start = (t.hour - LADDER_START_HOUR) * 60 + t.minute
    return int(minutes_from_start * (PX_PER_HOUR / 60))


# ✅ Correct way to expose helpers to templates
@bp.app_context_processor
def _inject_template_helpers():
    return {
        "appt_top": appt_top,
    }


# -----------------------------
# routes
# -----------------------------
@bp.get("/")
def index():
    return redirect(url_for("main.day_view", day_str="today"))


@bp.get("/day/<day_str>")
def day_view(day_str: str):
    user = get_or_create_default_user()

    if day_str == "today":
        day_date = date.today()
    else:
        day_date = datetime.strptime(day_str, "%Y-%m-%d").date()

    day = get_or_create_day(user.id, day_date)

    # tasks for this day
    day_tasks = (
        db.session.query(Task)
        .filter(Task.user_id == user.id, Task.day_id == day.id)
        .order_by(Task.priority.asc(), Task.created_at.asc())
        .all()
    )

    # appointments for this day
    appts = (
        db.session.query(Appointment)
        .filter(Appointment.day_id == day.id)
        .order_by(Appointment.start_time.asc())
        .all()
    )

    # notes for this day
    notes = (
        db.session.query(Note)
        .filter(Note.day_id == day.id)
        .order_by(Note.created_at.asc())
        .all()
    )

    # week nav
    week_days = week_strip(day_date)
    prev_week = day_date - timedelta(days=7)
    next_week = day_date + timedelta(days=7)

    return render_template(
        "day.html",
        user=user,
        day=day,
        day_date=day_date,
        day_str=day_date.isoformat(),
        day_tasks=day_tasks,
        appts=appts,
        notes=notes,
        week_days=week_days,
        prev_week=prev_week,
        next_week=next_week,
    )


@bp.get("/week/<week_str>")
def week_view(week_str: str):
    """
    Weekly view placeholder (so your /day page can link to it without exploding).
    week_str:
      - 'current' => week of today
      - 'YYYY-MM-DD' => a date within the week to display
    """
    user = get_or_create_default_user()

    if week_str == "current":
        anchor = date.today()
    else:
        anchor = datetime.strptime(week_str, "%Y-%m-%d").date()

    start = week_start(anchor)
    days = [start + timedelta(days=i) for i in range(7)]

    # For now: show the week dates + (optionally) tasks/appts grouped by day
    # Later we’ll add your “category buckets” + dropdown capture.
    day_rows = []
    for d in days:
        day_obj = get_or_create_day(user.id, d)

        appts = (
            db.session.query(Appointment)
            .filter(Appointment.day_id == day_obj.id)
            .order_by(Appointment.start_time.asc())
            .all()
        )

        tasks = (
            db.session.query(Task)
            .filter(Task.user_id == user.id, Task.day_id == day_obj.id, Task.status == "open")
            .order_by(Task.priority.asc(), Task.created_at.asc())
            .all()
        )

        day_rows.append({"date": d, "day": day_obj, "appts": appts, "tasks": tasks})

    prev_week = start - timedelta(days=7)
    next_week = start + timedelta(days=7)

    return render_template(
        "week.html",
        user=user,
        week_start=start,
        days=days,
        day_rows=day_rows,
        prev_week=prev_week,
        next_week=next_week,
    )


@bp.post("/day/<day_str>/update")
def update_day(day_str: str):
    user = get_or_create_default_user()
    d = date.today() if day_str == "today" else datetime.strptime(day_str, "%Y-%m-%d").date()
    day = get_or_create_day(user.id, d)

    day.focus = request.form.get("focus", "").strip() or None
    day.wins = request.form.get("wins", "").strip() or None
    db.session.commit()

    return redirect(url_for("main.day_view", day_str=d.isoformat()))


@bp.post("/day/<day_str>/capture")
def capture(day_str: str):
    """
    One input box to rule them all.
    Examples:
      9:30 call Tony
      A: order bearings
      B: update forecast
      note: cabinet paint arrived
    """
    user = get_or_create_default_user()
    d = date.today() if day_str == "today" else datetime.strptime(day_str, "%Y-%m-%d").date()
    day = get_or_create_day(user.id, d)

    raw = (request.form.get("capture") or "").strip()
    if not raw:
        return redirect(url_for("main.day_view", day_str=d.isoformat()))

    lowered = raw.lower()

    # NOTE
    if lowered.startswith("note:"):
        body = raw.split(":", 1)[1].strip()
        if body:
            db.session.add(Note(day_id=day.id, body=body))
            db.session.commit()
        return redirect(url_for("main.day_view", day_str=d.isoformat()))

    # PRIORITY TASK (A:/B:/C:)
    m = re.match(r"^\s*([abcABC])\s*:\s*(.+)$", raw)
    if m:
        pr = m.group(1).upper()
        text = m.group(2).strip()
        if text:
            db.session.add(Task(user_id=user.id, day_id=day.id, priority=pr, text=text))
            db.session.commit()
        return redirect(url_for("main.day_view", day_str=d.isoformat()))

    # APPOINTMENT: starts with time token like "9:30 ..." or "930 ..."
    parts = raw.split()
    if parts:
        t = parse_time_token(parts[0])
        if t is not None and len(parts) >= 2:
            title = " ".join(parts[1:]).strip()
            db.session.add(Appointment(day_id=day.id, start_time=t, title=title))
            db.session.commit()
            return redirect(url_for("main.day_view", day_str=d.isoformat()))

    # fallback: B task
    db.session.add(Task(user_id=user.id, day_id=day.id, priority="B", text=raw))
    db.session.commit()
    return redirect(url_for("main.day_view", day_str=d.isoformat()))


@bp.post("/task/<int:task_id>/toggle")
def toggle_task(task_id: int):
    task = db.session.get(Task, task_id)
    if not task:
        flash("Task not found", "error")
        return redirect(url_for("main.index"))

    if task.status == "open":
        task.status = "done"
        task.done_at = datetime.utcnow()
    else:
        task.status = "open"
        task.done_at = None

    db.session.commit()

    if task.day_id:
        day = db.session.get(Day, task.day_id)
        return redirect(url_for("main.day_view", day_str=day.day_date.isoformat()))
    return redirect(url_for("main.day_view", day_str="today"))


@bp.post("/appt/<int:appt_id>/delete")
def delete_appt(appt_id: int):
    appt = db.session.get(Appointment, appt_id)
    if not appt:
        return redirect(url_for("main.index"))
    day = db.session.get(Day, appt.day_id)
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for("main.day_view", day_str=day.day_date.isoformat()))
