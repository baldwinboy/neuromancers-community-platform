(function () {
  const React = window.React;
  const { RichUtils, EditorState, Modifier } = window.DraftJS;
  const { ToolbarButton, Tooltip } = window.Draftail;

  const predefinedColors = window.customTextColors || [];

  let savedSelection = null;

  function getActiveColor(editorState) {
    let active = null;
    const currentStyle = editorState.getCurrentInlineStyle();
    currentStyle.forEach((style) => {
      if (style && style.startsWith("TEXT_COLOR_")) {
        const predefined = predefinedColors.find((c) => c.type === style);
        if (predefined) {
          active = predefined;
        }
      }
    });

    // Check for custom color entity
    if (!active) {
      const selection = editorState.getSelection();
      const contentState = editorState.getCurrentContent();
      const startKey = selection.getStartKey();
      const startOffset = selection.getStartOffset();
      const block = contentState.getBlockForKey(startKey);
      const entityKey = block.getEntityAt(startOffset);
      if (entityKey) {
        const entity = contentState.getEntity(entityKey);
        if (entity.getType() === "CUSTOM_TEXT_COLOR") {
          const data = entity.getData();
          active = { type: "CUSTOM_TEXT_COLOR", label: data.color, value: data.color, key: "custom" };
        }
      }
    }

    return active;
  }

  function removeAllTextColors(state) {
    let newState = state;
    const currentStyles = state.getCurrentInlineStyle();
    currentStyles.forEach((style) => {
      if (style && style.startsWith("TEXT_COLOR_")) {
        newState = RichUtils.toggleInlineStyle(newState, style);
      }
    });
    return newState;
  }

  function removeCustomColorEntity(editorState) {
    const selection = editorState.getSelection();
    if (selection.isCollapsed()) return editorState;
    const contentState = Modifier.applyEntity(editorState.getCurrentContent(), selection, null);
    return EditorState.push(editorState, contentState, "apply-entity");
  }

  function saveSelection(getEditorState) {
    const selection = getEditorState().getSelection();
    if (selection && !selection.isCollapsed()) {
      savedSelection = selection;
    }
  }

  function restoreSelection(editorState) {
    if (savedSelection && !savedSelection.isCollapsed()) {
      return EditorState.forceSelection(editorState, savedSelection);
    }
    return editorState;
  }

  function applyTextColor(color, getEditorState, onChange) {
    let currentEditorState = restoreSelection(getEditorState());

    // Remove any existing custom color entity + inline styles
    currentEditorState = removeCustomColorEntity(currentEditorState);
    let newState = removeAllTextColors(currentEditorState);
    newState = RichUtils.toggleInlineStyle(newState, color.type);
    onChange(newState);

    const dropdown = document.querySelector(".Draftail--text-color-control .Draftail--color-dropdown");
    if (dropdown) dropdown.setAttribute("aria-expanded", "false");
  }

  function applyCustomTextColor(colorValue, getEditorState, onChange) {
    let currentEditorState = restoreSelection(getEditorState());

    // Remove any existing inline style colors
    currentEditorState = removeAllTextColors(currentEditorState);

    // Create an entity for the custom color
    const selection = currentEditorState.getSelection();
    if (selection.isCollapsed()) return;

    const contentState = currentEditorState.getCurrentContent();
    const contentWithEntity = contentState.createEntity("CUSTOM_TEXT_COLOR", "MUTABLE", { color: colorValue });
    const entityKey = contentWithEntity.getLastCreatedEntityKey();
    const newContent = Modifier.applyEntity(contentWithEntity, selection, entityKey);
    const newState = EditorState.push(currentEditorState, newContent, "apply-entity");
    onChange(newState);

    const dropdown = document.querySelector(".Draftail--text-color-control .Draftail--color-dropdown");
    if (dropdown) dropdown.setAttribute("aria-expanded", "false");
  }

  function removeColor(getEditorState, onChange) {
    let currentEditorState = restoreSelection(getEditorState());
    currentEditorState = removeCustomColorEntity(currentEditorState);
    const newState = removeAllTextColors(currentEditorState);
    onChange(newState);

    const dropdown = document.querySelector(".Draftail--text-color-control .Draftail--color-dropdown");
    if (dropdown) dropdown.setAttribute("aria-expanded", "false");
  }

  const TextColorControl = ({ getEditorState, onChange }) => {
    const editorState = getEditorState();
    const active = getActiveColor(editorState);

    const dropdown = React.createElement(
      "div",
      { className: "Draftail--color-dropdown" },
      [
        React.createElement(
          "div",
          { key: "presets", className: "Draftail--color-grid" },
          predefinedColors.map((color) =>
            React.createElement("button", {
              key: color.type,
              type: "button",
              className: `Draftail--color-swatch${active && active.type === color.type ? " selected" : ""}`,
              style: {
                backgroundColor: color.value,
                ...(color.value === "transparent"
                  ? {
                      backgroundImage:
                        "linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)",
                      backgroundSize: "8px 8px",
                      backgroundPosition: "0 0, 0 4px, 4px -4px, -4px 0px",
                    }
                  : {}),
              },
              onClick: () => applyTextColor(color, getEditorState, onChange),
              title: color.label,
              "aria-label": color.label,
            }),
          ),
        ),
        React.createElement(
          "div",
          { key: "custom", className: "Draftail--color-custom" },
          [
            React.createElement("input", {
              key: "picker",
              type: "color",
              className: "Draftail--color-picker-input",
              defaultValue: active && active.key === "custom" ? active.value : "#000000",
              onFocus: () => saveSelection(getEditorState),
              title: "Pick custom color",
            }),
            React.createElement(
              "button",
              {
                key: "apply",
                type: "button",
                className: "Draftail--color-apply-btn",
                onClick: () => {
                  const picker = document.querySelector(".Draftail--text-color-control .Draftail--color-picker-input");
                  if (picker && picker.value) {
                    applyCustomTextColor(picker.value, getEditorState, onChange);
                  }
                },
              },
              "Apply",
            ),
          ],
        ),
        React.createElement(
          "button",
          {
            key: "remove",
            type: "button",
            className: "Draftail--color-remove-btn",
            onClick: () => removeColor(getEditorState, onChange),
          },
          "Remove Color",
        ),
      ],
    );

    const icon = React.createElement(
      "span",
      { className: "Draftail--text-color-icon", title: "Text Color" },
      [
        React.createElement("span", { key: "letter", className: "Draftail--text-color-letter" }, "A"),
        React.createElement("span", {
          key: "bar",
          className: "Draftail--text-color-bar",
          style: { backgroundColor: active ? active.value : "currentColor" },
        }),
      ],
    );

    const button = React.createElement(ToolbarButton, {
      onClick: () => {
        saveSelection(getEditorState);
        const el = document.querySelector(".Draftail--text-color-control .Draftail--color-dropdown");
        if (el) {
          const isExpanded = el.getAttribute("aria-expanded") === "true";
          el.setAttribute("aria-expanded", !isExpanded);
        }
      },
      icon: icon,
    });

    return React.createElement(
      Tooltip,
      { content: active ? `Text: ${active.label}` : "Text Color" },
      React.createElement(
        "div",
        { className: "Draftail--text-color-control" },
        dropdown,
        button,
      ),
    );
  };

  window.draftail.registerPlugin(
    { type: "text-color", inline: TextColorControl },
    "controls",
  );
})();

