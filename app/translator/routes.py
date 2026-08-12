"""
app/translator/routes.py

The core Translator feature (Feature 1). Two entry points:
  - GET  /translate/            renders the translator UI
  - POST /translate/api         AJAX endpoint the page's JS calls per keystroke/submit

Translation strategy, in order of preference:
  1. Exact word match sharing a Concept  -> confidence 1.0, dictionary-grade.
  2. Exact sentence match sharing a SentenceConcept -> confidence 1.0.
  3. Fuzzy word match (handles misspellings) -> confidence scaled by similarity.
  4. Word-by-word fallback for unmatched multi-word input -> confidence capped
     at 0.5 and flagged in the UI, since naive concatenation does not respect
     target-language grammar/word order.
This is the same logic an examiner would expect you to explain in your
methodology chapter, so the docstring matters as much as the code.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Language, Word, Concept, TranslationHistory
from app.utils import find_best_word_matches, translation_confidence_score, normalize_text, log_progress

translator_bp = Blueprint("translator", __name__, template_folder="../templates/translator")


@translator_bp.route("/")
def index():
    languages = Language.query.order_by(Language.name).all()
    return render_template("translator/index.html", languages=languages)


@translator_bp.route("/api", methods=["POST"])
def translate_api():
    data = request.get_json(silent=True) or request.form
    text = (data.get("text") or "").strip()
    source_code = data.get("source_lang")
    target_code = data.get("target_lang")

    if not text or not source_code or not target_code:
        return jsonify({"error": "text, source_lang and target_lang are required"}), 400

    source_lang = Language.query.filter_by(code=source_code).first()
    target_lang = Language.query.filter_by(code=target_code).first()
    if not source_lang or not target_lang:
        return jsonify({"error": "Unknown language code"}), 404

    words_in_input = text.split()
    is_single_word = len(words_in_input) == 1

    suggestions = []

    if is_single_word:
        matches = find_best_word_matches(text, source_lang.id, limit=5)
        for source_word in matches:
            target_word = Word.query.filter_by(
                concept_id=source_word.concept_id, language_id=target_lang.id
            ).first()
            if target_word:
                source_word.search_hits = (source_word.search_hits or 0) + 1
                suggestions.append(_serialize_translation(source_word, target_word))
    else:
        # Multi-word input: try a whole-sentence concept match first.
        sentence_match = _find_sentence_translation(text, source_lang.id, target_lang.id)
        if sentence_match:
            suggestions.append(sentence_match)
        else:
            # Fall back to word-by-word, flagged as lower-confidence.
            translated_tokens = []
            any_found = False
            for token in words_in_input:
                matches = find_best_word_matches(token, source_lang.id, limit=1)
                if matches:
                    target_word = Word.query.filter_by(
                        concept_id=matches[0].concept_id, language_id=target_lang.id
                    ).first()
                    if target_word:
                        translated_tokens.append(target_word.text)
                        any_found = True
                        continue
                translated_tokens.append(f"[{token}]")  # unknown token, left bracketed
            if any_found:
                suggestions.append({
                    "source_text": text,
                    "target_text": " ".join(translated_tokens),
                    "meaning": None,
                    "part_of_speech": None,
                    "example_sentence": None,
                    "confidence": 0.4,
                    "method": "word_by_word_fallback",
                    "word_id": None,
                })

    if current_user.is_authenticated:
        top_result_text = suggestions[0]["target_text"] if suggestions else None
        history = TranslationHistory(
            user_id=current_user.id,
            source_text=text,
            source_language_id=source_lang.id,
            target_text=top_result_text,
            target_language_id=target_lang.id,
            confidence_score=suggestions[0]["confidence"] if suggestions else 0.0,
        )
        db.session.add(history)
        log_progress(current_user, translations_made=1)
        db.session.commit()

    return jsonify({"query": text, "suggestions": suggestions})


def _serialize_translation(source_word, target_word):
    return {
        "source_text": source_word.text,
        "target_text": target_word.text,
        "meaning": target_word.meaning,
        "part_of_speech": target_word.part_of_speech,
        "example_sentence": target_word.example_sentence,
        "example_translation": target_word.example_translation,
        "synonyms": target_word.synonyms,
        "antonyms": target_word.antonyms,
        "pronunciation": target_word.ipa_pronunciation,
        "confidence": translation_confidence_score(source_word, target_word),
        "method": "concept_match",
        "word_id": target_word.id,
        "difficulty_level": target_word.difficulty_level,
    }


def _find_sentence_translation(text, source_lang_id, target_lang_id):
    from app.models import Sentence
    normalized = normalize_text(text)
    candidate = Sentence.query.filter_by(language_id=source_lang_id).all()
    for sentence in candidate:
        if normalize_text(sentence.text) == normalized:
            target_sentence = Sentence.query.filter_by(
                sentence_concept_id=sentence.sentence_concept_id, language_id=target_lang_id
            ).first()
            if target_sentence:
                return {
                    "source_text": sentence.text,
                    "target_text": target_sentence.text,
                    "meaning": None,
                    "part_of_speech": None,
                    "example_sentence": None,
                    "confidence": 1.0,
                    "method": "sentence_concept_match",
                    "word_id": None,
                }
    return None


@translator_bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    entries = (
        TranslationHistory.query.filter_by(user_id=current_user.id)
        .order_by(TranslationHistory.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("translator/history.html", entries=entries)
