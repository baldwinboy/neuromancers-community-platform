// Temporary shim for wagtail-daisIE 2.1.0: the published wheel omits this file.
// Remove once the dependency is bumped to a release that ships it.
/**
 * Persist the visitor's DaisyUI theme choice.
 *
 * The menu theme toggle is a ``.theme-controller`` input whose value names the
 * alternate theme. This script stores the choice in a cookie (so the server can
 * render the right ``data-theme`` on AllAuth and other non-page chrome) and in
 * localStorage, then re-applies it on load.
 */
(function () {
  'use strict';

  var COOKIE = 'daisie_theme';
  var STORAGE = 'daisie-theme';

  function readCookie() {
    var match = document.cookie.match(
      new RegExp('(?:^|;\\s*)' + COOKIE + '=([^;]*)'),
    );
    return match ? decodeURIComponent(match[1]) : '';
  }

  function writeCookie(value) {
    var maxAge = 60 * 60 * 24 * 365;
    document.cookie =
      COOKIE +
      '=' +
      encodeURIComponent(value) +
      '; path=/; max-age=' +
      maxAge +
      '; samesite=lax';
  }

  function storedTheme() {
    try {
      return window.localStorage.getItem(STORAGE) || readCookie() || '';
    } catch (_e) {
      return readCookie() || '';
    }
  }

  function controllers() {
    return Array.prototype.slice.call(
      document.querySelectorAll('input.theme-controller'),
    );
  }

  function apply(theme) {
    if (!theme) {
      return;
    }
    document.documentElement.setAttribute('data-theme', theme);
    controllers().forEach(function (input) {
      input.checked = input.value === theme;
    });
  }

  function remember(theme) {
    if (!theme) {
      return;
    }
    try {
      window.localStorage.setItem(STORAGE, theme);
    } catch (_e) {
      /* storage unavailable; the cookie still works */
    }
    writeCookie(theme);
  }

  function init() {
    var theme = storedTheme();
    apply(theme);
    controllers().forEach(function (input) {
      input.addEventListener('change', function () {
        if (input.checked) {
          apply(input.value);
          remember(input.value);
        }
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
