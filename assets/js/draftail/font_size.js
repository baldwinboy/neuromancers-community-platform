(function () {
  const React = window.React;
  const { RichUtils, EditorState } = window.DraftJS;
  const { ToolbarButton, Tooltip } = window.Draftail;

  // Predefined sizes (Google Docs style)
  const presetSizes = [8, 9, 10, 11, 12, 14, 16, 18, 24, 30, 36, 48, 60, 72, 96];

  const presetOptions = presetSizes.map((size) => ({
    label: `${size}`,
    type: `FONT_SIZE_${size}`,
    style: { fontSize: `${size}px` },
    size: size,
  }));

  function getSizeOption(size) {
    const type = `FONT_SIZE_${size}`;
    return { label: `${size}`, type: type, style: { fontSize: `${size}px` }, size: size };
  }

  // Shared mutable state (no hooks needed)
  let savedSelection = null;

  function getActiveSize(editorState) {
    let active = null;
    const currentStyle = editorState.getCurrentInlineStyle();
    currentStyle.forEach((style) => {
      if (style && style.startsWith("FONT_SIZE_")) {
        const size = parseInt(style.replace("FONT_SIZE_", ""), 10);
        if (!isNaN(size)) {
          active = getSizeOption(size);
        }
      }
    });
    return active;
  }

  function removeAllFontSizes(state) {
    let newState = state;
    const currentStyles = state.getCurrentInlineStyle();
    currentStyles.forEach((style) => {
      if (style && style.startsWith("FONT_SIZE_")) {
        newState = RichUtils.toggleInlineStyle(newState, style);
      }
    });
    return newState;
  }

  function saveSelection(getEditorState) {
    const selection = getEditorState().getSelection();
    if (selection && !selection.isCollapsed()) {
      savedSelection = selection;
    }
  }

  function applyFontSize(size, getEditorState, onChange) {
    const opt = getSizeOption(size);
    let currentEditorState = getEditorState();

    if (savedSelection && !savedSelection.isCollapsed()) {
      currentEditorState = EditorState.forceSelection(currentEditorState, savedSelection);
    }

    let newState = removeAllFontSizes(currentEditorState);
    newState = RichUtils.toggleInlineStyle(newState, opt.type);
    onChange(newState);

    const dropdown = document.querySelector(".Draftail--font-size-dropdown");
    if (dropdown) dropdown.setAttribute("aria-expanded", "false");

    const input = document.querySelector(".Draftail--font-size-input");
    if (input) input.value = size.toString();
  }

  const FontSizeControl = ({ getEditorState, onChange }) => {
    const editorState = getEditorState();
    const active = getActiveSize(editorState);

    const dropdown = React.createElement(
      "div",
      { className: "Draftail--font-size-dropdown" },
      [
        React.createElement(
          "div",
          { key: "input-wrapper", className: "Draftail--font-size-input-wrapper" },
          React.createElement("input", {
            type: "text",
            className: "Draftail--font-size-input",
            defaultValue: active ? active.size.toString() : "",
            onFocus: () => saveSelection(getEditorState),
            onKeyDown: (e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                const size = parseInt(e.target.value, 10);
                if (size > 0 && size <= 400) {
                  applyFontSize(size, getEditorState, onChange);
                }
              } else if (e.key === "Escape") {
                const dd = document.querySelector(".Draftail--font-size-dropdown");
                if (dd) dd.setAttribute("aria-expanded", "false");
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                const current = parseInt(e.target.value, 10) || 12;
                e.target.value = Math.min(400, current + 1).toString();
              } else if (e.key === "ArrowDown") {
                e.preventDefault();
                const current = parseInt(e.target.value, 10) || 12;
                e.target.value = Math.max(1, current - 1).toString();
              }
            },
            onChange: (e) => {
              e.target.value = e.target.value.replace(/[^0-9]/g, "");
            },
            placeholder: "Size",
            "aria-label": "Custom font size",
          }),
        ),
        React.createElement(
          "ul",
          { key: "presets", className: "Draftail--font-size-presets" },
          presetOptions.map((opt) =>
            React.createElement(
              "li",
              {
                key: opt.label,
                onClick: () => applyFontSize(opt.size, getEditorState, onChange),
                className: "Draftail--font-size-option",
                "aria-selected": active && active.type === opt.type,
              },
              opt.label,
            ),
          ),
        ),
      ],
    );

    const icon = React.createElement(
      "span",
      { className: "Draftail--font-size-icon", title: "Font Size" },
      active ? active.size : "—",
    );

    const button = React.createElement(ToolbarButton, {
      onClick: () => {
        saveSelection(getEditorState);
        const el = document.querySelector(".Draftail--font-size-dropdown");
        if (el) {
          const isExpanded = el.getAttribute("aria-expanded") === "true";
          el.setAttribute("aria-expanded", !isExpanded);
        }
      },
      icon: icon,
    });

    return React.createElement(
      Tooltip,
      { content: active ? `${active.size}px` : "Font Size" },
      React.createElement(
        "div",
        { className: "Draftail--font-size-control" },
        dropdown,
        button,
      ),
    );
  };

  window.draftail.registerPlugin(
    { type: "font-size", inline: FontSizeControl },
    "controls",
  );
})();
