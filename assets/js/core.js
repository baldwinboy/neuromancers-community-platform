// Prevent submission on Enter
function handleKeydown(event) {
  const target = event.target;

  if (event.key !== "Enter") return;

  // Ignore if inside a <textarea>
  if (target.tagName === "TEXTAREA") return;

  // Ignore if it's a button or submit input
  if (
    target.tagName === "BUTTON" ||
    (target.tagName === "INPUT" &&
      ["submit", "button", "reset"].includes(target.type))
  )
    return;

  const form = target.form;
  if (!form) return;

  event.preventDefault();

  // Focus next focusable input in form
  const focusables = Array.from(
    form.querySelectorAll("input, select, textarea, button"),
  ).filter((el) => !el.disabled && el.offsetParent !== null);

  const index = focusables.indexOf(target);
  const next = focusables[index + 1];
  if (next) {
    next.focus();
  }
}

// Search in typed multiselect widgets

// Attach listener
function mountKeydownPrevention() {
  document.addEventListener("keydown", handleKeydown);
}

// Remove listener
function unmountKeydownPrevention() {
  document.removeEventListener("keydown", handleKeydown);
}

// Toggle element visibility by id
var toggleEl = (id, currentId) => {
  const el = document.getElementById(id);
  el.classList.toggle("hidden");
  if (currentId) {
    const output = document.getElementById(
      "request_calendar_month__available_times",
    );
    if (output) {
      output.replaceChildren();
    }
    toggleEl(currentId);
  }
};

(function () {
  mountKeydownPrevention();
  // Remove any Wagtail admin messages on base site
  const wagtailMessages = document.querySelectorAll(".wagtailadmin_messages");
  if (wagtailMessages.length) {
    wagtailMessages.forEach((el) => el.remove());
  }
  window.addEventListener("beforeunload", unmountKeydownPrevention);
})();
