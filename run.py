"""
run.py
Local development entry point. Production deployments should use gunicorn
(e.g. `gunicorn 'run:app'`) instead of the Flask dev server started here.
"""

import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(debug=True)
