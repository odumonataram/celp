"""
app/models.py

Database schema for the platform. Design notes:

- A `Concept` is one "idea" (e.g. the idea of HOUSE). Each `Word` is how a
  specific Language realises that concept. This is what lets the Translator
  go English -> Ijaw -> Nembe -> Epie -> Ogbia from a single table instead of
  needing a separate translation row for every language pair (5 languages
  would otherwise mean 20 directional pairs to maintain by hand).
- The same pattern is used for `SentenceConcept` -> `Sentence`.
- Dictionary-style fields (meaning, example, synonyms, grammar notes, etc.)
  live directly on `Word` since they are always language-specific.
"""

from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


# ---------------------------------------------------------------------------
# Users & roles
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # student | lecturer | admin
    role = db.Column(db.String(20), nullable=False, default="student")
    matric_number = db.Column(db.String(30), unique=True, nullable=True)  # students only
    department = db.Column(db.String(120), default="CND")

    # Gamification counters live on the user for fast lookups (leaderboards etc.)
    xp_points = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_activity_date = db.Column(db.Date, nullable=True)

    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bookmarks = db.relationship("Bookmark", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    history_entries = db.relationship("TranslationHistory", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    quiz_attempts = db.relationship("QuizAttempt", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    badges = db.relationship("UserBadge", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    progress_logs = db.relationship("ProgressLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    settings = db.relationship("UserSettings", backref="user", uselist=False, cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", backref="student", lazy="dynamic", cascade="all, delete-orphan")
    practice_sessions = db.relationship("PracticeSession", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self):
        return self.role == "admin"

    def is_lecturer(self):
        return self.role == "lecturer"

    def record_activity_for_streak(self):
        """Call once per day a user does something learning-related.
        Increments the streak if they were active yesterday, resets if a day
        was missed, and is a no-op if already logged today."""
        today = date.today()
        if self.last_activity_date == today:
            return
        if self.last_activity_date is not None and (today - self.last_activity_date).days == 1:
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.last_activity_date = today

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False)
    large_fonts = db.Column(db.Boolean, default=False)
    color_blind_mode = db.Column(db.Boolean, default=False)
    daily_reminder_enabled = db.Column(db.Boolean, default=True)
    daily_reminder_time = db.Column(db.Time, nullable=True)
    preferred_voice_gender = db.Column(db.String(10), default="female")  # male | female
    preferred_speech_speed = db.Column(db.String(10), default="normal")  # slow | normal


# ---------------------------------------------------------------------------
# Languages, the core dictionary, sentences, grammar
# ---------------------------------------------------------------------------

class Language(db.Model):
    __tablename__ = "languages"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)   # en, ijw, nem, epi, ogb
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_target_language = db.Column(db.Boolean, default=True)  # False for English (the bridge language)

    words = db.relationship("Word", backref="language", lazy="dynamic", cascade="all, delete-orphan")
    sentences = db.relationship("Sentence", backref="language", lazy="dynamic", cascade="all, delete-orphan")
    grammar_topics = db.relationship("GrammarTopic", backref="language", lazy="dynamic", cascade="all, delete-orphan")


class Concept(db.Model):
    """One language-independent idea, anchored by an English gloss
    (e.g. 'house', 'to greet someone'). Every Word that is a translation of
    the same idea points back to the same Concept."""
    __tablename__ = "concepts"

    id = db.Column(db.Integer, primary_key=True)
    english_gloss = db.Column(db.String(150), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=True)  # greetings, travel, market, family, etc. (Phrase Library)
    image_path = db.Column(db.String(255), nullable=True)

    words = db.relationship("Word", backref="concept", lazy="dynamic", cascade="all, delete-orphan")


class Word(db.Model):
    """A single language's realisation of a Concept, with full dictionary
    metadata. This one model backs Feature 1 (Translator) and Feature 2
    (AI Dictionary) -- a translation lookup is just 'find Words sharing this
    concept_id', and a dictionary lookup is just 'show me this Word's fields'."""
    __tablename__ = "words"

    id = db.Column(db.Integer, primary_key=True)
    concept_id = db.Column(db.Integer, db.ForeignKey("concepts.id"), nullable=False)
    language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)

    text = db.Column(db.String(150), nullable=False, index=True)
    ipa_pronunciation = db.Column(db.String(150), nullable=True)
    part_of_speech = db.Column(db.String(30), nullable=True)
    meaning = db.Column(db.Text, nullable=True)
    example_sentence = db.Column(db.Text, nullable=True)
    example_translation = db.Column(db.Text, nullable=True)
    origin_note = db.Column(db.Text, nullable=True)
    usage_note = db.Column(db.Text, nullable=True)
    grammar_note = db.Column(db.Text, nullable=True)
    common_mistake_note = db.Column(db.Text, nullable=True)
    synonyms = db.Column(db.String(255), nullable=True)   # comma-separated for simplicity
    antonyms = db.Column(db.String(255), nullable=True)
    difficulty_level = db.Column(db.String(15), default="beginner")  # beginner|intermediate|advanced
    image_path = db.Column(db.String(255), nullable=True)
    search_hits = db.Column(db.Integer, default=0)  # powers "trending/popular words"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    audio_files = db.relationship("AudioRecording", backref="word", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("concept_id", "language_id", name="uq_concept_language"),)

    def __repr__(self):
        return f"<Word {self.text} [{self.language.code if self.language else '?'}]>"


class AudioRecording(db.Model):
    """Metadata for a pronunciation clip. file_path is null when audio is
    meant to be generated on-demand (gTTS) rather than pre-recorded."""
    __tablename__ = "audio_recordings"

    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey("words.id"), nullable=False)
    voice_gender = db.Column(db.String(10), default="female")
    speed = db.Column(db.String(10), default="normal")  # slow | normal
    file_path = db.Column(db.String(255), nullable=True)


class SentenceConcept(db.Model):
    __tablename__ = "sentence_concepts"

    id = db.Column(db.Integer, primary_key=True)
    english_gloss = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=True)

    sentences = db.relationship("Sentence", backref="concept", lazy="dynamic", cascade="all, delete-orphan")


class Sentence(db.Model):
    __tablename__ = "sentences"

    id = db.Column(db.Integer, primary_key=True)
    sentence_concept_id = db.Column(db.Integer, db.ForeignKey("sentence_concepts.id"), nullable=False)
    language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    word_order_tokens = db.Column(db.Text, nullable=True)  # JSON list, used by Sentence Construction game
    grammar_explanation = db.Column(db.Text, nullable=True)


class GrammarTopic(db.Model):
    __tablename__ = "grammar_topics"

    id = db.Column(db.Integer, primary_key=True)
    language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)   # Pronouns, Verbs, Tenses, ...
    content = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(15), default="beginner")
    order_index = db.Column(db.Integer, default=0)


# ---------------------------------------------------------------------------
# Courses & lessons (lecturer-managed structure students enrol in)
# ---------------------------------------------------------------------------

class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lessons = db.relationship("Lesson", backref="course", lazy="dynamic", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", backref="course", lazy="dynamic", cascade="all, delete-orphan")
    quizzes = db.relationship("Quiz", backref="course", lazy="dynamic")


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=True)
    attachment_path = db.Column(db.String(255), nullable=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("student_id", "course_id", name="uq_student_course"),)


# ---------------------------------------------------------------------------
# Quiz engine
# ---------------------------------------------------------------------------

class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    quiz_type = db.Column(db.String(30), default="mcq")  # mcq|fill_blank|match|arrange|listening|typing|image
    difficulty = db.Column(db.String(15), default="beginner")
    time_limit_seconds = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("QuizQuestion", backref="quiz", lazy="dynamic", cascade="all, delete-orphan")
    attempts = db.relationship("QuizAttempt", backref="quiz", lazy="dynamic", cascade="all, delete-orphan")


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=True)  # JSON-encoded list for MCQ
    related_word_id = db.Column(db.Integer, db.ForeignKey("words.id"), nullable=True)
    order_index = db.Column(db.Integer, default=0)


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    score = db.Column(db.Float, default=0.0)
    total_questions = db.Column(db.Integer, default=0)
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    responses = db.relationship("QuizResponse", backref="attempt", lazy="dynamic", cascade="all, delete-orphan")


class QuizResponse(db.Model):
    __tablename__ = "quiz_responses"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("quiz_questions.id"), nullable=False)
    given_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# Gamification
# ---------------------------------------------------------------------------

class Badge(db.Model):
    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_path = db.Column(db.String(255), nullable=True)
    criteria_note = db.Column(db.String(255), nullable=True)  # human-readable, e.g. "7-day streak"

    awarded_to = db.relationship("UserBadge", backref="badge", lazy="dynamic")


class UserBadge(db.Model):
    __tablename__ = "user_badges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), nullable=False)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),)


# ---------------------------------------------------------------------------
# Practice, bookmarks, history, progress
# ---------------------------------------------------------------------------

class PracticeSession(db.Model):
    """One sentence-construction or speaking-practice attempt."""
    __tablename__ = "practice_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sentence_id = db.Column(db.Integer, db.ForeignKey("sentences.id"), nullable=True)
    session_type = db.Column(db.String(30), default="sentence_construction")
    is_correct = db.Column(db.Boolean, default=False)
    submitted_answer = db.Column(db.Text, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Bookmark(db.Model):
    __tablename__ = "bookmarks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey("words.id"), nullable=True)
    sentence_id = db.Column(db.Integer, db.ForeignKey("sentences.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    word = db.relationship("Word")
    sentence = db.relationship("Sentence")


class TranslationHistory(db.Model):
    __tablename__ = "translation_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    source_text = db.Column(db.String(500), nullable=False)
    source_language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    target_text = db.Column(db.String(500), nullable=True)
    target_language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    confidence_score = db.Column(db.Float, default=1.0)
    is_favourite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    source_language = db.relationship("Language", foreign_keys=[source_language_id])
    target_language = db.relationship("Language", foreign_keys=[target_language_id])


class ProgressLog(db.Model):
    """One row per user/day, aggregated. Powers the dashboard charts/heatmap
    without expensive recomputation from raw event tables."""
    __tablename__ = "progress_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    log_date = db.Column(db.Date, default=date.today)
    words_learned = db.Column(db.Integer, default=0)
    quiz_score_avg = db.Column(db.Float, default=0.0)
    practice_minutes = db.Column(db.Integer, default=0)
    translations_made = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint("user_id", "log_date", name="uq_user_date"),)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    subject = db.Column(db.String(150), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
