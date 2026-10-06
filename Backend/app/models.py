from datetime import datetime
from .extensions import db

from datetime import datetime
from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("exams.id"),
        nullable=False,
        index=True
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False, default=1)
    order_index = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "title": self.title,
            "description": self.description,
            "points": self.points,
            "order_index": self.order_index,
            "created_at": self.created_at.isoformat(),
        }


class Attempt(db.Model):
    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("exams.id"),
        nullable=False,
        index=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="running"
    )

    started_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    finished_at = db.Column(
        db.DateTime,
        nullable=True
    )

    score = db.Column(
        db.Integer,
        nullable=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "exam_id": self.exam_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "score": self.score,
        }


class TaskResult(db.Model):
    __tablename__ = "task_results"

    id = db.Column(db.Integer, primary_key=True)

    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("attempts.id"),
        nullable=False,
        index=True
    )

    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id"),
        nullable=False,
        index=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    score = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    evaluated_at = db.Column(
        db.DateTime,
        nullable=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "attempt_id": self.attempt_id,
            "task_id": self.task_id,
            "status": self.status,
            "score": self.score,
            "evaluated_at": (
                self.evaluated_at.isoformat()
                if self.evaluated_at
                else None
            ),
        }


class Lab(db.Model):
    __tablename__ = "labs"

    id = db.Column(db.Integer, primary_key=True)

    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("attempts.id"),
        nullable=False,
        unique=True,
        index=True
    )

    provider = db.Column(
        db.String(50),
        nullable=False,
        default="proxmox"
    )

    node = db.Column(
        db.String(100),
        nullable=True
    )

    task_upid = db.Column(
        db.String(255),
        nullable=True
    )

    vm_id = db.Column(
        db.Integer,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="creating"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    destroyed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "attempt_id": self.attempt_id,
            "provider": self.provider,
            "node": self.node,
            "vm_id": self.vm_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "destroyed_at": (
                self.destroyed_at.isoformat()
                if self.destroyed_at
                else None
            ),
        }