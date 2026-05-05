/**
 * Feed Filters — drill-down navigation pattern.
 *
 * Each filter group (Languages, Countries, Categories, …) becomes a nav item.
 * Clicking a group slides into a sub-panel that shows only that group's
 * checkboxes, with a "Back" button to return to the top-level list.
 *
 * Usage: include this script after the feed HTML.  It will automatically
 * initialise every `[data-feed-filter-form]` on the page.
 */
(function () {
  'use strict';

  document.querySelectorAll('[data-feed-filter-form]').forEach(initFilterNav);

  /* ------------------------------------------------------------------ */

  function initFilterNav(form) {
    var feed = form.closest('[data-feed-type]');
    if (!feed) return;

    var content = feed.querySelector('.feed-filters__content');
    if (!content) return;

    /* ---- mobile toggle (unchanged behaviour) ---- */
    var toggle = feed.querySelector('.feed-filters__toggle');
    var toggleIcon = toggle ? toggle.querySelector('.feed-filters__toggle-icon') : null;

    if (toggle && content) {
      toggle.addEventListener('click', function () {
        var isExpanded = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', !isExpanded);
        content.classList.toggle('feed-filters__content--open');
        if (toggleIcon) {
          toggleIcon.classList.toggle('feed-filters__toggle-icon--open');
        }
      });
    }

    /* ---- collect groups & build the nav ---- */
    var fieldsets = form.querySelectorAll('fieldset.feed-filters__group');
    // Also keep "Sort by" and "Apply" controls that are NOT inside fieldsets
    var sortGroup = form.querySelector('.feed-filters__group:not(fieldset)');
    var submitBtn = form.querySelector('.feed-filters__submit');

    // Bail out if there are fewer than 2 groups — no need for drill-down
    if (fieldsets.length < 2) return;

    // Wrapper that holds both top-level nav and sub-panels
    var navWrapper = document.createElement('div');
    navWrapper.className = 'feed-filters-nav';

    // --- Top-level list ---
    var topLevel = document.createElement('div');
    topLevel.className = 'feed-filters-nav__top';
    topLevel.setAttribute('data-filter-level', 'top');

    // Title
    var topTitle = content.querySelector('.feed-filters__title');

    fieldsets.forEach(function (fieldset, i) {
      var legend = fieldset.querySelector('.feed-filters__legend');
      var label = legend ? legend.textContent.trim() : 'Filter ' + (i + 1);

      // Count currently-checked boxes
      var checkedCount = fieldset.querySelectorAll('input:checked').length;

      // Top-level nav item
      var navItem = document.createElement('button');
      navItem.type = 'button';
      navItem.className = 'feed-filters-nav__item';
      navItem.setAttribute('data-target', 'group-' + i);
      navItem.innerHTML =
        '<span class="feed-filters-nav__item-label">' + label + '</span>' +
        '<span class="feed-filters-nav__item-meta">' +
          (checkedCount > 0
            ? '<span class="feed-filters-nav__badge">' + checkedCount + '</span>'
            : '') +
          '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 20 20" fill="currentColor" class="feed-filters-nav__chevron"><path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd"/></svg>' +
        '</span>';

      topLevel.appendChild(navItem);

      // --- Sub-panel for this group ---
      var subPanel = document.createElement('div');
      subPanel.className = 'feed-filters-nav__sub';
      subPanel.setAttribute('data-filter-level', 'group-' + i);
      subPanel.style.display = 'none';

      // Back button
      var backBtn = document.createElement('button');
      backBtn.type = 'button';
      backBtn.className = 'feed-filters-nav__back';
      backBtn.innerHTML =
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd"/></svg>' +
        '<span>' + label + '</span>';

      subPanel.appendChild(backBtn);

      // Move the fieldset's inner options into the sub-panel
      var options = fieldset.querySelector('.feed-filters__options');
      if (options) {
        // Clone classes to preserve scrollable styling
        var optionsClone = options.cloneNode(false);
        while (options.firstChild) {
          optionsClone.appendChild(options.firstChild);
        }
        // Remove max-height constraint so the full list shows in the sub-panel
        optionsClone.classList.remove('feed-filters__options--scrollable');
        subPanel.appendChild(optionsClone);
      }

      navWrapper.appendChild(subPanel);

      // Navigation: top-level > sub-panel
      navItem.addEventListener('click', function () {
        topLevel.style.display = 'none';
        subPanel.style.display = '';
      });

      // Navigation: sub-panel > top-level
      backBtn.addEventListener('click', function () {
        subPanel.style.display = 'none';
        topLevel.style.display = '';
        // Update badge count
        var newCount = subPanel.querySelectorAll('input:checked').length;
        var badge = navItem.querySelector('.feed-filters-nav__badge');
        if (newCount > 0) {
          if (badge) {
            badge.textContent = newCount;
          } else {
            var meta = navItem.querySelector('.feed-filters-nav__item-meta');
            var newBadge = document.createElement('span');
            newBadge.className = 'feed-filters-nav__badge';
            newBadge.textContent = newCount;
            meta.insertBefore(newBadge, meta.firstChild);
          }
        } else if (badge) {
          badge.remove();
        }
      });

      // Hide the original fieldset — its inputs are now in the sub-panel
      fieldset.style.display = 'none';
    });

    // Insert the nav wrapper right before the first fieldset (or the sort group)
    var insertRef = form.querySelector('fieldset') || sortGroup || submitBtn;
    if (insertRef) {
      form.insertBefore(navWrapper, insertRef);
    } else {
      form.appendChild(navWrapper);
    }
    navWrapper.insertBefore(topLevel, navWrapper.firstChild);

    /* ---- restore state from URL ---- */
    restoreFromUrl(form, feed);

    /* ---- form submit handler ---- */
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      submitFilters(form);
    });
  }

  /* ------------------------------------------------------------------ */

  function restoreFromUrl(form, feed) {
    var params = new URLSearchParams(window.location.search);

    // Restore language checkboxes
    var langParam = params.get('languages');
    if (langParam) {
      var langs = langParam.split(',');
      form.querySelectorAll('input[data-category="languages"]').forEach(function (cb) {
        cb.checked = langs.includes(cb.value);
      });
    }

    // Restore country checkboxes (peer feed)
    var countryParam = params.get('countries');
    if (countryParam) {
      var countries = countryParam.split(',');
      form.querySelectorAll('input[data-category="countries"]').forEach(function (cb) {
        cb.checked = countries.includes(cb.value);
      });
    }

    // Restore generic category checkboxes
    form.querySelectorAll('input[data-category]:not([data-category="languages"]):not([data-category="countries"])').forEach(function (cb) {
      var paramName = 'filter_' + cb.dataset.category;
      var paramValue = params.get(paramName);
      if (paramValue) {
        cb.checked = paramValue.split(',').includes(cb.value);
      }
    });

    // Update all badge counts to reflect restored state
    feed.querySelectorAll('.feed-filters-nav__item').forEach(function (navItem) {
      var targetId = navItem.getAttribute('data-target');
      var subPanel = feed.querySelector('[data-filter-level="' + targetId + '"]');
      if (!subPanel) return;
      var checkedCount = subPanel.querySelectorAll('input:checked').length;
      var badge = navItem.querySelector('.feed-filters-nav__badge');
      if (checkedCount > 0) {
        if (badge) {
          badge.textContent = checkedCount;
        } else {
          var meta = navItem.querySelector('.feed-filters-nav__item-meta');
          var newBadge = document.createElement('span');
          newBadge.className = 'feed-filters-nav__badge';
          newBadge.textContent = checkedCount;
          meta.insertBefore(newBadge, meta.firstChild);
        }
      } else if (badge) {
        badge.remove();
      }
    });
  }

  /* ------------------------------------------------------------------ */

  function submitFilters(form) {
    var params = new URLSearchParams();

    // Simple checkboxes (include_peer, include_group, etc.)
    form.querySelectorAll('input[data-simple-checkbox]').forEach(function (cb) {
      params.set(cb.name, cb.checked ? '1' : '0');
    });

    // Language checkboxes
    var langValues = [];
    form.querySelectorAll('input[data-category="languages"]').forEach(function (cb) {
      if (cb.checked) langValues.push(cb.value);
    });
    if (langValues.length > 0) params.set('languages', langValues.join(','));

    // Country checkboxes
    var countryValues = [];
    form.querySelectorAll('input[data-category="countries"]').forEach(function (cb) {
      if (cb.checked) countryValues.push(cb.value);
    });
    if (countryValues.length > 0) params.set('countries', countryValues.join(','));

    // Generic category checkboxes
    var catValues = {};
    form.querySelectorAll('input[data-category]:not([data-category="languages"]):not([data-category="countries"])').forEach(function (cb) {
      var cat = cb.dataset.category;
      if (!catValues[cat]) catValues[cat] = [];
      if (cb.checked) catValues[cat].push(cb.value);
    });
    for (var cat in catValues) {
      if (catValues[cat].length > 0) {
        params.set('filter_' + cat, catValues[cat].join(','));
      }
    }

    // Sort
    var sortSelect = form.querySelector('select[name="sort"]');
    if (sortSelect) params.set('sort', sortSelect.value);

    window.location.href = window.location.pathname + '?' + params.toString();
  }
})();
