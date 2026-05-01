(function () {
    var TRACKING_ENDPOINT = '/api/track-event/';
    var ANON_KEY = 'vasu_analytics_anon_id';

    function getCookie(name) {
        var cookieValue = null;
        if (!document.cookie) {
            return cookieValue;
        }

        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i += 1) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }

        return cookieValue;
    }

    function createAnonymousId() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return window.crypto.randomUUID();
        }
        return 'anon_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    }

    function getAnonymousId() {
        var existing = localStorage.getItem(ANON_KEY);
        if (existing) {
            return existing;
        }

        var created = createAnonymousId();
        localStorage.setItem(ANON_KEY, created);
        return created;
    }

    function parseJson(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (error) {
            return fallback;
        }
    }

    function isTrackingAllowed() {
        if (window.VASU_ANALYTICS_DISABLED) {
            return false;
        }

        var consentFlag = document.documentElement.dataset.cookieAnalytics;
        return consentFlag !== 'denied';
    }

    function sendTrackingEvent(payload) {
        if (!isTrackingAllowed()) {
            return Promise.resolve(false);
        }

        return fetch(TRACKING_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || '',
            },
            body: JSON.stringify(payload),
            keepalive: true,
        })
            .then(function (response) {
                return response.ok;
            })
            .catch(function () {
                return false;
            });
    }

    function trackEvent(eventName, properties) {
        var safeName = String(eventName || '').trim();
        if (!safeName) {
            return Promise.resolve(false);
        }

        var payload = {
            eventType: 'user_event',
            eventName: safeName,
            pagePath: window.location.pathname + window.location.search,
            referrer: document.referrer || '',
            anonymousId: getAnonymousId(),
            properties: properties || {},
        };

        return sendTrackingEvent(payload);
    }

    function trackPageView() {
        return sendTrackingEvent({
            eventType: 'page_view',
            eventName: 'page_view',
            pagePath: window.location.pathname + window.location.search,
            referrer: document.referrer || '',
            anonymousId: getAnonymousId(),
            properties: {
                title: document.title || '',
            },
        });
    }

    function bindAutoTrackedClicks() {
        document.addEventListener('click', function (event) {
            var target = event.target.closest('[data-track-event]');
            if (!target) {
                return;
            }

            var eventName = target.getAttribute('data-track-event');
            var rawProperties = target.getAttribute('data-track-props');
            var parsedProperties = rawProperties ? parseJson(rawProperties, {}) : {};
            if (!parsedProperties || typeof parsedProperties !== 'object') {
                parsedProperties = {};
            }

            if (!parsedProperties.text && target.textContent) {
                parsedProperties.text = target.textContent.trim().slice(0, 120);
            }

            if (!parsedProperties.href && target.getAttribute('href')) {
                parsedProperties.href = target.getAttribute('href');
            }

            trackEvent(eventName, parsedProperties);
        });
    }

    window.vasuTrackEvent = trackEvent;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            trackPageView();
            bindAutoTrackedClicks();
        });
    } else {
        trackPageView();
        bindAutoTrackedClicks();
    }
})();
