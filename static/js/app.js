/* ===================================================================
   AI Job Application Assistant — Shared JavaScript
   =================================================================== */

// ---------- User ID Sync (localStorage ↔ Flask session) ----------
(async function syncUserId() {
    try {
        const storedId = localStorage.getItem('jobApp_user_id');
        if (storedId) {
            await fetch('/api/set_user_id', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: storedId })
            });
        } else {
            const resp = await fetch('/api/get_user_id');
            const data = await resp.json();
            if (data.user_id) {
                localStorage.setItem('jobApp_user_id', data.user_id);
            }
        }
    } catch (e) {
        console.warn('User ID sync failed:', e);
    }
})();

// ---------- Credential Helpers ----------
const Credentials = {
    save(email, password, service) {
        localStorage.setItem('jobApp_email', email);
        localStorage.setItem('jobApp_pass', password);
        localStorage.setItem('jobApp_service', service);
    },

    load() {
        return {
            email: localStorage.getItem('jobApp_email') || '',
            password: localStorage.getItem('jobApp_pass') || '',
            service: localStorage.getItem('jobApp_service') || 'gmail'
        };
    },

    clear() {
        localStorage.removeItem('jobApp_email');
        localStorage.removeItem('jobApp_pass');
        localStorage.removeItem('jobApp_service');
    },

    hasSaved() {
        return !!(localStorage.getItem('jobApp_email') && localStorage.getItem('jobApp_pass'));
    }
};

// ---------- Mobile Sidebar Toggle ----------
document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.getElementById('mobileToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('show');
        });

        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.remove('open');
                overlay.classList.remove('show');
            });
        }
    }

    // ---------- Fade-in Animations ----------
    const animatedEls = document.querySelectorAll('.animate-in');
    if ('IntersectionObserver' in window && animatedEls.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animationPlayState = 'running';
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        animatedEls.forEach(el => {
            el.style.animationPlayState = 'paused';
            observer.observe(el);
        });
    }

    // ---------- Upload Zone Drag & Drop ----------
    const uploadZones = document.querySelectorAll('.upload-zone');
    uploadZones.forEach(zone => {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });
        zone.addEventListener('drop', () => {
            zone.classList.remove('dragover');
        });
    });

    // ---------- Auto-dismiss flash alerts after 5s ----------
    const alerts = document.querySelectorAll('.alert-flash');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// ---------- Loading Overlay ----------
function showLoading(message) {
    const overlay = document.getElementById('loadingOverlay');
    const text = document.getElementById('loadingText');
    if (overlay) {
        if (text && message) text.textContent = message;
        overlay.classList.add('show');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.remove('show');
}

// ---------- Confirm Dialog ----------
function confirmAction(message) {
    return confirm(message);
}
