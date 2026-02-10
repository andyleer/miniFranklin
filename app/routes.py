@bp.post("/task/<int:task_id>/push_next")
def push_task_next(task_id: int):
    user = get_or_create_default_user()

    task = db.session.get(Task, task_id)
    if not task:
        flash("Task not found", "error")
        return redirect(url_for("main.day_view", day_str="today"))

    # Figure out what day this task currently belongs to
    current_day_date = date.today()
    if task.day_id:
        day = db.session.get(Day, task.day_id)
        if day:
            current_day_date = day.day_date

    # Move to next day
    next_day_date = current_day_date + timedelta(days=1)
    next_day = get_or_create_day(user.id, next_day_date)

    task.day_id = next_day.id
    db.session.commit()

    return redirect(url_for("main.day_view", day_str=current_day_date.isoformat()))
