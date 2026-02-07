let initializedAccordions = new WeakSet();

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function initializeAccordion(accordionEl) {
    accordionEl.addEventListener('click', function() {
        this.classList.toggle('active');
        const panel = this.nextElementSibling;
        if (panel.style.maxHeight) {
            panel.style.maxHeight = null;
        } else {
            panel.style.maxHeight = panel.scrollHeight + 16 + "px";
        }
    });
}

function cachedInitializeAccordion(accordionEl) {
  if (initializedAccordions.has(accordionEl)) {
    return;
  }
  initializedAccordions.add(accordionEl);
  initializeAccordion(accordionEl);
}

(function () {
  console.log("Initializing accordion blocks");

  document.addEventListener("DOMContentLoaded", () => {
    const accordionEls = document.getElementsByClassName('accordion');
    for (let i = 0, j = accordionEls.length; i < j; i++) {
      cachedInitializeAccordion(accordionEls[i]);
    }
  });

  window.addEventListener("beforeunload", () => {
    initializedAccordions = new WeakSet();
  });
})();
