# E-Commerce Web Application

A role-based e-commerce web application built with Flask and MySQL. This repository contains the application, helper scripts, and documentation for local development and seeding demo data.

## Quick Status — Recent changes
- Added seed and initialization scripts: `init_db.py`, `add_demo_users.py`, `add_more_products.py`, `add_sample_blogs.py`, `seed_reviews.py`, `init_search_history.py`.
- Project packaged as a Flask application under `flask_app/` with modular routes and extensions.
- Added tests: `test_login.py`, `test_roles.py`, `test_shop.py`, `TEST_SEARCH_FEATURE.py`.
- Added documentation for GST pricing integration: `GST_PRICING_CODE_REFERENCE.md`, `GST_PRICING_MODULE_UPGRADE.md`.

## What this repo includes
- Application entry: `app.py`
- Flask package: `flask_app/` (routes, models, templates, static assets)
- Seed & helper scripts in project root for populating demo data
- Virtual environment folder: `env/` (local, optional — may be excluded from commits)
- Tests at the repository root

## Setup (Local - Windows)
1. (Optional) Create a virtual environment and activate it:

	PowerShell:
	```powershell
	python -m venv env
	.\env\Scripts\Activate.ps1
	```

	Bash (Git Bash / WSL):
	```bash
	python -m venv env
	source "env/Scripts/activate"
	```

2. Install dependencies:

	```bash
	pip install -r requirements.txt
	```

3. Configure environment variables (example):

	- `FLASK_APP=app.py`
	- `FLASK_ENV=development`
	- Database connection settings (see `flask_app/config.py`)

4. Initialize database and seed demo data (examples):

	```bash
	python init_db.py
	python add_demo_users.py
	python add_more_products.py
	python seed_reviews.py
	python init_search_history.py
	```

5. Run the app:

	```bash
	python app.py
	# or
	flask run
	```

## Running tests

Run the test suite with `pytest`:

```bash
pip install -r requirements.txt
pytest -q
```

## Project structure (high level)

```
app.py
flask_app/               # application package (routes, models, extensions)
templates/               # Jinja2 templates
static/                  # CSS, JS, images
*.py                     # seed and helper scripts
env/                     # local virtualenv (optional)
tests/ or root tests     # pytest tests like test_login.py
```

## Notes / Links
- See [GST_PRICING_CODE_REFERENCE.md](GST_PRICING_CODE_REFERENCE.md) and [GST_PRICING_MODULE_UPGRADE.md](GST_PRICING_MODULE_UPGRADE.md) for pricing-related docs.
- Database and secret configuration live in `flask_app/config.py` and `flask_app/extensions.py`.
- If you need a clean start, drop the database, run `python init_db.py`, then run the seed scripts.

## Contributing
- Add feature branches, include tests, and open pull requests against `main`.

## Next steps I can help with
- Update README further for CI, Docker, or GitHub Actions.
- Create a CONTRIBUTING.md or a small dev script to automate seeding and testing.

