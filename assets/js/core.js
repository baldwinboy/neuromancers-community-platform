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

/**
 * Convert RGB to Hex. Allows whitespace. If given hex, returns that hex. Alpha opacity is discarded.
 * https://gist.github.com/RadGH/c277f220cb41cd0c222f297bad0bbbf5
 * Supports formats:
 * #fc0
 * #ffcc00
 * rgb( 255, 255, 255 )
 * rgba( 255, 255, 255, 0.5 )
 * rgba( 255 255 255 / 0.5 )
 */
var rgb_any_to_hex = function(orig) {	
	var regex_hex, regex_trim, color, regex_rgb, matches, hex;
	
	// Remove whitespace
	regex_trim = new RegExp(/[^#0-9a-f\.\(\)rgba]+/gim);
	color = orig.replace( regex_trim, ' ' ).trim();
	
	// Check if already hex
	regex_hex = new RegExp(/#(([0-9a-f]{1})([0-9a-f]{1})([0-9a-f]{1}))|(([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2}))/gi);
	if ( regex_hex.exec( color ) ) {
		return color;
	}
	
	// Extract RGB values
	regex_rgb = new RegExp( /rgba?\([\t\s]*([0-9]{1,3})[\t\s]*[, ][\t\s]*([0-9]{1,3})[\t\s]*[, ][\t\s]*([0-9]{1,3})[\t\s]*([,\/][\t\s]*[0-9\.]{1,})?[\t\s]*\);?/gim );
	matches = regex_rgb.exec( orig );
	
	if ( matches ) {
		hex = 
			'#' +
			(matches[1] | 1 << 8).toString(16).slice(1) +
			(matches[2] | 1 << 8).toString(16).slice(1) +
			(matches[3] | 1 << 8).toString(16).slice(1);
		return hex;
	}else{
		return orig;
	}
}