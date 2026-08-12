"""
app/admin/routes.py

Feature 18 (Admin Panel). This stage implements the parts an examiner can
actually click through end-to-end: platform-wide stats, user management
(activate/deactivate, role view), and adding dictionary content (the data
entry workflow every other feature depends on). Bulk CSV import, backups,
and full analytics export are listed in the project README as the Stage 2
admin increment so the gap between "designed" and "built" stays honest.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app.extensions import db
from app.models import User, Word, Concept, Language, Course, Quiz, QuizAttempt

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.before_request
def restrict_to_admins():
    """Every route in this blueprint is admin-only. A single before_request
    guard here is simpler to audit than decorating each view individually --
    there is no route in this blueprint that should ever skip this check."""
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.path))
    if not current_user.is_admin():
        abort(403)


@admin_bp.route("/")
def index():
    stats = {
        "users": User.query.count(),
        "students": User.query.filter_by(role="student").count(),
        "lecturers": User.query.filter_by(role="lecturer").count(),
        "words": Word.query.count(),
        "courses": Course.query.count(),
        "quizzes": Quiz.query.count(),
        "quiz_attempts": QuizAttempt.query.count(),
    }
    return render_template("admin/index.html", stats=stats)


@admin_bp.route("/users")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You can't deactivate your own account.", "warning")
        return redirect(url_for("admin.users"))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    flash(f"{user.username} is now {'active' if user.is_active_account else 'deactivated'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/words")
def words():
    all_words = Word.query.order_by(Word.created_at.desc()).limit(100).all()
    return render_template("admin/words.html", words=all_words)


@admin_bp.route("/words/new", methods=["GET", "POST"])
def new_word():
    languages = Language.query.order_by(Language.name).all()

    if request.method == "POST":
        english_gloss = request.form.get("english_gloss", "").strip()
        language_id = request.form.get("language_id", type=int)
        text = request.form.get("text", "").strip()

        if not english_gloss or not language_id or not text:
            flash("English gloss, language, and word text are required.", "danger")
            return render_template("admin/word_form.html", languages=languages)

        concept = Concept.query.filter_by(english_gloss=english_gloss).first()
        if not concept:
            concept = Concept(english_gloss=english_gloss, category=request.form.get("category") or None)
            db.session.add(concept)
            db.session.flush()

        word = Word(
            concept_id=concept.id,
            language_id=language_id,
            text=text,
            ipa_pronunciation=request.form.get("ipa_pronunciation") or None,
            part_of_speech=request.form.get("part_of_speech") or None,
            meaning=request.form.get("meaning") or None,
            example_sentence=request.form.get("example_sentence") or None,
            example_translation=request.form.get("example_translation") or None,
            origin_note=request.form.get("origin_note") or None,
            usage_note=request.form.get("usage_note") or None,
            grammar_note=request.form.get("grammar_note") or None,
            common_mistake_note=request.form.get("common_mistake_note") or None,
            synonyms=request.form.get("synonyms") or None,
            antonyms=request.form.get("antonyms") or None,
            difficulty_level=request.form.get("difficulty_level", "beginner"),
        )
        db.session.add(word)
        db.session.commit()
        flash(f"Added '{text}' to the dictionary.", "success")
        return redirect(url_for("admin.words"))

    return render_template("admin/word_form.html", languages=languages)
