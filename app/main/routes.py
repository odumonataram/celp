"""
app/main/routes.py
Public-facing pages that don't require login: landing page, about, contact/feedback.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user

from app.extensions import db
from app.forms import FeedbackForm
from app.models import Feedback, Language, Word

main_bp = Blueprint("main", __name__, template_folder="../templates/main")


@main_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    languages = Language.query.filter_by(is_target_language=True).all()
    word_count = Word.query.count()
    return render_template("main/landing.html", languages=languages, word_count=word_count)


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/feedback", methods=["GET", "POST"])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        entry = Feedback(
            user_id=current_user.id if current_user.is_authenticated else None,
            subject=form.subject.data,
            message=form.message.data,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Thanks -- your feedback has been recorded.", "success")
        return redirect(url_for("main.feedback"))
    return render_template("main/feedback.html", form=form)
