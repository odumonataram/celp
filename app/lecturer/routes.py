"""
app/lecturer/routes.py

Feature 19 (Lecturer Dashboard), Stage 1 scope: create/manage courses and
lessons, and see which students are enrolled with their basic stats. Quiz
authoring, announcements, and CSV export of reports are scaffolded in the
Course model already (it already supports quizzes via the relationship) and
are next in the build queue -- see project README.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app.extensions import db
from app.models import Course, Lesson, Language, Enrollment, User

lecturer_bp = Blueprint("lecturer", __name__, template_folder="../templates/lecturer")


@lecturer_bp.before_request
def restrict_to_lecturers():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.path))
    if not (current_user.is_lecturer() or current_user.is_admin()):
        abort(403)


@lecturer_bp.route("/")
def index():
    courses = Course.query.filter_by(lecturer_id=current_user.id).all()
    return render_template("lecturer/index.html", courses=courses)


@lecturer_bp.route("/courses/new", methods=["GET", "POST"])
def new_course():
    languages = Language.query.order_by(Language.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("A course title is required.", "danger")
            return render_template("lecturer/course_form.html", languages=languages)

        course = Course(
            title=title,
            description=request.form.get("description"),
            language_id=request.form.get("language_id", type=int),
            lecturer_id=current_user.id,
        )
        db.session.add(course)
        db.session.commit()
        flash("Course created.", "success")
        return redirect(url_for("lecturer.course_detail", course_id=course.id))

    return render_template("lecturer/course_form.html", languages=languages)


@lecturer_bp.route("/courses/<int:course_id>")
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    if course.lecturer_id != current_user.id and not current_user.is_admin():
        abort(403)
    lessons = course.lessons.order_by(Lesson.order_index).all()
    enrolled_students = (
        User.query.join(Enrollment, Enrollment.student_id == User.id)
        .filter(Enrollment.course_id == course.id)
        .all()
    )
    return render_template(
        "lecturer/course_detail.html", course=course, lessons=lessons, students=enrolled_students
    )


@lecturer_bp.route("/courses/<int:course_id>/lessons/new", methods=["GET", "POST"])
def new_lesson(course_id):
    course = Course.query.get_or_404(course_id)
    if course.lecturer_id != current_user.id and not current_user.is_admin():
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("A lesson title is required.", "danger")
            return render_template("lecturer/lesson_form.html", course=course)

        lesson = Lesson(
            course_id=course.id,
            title=title,
            content=request.form.get("content"),
            order_index=course.lessons.count(),
        )
        db.session.add(lesson)
        db.session.commit()
        flash("Lesson added.", "success")
        return redirect(url_for("lecturer.course_detail", course_id=course.id))

    return render_template("lecturer/lesson_form.html", course=course)
