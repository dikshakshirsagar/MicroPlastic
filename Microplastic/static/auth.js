// =====================================================================
//  Firebase Authentication — µPlastic Detection System
// =====================================================================
//
//  SETUP: Replace the firebaseConfig below with YOUR Firebase config.
//         See the Firebase Setup Guide in README for step-by-step help.
//
// =====================================================================

// ── Firebase Configuration ──────────────────────────────────────────
// ⚠️  REPLACE THIS with your own Firebase project config!
//     Go to: Firebase Console → Project Settings → Your App → Config
const firebaseConfig = {
    apiKey: "AIzaSyDYUVoylmwjNuBkTd9rG9mZV6EbDMrGPHs",
    authDomain: "microplastic-detection-307db.firebaseapp.com",
    projectId: "microplastic-detection-307db",
    storageBucket: "microplastic-detection-307db.firebasestorage.app",
    messagingSenderId: "471338762145",
    appId: "1:471338762145:web:7cca65ac1aa2e5987395e0",
    measurementId: "G-0RTEK873VM"
};

// ── Initialize Firebase ─────────────────────────────────────────────
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

// ── Tab Switching ───────────────────────────────────────────────────
function switchTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const loginTab = document.getElementById('loginTab');
    const signupTab = document.getElementById('signupTab');
    const indicator = document.getElementById('tabIndicator');
    const message = document.getElementById('authMessage');

    // Hide any messages
    message.classList.add('hidden');

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        loginTab.classList.add('active');
        signupTab.classList.remove('active');
        indicator.classList.remove('signup');
    } else {
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        loginTab.classList.remove('active');
        signupTab.classList.add('active');
        indicator.classList.add('signup');
    }
}

// ── Show Message ────────────────────────────────────────────────────
function showMessage(text, type = 'error') {
    const msgBox = document.getElementById('authMessage');
    const msgIcon = msgBox.querySelector('.msg-icon');
    const msgText = msgBox.querySelector('.msg-text');

    msgBox.className = 'auth-message ' + type;
    msgIcon.textContent = type === 'error' ? '⚠' : '✓';
    msgText.textContent = text;
    msgBox.classList.remove('hidden');

    // Auto-hide after 6 seconds
    setTimeout(() => {
        msgBox.classList.add('hidden');
    }, 6000);
}

// ── Set Button Loading State ────────────────────────────────────────
function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');

    btn.disabled = loading;
    if (loading) {
        text.style.opacity = '0.5';
        loader.classList.remove('hidden');
    } else {
        text.style.opacity = '1';
        loader.classList.add('hidden');
    }
}

// ── Toggle Password Visibility ──────────────────────────────────────
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
    } else {
        input.type = 'password';
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
    }
}

// ── Friendly Error Messages ─────────────────────────────────────────
function getErrorMessage(code) {
    const messages = {
        'auth/user-not-found': 'No account found with this email.',
        'auth/wrong-password': 'Incorrect password. Please try again.',
        'auth/invalid-credential': 'Invalid email or password.',
        'auth/email-already-in-use': 'This email is already registered. Try signing in.',
        'auth/weak-password': 'Password must be at least 6 characters.',
        'auth/invalid-email': 'Please enter a valid email address.',
        'auth/too-many-requests': 'Too many attempts. Please wait and try again.',
        'auth/network-request-failed': 'Network error. Check your internet connection.',
        'auth/popup-closed-by-user': 'Sign-in popup was closed. Try again.',
        'auth/api-key-not-valid.-please-pass-a-valid-api-key.': 'Firebase not configured yet. See setup guide in README.'
    };
    return messages[code] || 'Something went wrong. Please try again.';
}

// =====================================================================
//  AUTH HANDLERS
// =====================================================================

// ── Email/Password Login ────────────────────────────────────────────
async function handleLogin(e) {
    e.preventDefault();
    setLoading('loginBtn', true);

    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
        const result = await auth.signInWithEmailAndPassword(email, password);
        showMessage(`Welcome back, ${result.user.email}!`, 'success');

        // Store user info in sessionStorage
        sessionStorage.setItem('user', JSON.stringify({
            uid: result.user.uid,
            email: result.user.email,
            name: result.user.displayName || email.split('@')[0]
        }));

        // Redirect to dashboard after brief delay
        setTimeout(() => {
            window.location.href = '/';
        }, 800);

    } catch (error) {
        showMessage(getErrorMessage(error.code));
    } finally {
        setLoading('loginBtn', false);
    }
}

// ── Email/Password Signup ───────────────────────────────────────────
async function handleSignup(e) {
    e.preventDefault();
    setLoading('signupBtn', true);

    const name = document.getElementById('signupName').value.trim();
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value;
    const confirm = document.getElementById('signupConfirm').value;

    // Validate passwords match
    if (password !== confirm) {
        showMessage('Passwords do not match.');
        setLoading('signupBtn', false);
        return;
    }

    try {
        const result = await auth.createUserWithEmailAndPassword(email, password);

        // Update user profile with name
        await result.user.updateProfile({ displayName: name });

        showMessage(`Account created! Welcome, ${name}!`, 'success');

        // Store user info
        sessionStorage.setItem('user', JSON.stringify({
            uid: result.user.uid,
            email: result.user.email,
            name: name
        }));

        // Redirect to dashboard
        setTimeout(() => {
            window.location.href = '/';
        }, 1000);

    } catch (error) {
        console.error('Signup error:', error.code, error.message);
        showMessage(getErrorMessage(error.code));
    } finally {
        setLoading('signupBtn', false);
    }
}

// ── Google Sign-In ──────────────────────────────────────────────────
async function handleGoogleSignIn() {
    const provider = new firebase.auth.GoogleAuthProvider();

    try {
        const result = await auth.signInWithPopup(provider);
        showMessage(`Welcome, ${result.user.displayName}!`, 'success');

        sessionStorage.setItem('user', JSON.stringify({
            uid: result.user.uid,
            email: result.user.email,
            name: result.user.displayName
        }));

        setTimeout(() => {
            window.location.href = '/';
        }, 800);

    } catch (error) {
        showMessage(getErrorMessage(error.code));
    }
}

// ── Forgot Password ────────────────────────────────────────────────
async function handleForgotPassword(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();

    if (!email) {
        showMessage('Enter your email above, then click "Forgot password".');
        return;
    }

    try {
        await auth.sendPasswordResetEmail(email);
        showMessage(`Password reset email sent to ${email}`, 'success');
    } catch (error) {
        showMessage(getErrorMessage(error.code));
    }
}

// ── Auth State Observer ─────────────────────────────────────────────
// If user is already logged in, redirect straight to dashboard
auth.onAuthStateChanged((user) => {
    if (user) {
        sessionStorage.setItem('user', JSON.stringify({
            uid: user.uid,
            email: user.email,
            name: user.displayName || user.email.split('@')[0]
        }));
        // Only redirect if we're on the login page
        if (window.location.pathname === '/login') {
            window.location.href = '/';
        }
    }
});
