"""
app/dictionary/routes.py

Implements Feature 2 (AI Dictionary), Feature 3 (Voice Pronunciation,
generation side), Feature 11 (Bookmarks), Feature 13 (Word of the Day), and
Feature 22 (Search Engine: instant search + autocomplete + trending words).
"""

import random
from datetime import date

from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app, abort
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Word, Language, Bookmark
from app.utils import find_best_word_matches, log_progress

dictionary_bp = Blueprint("dictionary", __name__, template_folder="../templates/dictionary")


@dictionary_bp.route("/")
def index():
    languages = Language.query.order_by(Language.name).all()
    trending = Word.query.order_by(Word.search_hits.desc()).limit(8).all()
    return render_template("dictionary/index.html", languages=languages, trending=trending)


@dictionary_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    lang_code = request.args.get("lang", "")
    language = Language.query.filter_by(code=lang_code).first() if lang_code else None

    results = []
    if query and language:
        results = find_best_word_matches(query, language.id, limit=15)
        for w in results:
            w.search_hits = (w.search_hits or 0) + 1
        db.session.commit()

    languages = Language.query.order_by(Language.name).all()
    return render_template(
        "dictionary/search_results.html",
        query=query, results=results, languages=languages, selected_lang=lang_code
    )


@dictionary_bp.route("/autocomplete")
def autocomplete():
    """Powers the instant-search dropdown. Returns up to 8 lightweight
    suggestions so the request stays fast even on a slow connection."""
    query = request.args.get("q", "").strip()
    lang_code = request.args.get("lang", "")
    language = Language.query.filter_by(code=lang_code).first() if lang_code else None
    if not query or not language or len(query) < 2:
        return jsonify([])

    matches = (
        Word.query.filter(Word.language_id == language.id)
        .filter(Word.text.ilike(f"{query}%"))
        .order_by(Word.search_hits.desc())
        .limit(8)
        .all()
    )
    return jsonify([{"id": w.id, "text": w.text, "meaning": w.meaning} for w in matches])


@dictionary_bp.route("/word/<int:word_id>")
def word_detail(word_id):
    word = Word.query.get_or_404(word_id)

    is_bookmarked = False
    if current_user.is_authenticated:
        is_bookmarked = Bookmark.query.filter_by(user_id=current_user.id, word_id=word.id).first() is not None

    # Other languages' realisation of the same concept, for quick cross-reference.
    sibling_words = (
        Word.query.filter(Word.concept_id == word.concept_id, Word.id != word.id).all()
    )

    return render_template(
        "dictionary/word_detail.html", word=word, is_bookmarked=is_bookmarked, sibling_words=sibling_words
    )


@dictionary_bp.route("/word-of-the-day")
def word_of_the_day():
    lang_code = request.args.get("lang", "ijw")
    language = Language.query.filter_by(code=lang_code).first()
    if not language:
        abort(404)

    count = Word.query.filter_by(language_id=language.id).count()
    if count == 0:
        return render_template("dictionary/word_of_the_day.html", word=None, language=language)

    # Deterministic by date so every visitor sees the same word today, and it
    # changes automatically tomorrow without a scheduled job.
    seed = int(date.today().strftime("%Y%m%d"))
    rng = random.Random(seed + language.id)
    offset = rng.randrange(count)
    word = Word.query.filter_by(language_id=language.id).offset(offset).first()

    return render_template("dictionary/word_of_the_day.html", word=word, language=language)


@dictionary_bp.route("/bookmark/<int:word_id>", methods=["POST"])
@login_required
def toggle_bookmark(word_id):
    word = Word.query.get_or_404(word_id)
    existing = Bookmark.query.filter_by(user_id=current_user.id, word_id=word.id).first()
    if existing:
        db.session.delete(existing)
        bookmarked = False
    else:
        db.session.add(Bookmark(user_id=current_user.id, word_id=word.id))
        bookmarked = True
    db.session.commit()
    return jsonify({"bookmarked": bookmarked})


@dictionary_bp.route("/bookmarks")
@login_required
def bookmarks():
    items = Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.created_at.desc()).all()
    return render_template("dictionary/bookmarks.html", items=items)


@dictionary_bp.route("/audio/<int:word_id>")
def audio(word_id):
    """Serves pronunciation audio for a word. Pre-recorded native-speaker
    clips (AudioRecording rows) are preferred; gTTS is only a fallback and
    only meaningful for English since it has no Ijaw/Nembe/Epie/Ogbia voice
    model -- see app/utils.py for the full rationale."""
    word = Word.query.get_or_404(word_id)
    recording = word.audio_files.first()
    if recording and recording.file_path:
        directory, filename = recording.file_path.rsplit("/", 1)
        return send_from_directory(
            current_app.config["AUDIO_UPLOAD_FOLDER"], filename
        )

    if word.language.code == "en":
        from app.utils import generate_tts_audio
        relative_path = generate_tts_audio(word.text, "en")
        filename = relative_path.split("/", 1)[1]
        return send_from_directory(current_app.config["AUDIO_UPLOAD_FOLDER"], filename)

    return jsonify({"error": "No audio recording available for this word yet."}), 404
