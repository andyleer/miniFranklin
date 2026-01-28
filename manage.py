from app import create_app
from app.db import db
from app.models import User, Day, Appointment, Task, Note

app = create_app()

# Flask CLI will discover this app, plus you can import db/models for shell work.
