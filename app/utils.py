"""
app/utils.py

Cross-cutting helpers used by more than one blueprint. Kept separate from
models.py (data shape) and routes (request/response handling) so business
logic like "how do we score a fuzzy match" has one home and one set of tests.
"""

import os
import re
from difflib import SequenceMatcher

from app.extensions import db
from app.models import Word, Language, Badge, UserBadge, ProgressLog
from datetime import date


def normalize_text(text):
    """Lowercase + strip punctuation so 'House?' and 'house' match."""
    return re.sub(r"[^\w\s]", "", text.strip().lower())


def fuzzy_ratio(a, b):
    """Similarity ratio between 0 and 1. Used instead of an exact-match-only
    lookup so common misspellings (e.g. 'hous') still surface a result,
    per the 'fuzzy search to handle misspellings' requirement."""
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def find_best_word_matches(query_text, language_id, limit=5, min_ratio=0.6):
    """Returns the best-matching Word rows for free-text input in a given
    language, ranked by similarity. Falls back to substring search first
    (cheap, exact) before scoring fuzzy matches (more expensive) so a typical
    correctly-spelled lookup never pays the fuzzy-matching cost."""
    normalized_query = normalize_text(query_text)
    if not normalized_query:
        return []

    exact_or_substring = (
        Word.query.filter(Word.language_id == language_id)
        .filter(Word.text.ilike(f"%{query_text.strip()}%"))
        .limit(limit)
        .all()
    )
    if exact_or_substring:
        return exact_or_substring

    candidates = Word.query.filter(Word.language_id == language_id).all()
    scored = [(w, fuzzy_ratio(query_text, w.text)) for w in candidates]
    scored = [pair for pair in scored if pair[1] >= min_ratio]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [w for w, _ in scored[:limit]]


def translation_confidence_score(source_word, target_word):
    """A simple, explainable confidence heuristic for the Translator UI:
    1.0 when the words share a concept_id (a verified dictionary entry),
    degrading for fuzzy/community-sourced matches. Kept transparent rather
    than a black box, since this is shown directly to students."""
    if source_word and target_word and source_word.concept_id == target_word.concept_id:
        return 1.0
    if source_word and target_word:
        return round(fuzzy_ratio(source_word.text, target_word.text), 2)
    return 0.0


def award_xp(user, amount, reason=""):
    """Central place XP is granted, so future features (new quiz types,
    streak bonuses) don't each reinvent leveling logic."""
    user.xp_points = (user.xp_points or 0) + amount
    db.session.add(user)


def check_and_award_streak_badges(user):
    """Award streak-based badges. Idempotent: re-checks rather than assuming
    this is only ever called once per threshold crossing."""
    thresholds = {3: "3-Day Streak", 7: "7-Day Streak", 30: "30-Day Streak"}
    for days, badge_name in thresholds.items():
        if user.current_streak >= days:
            badge = Badge.query.filter_by(name=badge_name).first()
            if badge and not UserBadge.query.filter_by(user_id=user.id, badge_id=badge.id).first():
                db.session.add(UserBadge(user_id=user.id, badge_id=badge.id))


def log_progress(user, words_learned=0, quiz_score=None, practice_minutes=0, translations_made=0):
    """Upserts today's ProgressLog row for the dashboard charts."""
    today_log = ProgressLog.query.filter_by(user_id=user.id, log_date=date.today()).first()
    if not today_log:
        today_log = ProgressLog(user_id=user.id, log_date=date.today())
        db.session.add(today_log)

    today_log.words_learned += words_learned
    today_log.practice_minutes += practice_minutes
    today_log.translations_made += translations_made
    if quiz_score is not None:
        if today_log.quiz_score_avg:
            today_log.quiz_score_avg = (today_log.quiz_score_avg + quiz_score) / 2
        else:
            today_log.quiz_score_avg = quiz_score


def generate_tts_audio(text, language_code, voice_gender="female", speed="normal"):
    """Generates a pronunciation MP3 via gTTS and returns the static-relative
    path to it, caching by content hash so the same word/voice/speed
    combination is never synthesised twice.

    NOTE: gTTS calls Google's public endpoint and requires outbound internet
    access at runtime (it will simply fail offline). For Ijaw/Nembe/Epie/Ogbia,
    gTTS has no native voice model, so this should be treated as a fallback;
    the primary pronunciation path for indigenous languages is pre-recorded
    native-speaker audio (AudioRecording.file_path) or the browser's Web
    Speech API on the client side for English.
    """
    import hashlib
    from flask import current_app
    from gtts import gTTS

    cache_key = hashlib.md5(f"{text}-{language_code}-{voice_gender}-{speed}".encode()).hexdigest()
    filename = f"{cache_key}.mp3"
    folder = current_app.config["AUDIO_UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)

    if not os.path.exists(full_path):
        slow = speed == "slow"
        tts = gTTS(text=text, lang=language_code if language_code == "en" else "en", slow=slow)
        tts.save(full_path)

    return f"audio/{filename}"
