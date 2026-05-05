/**
 * Shared dynamic style map for Draftail editor.
 * All styles are pre-registered via InlineStyleFeature in Python.
 * This module is kept as a no-op for backward compatibility.
 */
(function () {
  if (window.draftailDynamicStyleMapInitialized) {
    return;
  }
  window.draftailDynamicStyleMapInitialized = true;
  window.draftailDynamicStyleMap = {};
})();
