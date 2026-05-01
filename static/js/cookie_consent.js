(function () {
    var CONSENT_KEY = 'vasu_cookie_consent_v1';

    function safeParse(value) {
        try {
            return JSON.parse(value);
        } catch (error) {
            return null;
        }
    }

    function getStoredConsent() {
        var raw = localStorage.getItem(CONSENT_KEY);
        if (!raw) {
            return null;
        }
        var parsed = safeParse(raw);
        if (!parsed || typeof parsed !== 'object') {
            return null;
        }
        return {
            necessary: true,
            analytics: !!parsed.analytics,
            marketing: !!parsed.marketing,
            updatedAt: parsed.updatedAt || null,
            method: parsed.method || 'custom',
        };
    }

    function setStoredConsent(consent) {
        localStorage.setItem(CONSENT_KEY, JSON.stringify(consent));
        applyConsentFlags(consent);
    }

    function applyConsentFlags(consent) {
        document.documentElement.dataset.cookieAnalytics = consent.analytics ? 'granted' : 'denied';
        document.documentElement.dataset.cookieMarketing = consent.marketing ? 'granted' : 'denied';
    }

    function showElement(element) {
        if (element) {
            element.hidden = false;
        }
    }

    function hideElement(element) {
        if (element) {
            element.hidden = true;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var banner = document.getElementById('cookie-consent-banner');
        var modal = document.getElementById('cookie-preferences-modal');
        var analyticsInput = document.getElementById('cookie-analytics-input');
        var marketingInput = document.getElementById('cookie-marketing-input');
        var acceptBtn = document.getElementById('cookie-accept-btn');
        var rejectBtn = document.getElementById('cookie-reject-btn');
        var manageBtn = document.getElementById('cookie-manage-btn');
        var cancelBtn = document.getElementById('cookie-cancel-btn');
        var saveBtn = document.getElementById('cookie-save-btn');

        if (!banner || !modal) {
            return;
        }

        var existingConsent = getStoredConsent();
        if (existingConsent) {
            applyConsentFlags(existingConsent);
        } else {
            showElement(banner);
        }

        function openManageModal() {
            var current = getStoredConsent() || { analytics: false, marketing: false };
            if (analyticsInput) {
                analyticsInput.checked = !!current.analytics;
            }
            if (marketingInput) {
                marketingInput.checked = !!current.marketing;
            }
            showElement(modal);
        }

        function closeManageModal() {
            hideElement(modal);
        }

        function saveConsent(analytics, marketing, method) {
            setStoredConsent({
                necessary: true,
                analytics: !!analytics,
                marketing: !!marketing,
                updatedAt: new Date().toISOString(),
                method: method,
            });
            hideElement(banner);
            closeManageModal();
        }

        if (acceptBtn) {
            acceptBtn.addEventListener('click', function () {
                saveConsent(true, true, 'accept_all');
            });
        }

        if (rejectBtn) {
            rejectBtn.addEventListener('click', function () {
                saveConsent(false, false, 'reject_optional');
            });
        }

        if (manageBtn) {
            manageBtn.addEventListener('click', openManageModal);
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', closeManageModal);
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', function () {
                saveConsent(
                    analyticsInput ? analyticsInput.checked : false,
                    marketingInput ? marketingInput.checked : false,
                    'custom'
                );
            });
        }

        Array.prototype.forEach.call(document.querySelectorAll('.cookie-preferences-link'), function (link) {
            link.addEventListener('click', function (event) {
                event.preventDefault();
                openManageModal();
            });
        });

        window.openCookiePreferences = openManageModal;
    });
})();
