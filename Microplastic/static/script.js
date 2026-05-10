// =====================================================================
//  Firebase Auth Guard — Protects the Dashboard
// =====================================================================
//  Uses the same config as auth.js. If user is not logged in,
//  they are redirected to /login.
// =====================================================================

const firebaseConfig = {
    apiKey: "AIzaSyDYUVoylmwjNuBkTd9rG9mZV6EbDMrGPHs",
    authDomain: "microplastic-detection-307db.firebaseapp.com",
    projectId: "microplastic-detection-307db",
    storageBucket: "microplastic-detection-307db.firebasestorage.app",
    messagingSenderId: "471338762145",
    appId: "1:471338762145:web:7cca65ac1aa2e5987395e0",
    measurementId: "G-0RTEK873VM"
};

// Initialize Firebase (only if not already initialized)
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}
const dashboardAuth = firebase.auth();

// ── Auth Guard ──────────────────────────────────────────────────────
dashboardAuth.onAuthStateChanged((user) => {
    if (!user) {
        window.location.href = '/login';
    } else {
        loadUserProfile(user);
    }
});

// ── Load User Profile into Sidebar ──────────────────────────────────
function loadUserProfile(user) {
    const name    = user.displayName || user.email.split('@')[0];
    const email   = user.email;
    const initial = name.charAt(0).toUpperCase();

    const nameEl   = document.getElementById('userName');
    const emailEl  = document.getElementById('userEmail');
    const avatarEl = document.getElementById('userAvatar');

    if (nameEl)   nameEl.textContent   = name;
    if (emailEl)  emailEl.textContent  = email;
    if (avatarEl) avatarEl.textContent = initial;
}

// ── Logout ──────────────────────────────────────────────────────────
function handleLogout() {
    dashboardAuth.signOut().then(() => {
        sessionStorage.clear();
        window.location.href = '/login';
    });
}

// ===== CONFIGURATION =====
const CONFIG = {
    API_BASE:         window.location.origin,
    POLL_INTERVAL:    3000,    // Poll sensor data every 3 seconds
    MAX_CHART_POINTS: 30,
    ALERT_THRESHOLD:  16,      // Matches "Contaminated" threshold
    CAMERA_URL:       ''
};

// ===== STATE =====
let previousParticles = null;
let previousSize      = null;
let historyData       = [];
let lastSensorTime    = null;   // Date object of last successful ESP32 read

// ===== CHART SETUP =====
const ctx = document.getElementById('particleChart').getContext('2d');

const gradient = ctx.createLinearGradient(0, 0, 0, 300);
gradient.addColorStop(0, 'rgba(59, 130, 246, 0.25)');
gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

const particleChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Particle Count',
            data: [],
            borderColor: '#3b82f6',
            backgroundColor: gradient,
            borderWidth: 2.5,
            pointBackgroundColor: '#3b82f6',
            pointBorderColor: '#1a1f35',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 7,
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#1a1f35',
                titleColor: '#e8eaf0',
                bodyColor: '#8892a8',
                borderColor: '#1e2a45',
                borderWidth: 1,
                cornerRadius: 10,
                padding: 12,
                displayColors: false,
                callbacks: {
                    title: (items) => '⏱ ' + items[0].label,
                    label: (item)  => 'Particles: ' + item.formattedValue
                }
            }
        },
        scales: {
            x: {
                grid:  { color: 'rgba(30, 42, 69, 0.5)', drawBorder: false },
                ticks: { color: '#5a6478', font: { size: 11, family: 'Inter' },
                         maxRotation: 0, maxTicksLimit: 8 }
            },
            y: {
                grid:  { color: 'rgba(30, 42, 69, 0.5)', drawBorder: false },
                ticks: { color: '#5a6478', font: { size: 11, family: 'Inter' }, padding: 8 },
                beginAtZero: true
            }
        }
    }
});

// =====================================================================
//  TASK 2 — Live ESP32 IR Sensor Polling
//  Polls GET /api/sensor-data every 3 seconds
// =====================================================================

// Quality → CSS class + description
const QUALITY_META = {
    'Good':         { cls: 'good',         desc: 'Water is safe for use',         color: '#10b981' },
    'Moderate':     { cls: 'moderate',     desc: 'Trace contamination detected',   color: '#f59e0b' },
    'Poor':         { cls: 'poor',         desc: 'Elevated contamination — caution', color: '#f97316' },
    'Contaminated': { cls: 'contaminated', desc: 'Unsafe — take action immediately', color: '#ef4444' },
    // Legacy labels from /data endpoint:
    'good':         { cls: 'good',         desc: 'Water is safe for use',          color: '#10b981' },
    'moderate':     { cls: 'moderate',     desc: 'Minor contamination detected',   color: '#f59e0b' },
    'contaminated': { cls: 'contaminated', desc: 'Unsafe — take action',           color: '#ef4444' },
};

async function fetchSensorData() {
    try {
        const res  = await fetch(`${CONFIG.API_BASE}/api/sensor-data`);
        if (!res.ok) throw new Error('Server error');
        const data = await res.json();

        // Only update if we have a timestamp (data has been received from ESP32)
        if (data.timestamp) {
            lastSensorTime = new Date(data.last_seen || Date.now());
            updateDashboardFromSensor(data);
        } else {
            // No ESP32 data yet — show connecting state
            setEsp32Status('connecting');
        }
    } catch (err) {
        console.warn('Sensor fetch failed:', err.message);
        setEsp32Status('offline');
    }
}

function updateDashboardFromSensor(data) {
    const now     = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });

    // ── Total Particles card ─────────────────────────────────────
    const particleEl = document.getElementById('particleCount');
    const count      = data.particle_count ?? 0;
    animateValue(particleEl, parseInt(particleEl.textContent) || 0, count, 500);
    updateTrend('particleTrend', count, previousParticles);
    previousParticles = count;

    // ── Water Quality card ───────────────────────────────────────
    const quality   = data.water_quality || 'Good';
    const qMeta     = QUALITY_META[quality] || QUALITY_META['Good'];
    const statusEl  = document.getElementById('waterStatus');
    const statusDesc = document.getElementById('statusDescription');
    statusEl.textContent = quality;
    statusEl.className   = 'stat-value status-text ' + qMeta.cls;
    statusDesc.textContent = qMeta.desc;

    // ── Detection Status card ────────────────────────────────────
    const state       = data.state || 'CLEAR';
    const detectionEl = document.getElementById('detectionStatus');
    const detectionInfo = document.getElementById('detectionInfo');
    const isPresent   = state === 'PARTICLE PRESENT';
    detectionEl.textContent  = isPresent ? 'Particle Present' : 'Clear';
    detectionEl.style.color  = isPresent ? '#f97316' : '#10b981';
    detectionInfo.textContent = `Last read: ${data.timestamp || '--'}`;

    // ── Last Updated (header) ────────────────────────────────────
    document.getElementById('lastUpdate').textContent = data.timestamp
        ? data.timestamp.split(' ')[1]   // show just the time portion
        : timeStr;

    // ── ESP32 online/offline indicator ───────────────────────────
    const ageMs = now - lastSensorTime;
    if (ageMs < 10000)       setEsp32Status('online');
    else if (ageMs < 30000)  setEsp32Status('connecting');
    else                     setEsp32Status('offline');

    // ── Chart update ─────────────────────────────────────────────
    particleChart.data.labels.push(timeStr);
    particleChart.data.datasets[0].data.push(count);
    if (particleChart.data.labels.length > CONFIG.MAX_CHART_POINTS) {
        particleChart.data.labels.shift();
        particleChart.data.datasets[0].data.shift();
    }
    particleChart.update('none');

    // ── History table ─────────────────────────────────────────────
    addHistoryRow(timeStr, { particles: count, size: 0, status: quality });

    // ── Alert check ───────────────────────────────────────────────
    checkAlert(count);

    // ── Flash cards ───────────────────────────────────────────────
    document.querySelectorAll('.stat-card').forEach(card => {
        card.classList.remove('flash');
        void card.offsetWidth;
        card.classList.add('flash');
    });
}

// ── ESP32 Online / Connecting / Offline indicator ─────────────────
function setEsp32Status(status) {
    const dot   = document.getElementById('connectionDot');
    const text  = document.getElementById('connectionText');
    const badge = document.getElementById('espStatusBadge');

    const STATE = {
        online:     { dotClass: 'status-dot connected',    label: 'ESP32 Online',  badgeClass: 'topbar-badge online' },
        connecting: { dotClass: 'status-dot connecting',   label: 'Connecting…',   badgeClass: 'topbar-badge connecting' },
        offline:    { dotClass: 'status-dot disconnected', label: 'Offline',        badgeClass: 'topbar-badge offline' },
    };

    const s = STATE[status] || STATE.offline;
    dot.className   = s.dotClass;
    text.textContent = s.label;
    badge.className  = s.badgeClass;
}

// ===== LEGACY: also poll /data for backward compatibility =====
async function fetchLegacyData() {
    try {
        const res  = await fetch(`${CONFIG.API_BASE}/data`);
        if (!res.ok) return;
        const data = await res.json();
        // Only use legacy data if sensor cache has no timestamp yet
        if (!lastSensorTime && data.particles !== undefined && data.timestamp) {
            const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
            const quality = data.status || 'Good';
            const qMeta   = QUALITY_META[quality.toLowerCase()] || QUALITY_META['good'];

            const particleEl = document.getElementById('particleCount');
            animateValue(particleEl, parseInt(particleEl.textContent) || 0, data.particles, 500);
            updateTrend('particleTrend', data.particles, previousParticles);
            previousParticles = data.particles;

            const statusEl   = document.getElementById('waterStatus');
            const statusDesc = document.getElementById('statusDescription');
            statusEl.textContent   = quality;
            statusEl.className     = 'stat-value status-text ' + qMeta.cls;
            statusDesc.textContent = qMeta.desc;

            document.getElementById('lastUpdate').textContent = timeStr;
            particleChart.data.labels.push(timeStr);
            particleChart.data.datasets[0].data.push(data.particles);
            if (particleChart.data.labels.length > CONFIG.MAX_CHART_POINTS) {
                particleChart.data.labels.shift();
                particleChart.data.datasets[0].data.shift();
            }
            particleChart.update('none');
            addHistoryRow(timeStr, data);
            checkAlert(data.particles);
        }
    } catch (_) { /* silent */ }
}

// ===== ANIMATE NUMBER =====
function animateValue(el, start, end, duration) {
    if (start === end) { el.textContent = end; return; }
    const range     = end - start;
    const startTime = performance.now();

    function step(currentTime) {
        const elapsed  = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased    = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + range * eased);
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ===== UPDATE TREND INDICATOR =====
function updateTrend(elementId, current, previous) {
    const el = document.getElementById(elementId);
    if (previous === null) {
        el.innerHTML = '<span class="trend-arrow trend-stable">—</span> First reading';
        return;
    }
    const diff = current - previous;
    if (diff > 0) {
        el.innerHTML = `<span class="trend-arrow trend-up">▲</span> +${diff} from last`;
    } else if (diff < 0) {
        el.innerHTML = `<span class="trend-arrow trend-down">▼</span> ${diff} from last`;
    } else {
        el.innerHTML = '<span class="trend-arrow trend-stable">●</span> Stable';
    }
}

// ===== HISTORY TABLE =====
function addHistoryRow(time, data) {
    const tbody = document.getElementById('historyBody');

    const emptyRow = tbody.querySelector('.empty-row');
    if (emptyRow) emptyRow.remove();

    const row = document.createElement('tr');

    const statusKey  = (data.status || 'good').toLowerCase();
    const badgeClass = `badge-${statusKey}`;
    const isAlert    = data.particles > CONFIG.ALERT_THRESHOLD;

    row.innerHTML = `
        <td>${time}</td>
        <td><strong>${data.particles}</strong></td>
        <td>${data.size !== undefined ? data.size + ' µm' : '—'}</td>
        <td><span class="badge ${badgeClass}">${data.status}</span></td>
        <td>${isAlert ? '<span class="badge badge-alert">⚠ ALERT</span>' : '<span class="badge badge-normal">Normal</span>'}</td>
    `;

    tbody.insertBefore(row, tbody.firstChild);

    while (tbody.children.length > 50) {
        tbody.removeChild(tbody.lastChild);
    }

    historyData.push(data);
    document.getElementById('recordCount').textContent = `${Math.min(historyData.length, 50)} records`;
}

// ===== ALERT SYSTEM =====
function checkAlert(particles) {
    const banner = document.getElementById('alertBanner');
    if (particles > CONFIG.ALERT_THRESHOLD) {
        banner.classList.remove('hidden');
    }
}

function dismissAlert() {
    document.getElementById('alertBanner').classList.add('hidden');
}

// ===== CAMERA =====
function connectCamera() {
    const urlInput = document.getElementById('cameraUrl');
    const url      = urlInput.value.trim();
    if (!url) return;

    CONFIG.CAMERA_URL = url;
    const feed = document.getElementById('cameraFeed');
    feed.src   = url;

    setTimeout(() => {
        if (feed.naturalWidth > 0 || feed.complete) {
            document.getElementById('cameraOverlay').classList.add('hidden');
        }
    }, 2000);
}

function handleCameraError() {
    document.getElementById('cameraOverlay').classList.remove('hidden');
    document.getElementById('liveBadge').style.display = 'none';
}

// ===== CLEAR CHART =====
function clearChart() {
    particleChart.data.labels = [];
    particleChart.data.datasets[0].data = [];
    particleChart.update();
}

// ===== MOBILE SIDEBAR TOGGLE =====
function toggleSidebar() {
    const sidebar  = document.getElementById('sidebar');
    const overlay  = document.getElementById('sidebarOverlay');
    const btn      = document.getElementById('mobileMenuBtn');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
    btn.classList.toggle('active');
}

// =====================================================================
//  POLLING LOOP
// =====================================================================
function startPolling() {
    fetchSensorData();          // primary: IR sensor via /api/sensor-data
    fetchLegacyData();          // fallback: legacy /data

    setInterval(fetchSensorData, CONFIG.POLL_INTERVAL);
    setInterval(fetchLegacyData, CONFIG.POLL_INTERVAL);
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    setEsp32Status('connecting');
    startPolling();
});
