# SCAFU — fresh rebuild

Minimal, Apple-inspired private one-to-one chat app using Flask, Firebase Authentication, SQLite and image uploads.

## Features
- Firebase email/password registration and sign-in
- Unique username profiles
- Private one-to-one messages between registered users
- PNG, JPG, GIF and WEBP image sharing (10 MB max)
- Session logout
- Responsive minimal interface

## Important architecture notes
- Firebase Authentication handles passwords; this app does not store passwords in SQLite.
- SQLite and uploaded files are stored at `DATABASE_PATH` and `UPLOAD_FOLDER`.
- On Render, attach a persistent disk at `/var/data` (or update the paths) if you need messages and uploaded images to survive restarts/redeploys. A disk is not available on every plan.
- This is a basic private chat app, not end-to-end encrypted. Use trusted recipients and do not send highly sensitive material.
- The first account can register, then the second person registers using a different email and username. Users appear in each other's contact list.
- Set Firebase Authentication > Sign-in method > Email/Password to enabled.
- For a fresh Firebase setup, create a Firebase project and service account; keep the service-account private key only in Render environment variables.

## Local run
1. Install Python 3.11+.
2. `python -m venv .venv`
3. macOS/Linux: `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. Set environment variables (see below), then `python app.py`.

Required environment:
- `FLASK_SECRET_KEY`: long random secret
- `FIREBASE_WEB_API_KEY`: Firebase project's Web API key
- `FIREBASE_PROJECT_ID`: Firebase project ID
- `FIREBASE_CLIENT_EMAIL`: service account email
- `FIREBASE_PRIVATE_KEY`: service account private key; preserve line breaks or store `\n` sequences

## Deploy to Render
1. Push this project to a new GitHub repository.
2. In Render, create a new **Web Service** connected to the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add the four required environment variables above.
6. If using a persistent disk, mount it at `/var/data`, and set:
   - `DATABASE_PATH=/var/data/scafu.db`
   - `UPLOAD_FOLDER=/var/data/uploads`
7. Deploy, then test registration with two accounts.

`render.yaml` is included as a Blueprint starting point. If you use it, review the disk settings and add the secrets in the Render dashboard.

## Firebase setup
1. Create a new Firebase project.
2. Open Authentication > Get started > Sign-in method and enable Email/Password.
3. Open Project settings > General and copy the Web API key into `FIREBASE_WEB_API_KEY`.
4. Open Project settings > Service accounts > Generate new private key. From that JSON file, copy `project_id`, `client_email`, and `private_key` into the corresponding Render environment variables. Never commit that JSON file to GitHub.
5. Make sure the service account belongs to the same Firebase project as the Web API key.
