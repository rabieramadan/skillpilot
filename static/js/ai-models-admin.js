/*
 * AI model management for the admin and super-admin screens.
 *
 * The catalogue lives in config.yaml, not in the code and not in the
 * database. This panel is the friendly way to edit it: list what each
 * provider offers, ask the provider what its key can actually reach, try a
 * candidate model for real, and — only once it has answered — offer to save
 * it and make it the default.
 *
 * Mount with:  SkpAIModels.mount('elementId')
 * It is self-contained: no framework, no build step, and it injects its own
 * styles once so it looks the same wherever it is dropped in.
 */
(function (global) {
    'use strict';

    var API = '/api/ai-models';
    var state = { data: null, container: null, busy: false, openProvider: null };

    /* ---------------------------------------------------------------- utils */

    function esc(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function tokens(n) {
        if (!n) { return '—'; }
        if (n >= 1000000) { return (n / 1000000).toFixed(n % 1000000 ? 1 : 0) + 'M'; }
        if (n >= 1000) { return Math.round(n / 1000) + 'K'; }
        return String(n);
    }

    function money(price) {
        if (!price) { return '<span class="skp-dim">not priced</span>'; }
        return '$' + price.input + ' / $' + price.output
            + ' <span class="skp-dim">per 1M</span>';
    }

    async function call(path, options) {
        var response = await fetch(API + path, Object.assign({
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin'
        }, options || {}));
        var body;
        try { body = await response.json(); } catch (e) { body = {}; }
        if (response.status === 401 || response.status === 403) {
            throw new Error(body.error || 'You are not signed in as an administrator.');
        }
        return body;
    }

    function setBusy(on, message) {
        state.busy = on;
        var bar = document.getElementById('skp-am-busy');
        if (!bar) { return; }
        bar.style.display = on ? 'flex' : 'none';
        if (on && message) { bar.querySelector('span').textContent = message; }
    }

    function toast(message, kind) {
        var box = document.getElementById('skp-am-toast');
        if (!box) { return; }
        box.className = 'skp-am-toast skp-am-' + (kind || 'ok');
        box.textContent = message;
        box.style.display = 'block';
        clearTimeout(box._timer);
        box._timer = setTimeout(function () { box.style.display = 'none'; }, 6000);
    }

    /* --------------------------------------------------------------- styles */

    var STYLE = [
        '.skp-am { font-size: 14px; color: #1f2937; }',
        '.skp-am * { box-sizing: border-box; }',
        '.skp-am-head { display:flex; justify-content:space-between; align-items:flex-start;',
        '  gap:12px; flex-wrap:wrap; margin-bottom:14px; }',
        '.skp-am-source { background:#f3f4f6; border-radius:8px; padding:10px 14px;',
        '  font-size:12.5px; color:#4b5563; line-height:1.6; }',
        '.skp-am-source code { background:#fff; padding:1px 5px; border-radius:4px;',
        '  font-size:12px; color:#111827; }',
        '.skp-am-warn { background:#fef3c7; border-left:3px solid #f59e0b; padding:8px 12px;',
        '  border-radius:6px; margin-top:8px; color:#78350f; font-size:12.5px; }',
        '.skp-am-prov { border:1px solid #e5e7eb; border-radius:12px; margin-bottom:14px;',
        '  overflow:hidden; background:#fff; }',
        '.skp-am-prov-head { display:flex; align-items:center; gap:12px; padding:14px 16px;',
        '  cursor:pointer; background:#fafafa; border-bottom:1px solid #f1f1f1; }',
        '.skp-am-prov-head:hover { background:#f5f6f8; }',
        '.skp-am-prov-name { font-weight:600; font-size:15px; flex:1; }',
        '.skp-am-prov-name small { display:block; font-weight:400; color:#6b7280;',
        '  font-size:12px; margin-top:2px; }',
        '.skp-am-pill { font-size:11px; padding:3px 9px; border-radius:999px;',
        '  font-weight:600; white-space:nowrap; }',
        '.skp-am-pill.ok { background:#dcfce7; color:#166534; }',
        '.skp-am-pill.no { background:#fee2e2; color:#991b1b; }',
        '.skp-am-pill.off { background:#e5e7eb; color:#4b5563; }',
        '.skp-am-body { padding:14px 16px; }',
        '.skp-am-table { width:100%; border-collapse:collapse; font-size:13px; }',
        '.skp-am-table th { text-align:left; font-weight:600; color:#6b7280; font-size:11.5px;',
        '  text-transform:uppercase; letter-spacing:.04em; padding:6px 8px;',
        '  border-bottom:1px solid #e5e7eb; }',
        '.skp-am-table td { padding:9px 8px; border-bottom:1px solid #f3f4f6;',
        '  vertical-align:top; }',
        '.skp-am-table tr:last-child td { border-bottom:none; }',
        '.skp-am-id { font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12.5px;',
        '  color:#111827; }',
        '.skp-am-id b { display:block; font-family:inherit; }',
        '.skp-am-sum { color:#6b7280; font-size:12px; margin-top:3px; max-width:340px; }',
        '.skp-dim { color:#9ca3af; }',
        '.skp-am-btn { border:1px solid #d1d5db; background:#fff; border-radius:7px;',
        '  padding:6px 11px; font-size:12.5px; cursor:pointer; color:#374151;',
        '  white-space:nowrap; }',
        '.skp-am-btn:hover:not(:disabled) { background:#f9fafb; border-color:#9ca3af; }',
        '.skp-am-btn:disabled { opacity:.5; cursor:not-allowed; }',
        '.skp-am-btn.primary { background:#2563eb; border-color:#2563eb; color:#fff; }',
        '.skp-am-btn.primary:hover:not(:disabled) { background:#1d4ed8; }',
        '.skp-am-btn.danger { color:#b91c1c; border-color:#fecaca; }',
        '.skp-am-btn.danger:hover:not(:disabled) { background:#fef2f2; }',
        '.skp-am-actions { display:flex; gap:6px; justify-content:flex-end; flex-wrap:wrap; }',
        '.skp-am-default { background:#eff6ff; color:#1d4ed8; font-size:11px;',
        '  padding:2px 8px; border-radius:999px; font-weight:600; }',
        '.skp-am-tools { display:flex; gap:8px; flex-wrap:wrap; margin-top:14px;',
        '  padding-top:14px; border-top:1px dashed #e5e7eb; }',
        '.skp-am-panel { margin-top:12px; border:1px solid #e5e7eb; border-radius:10px;',
        '  padding:14px; background:#fafafa; }',
        '.skp-am-panel h4 { margin:0 0 10px; font-size:13.5px; }',
        '.skp-am-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));',
        '  gap:10px; }',
        '.skp-am-field label { display:block; font-size:11.5px; color:#6b7280;',
        '  margin-bottom:3px; font-weight:600; }',
        '.skp-am-field input, .skp-am-field select { width:100%; padding:7px 9px;',
        '  border:1px solid #d1d5db; border-radius:6px; font-size:13px; background:#fff; }',
        '.skp-am-checks { display:flex; gap:16px; flex-wrap:wrap; margin:10px 0;',
        '  font-size:12.5px; }',
        '.skp-am-checks label { display:flex; align-items:center; gap:6px; cursor:pointer; }',
        '.skp-am-result { margin-top:12px; border-radius:10px; padding:12px 14px;',
        '  font-size:13px; line-height:1.6; }',
        '.skp-am-result.ok { background:#f0fdf4; border:1px solid #bbf7d0; color:#14532d; }',
        '.skp-am-result.bad { background:#fef2f2; border:1px solid #fecaca; color:#7f1d1d; }',
        '.skp-am-reply { background:#fff; border-radius:6px; padding:8px 10px; margin:8px 0;',
        '  font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12.5px;',
        '  color:#111827; white-space:pre-wrap; word-break:break-word; }',
        '.skp-am-busy { display:none; align-items:center; gap:9px; background:#eff6ff;',
        '  border-radius:8px; padding:9px 13px; margin-bottom:12px; color:#1d4ed8;',
        '  font-size:13px; }',
        '.skp-am-toast { display:none; border-radius:8px; padding:10px 14px;',
        '  margin-bottom:12px; font-size:13px; }',
        '.skp-am-ok { background:#dcfce7; color:#166534; }',
        '.skp-am-err { background:#fee2e2; color:#991b1b; }',
        '.skp-am-disc { max-height:230px; overflow:auto; background:#fff; border-radius:8px;',
        '  border:1px solid #e5e7eb; margin-top:10px; }',
        '.skp-am-disc div { display:flex; justify-content:space-between; align-items:center;',
        '  gap:10px; padding:7px 11px; border-bottom:1px solid #f3f4f6; font-size:12.5px; }',
        '.skp-am-disc div:last-child { border-bottom:none; }',
        '@media (max-width:640px) { .skp-am-table thead { display:none; }',
        '  .skp-am-table td { display:block; border:none; padding:3px 0; }',
        '  .skp-am-table tr { display:block; padding:10px 0;',
        '    border-bottom:1px solid #f3f4f6; }',
        '  .skp-am-actions { justify-content:flex-start; margin-top:8px; } }'
    ].join('\n');

    function injectStyles() {
        if (document.getElementById('skp-am-style')) { return; }
        var tag = document.createElement('style');
        tag.id = 'skp-am-style';
        tag.textContent = STYLE;
        document.head.appendChild(tag);
    }

    /* -------------------------------------------------------------- rendering */

    function renderStatus(registry) {
        var warnings = (registry.warnings || []).map(function (w) {
            return '<div class="skp-am-warn"><i class="fas fa-exclamation-triangle"></i> '
                + esc(w) + '</div>';
        }).join('');

        var writable = registry.writable
            ? ''
            : '<div class="skp-am-warn"><i class="fas fa-lock"></i> This file is '
              + 'read-only for the server, so changes cannot be saved from here. '
              + 'Grant write permission, or edit the file directly — it is re-read '
              + 'automatically.</div>';

        return '<div class="skp-am-source">'
            + '<strong>' + esc(registry.provider_count) + ' providers, '
            + esc(registry.model_count) + ' models</strong> — defined in '
            + '<code>' + esc(registry.path) + '</code>'
            + '<br>Editing here rewrites that file. Comments in it are preserved, '
            + 'and a running server picks the change up without a restart.'
            + writable + warnings + '</div>';
    }

    function renderModelRow(providerKey, provider, model) {
        var isDefault = model.id === provider.default_model;
        var caps = [];
        if (model.vision) { caps.push('vision'); }
        if (model.max_completion_tokens) { caps.push('max_completion_tokens'); }
        if (!model.sampling) { caps.push('no temperature'); }
        if (model.legacy) { caps.push('legacy'); }

        return '<tr>'
            + '<td class="skp-am-id"><b>' + esc(model.id) + '</b>'
            + (isDefault ? ' <span class="skp-am-default">default</span>' : '')
            + '<div class="skp-am-sum">' + esc(model.label)
            + (model.summary ? ' — ' + esc(model.summary) : '') + '</div>'
            + (caps.length ? '<div class="skp-am-sum skp-dim">' + esc(caps.join(' · '))
                + '</div>' : '')
            + '</td>'
            + '<td>' + tokens(model.context_tokens) + ' in<br>'
            + tokens(model.max_output_tokens) + ' out</td>'
            + '<td>' + money(model.price_per_million) + '</td>'
            + '<td><div class="skp-am-actions">'
            + '<button class="skp-am-btn" data-act="test" data-p="' + esc(providerKey)
            + '" data-m="' + esc(model.id) + '">Test</button>'
            + (isDefault ? ''
                : '<button class="skp-am-btn" data-act="default" data-p="' + esc(providerKey)
                  + '" data-m="' + esc(model.id) + '">Make default</button>')
            + '<button class="skp-am-btn danger" data-act="retire" data-p="' + esc(providerKey)
            + '" data-m="' + esc(model.id) + '">Retire</button>'
            + '</div></td></tr>';
    }

    function renderProvider(key, provider) {
        var open = state.openProvider === key;
        var pill = !provider.enabled
            ? '<span class="skp-am-pill off">Switched off</span>'
            : provider.configured
                ? '<span class="skp-am-pill ok">Key configured</span>'
                : '<span class="skp-am-pill no">No API key</span>';

        var unsupported = provider.supported ? ''
            : '<div class="skp-am-warn">Driver <code>' + esc(provider.driver)
              + '</code> is not one this version can call.</div>';

        var rows = provider.models.map(function (m) {
            return renderModelRow(key, provider, m);
        }).join('');

        var aliasCount = Object.keys(provider.aliases || {}).length;

        return '<div class="skp-am-prov">'
            + '<div class="skp-am-prov-head" data-act="toggle" data-p="' + esc(key) + '">'
            + '<i class="fas fa-chevron-' + (open ? 'down' : 'right') + '"></i>'
            + '<div class="skp-am-prov-name">' + esc(provider.label)
            + '<small>' + esc(provider.models.length) + ' models · default '
            + esc(provider.default_model)
            + (aliasCount ? ' · ' + aliasCount + ' retired ids still mapped' : '')
            + '</small></div>' + pill + '</div>'
            + (open ? '<div class="skp-am-body">' + unsupported
                + '<table class="skp-am-table"><thead><tr>'
                + '<th>Model</th><th>Tokens</th><th>Price</th><th></th>'
                + '</tr></thead><tbody>' + rows + '</tbody></table>'
                + '<div class="skp-am-tools">'
                + (provider.has_discovery
                    ? '<button class="skp-am-btn" data-act="discover" data-p="' + esc(key)
                      + '">Discover what this key can reach</button>' : '')
                + '<button class="skp-am-btn primary" data-act="addform" data-p="' + esc(key)
                + '">Add a model</button>'
                + '<button class="skp-am-btn" data-act="toggleprov" data-p="' + esc(key)
                + '">' + (provider.enabled ? 'Switch provider off' : 'Switch provider on')
                + '</button></div>'
                + '<div id="skp-am-work-' + esc(key) + '"></div>'
                + '</div>' : '')
            + '</div>';
    }

    function render() {
        if (!state.container || !state.data) { return; }
        var providers = state.data.providers || {};
        state.container.innerHTML =
            '<div class="skp-am">'
            + '<div class="skp-am-head"><div style="flex:1">'
            + renderStatus(state.data.registry || {}) + '</div>'
            + '<button class="skp-am-btn" data-act="reload">Re-read file</button></div>'
            + '<div id="skp-am-toast" class="skp-am-toast"></div>'
            + '<div id="skp-am-busy" class="skp-am-busy">'
            + '<i class="fas fa-spinner fa-spin"></i><span>Working…</span></div>'
            + Object.keys(providers).map(function (k) {
                return renderProvider(k, providers[k]);
            }).join('')
            + '</div>';
    }

    function workArea(providerKey) {
        return document.getElementById('skp-am-work-' + providerKey);
    }

    /* ------------------------------------------------------------- the flows */

    function addForm(providerKey) {
        var area = workArea(providerKey);
        if (!area) { return; }
        area.innerHTML =
            '<div class="skp-am-panel"><h4>Add a model to '
            + esc(state.data.providers[providerKey].label) + '</h4>'
            + '<p class="skp-am-sum">Enter the identifier exactly as the provider '
            + 'documents it. It is tested against the live API before anything is '
            + 'saved.</p>'
            + '<div class="skp-am-grid">'
            + field(providerKey, 'id', 'Model id (required)', 'text', '')
            + field(providerKey, 'label', 'Display name', 'text', '')
            + field(providerKey, 'context_tokens', 'Context window', 'number', '')
            + field(providerKey, 'max_output_tokens', 'Max response tokens', 'number', '8000')
            + field(providerKey, 'price_in', 'Input $ / 1M tokens', 'number', '')
            + field(providerKey, 'price_out', 'Output $ / 1M tokens', 'number', '')
            + '</div>'
            + '<div class="skp-am-field" style="margin-top:10px">'
            + '<label>One-line description for whoever picks it</label>'
            + '<input type="text" id="skp-f-' + esc(providerKey) + '-summary"></div>'
            + '<div class="skp-am-checks">'
            + check(providerKey, 'vision', 'Accepts images', false)
            + check(providerKey, 'sampling', 'Accepts a temperature setting', true)
            + check(providerKey, 'mct', 'Needs max_completion_tokens', false)
            + '</div>'
            + '<div class="skp-am-actions" style="justify-content:flex-start">'
            + '<button class="skp-am-btn primary" data-act="testnew" data-p="'
            + esc(providerKey) + '">Test this model</button>'
            + '<button class="skp-am-btn" data-act="cancel" data-p="' + esc(providerKey)
            + '">Cancel</button></div>'
            + '<div id="skp-am-res-' + esc(providerKey) + '"></div></div>';
        var first = document.getElementById('skp-f-' + providerKey + '-id');
        if (first) { first.focus(); }
    }

    function field(p, name, label, type, value) {
        return '<div class="skp-am-field"><label>' + esc(label) + '</label>'
            + '<input type="' + type + '" id="skp-f-' + esc(p) + '-' + esc(name)
            + '" value="' + esc(value) + '"></div>';
    }

    function check(p, name, label, checked) {
        return '<label><input type="checkbox" id="skp-c-' + esc(p) + '-' + esc(name) + '"'
            + (checked ? ' checked' : '') + '> ' + esc(label) + '</label>';
    }

    function readForm(providerKey) {
        function val(name) {
            var el = document.getElementById('skp-f-' + providerKey + '-' + name);
            return el ? el.value.trim() : '';
        }
        function bool(name) {
            var el = document.getElementById('skp-c-' + providerKey + '-' + name);
            return !!(el && el.checked);
        }
        var model = {
            id: val('id'),
            label: val('label') || val('id'),
            summary: val('summary'),
            context_tokens: parseInt(val('context_tokens'), 10) || 0,
            max_output_tokens: parseInt(val('max_output_tokens'), 10) || 8000,
            vision: bool('vision'),
            sampling: bool('sampling'),
            max_completion_tokens: bool('mct')
        };
        var pin = parseFloat(val('price_in'));
        var pout = parseFloat(val('price_out'));
        if (!isNaN(pin) && !isNaN(pout)) {
            model.price_per_million = { input: pin, output: pout };
        }
        return model;
    }

    async function runTest(providerKey, modelId, model) {
        var target = document.getElementById('skp-am-res-' + providerKey)
            || workArea(providerKey);
        if (!target) { return; }
        target.innerHTML = '<div class="skp-am-result ok">'
            + '<i class="fas fa-spinner fa-spin"></i> Sending a short prompt to '
            + esc(modelId) + '…</div>';

        var body;
        try {
            body = await call('/test', {
                method: 'POST',
                body: JSON.stringify({ provider: providerKey, model_id: modelId })
            });
        } catch (err) {
            target.innerHTML = '<div class="skp-am-result bad">' + esc(err.message)
                + '</div>';
            return;
        }

        if (!body.success) {
            target.innerHTML = '<div class="skp-am-result bad">'
                + '<strong>' + esc(modelId) + ' did not work.</strong>'
                + '<div class="skp-am-reply">' + esc(body.error || 'Unknown error')
                + '</div>'
                + (body.hint ? '<div>' + esc(body.hint) + '</div>' : '')
                + '<div class="skp-dim">Took ' + esc(body.elapsed_ms || 0) + ' ms. '
                + 'Nothing was saved.</div></div>';
            return;
        }

        var used = body.usage || {};
        var totals = (used.prompt_tokens || 0) + (used.completion_tokens || 0);
        var known = body.in_catalogue;

        // The model answered. Now ask whether to keep it — never save silently.
        target.innerHTML = '<div class="skp-am-result ok">'
            + '<strong>' + esc(modelId) + ' replied.</strong>'
            + '<div class="skp-am-reply">' + esc(body.reply || '(empty)') + '</div>'
            + '<div class="skp-dim">' + esc(body.elapsed_ms) + ' ms'
            + (totals ? ' · ' + totals + ' tokens' : '') + '</div>'
            + (known
                ? '<div style="margin-top:8px">This model is already in the catalogue.</div>'
                  + '<div class="skp-am-actions" style="justify-content:flex-start;margin-top:8px">'
                  + '<button class="skp-am-btn primary" data-act="makedefault" data-p="'
                  + esc(providerKey) + '" data-m="' + esc(modelId)
                  + '">Use it as the default</button>'
                  + '<button class="skp-am-btn" data-act="cancel" data-p="'
                  + esc(providerKey) + '">Close</button></div>'
                : '<div style="margin-top:8px"><strong>Save it to the catalogue?</strong> '
                  + 'It will be written to config.yaml and available everywhere in '
                  + 'the platform.</div>'
                  + '<div class="skp-am-actions" style="justify-content:flex-start;margin-top:8px">'
                  + '<button class="skp-am-btn primary" data-act="save" data-p="'
                  + esc(providerKey) + '" data-default="1">Save and make it the default</button>'
                  + '<button class="skp-am-btn" data-act="save" data-p="' + esc(providerKey)
                  + '" data-default="0">Save without changing the default</button>'
                  + '<button class="skp-am-btn" data-act="cancel" data-p="'
                  + esc(providerKey) + '">Discard</button></div>')
            + '</div>';

        // Hold the tested definition so Save writes exactly what was tested.
        state.pending = state.pending || {};
        state.pending[providerKey] = model || { id: modelId };
    }

    async function doSave(providerKey, makeDefault) {
        var model = (state.pending || {})[providerKey];
        if (!model) { toast('Nothing to save — test a model first.', 'err'); return; }
        setBusy(true, 'Writing to config.yaml…');
        try {
            var body = await call('/save', {
                method: 'POST',
                body: JSON.stringify({
                    provider: providerKey, model: model,
                    make_default: makeDefault, confirmed: true
                })
            });
            setBusy(false);
            if (!body.success) { toast(body.error || 'Save failed.', 'err'); return; }
            delete state.pending[providerKey];
            state.data = body;
            render();
            toast(body.message || 'Saved.', 'ok');
        } catch (err) {
            setBusy(false);
            toast(err.message, 'err');
        }
    }

    async function doDiscover(providerKey) {
        var area = workArea(providerKey);
        if (!area) { return; }
        area.innerHTML = '<div class="skp-am-panel"><i class="fas fa-spinner fa-spin"></i> '
            + 'Asking the provider what this key can reach…</div>';
        var body;
        try {
            body = await call('/discover', {
                method: 'POST', body: JSON.stringify({ provider: providerKey })
            });
        } catch (err) {
            area.innerHTML = '<div class="skp-am-panel"><div class="skp-am-result bad">'
                + esc(err.message) + '</div></div>';
            return;
        }
        if (!body.success) {
            area.innerHTML = '<div class="skp-am-panel"><div class="skp-am-result bad">'
                + esc(body.error) + '</div></div>';
            return;
        }

        var rows = (body.models || []).map(function (m) {
            var tag = m.in_catalogue
                ? '<span class="skp-am-pill ok">in catalogue</span>'
                : m.retired_here
                    ? '<span class="skp-am-pill off">retired here</span>'
                    : '<button class="skp-am-btn" data-act="testid" data-p="'
                      + esc(providerKey) + '" data-m="' + esc(m.id) + '">Test</button>';
            return '<div><span class="skp-am-id">' + esc(m.id) + '</span>' + tag + '</div>';
        }).join('') || '<div class="skp-dim" style="padding:10px">Nothing returned.</div>';

        var stale = (body.not_listed_by_provider || []).length
            ? '<div class="skp-am-warn">In the catalogue but not offered by the '
              + 'provider: <code>' + esc(body.not_listed_by_provider.join(', '))
              + '</code>. These were probably retired — test one to confirm, then '
              + 'retire it here.</div>'
            : '';

        area.innerHTML = '<div class="skp-am-panel">'
            + '<h4>' + esc(body.models.length) + ' models this key can reach</h4>'
            + '<p class="skp-am-sum">Straight from the provider. This is what to '
            + 'trust when an announcement and the API disagree.</p>'
            + stale
            + '<div class="skp-am-disc">' + rows + '</div>'
            + '<div class="skp-am-actions" style="justify-content:flex-start;margin-top:10px">'
            + '<button class="skp-am-btn" data-act="cancel" data-p="' + esc(providerKey)
            + '">Close</button></div>'
            + '<div id="skp-am-res-' + esc(providerKey) + '"></div></div>';
    }

    async function doDefault(providerKey, modelId) {
        setBusy(true, 'Updating the default…');
        try {
            var body = await call('/default', {
                method: 'POST',
                body: JSON.stringify({ provider: providerKey, model_id: modelId })
            });
            setBusy(false);
            if (!body.success) { toast(body.error, 'err'); return; }
            state.data = body;
            render();
            toast(body.message, 'ok');
        } catch (err) { setBusy(false); toast(err.message, 'err'); }
    }

    async function doRetire(providerKey, modelId) {
        var provider = state.data.providers[providerKey];
        var replacement = provider.default_model === modelId
            ? '(the next model in the list)' : provider.default_model;
        if (!global.confirm(
            'Retire ' + modelId + '?\n\n'
            + 'It will be removed from the menus, and anything still asking for it '
            + 'will be served by ' + replacement + ' instead. Nothing breaks.\n\n'
            + 'This edits config.yaml.')) { return; }

        setBusy(true, 'Retiring ' + modelId + '…');
        try {
            var body = await call('/' + encodeURIComponent(providerKey) + '/'
                + encodeURIComponent(modelId), { method: 'DELETE' });
            setBusy(false);
            if (!body.success) { toast(body.error, 'err'); return; }
            state.data = body;
            render();
            toast(body.message, 'ok');
        } catch (err) { setBusy(false); toast(err.message, 'err'); }
    }

    async function doToggleProvider(providerKey) {
        var provider = state.data.providers[providerKey];
        setBusy(true, 'Updating ' + provider.label + '…');
        try {
            var body = await call('/' + encodeURIComponent(providerKey) + '/enabled', {
                method: 'POST', body: JSON.stringify({ enabled: !provider.enabled })
            });
            setBusy(false);
            if (!body.success) { toast(body.error, 'err'); return; }
            state.data = body;
            render();
            toast(body.message, 'ok');
        } catch (err) { setBusy(false); toast(err.message, 'err'); }
    }

    /* ---------------------------------------------------------------- events */

    function onClick(event) {
        var target = event.target.closest('[data-act]');
        if (!target || !state.container.contains(target)) { return; }
        var act = target.getAttribute('data-act');
        var provider = target.getAttribute('data-p');
        var model = target.getAttribute('data-m');
        event.preventDefault();

        if (act === 'toggle') {
            state.openProvider = state.openProvider === provider ? null : provider;
            render();
        } else if (act === 'reload') {
            load(true);
        } else if (act === 'addform') {
            addForm(provider);
        } else if (act === 'cancel') {
            var area = workArea(provider);
            if (area) { area.innerHTML = ''; }
            if (state.pending) { delete state.pending[provider]; }
        } else if (act === 'discover') {
            doDiscover(provider);
        } else if (act === 'test') {
            var known = (state.data.providers[provider].models || []).find(function (m) {
                return m.id === model;
            });
            var area2 = workArea(provider);
            if (area2 && !document.getElementById('skp-am-res-' + provider)) {
                area2.innerHTML = '<div class="skp-am-panel"><div id="skp-am-res-'
                    + esc(provider) + '"></div></div>';
            }
            runTest(provider, model, known);
        } else if (act === 'testid') {
            runTest(provider, model, { id: model, label: model });
        } else if (act === 'testnew') {
            var built = readForm(provider);
            if (!built.id) { toast('A model id is required.', 'err'); return; }
            runTest(provider, built.id, built);
        } else if (act === 'save') {
            doSave(provider, target.getAttribute('data-default') === '1');
        } else if (act === 'default' || act === 'makedefault') {
            doDefault(provider, model);
        } else if (act === 'retire') {
            doRetire(provider, model);
        } else if (act === 'toggleprov') {
            doToggleProvider(provider);
        }
    }

    /* ------------------------------------------------------------------ init */

    async function load(force) {
        if (!state.container) { return; }
        if (!state.data || force) {
            state.container.innerHTML =
                '<div class="skp-am"><div class="skp-am-busy" style="display:flex">'
                + '<i class="fas fa-spinner fa-spin"></i><span>Loading the model '
                + 'catalogue…</span></div></div>';
        }
        try {
            var body = await call(force ? '/reload' : '', force ? { method: 'POST' } : {});
            if (!body.providers) {
                throw new Error(body.error || 'The catalogue could not be read.');
            }
            state.data = body;
            render();
        } catch (err) {
            state.container.innerHTML = '<div class="skp-am">'
                + '<div class="skp-am-result bad">' + esc(err.message) + '</div></div>';
        }
    }

    function mount(elementOrId) {
        injectStyles();
        var element = typeof elementOrId === 'string'
            ? document.getElementById(elementOrId) : elementOrId;
        if (!element) { return; }
        state.container = element;
        if (!element._skpBound) {
            element.addEventListener('click', onClick);
            element._skpBound = true;
        }
        load(false);
    }

    global.SkpAIModels = { mount: mount, reload: function () { load(true); } };
}(window));
