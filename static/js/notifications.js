(function () {
    'use strict';

    const POLL_MS = 60000;
    let pollTimer = null;
    let panelOpen = false;

    function $(id) { return document.getElementById(id); }

    async function fetchUnreadCount() {
        try {
            const r = await fetch('/api/v1/notifications/unread-count', { credentials: 'same-origin' });
            if (!r.ok) return;
            const data = await r.json();
            const badge = $('notifBadge');
            if (!badge) return;
            const n = data.unread || 0;
            badge.textContent = n > 99 ? '99+' : String(n);
            badge.style.display = n > 0 ? '' : 'none';
            const live = $('srLive');
            if (live && n > 0 && n !== window.__skpLastUnread) {
                live.textContent = n + ' unread notifications';
                window.__skpLastUnread = n;
            }
        } catch (e) { /* silent */ }
    }

    async function fetchList() {
        try {
            const r = await fetch('/api/v1/notifications', { credentials: 'same-origin' });
            if (!r.ok) return;
            const data = await r.json();
            renderList(data.items || []);
        } catch (e) { /* silent */ }
    }

    function renderList(items) {
        const body = $('notifPanelBody');
        if (!body) return;
        if (!items.length) {
            body.innerHTML = '<div class="notif-empty">No notifications yet.</div>';
            return;
        }
        body.innerHTML = items.map(it => {
            const cls = ['notif-item', it.read_at ? '' : 'unread', 'severity-' + (it.severity || 'info')].join(' ');
            const time = it.created_at ? new Date(it.created_at).toLocaleString() : '';
            return `<div class="${cls}" data-id="${it.id}" data-url="${escapeHtml(it.url || '')}" tabindex="0" role="button">
                <div class="notif-item-title">${escapeHtml(it.title)}</div>
                ${it.body ? `<div class="notif-item-body">${escapeHtml(it.body)}</div>` : ''}
                <div class="notif-item-time">${escapeHtml(time)}</div>
            </div>`;
        }).join('');
        body.querySelectorAll('.notif-item').forEach(el => {
            const handler = () => {
                const id = parseInt(el.getAttribute('data-id'), 10);
                const url = el.getAttribute('data-url') || '';
                open(id, url);
            };
            el.addEventListener('click', handler);
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handler(); }
            });
        });
        const first = body.querySelector('.notif-item');
        if (first) first.focus();
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    async function open(nid, url) {
        try {
            await fetch('/api/v1/notifications/' + nid + '/read', {
                method: 'POST', credentials: 'same-origin'
            });
        } catch (e) { /* silent */ }
        if (url) window.location.href = url;
        else { fetchUnreadCount(); fetchList(); }
    }

    async function markAllRead() {
        try {
            await fetch('/api/v1/notifications/read-all', {
                method: 'POST', credentials: 'same-origin'
            });
            fetchUnreadCount();
            fetchList();
        } catch (e) { /* silent */ }
    }

    function togglePanel() {
        const panel = $('notifPanel');
        const bell = $('notifBellBtn');
        if (!panel) return;
        panelOpen = !panelOpen;
        panel.style.display = panelOpen ? 'flex' : 'none';
        if (bell) bell.setAttribute('aria-expanded', panelOpen ? 'true' : 'false');
        if (panelOpen) fetchList();
    }

    function start() {
        if (pollTimer) return;
        const bell = $('notifBellBtn');
        const markAll = $('notifMarkAllBtn');
        if (bell) bell.addEventListener('click', (e) => { e.stopPropagation(); togglePanel(); });
        if (markAll) markAll.addEventListener('click', (e) => { e.stopPropagation(); markAllRead(); });
        document.addEventListener('click', (e) => {
            const wrap = $('notifWrap');
            if (panelOpen && wrap && !wrap.contains(e.target)) {
                panelOpen = false;
                const panel = $('notifPanel');
                if (panel) panel.style.display = 'none';
            }
        });
        fetchUnreadCount();
        pollTimer = setInterval(fetchUnreadCount, POLL_MS);
    }

    function stop() {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }

    window.SkillPilotNotifications = { start, stop, open, markAllRead, refresh: fetchUnreadCount };
})();
