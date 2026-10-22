# SCAFU — deployment and troubleshooting

SCAFU is a Flask chat app with Firebase Authentication, a community room, and a private room restricted server-side to `lichu@scafu.app` and `ammu@scafu.app`.

## Connect the existing Firebase project

Use the existing Firebase project **`scafu-59f30`**. Do not create a replacement project or delete existing users/data.

1. Open [Firebase Console](https://console.firebase.google.com/) and select `scafu-59f30`.
2. Open **Authentication → Sign-in method** and enable **Email/Password**.
3. Open **Project settings → General → Your apps** and copy the Web API key.
4. Open **Project settings → Service accounts**. Use an existing service account or create a private key for the Firebase Admin SDK. Keep the JSON file private; never commit it or paste it into chat.
5. Confirm the existing user accounts are in this exact Firebase project.

## Render environment variables

Open the Render web service connected to this repository and go to **Environment**. Set:

| Key | Value |
| --- | --- |
| `FLASK_SECRET_KEY` | A long, random secret; do not publish it |
| `FIREBASE_WEB_API_KEY` | Web API key from project `scafu-59f30` |
| `FIREBASE_PROJECT_ID` | `scafu-59f30` |
| `FIREBASE_CLIENT_EMAIL` | `client_email` from the service-account JSON |
| `FIREBASE_PRIVATE_KEY` | Full `private_key` value, including BEGIN/END lines; preserve newlines or enter them as `\\n` |

The Render Blueprint sets `FIREBASE_PROJECT_ID=scafu-59f30`. The other Firebase credentials must be entered privately in Render. Save changes and deploy the latest `main` branch after merging the setup PR.

Build command: `pip install -r requirements.txt`. Start command: `gunicorn app:app`.

## Important: existing user profiles and data

Firebase Authentication accounts are separate from this app's local SQLite profile database. A user who exists in Firebase may still get **Account profile not found** if there is no matching profile in this new app's SQLite database. Signing up through the new app creates a profile, but an already-existing email may be rejected as already registered. Do not delete Firebase users to work around this; existing-profile linking/import needs to be handled safely if that error occurs.

The app currently stores profiles, messages, and uploaded images in SQLite/local files. On a Render instance without a persistent disk, these files may be lost during redeploys/restarts. If your Render plan supports it, mount a persistent disk at `/var/data` and set `DATABASE_PATH=/var/data/scafu.db` and `UPLOAD_FOLDER=/var/data/uploads`. For multi-instance or durable scaling, migrate to managed database and object storage.

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

- **Authentication setup error:** check the environment variables and Render logs.
- **Email or password is incorrect:** confirm the account exists in Firebase project `scafu-59f30`.
- **Account profile not found:** the Firebase account has no matching profile in the new app's SQLite database.
- **Could not reach SCAFU:** check Render service status and network access.

## Security notes

- Never expose Firebase Admin private keys, passwords, or `FLASK_SECRET_KEY`.
- Private chat access is checked by the server; hiding the tab in the browser is not the security boundary.
- Image uploads are limited to PNG/JPG/GIF/WEBP and 10 MB.
- Rotate credentials immediately if a private key is accidentally shared or committed.
