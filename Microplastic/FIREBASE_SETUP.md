# 🔥 Firebase Setup Guide — Step by Step

Follow these steps to connect Firebase authentication to your µPlastic Detection Dashboard.

---

## Step 1: Create a Firebase Project

1. Go to **[Firebase Console](https://console.firebase.google.com/)**
2. Click **"Create a project"** (or "Add project")
3. Enter project name: `Microplastic-Detection`
4. Disable Google Analytics (not needed) → Click **"Create Project"**
5. Wait for it to finish → Click **"Continue"**

---

## Step 2: Enable Authentication

1. In Firebase Console, click **"Authentication"** in the left sidebar
2. Click the **"Get started"** button
3. Go to **"Sign-in method"** tab
4. Enable **Email/Password**:
   - Click on "Email/Password"
   - Toggle the **first switch ON** (Enable)
   - Click **Save**
5. Enable **Google** (for Google Sign-In):
   - Click on "Google"
   - Toggle the switch **ON**
   - Select your **support email** from the dropdown
   - Click **Save**

---

## Step 3: Register a Web App

1. Go to ⚙ **Project Settings** (gear icon near "Project Overview")
2. Scroll down to **"Your apps"** section
3. Click the **Web icon** `</>` to add a web app
4. Enter app nickname: `microplastic-dashboard`
5. ❌ Do NOT check "Firebase Hosting"
6. Click **"Register app"**
7. You'll see a code block with your config — **copy it!**

It looks like this:
```javascript
const firebaseConfig = {
    apiKey: "AIzaSyB.....................",
    authDomain: "microplastic-detection.firebaseapp.com",
    projectId: "microplastic-detection",
    storageBucket: "microplastic-detection.appspot.com",
    messagingSenderId: "123456789",
    appId: "1:123456789:web:abcdef"
};
```

---

## Step 4: Paste Config in Your Code

You need to paste the config in **two files**:

### File 1: `static/auth.js` (line 14–19)

Open `static/auth.js` and replace the placeholder config:

```javascript
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",              // ← Replace
    authDomain: "YOUR_PROJECT_ID...",    // ← Replace
    projectId: "YOUR_PROJECT_ID",        // ← Replace
    storageBucket: "YOUR_PROJECT_ID...", // ← Replace
    messagingSenderId: "YOUR_SENDER_ID", // ← Replace
    appId: "YOUR_APP_ID"                 // ← Replace
};
```

### File 2: `static/script.js` (line 8–13)

Open `static/script.js` and replace the **same** placeholder config with your Firebase values.

> **Both files must have identical configs!**

---

## Step 5: Add Authorized Domain (Important!)

1. In Firebase Console → **Authentication** → **Settings** tab
2. Scroll to **"Authorized domains"**
3. Click **"Add domain"**
4. Add: `localhost`
5. If deploying, also add your domain (e.g., `your-site.com`)

---

## Step 6: Run and Test

```bash
cd C:\Users\HP\Desktop\Microplastic
python app.py
```

1. Open **http://localhost:5000** → You'll be redirected to **/login**
2. Click **"Sign Up"** → Create an account
3. After signup, you're redirected to the dashboard
4. Click the **logout button** (↗ icon) to sign out

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Firebase not configured" error | Make sure you pasted the config in BOTH `auth.js` AND `script.js` |
| Google Sign-In popup closes | Add `localhost` to Authorized Domains (Step 5) |
| "auth/api-key-not-valid" | Double-check the apiKey from Firebase Console |
| Login works but dashboard redirects back | Make sure config in `script.js` matches `auth.js` |
| Page shows blank | Open browser console (F12) to see error details |

---

## Summary of What Happens

```
User visits localhost:5000
    ↓
script.js checks Firebase auth state
    ↓
Not logged in? → Redirect to /login
    ↓
User signs up / logs in on login.html
    ↓
Firebase authenticates → Redirect to /
    ↓
Dashboard loads with user profile in sidebar
```
