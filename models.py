from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# =========================
# USERS
# =========================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="student")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship(
        "UserCourse",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    lessons = db.relationship(
        "UserLesson",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# =========================
# COURSES
# =========================

class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lessons = db.relationship(
        "Lesson",
        back_populates="course",
        cascade="all, delete-orphan"
    )

    enrollments = db.relationship(
        "UserCourse",
        back_populates="course",
        cascade="all, delete-orphan"
    )


# =========================
# LESSONS
# =========================

class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id"),
        nullable=False
    )

    title = db.Column(db.String(255))
    content = db.Column(db.Text)

    course = db.relationship(
        "Course",
        back_populates="lessons"
    )


# =========================
# USER COURSES
# =========================

class UserCourse(db.Model):
    __tablename__ = "user_courses"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id"),
        nullable=False
    )

    progress = db.Column(db.Float, default=0)

    user = db.relationship(
        "User",
        back_populates="courses"
    )

    course = db.relationship(
        "Course",
        back_populates="enrollments"
    )


# =========================
# USER LESSONS
# =========================

class UserLesson(db.Model):
    __tablename__ = "user_lessons"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    lesson_id = db.Column(
        db.Integer,
        db.ForeignKey("lessons.id")
    )

    completed = db.Column(db.Boolean, default=False)

    user = db.relationship(
        "User",
        back_populates="lessons"
    )


# =========================
# ASSIGNMENTS
# =========================

class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id")
    )

    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)


# =========================
# USER ASSIGNMENTS
# =========================

class UserAssignment(db.Model):
    __tablename__ = "user_assignments"

    id = db.Column(db.Integer, primary_key=True)

    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignments.id")
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    submission = db.Column(db.Text)
    score = db.Column(db.Float)


# =========================
# MESSAGES
# =========================

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    message = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================
# NOTIFICATIONS
# =========================

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    title = db.Column(db.String(255))
    message = db.Column(db.Text)

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================
# CERTIFICATES
# =========================

class Certificate(db.Model):
    __tablename__ = "certificates"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id")
    )

    certificate_code = db.Column(
        db.String(255),
        unique=True
    )

    issued_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================
# ACHIEVEMENTS
# =========================

class Achievement(db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(255))
    description = db.Column(db.Text)


class UserAchievement(db.Model):
    __tablename__ = "user_achievements"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    achievement_id = db.Column(
        db.Integer,
        db.ForeignKey("achievements.id")
    )

    earned_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================
# QUIZ QUESTIONS
# =========================

class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id")
    )

    question = db.Column(db.Text)

    option_a = db.Column(db.String(255))
    option_b = db.Column(db.String(255))
    option_c = db.Column(db.String(255))
    option_d = db.Column(db.String(255))

    correct_answer = db.Column(
        db.String(10)
    )


# =========================
# SCHEDULE EVENTS
# =========================

class ScheduleEvent(db.Model):
    __tablename__ = "schedule_events"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    title = db.Column(db.String(255))
    description = db.Column(db.Text)

    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)


# =========================
# STREAK LOGS
# =========================

class StreakLog(db.Model):
    __tablename__ = "streak_logs"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    streak_date = db.Column(db.Date)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================
# PASSWORD RESET TOKENS
# =========================

class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    token = db.Column(
        db.String(255),
        unique=True
    )

    expires_at = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )