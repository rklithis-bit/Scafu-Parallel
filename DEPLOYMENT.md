# SCAFU — deployment and troubleshooting

SCAFU is a Flask chat app with Firebase Authentication, a community room, and a private room restricted server-side to `lichu@scafu.app` and `ammu@scafu.app`.

## Required services and configuration

### 1. Firebase project

In the Firebase console:

1. Create or select the project used by SCAFU.
2. Enable **Authentication → Sign-in method → Email/Password**.
3. In **Project settings → General**, copy the Web API key.
4. In **Project settings → Service accounts**, create a private key for the server. Keep this JSON private; never commit it or paste it into chat.
5. Register both private-chat accounts using the app's Create account screen. Each account must have a SCAFU profile created by signup; creating a Firebase user manually alone is not enough for this app's current SQLite profile flow.

### 2. Render environment variables

In the Render web service's **Environment** settings, configure:

| Key | Value |
| --- | --- |
| `FLASK_SECRET_KEY` | A long, random secret (or let the Blueprint generate one) |
| `FIREBASE_WEB_API_KEY` | Firebase project's Web API key |
| `FIREBASE_PROJECT_ID` | `project_id` from the service-account JSON |
| `FIREBASE_CLIENT_EMAIL` | `client_email` from the service-account JSON |
| `FIREBASE_PRIVATE_KEY` | Full `private_key` value, including BEGIN/END lines; preserve newlines or enter them as `\n` |
| `DATABASE_PATH` | Optional; for a persistent disk, use a path on that disk, e.g. `/var/data/scafu.db` |
| `UPLOAD_FOLDER` | Optional; for a persistent disk, use a path on that disk, e.g. `/var/data/uploads` |

Then deploy the latest `main` branch. Build command: `pip install -r requirements.txt`. Start command: `gunicorn app:app`.

**Persistence warning:** the app currently stores profiles, messages, and uploaded images in SQLite/local files. On a Render instance without a persistent disk, those files may be lost during redeploys/restarts. A persistent disk requires a Render plan that supports it; mount it at `/var/data` and set both paths above. For multiple instances or durable scaling, migrate the database and image storage to managed services.

## Login troubleshooting

1. Open the deployed URL and hard-refresh it.
2. Open Safari Web Inspector → Console.
3. Run:

```js
({
  formFound: !!document.querySelector("#auth-form"),
  buttonFound: !!document.querySelector("#submit"),
  buttonDisabled: document.querySelector("#submit")?.disabled,
  scriptLoaded: [...document.scripts].some(s => s.src.includes("auth.js"))
})
```

Expected values: `formFound: true`, `buttonFound: true`, `scriptLoaded: true`. If the click still does nothing, copy the returned object and the red console error.

If an error appears inside the page:
- **Authentication setup error**: check all four Firebase/Flask environment variables and the Render logs.
- **Email or password is incorrect**: confirm the account exists in the same Firebase project as `FIREBASE_WEB_API_KEY`.
- **Account profile not found**: this Firebase account has no matching row in the app's current SQLite database. Sign-up through SCAFU creates the profile; if the database was reset, persistence/profile recovery needs attention.
- **Could not reach SCAFU**: check Render service status and network access.

## Security notes

- Do not expose Firebase Admin private keys, passwords, or `FLASK_SECRET_KEY`.
- Private chat access is checked by the server; hiding the tab in the browser is not the security boundary.
- Image uploads are limited to PNG/JPG/GIF/WEBP and 10 MB.
- Rotate credentials immediately if a private key is accidentally shared or committed.
