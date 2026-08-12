"""
app/dashboard/routes.py

Feature 10 (Progress Dashboard) and the home screen a logged-in user lands
on. Chart data is returned as plain JSON-serialisable lists so the template
can hand it straight to Chart.js without a templating dance.
"""

from datetime import date, timedelta

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.models import ProgressLog, QuizAttempt, TranslationHistory, UserBadge

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    if current_user.is_admin():
        return redirect(url_for("admin.index"))
    if current_user.is_lecturer():
        return redirect(url_for("lecturer.index"))

    today = date.today()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    logs_by_date = {
        log.log_date: log
        for log in ProgressLog.query.filter(
            ProgressLog.user_id == current_user.id, ProgressLog.log_date >= last_7_days[0]
        ).all()
    }

    chart_labels = [d.strftime("%a") for d in last_7_days]
    words_learned_series = [logs_by_date.get(d).words_learned if logs_by_date.get(d) else 0 for d in last_7_days]
    practice_minutes_series = [logs_by_date.get(d).practice_minutes if logs_by_date.get(d) else 0 for d in last_7_days]

    recent_quiz_attempts = (
        QuizAttempt.query.filter_by(user_id=current_user.id)
        .order_by(QuizAttempt.started_at.desc())
        .limit(5)
        .all()
    )
    recent_translations = (
        TranslationHistory.query.filter_by(user_id=current_user.id)
        .order_by(TranslationHistory.created_at.desc())
        .limit(5)
        .all()
    )
    badge_count = UserBadge.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "dashboard/index.html",
        chart_labels=chart_labels,
        words_learned_series=words_learned_series,
        practice_minutes_series=practice_minutes_series,
        recent_quiz_attempts=recent_quiz_attempts,
        recent_translations=recent_translations,
        badge_count=badge_count,
    )
