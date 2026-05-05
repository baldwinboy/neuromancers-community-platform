(function () {
  const React = window.React;
  const { RichUtils, EditorState, Modifier } = window.DraftJS;
  const { ToolbarButton, Tooltip } = window.Draftail;

  const predefinedColors = window.customHighlightColors || [];

  let savedSelection = null;

  function getActiveColor(editorState) {
    let active = null;
    const currentStyle = editorState.getCurrentInlineStyle();
    currentStyle.forEach((style) => {
      if (style && style.startsWith("HIGHLIGHT_COLOR_")) {
        const predefined = predefinedColors.find((c) => c.type === style);
        if (predefined) {
          active = predefined;
        }
      }
    });

    // Check for custom highlight color entity
    if (!active) {
      const selection = editorState.getSelection();
      const contentState = editorState.getCurrentContent();
      const startKey = selection.getStartKey();
      const startOffset = selection.getStartOffset();
      const block = contentState.getBlockForKey(startKey);
      const entityKey = block.getEntityAt(startOffset);
      if (entityKey) {
        const entity = contentState.getEntity(entityKey);
        if (entity.getType() === "CUSTOM_HIGHLIGHT_COLOR") {
          const data = entity.getData();
          active = { type: "CUSTOM_HIGHLIGHT_COLOR", label: data.color, value: data.color, key: "custom" };
        }
      }
    }

    return active;
  }

  function removeAllHighlightColors(state) {
    let newState = state;
    const currentStyles = state.getCurrentInlineStyle();
    currentStyles.forEach((style) => {
      if (style && style.startsWith("HIGHLIGHT_COLOR_")) {
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

  function applyHighlightColor(color, getEditorState, onChange) {
    let currentEditorState = restoreSelection(getEditorState());

    // Remove any existing custom color entity + inline styles
    currentEditorState = removeCustomColorEntity(currentEditorState);
    let newState = removeAllHighlightColors(currentEditorState);
    newState = RichUtils.toggleInlineStyle(newState, color.type);
    onChange(newState);

    const dropdown = document.querySelector(".Draftail--highlight-color-control .Draftail--color-dropdown");
    if (dropdown) dropdown.setAttribute("aria-expanded", "false");
  }

  function applyCustomHighlightColor(colorValue, getEditorState, onChange) {
    let currentEditorState = restoreSelection(getEditorState());

    // Remove any existing inline style colors
    currentEditorState = removeAllHighlightColors(currentEditorState);

    // Create an entity for the custom color
    const selection = currentEditorState.getSelection();
    if (selection.isCollapsed()) return;

    const contentState = currentEditorState.getCurrentContent();
    const contentWithEntity = contentState.createEntity("CUSTOM_HIGHLIGHT_COLOR", "MUTABLE", { color: colorValue });
    const entityKey = contentWithEntity.getLastCreatedEntityKey();
    const newContent = Modifier.applyEntity(contentWithEntity, selection, entityKey);
    const newState = EditorState.push(currentEditorState, newContent, "apply-entity");
    onChange(newState);

    const dropdown = document.querySelector(".Draftail--highlight-color-control .Draftail--color-dropdown");
    if (dropdown) dropdown.setAttribute("aria-expanded", "false");
  }

  function removeColor(getEditorState, onChange) {
    let currentEditorState = restoreSelection(getEditorState());
    currentEditorState = removeCustomColorEntity(currentEditorState);
    const newState = removeAllHighlightColors(currentEditorState);
    onChange(newState);

    const dropdown = document.querySelector(".Draftail--highlight-color-control .Draftail--color-dropdown");
    if (dropdown) dropdown.setAttribute("aria-expanded", "false");
  }

  const HighlightColorControl = ({ getEditorState, onChange }) => {
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
              onClick: () => applyHighlightColor(color, getEditorState, onChange),
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
              defaultValue: active && active.key === "custom" ? active.value : "#ffff00",
              onFocus: () => saveSelection(getEditorState),
              title: "Pick custom highlight color",
            }),
            React.createElement(
              "button",
              {
                key: "apply",
                type: "button",
                className: "Draftail--color-apply-btn",
                onClick: () => {
                  const picker = document.querySelector(".Draftail--highlight-color-control .Draftail--color-picker-input");
                  if (picker && picker.value) {
                    applyCustomHighlightColor(picker.value, getEditorState, onChange);
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
          "Remove Highlight",
        ),
      ],
    );

    const icon = React.createElement(
      "span",
      {
        className: "Draftail--highlight-color-icon",
        title: "Highlight Color",
        style: { backgroundColor: active ? active.value : "transparent" },
      },
      React.createElement("span", { className: "bi bi-highlighter" }),
    );

    const button = React.createElement(ToolbarButton, {
      onClick: () => {
        saveSelection(getEditorState);
        const el = document.querySelector(".Draftail--highlight-color-control .Draftail--color-dropdown");
        if (el) {
          const isExpanded = el.getAttribute("aria-expanded") === "true";
          el.setAttribute("aria-expanded", !isExpanded);
        }
      },
      icon: icon,
    });

    return React.createElement(
      Tooltip,
      { content: active ? `Highlight: ${active.label}` : "Highlight Color" },
      React.createElement(
        "div",
        { className: "Draftail--highlight-color-control" },
        dropdown,
        button,
      ),
    );
  };

  window.draftail.registerPlugin(
    { type: "highlight-color", inline: HighlightColorControl },
    "controls",
  );
})();


