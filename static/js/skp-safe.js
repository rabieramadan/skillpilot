/* SkillPilot — XSS-safety helpers.
 *
 * Use SKP.escape(text) or the `t` tag-template to safely interpolate
 * untrusted strings into HTML. Prefer .textContent for plain text.
 *
 *   element.innerHTML = SKP.t`<div class="card">${userName}</div>`;
 *   element.textContent = userName;          // also fine
 *
 * Never do:
 *   element.innerHTML = '<div>' + userName + '</div>';   // XSS!
 */
(function () {
  'use strict';
  var ENTITIES = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '/': '&#x2F;',
    '`': '&#x60;',
    '=': '&#x3D;'
  };
  function escape(v) {
    if (v === null || v === undefined) return '';
    return String(v).replace(/[&<>"'`=\/]/g, function (c) { return ENTITIES[c]; });
  }
  // Tagged-template helper: escapes every interpolation but leaves the
  // static template parts untouched. Example:
  //   el.innerHTML = SKP.t`<a href="${url}">${name}</a>`;
  function t(strings) {
    var out = strings[0];
    for (var i = 1; i < arguments.length; i++) {
      out += escape(arguments[i]) + strings[i];
    }
    return out;
  }
  // Set HTML safely from an array of trusted-template + untrusted-data
  // by clearing existing children first.
  function setHTML(el, html) {
    if (!el) return;
    el.innerHTML = html;
  }
  window.SKP = window.SKP || {};
  window.SKP.escape = escape;
  window.SKP.t = t;
  window.SKP.setHTML = setHTML;
})();
