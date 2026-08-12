"""
app/quiz/routes.py

Feature 8 (Quiz Engine), implemented fully for the MCQ quiz type as the
reference implementation. Other quiz_type values (fill_blank, match,
arrange, listening, voice, typing, image, timed, adaptive) share the same
Quiz/QuizQuestion/QuizAttempt/QuizResponse schema -- extending the engine to
render each one is templating work on top of an already-correct data model,
which is the planned Stage 2 increment (see project README).
"""

import json
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Quiz, QuizQuestion, QuizAttempt, QuizResponse, User, Language
from app.utils import award_xp, log_progress, check_and_award_streak_badges

quiz_bp = Blueprint("quiz", __name__, template_folder="../templates/quiz")


@quiz_bp.route("/")
@login_required
def index():
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    return render_template("quiz/index.html", quizzes=quizzes)


@quiz_bp.route("/<int:quiz_id>/take", methods=["GET", "POST"])
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions.order_by(QuizQuestion.order_index).all()
    if not questions:
        flash("This quiz has no questions yet.", "warning")
        return redirect(url_for("quiz.index"))

    if request.method == "POST":
        attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz.id,
            total_questions=len(questions),
            started_at=datetime.utcnow(),
        )
        db.session.add(attempt)
        db.session.flush()

        correct_count = 0
        for question in questions:
            given = request.form.get(f"question_{question.id}", "").strip()
            is_correct = given.lower() == question.correct_answer.strip().lower()
            if is_correct:
                correct_count += 1
            db.session.add(
                QuizResponse(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    given_answer=given,
                    is_correct=is_correct,
                )
            )

        score_percent = round((correct_count / len(questions)) * 100, 1)
        attempt.score = score_percent
        attempt.completed_at = datetime.utcnow()

        xp_earned = correct_count * 10
        award_xp(current_user, xp_earned, reason=f"Quiz {quiz.id}")
        current_user.record_activity_for_streak()
        check_and_award_streak_badges(current_user)
        log_progress(current_user, quiz_score=score_percent)

        db.session.commit()

        return render_template(
            "quiz/result.html", quiz=quiz, attempt=attempt, correct_count=correct_count,
            total=len(questions), xp_earned=xp_earned
        )

    # GET: render the quiz form. MCQ options are stored as a JSON list.
    for q in questions:
        q.option_list = json.loads(q.options) if q.options else []

    return render_template("quiz/take.html", quiz=quiz, questions=questions)


@quiz_bp.route("/leaderboard")
@login_required
def leaderboard():
    top_users = User.query.order_by(User.xp_points.desc()).limit(20).all()
    return render_template("quiz/leaderboard.html", top_users=top_users)


@quiz_bp.route("/history")
@login_required
def history():
    attempts = (
        QuizAttempt.query.filter_by(user_id=current_user.id)
        .order_by(QuizAttempt.started_at.desc())
        .all()
    )
    return render_template("quiz/history.html", attempts=attempts)
