"""
app/seed.py

Populates a fresh database with enough structure and sample content to
demo every wired-up feature end to end.

IMPORTANT -- READ BEFORE YOUR DEFENSE:
The Ijaw/Nembe/Epie/Ogbia entries below are placeholders, written as
"[<LANG>: <gloss>]" rather than real translations. I do not have a
verified, native-speaker-checked vocabulary list for these languages, and
inventing one would put incorrect "facts" into your dictionary -- exactly
the kind of error an external examiner from the CND department, or a
native speaker, would catch immediately and that would undermine the
credibility of the whole project.

Before your defense, replace every placeholder with vocabulary from your
own data collection (the word lists / interviews your Chapter 3 methodology
describes, ideally checked by your supervisor or a native-speaker
informant). The CSV import path is: edit this file's VOCAB list, or write a
short script that reads a spreadsheet of verified words into the Word
table using the same Concept-linking pattern shown here.
"""

from datetime import date, timedelta
import json

from app import create_app
from app.extensions import db
from app.models import (
    Language, Concept, Word, SentenceConcept, Sentence, GrammarTopic,
    Badge, User, UserSettings, Course, Quiz, QuizQuestion,
)

LANGUAGES = [
    {"code": "en", "name": "English", "is_target_language": False,
     "description": "The bridge language used to anchor every concept."},
    {"code": "ijw", "name": "Ijaw", "is_target_language": True,
     "description": "An Ijaw-cluster language taught in the CND course."},
    {"code": "nem", "name": "Nembe", "is_target_language": True,
     "description": "Nembe, spoken across several Bayelsa LGAs."},
    {"code": "epi", "name": "Epie", "is_target_language": True,
     "description": "Epie (Epie-Atissa), spoken in Yenagoa LGA."},
    {"code": "ogb", "name": "Ogbia", "is_target_language": True,
     "description": "Ogbia, spoken in Ogbia LGA, Bayelsa State."},
]

# Each tuple: (english_gloss, category, part_of_speech, [example_en, example_translation_placeholder])
VOCAB = [
    ("house", "general", "noun"),
    ("water", "general", "noun"),
    ("food", "general", "noun"),
    ("hello", "greetings", "interjection"),
    ("good morning", "greetings", "phrase"),
    ("thank you", "greetings", "phrase"),
    ("market", "market", "noun"),
    ("family", "family", "noun"),
    ("mother", "family", "noun"),
    ("father", "family", "noun"),
    ("school", "school", "noun"),
    ("teacher", "school", "noun"),
    ("river", "general", "noun"),
    ("fish", "food", "noun"),
    ("one", "numbers", "number"),
    ("two", "numbers", "number"),
    ("three", "numbers", "number"),
    ("to go", "verbs", "verb"),
    ("to eat", "verbs", "verb"),
    ("to greet", "verbs", "verb"),
]

GRAMMAR_TOPICS = [
    ("Pronouns", "Personal pronouns (I, you, he/she, we, they) and how they attach to verbs.", "beginner"),
    ("Greetings & Politeness", "Time-of-day greetings and respectful forms of address for elders.", "beginner"),
    ("Sentence Order", "Typical subject-verb-object patterns and how questions are formed.", "intermediate"),
    ("Tenses", "How past, present, and future actions are marked.", "intermediate"),
    ("Plural Forms", "How nouns are pluralised.", "intermediate"),
]

BADGES = [
    ("3-Day Streak", "Practised for 3 days in a row.", "3-day streak"),
    ("7-Day Streak", "Practised for 7 days in a row.", "7-day streak"),
    ("30-Day Streak", "Practised for 30 days in a row.", "30-day streak"),
    ("First Quiz", "Completed your first quiz.", "1 quiz attempt"),
    ("Vocabulary Builder", "Bookmarked 10 words.", "10 bookmarks"),
]


def run_seed():
    app = create_app("development")
    with app.app_context():
        db.create_all()

        if Language.query.count() > 0:
            print("Database already seeded -- skipping. Drop the DB first if you want a clean reseed.")
            return

        lang_objs = {}
        for lang in LANGUAGES:
            obj = Language(**lang)
            db.session.add(obj)
            lang_objs[lang["code"]] = obj
        db.session.flush()

        # Vocabulary: one Concept per gloss, one Word per language (English real,
        # others a clearly-marked placeholder -- see module docstring).
        for gloss, category, pos in VOCAB:
            concept = Concept(english_gloss=gloss, category=category)
            db.session.add(concept)
            db.session.flush()

            db.session.add(Word(
                concept_id=concept.id, language_id=lang_objs["en"].id, text=gloss,
                part_of_speech=pos, meaning=f"The English word for '{gloss}'.",
                example_sentence=f"This is an example sentence using '{gloss}'.",
                difficulty_level="beginner",
            ))
            for code in ("ijw", "nem", "epi", "ogb"):
                db.session.add(Word(
                    concept_id=concept.id, language_id=lang_objs[code].id,
                    text=f"[{code.upper()}: {gloss}]",
                    part_of_speech=pos,
                    meaning=f"PLACEHOLDER -- replace with the verified {lang_objs[code].name} translation of '{gloss}'.",
                    difficulty_level="beginner",
                ))

        # One demo sentence concept, same placeholder caveat applies.
        sent_concept = SentenceConcept(english_gloss="I will go to school tomorrow.", category="school")
        db.session.add(sent_concept)
        db.session.flush()
        db.session.add(Sentence(
            sentence_concept_id=sent_concept.id, language_id=lang_objs["en"].id,
            text="I will go to school tomorrow.",
            word_order_tokens=json.dumps(["I", "will", "go", "to", "school", "tomorrow"]),
            grammar_explanation="Subject (I) + future auxiliary (will) + verb (go) + prepositional phrase + time adverb.",
        ))
        for code in ("ijw", "nem", "epi", "ogb"):
            db.session.add(Sentence(
                sentence_concept_id=sent_concept.id, language_id=lang_objs[code].id,
                text=f"[{code.upper()}: I will go to school tomorrow.]",
                grammar_explanation="PLACEHOLDER -- replace with verified word order for this language.",
            ))

        for code in ("ijw", "nem", "epi", "ogb"):
            for title, content, level in GRAMMAR_TOPICS:
                db.session.add(GrammarTopic(
                    language_id=lang_objs[code].id, title=title,
                    content=f"PLACEHOLDER notes for '{title}' in {lang_objs[code].name}. {content}",
                    level=level,
                ))

        for name, desc, criteria in BADGES:
            db.session.add(Badge(name=name, description=desc, criteria_note=criteria))

        # Demo accounts -- change these passwords immediately if this ever
        # touches a real deployment.
        admin = User(full_name="Platform Admin", username="admin", email="admin@cnd.fuotuoke.edu.ng", role="admin")
        admin.set_password("ChangeMe123!")
        lecturer = User(full_name="Dr. Demo Lecturer", username="lecturer1", email="lecturer1@cnd.fuotuoke.edu.ng", role="lecturer")
        lecturer.set_password("ChangeMe123!")
        student = User(full_name="Demo Student", username="student1", email="student1@cnd.fuotuoke.edu.ng",
                        role="student", matric_number="CND/20/0001")
        student.set_password("ChangeMe123!")

        db.session.add_all([admin, lecturer, student])
        db.session.flush()
        for u in (admin, lecturer, student):
            db.session.add(UserSettings(user_id=u.id))

        # A demo course + a 5-question MCQ quiz so quiz.take_quiz is demoable.
        course = Course(title="CND 201: Introduction to Ijaw", description="Beginner Ijaw vocabulary and greetings.",
                         language_id=lang_objs["ijw"].id, lecturer_id=lecturer.id)
        db.session.add(course)
        db.session.flush()

        quiz = Quiz(course_id=course.id, language_id=lang_objs["ijw"].id, title="Greetings & Basics (MCQ)",
                    quiz_type="mcq", difficulty="beginner", time_limit_seconds=300)
        db.session.add(quiz)
        db.session.flush()

        sample_questions = [
            ("What is the Ijaw word for 'hello'?", "[IJW: hello]", ["[IJW: hello]", "[IJW: water]", "[IJW: house]", "[IJW: food]"]),
            ("What is the Ijaw word for 'water'?", "[IJW: water]", ["[IJW: hello]", "[IJW: water]", "[IJW: house]", "[IJW: food]"]),
            ("What is the Ijaw word for 'house'?", "[IJW: house]", ["[IJW: school]", "[IJW: house]", "[IJW: market]", "[IJW: family]"]),
            ("What is the Ijaw word for 'thank you'?", "[IJW: thank you]", ["[IJW: thank you]", "[IJW: mother]", "[IJW: river]", "[IJW: fish]"]),
            ("What is the Ijaw word for 'one'?", "[IJW: one]", ["[IJW: two]", "[IJW: three]", "[IJW: one]", "[IJW: father]"]),
        ]
        for idx, (prompt, answer, options) in enumerate(sample_questions):
            db.session.add(QuizQuestion(
                quiz_id=quiz.id, prompt=prompt, correct_answer=answer,
                options=json.dumps(options), order_index=idx,
            ))

        db.session.commit()
        print("Seed complete: 5 languages, %d vocabulary concepts, demo accounts (admin/lecturer1/student1, "
              "password ChangeMe123!), 1 course, 1 quiz." % len(VOCAB))


if __name__ == "__main__":
    run_seed()
