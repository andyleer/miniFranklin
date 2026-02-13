from __future__ import annotations

from datetime import datetime, date, time, timedelta
import re

from flask import Blueprint, redirect, render_template, request, url_for, flash

from .db import db
from .models import User, Day, Appointment, Task, Note, WeeklyGoal

bp = Blueprint("main", __name__)


# routes.py (add near the top, after bp = Blueprint(...))

HOUR_HEIGHT_PX = 48
DISPLAY_START_HOUR = 6

@bp.app_template_global()
def appt_top(t: time) -> int:
    if not t:
        return 0
    minutes_from_start = (t.hour - DISPLAY_START_HOUR) * 60 + t.minute
    return int(minutes_from_start * (HOUR_HEIGHT_PX / 60.0))


# ---------- helpers ----------
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


def week_start_for(d: date) -> date:
    # Monday-start week
    return d - timedelta(days=d.weekday())


def week_strip(center: date) -> list[date]:
    start = week_start_for(center)
    return [start + timedelta(days=i) for i in range(7)]


# ---------- routes ----------
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

    day_tasks = (
        db.session.query(Task)
        .filter(Task.user_id == user.id, Task.day_id == day.id)
        .order_by(Task.priority.asc(), Task.created_at.asc())
        .all()
    )

    global_tasks = (
        db.session.query(Task)
        .filter(Task.user_id == user.id, Task.day_id.is_(None), Task.status == "open")
        .order_by(Task.priority.asc(), Task.created_at.asc())
        .all()
    )

    appts = (
        db.session.query(Appointment)
        .filter(Appointment.day_id == day.id)
        .order_by(Appointment.start_time.asc())
        .all()
    )

    notes = (
        db.session.query(Note)
        .filter(Note.day_id == day.id)
        .order_by(Note.created_at.desc())
        .all()
    )

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
        global_tasks=global_tasks,
        appts=appts,
        notes=notes,
        week_days=week_days,
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
    user = get_or_create_default_user()
    d = date.today() if day_str == "today" else datetime.strptime(day_str, "%Y-%m-%d").date()
    day = get_or_create_day(user.id, d)

    raw = (request.form.get("capture") or "").strip()
    if not raw:
        return redirect(url_for("main.day_view", day_str=d.isoformat()))

    lowered = raw.lower()

    if lowered.startswith("note:"):
        body = raw.split(":", 1)[1].strip()
        if body:
            db.session.add(Note(day_id=day.id, body=body))
            db.session.commit()
        return redirect(url_for("main.day_view", day_str=d.isoformat()))

    m = re.match(r"^\s*([abcABC])\s*:\s*(.+)$", raw)
    if m:
        pr = m.group(1).upper()
        text = m.group(2).strip()
        if text:
            db.session.add(Task(user_id=user.id, day_id=day.id, priority=pr, text=text))
            db.session.commit()
        return redirect(url_for("main.day_view", day_str=d.isoformat()))

    parts = raw.split()
    if parts:
        t = parse_time_token(parts[0])
        if t is not None and len(parts) >= 2:
            title = " ".join(parts[1:]).strip()
            db.session.add(Appointment(day_id=day.id, start_time=t, title=title))
            db.session.commit()
            return redirect(url_for("main.day_view", day_str=d.isoformat()))

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


@bp.post("/task/<int:task_id>/push_next")
def push_task_next(task_id: int):
    user = get_or_create_default_user()

    task = db.session.get(Task, task_id)
    if not task:
        flash("Task not found", "error")
        return redirect(url_for("main.day_view", day_str="today"))

    current_day_date = date.today()
    if task.day_id:
        day = db.session.get(Day, task.day_id)
        if day:
            current_day_date = day.day_date

    next_day_date = current_day_date + timedelta(days=1)
    next_day = get_or_create_day(user.id, next_day_date)

    task.day_id = next_day.id
    db.session.commit()

    return redirect(url_for("main.day_view", day_str=current_day_date.isoformat()))


@bp.post("/appt/<int:appt_id>/delete")
def delete_appt(appt_id: int):
    appt = db.session.get(Appointment, appt_id)
    if not appt:
        return redirect(url_for("main.index"))
    day = db.session.get(Day, appt.day_id)
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for("main.day_view", day_str=day.day_date.isoformat()))


# ─────────────────────────────────────────────────────────────
# WEEKLY PAGE
# ─────────────────────────────────────────────────────────────
@bp.get("/week/<week_str>")
def week_view(week_str: str):
    user = get_or_create_default_user()

    # week_str can be "current" or YYYY-MM-DD (any day in that week)
    if week_str == "current":
        anchor = date.today()
    else:
        anchor = datetime.strptime(week_str, "%Y-%m-%d").date()

    wk_start = week_start_for(anchor)
    wk_days = week_strip(anchor)

    prev_week = wk_start - timedelta(days=7)
    next_week = wk_start + timedelta(days=7)

    # Summary of everything (tasks/appts that are linked to days in that week)
    week_day_rows = (
        db.session.query(Day)
        .filter(Day.user_id == user.id, Day.day_date >= wk_start, Day.day_date <= (wk_start + timedelta(days=6)))
        .order_by(Day.day_date.asc())
        .all()
    )
    day_ids = [d.id for d in week_day_rows]

    week_tasks = []
    week_appts = []
    if day_ids:
        week_tasks = (
            db.session.query(Task)
            .filter(Task.user_id == user.id, Task.day_id.in_(day_ids))
            .order_by(Task.priority.asc(), Task.created_at.asc())
            .all()
        )
        week_appts = (
            db.session.query(Appointment)
            .filter(Appointment.day_id.in_(day_ids))
            .order_by(Appointment.start_time.asc())
            .all()
        )

    # Weekly initiatives/goals (your requested categories)
    categories = ["Family", "Work", "Main Street", "House", "Music", "Projects"]

    goals = (
        db.session.query(WeeklyGoal)
        .filter(WeeklyGoal.user_id == user.id, WeeklyGoal.week_start == wk_start)
        .order_by(WeeklyGoal.created_at.asc())
        .all()
    )

    goals_by_cat: dict[str, list[WeeklyGoal]] = {c: [] for c in categories}
    for g in goals:
        # If older data has a category not in our fixed list, still show it rather than losing it
        goals_by_cat.setdefault(g.category, []).append(g)

    return render_template(
        "week.html",
        user=user,
        week_start=wk_start,
        week_days=wk_days,
        prev_week=prev_week,
        next_week=next_week,
        week_tasks=week_tasks,
        week_appts=week_appts,
        week_str=wk_start.isoformat(),  # IMPORTANT: used by the add form

        goal_categories=categories,
        goals_by_cat=goals_by_cat,
    )


@bp.post("/week/<week_str>/goal/add")
def add_week_goal(week_str: str):
    user = get_or_create_default_user()

    if week_str == "current":
        anchor = date.today()
    else:
        anchor = datetime.strptime(week_str, "%Y-%m-%d").date()

    wk_start = week_start_for(anchor)

    category = (request.form.get("category") or "").strip()
    text = (request.form.get("text") or "").strip()

    if text and category:
        db.session.add(WeeklyGoal(user_id=user.id, week_start=wk_start, category=category, text=text))
        db.session.commit()

    return redirect(url_for("main.week_view", week_str=wk_start.isoformat()))


@bp.post("/week/goal/<int:goal_id>/delete")
def delete_week_goal(goal_id: int):
    goal = db.session.get(WeeklyGoal, goal_id)
    if not goal:
        return redirect(url_for("main.week_view", week_str="current"))

    wk = goal.week_start
    db.session.delete(goal)
    db.session.commit()
    return redirect(url_for("main.week_view", week_str=wk.isoformat()))


@bp.post("/week/goal/<int:goal_id>/push_next")
def push_week_goal_next(goal_id: int):
    goal = db.session.get(WeeklyGoal, goal_id)
    if not goal:
        return redirect(url_for("main.week_view", week_str="current"))

    old_week = goal.week_start
    goal.week_start = goal.week_start + timedelta(days=7)
    db.session.commit()

    return redirect(url_for("main.week_view", week_str=old_week.isoformat()))
