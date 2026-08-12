# CND Multilingual Translation & Learning Platform

A Flask-based web platform for the Communication in Niger Delta (CND) course
at Federal University Otuoke, supporting English, Ijaw, Nembe, Epie, and
Ogbia.

## ⚠️ Before you do anything else

1. **The Ijaw/Nembe/Epie/Ogbia vocabulary in `app/seed.py` is placeholder
   data** (e.g. `[IJW: house]`), not real translations. I (the AI assisting
   with this build) do not have a verified vocabulary list for these
   languages, and inventing one would put incorrect linguistic claims into
   your project. Replace every placeholder with words from your own data
   collection before you demo or defend this. The seed file's docstring
   explains exactly where to make the change.
2. **Change the demo passwords.** `admin` / `lecturer1` / `student1` all use
   `ChangeMe123!`. Fine for local development, not fine anywhere public.
3. **gTTS (text-to-speech) needs internet access at runtime.** It calls
   Google's public endpoint, so it'll fail offline. It's also English-only --
   it has no voice model for the four indigenous languages. For those,
   either upload pre-recorded native-speaker audio (`AudioRecording.file_path`)
   or rely on typed/visual learning until recordings exist.

## What's fully working right now

- **Authentication** -- registration (student/lecturer roles), login,
  logout, password hashing, streak tracking on login.
- **Translator** -- type a word/phrase, get ranked suggestions across
  languages with a transparent confidence score, fuzzy-match fallback for
  misspellings, and word-by-word fallback (clearly flagged as lower
  confidence) for unmatched multi-word input. Logs history for signed-in users.
- **Dictionary** -- full entries (meaning, IPA, part of speech, examples,
  synonyms/antonyms, grammar/usage notes), instant-search autocomplete,
  trending words, Word of the Day (deterministic per day), bookmarking.
- **Pronunciation** -- browser Web Speech API for English (no server round
  trip); server-side audio endpoint ready for pre-recorded indigenous-language
  clips, with a gTTS fallback for English.
- **Quiz engine** -- multiple-choice quizzes fully working end to end: take,
  score, XP award, streak/badge checks, leaderboard, history. The schema
  already supports nine other quiz types (fill-blank, match, arrange,
  listening, voice, typing, image, timed, adaptive) -- see "What's scaffolded"
  below.
- **Dashboard** -- Chart.js graphs of 7-day word/practice activity, XP,
  streak, badge count, recent quizzes/translations.
- **Admin panel** -- platform stats, user activate/deactivate, add dictionary
  words through a form (auto-links to existing concepts across languages).
- **Lecturer panel** -- create courses, add lessons, view enrolled students.
- **Dark mode / large font / colour-blind mode** toggle, responsive Bootstrap
  5 layout, custom design system (not default Bootstrap blue).
- **Database** -- 24-table schema covering every feature in the brief,
  including ones not yet wired into the UI (so the next build stage is
  templating against an already-correct data model, not a redesign).

## What's designed in the database but not yet built into the UI

This is the honest gap between the full 25-feature brief and what's
demoable today. Each of these has its tables already in `app/models.py`:

- The other 9 quiz types beyond MCQ (schema supports them; renderer doesn't yet)
- Gamification UI polish: badge gallery, coin spending, levels
- Sentence Construction drag-and-drop game (Sentence.word_order_tokens exists)
- Speech recognition input (would need a JS Web Speech API recognition wrapper)
- Conversation practice / chatbot-style dialogue
- Flashcard review UI (data model: Word + Bookmark cover this)
- Phrase library browsing by category (Concept.category already supports it)
- Culture/maps module, image-based learning
- Offline support (service worker / PWA)
- Export features (PDF/Word progress reports -- reportlab/python-docx are
  already in requirements.txt for this)
- UML/ER diagrams for your write-up (can be generated from `app/models.py`
  on request)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

export FLASK_APP=run.py           # Windows: set FLASK_APP=run.py
flask db init
flask db migrate -m "initial schema"
flask db upgrade
flask seed-db                     # populates languages, placeholder vocab, demo accounts

flask run
```

Then visit `http://127.0.0.1:5000`.

## Project structure

```
celp/
├── app/
│   ├── auth/            # registration, login, logout
│   ├── main/             # landing, about, feedback
│   ├── translator/       # translation engine
│   ├── dictionary/       # dictionary, search, bookmarks, audio
│   ├── quiz/              # quiz engine
│   ├── dashboard/        # student dashboard + charts
│   ├── admin/             # admin panel
│   ├── lecturer/          # lecturer panel
│   ├── static/            # css/js/audio/img
│   ├── templates/         # one folder per blueprint
│   ├── models.py          # full database schema
│   ├── forms.py           # WTForms
│   ├── utils.py           # fuzzy matching, TTS, gamification helpers
│   └── seed.py            # demo data (PLACEHOLDER translations -- read warning above)
├── config.py
├── requirements.txt
└── run.py
```
