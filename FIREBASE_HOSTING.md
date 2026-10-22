# Firebase Hosting deployment (existing project)

This setup keeps the Flask app and its server-side routes together on Cloud Run, then routes the Firebase Hosting URL to that backend. It uses the existing Firebase project `scafu-59f30`; it does not create a new project.

## Important before deploying

- Cloud Run may require a billing account and charges can apply. Review Google Cloud pricing and enable billing only if you agree.
- This is a hosting configuration, not a completed deployment. It does not grant this repository access to your Google account or create cloud resources automatically.
- SQLite and uploaded files are stored on the container filesystem by the current app. Cloud Run's local filesystem is ephemeral. **Do not treat this as production-ready for persistent chats or uploads** until storage is migrated to a durable database and object storage, or a suitable persistent storage design is added.
- The existing Render service is not changed by this configuration.

## 1. Install and authenticate

Install the Firebase CLI and Google Cloud CLI on your Mac, then run:

```sh
firebase login
gcloud auth login
gcloud config set project scafu-59f30
```

Ensure project `scafu-59f30` is selected in Firebase Console and Google Cloud Console.

## 2. Configure backend secrets

In Google Cloud Console → Cloud Run, configure the service environment variables. Use the same Firebase project:

- `FLASK_SECRET_KEY`: long random secret
- `FIREBASE_WEB_API_KEY`: Web API key from Firebase project `scafu-59f30`
- `FIREBASE_PROJECT_ID`: `scafu-59f30`
- `FIREBASE_CLIENT_EMAIL`: `client_email` from a service-account JSON for this project
- `FIREBASE_PRIVATE_KEY`: full `private_key` value; keep it secret

Prefer Google Secret Manager for the private key and Flask secret. Do not commit secrets to Git or paste them into chat.

## 3. Deploy the Flask backend

From the repository root, after merging these configuration files:

```sh
gcloud run deploy scafu \
  --source . \
  --region asia-south1 \
  --project scafu-59f30 \
  --allow-unauthenticated
```

If the service is created by this command before its environment variables are configured, add the variables through Cloud Run → service `scafu` → Edit & deploy new revision. The app needs all five variables above to start correctly.

## 4. Deploy Firebase Hosting

From the repository root:

```sh
firebase use scafu-59f30
firebase deploy --only hosting
```

The Hosting rewrite in `firebase.json` routes requests to the Cloud Run service named `scafu` in `asia-south1`. Deploy the Cloud Run service first. Firebase Hosting should then serve the app on the existing project's Hosting domain (typically `https://scafu-59f30.web.app`).

## 5. Test carefully

1. Open the Hosting URL and check that the login page loads.
2. Test sign-in and signup with a test account.
3. Test community chat, private-chat access control, and image upload.
4. Inspect Cloud Run logs if the app returns an error.

Do not delete or disable the Render service until Cloud Run, Firebase Hosting, authentication, and storage have all been verified.
