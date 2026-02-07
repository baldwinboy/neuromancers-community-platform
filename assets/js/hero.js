let initializedHeros = new WeakSet();

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

function initializeHero(heroEl) {
  // Get header height
  const headerEl = document.querySelector("header");
  const headerHeight = headerEl ? headerEl.offsetHeight : 0;

  // Set hero height to viewport height minus header height
  const viewportHeight = window.innerHeight;
  const calculatedHeight = `${viewportHeight - headerHeight}px`;
  heroEl.style.height = calculatedHeight;
}

function cachedInitializeHero(heroEl) {
  if (initializedHeros.has(heroEl)) {
    return;
  }
  initializedHeros.add(heroEl);
  initializeHero(heroEl);
}

(function () {
  console.log("Initializing hero blocks");

  document.addEventListener("DOMContentLoaded", () => {
    const heroEls = document.querySelectorAll('[data-id="hero_block__container"]');
    for (let i = 0, j = heroEls.length; i < j; i++) {
      cachedInitializeHero(heroEls[i]);
    }

    window.addEventListener("resize", debounce(() => {
      const heroEls = document.querySelectorAll('[data-id="hero_block__container"]');
      for (let i = 0, j = heroEls.length; i < j; i++) {
        initializeHero(heroEls[i]);
      }
    }, 500));
  });

  window.addEventListener("beforeunload", () => {
    initializedHeros = new WeakSet();
  });
})();
