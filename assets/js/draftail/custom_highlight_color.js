/**
 * Custom highlight color entity for Draftail.
 * Registers an entity type (CUSTOM_HIGHLIGHT_COLOR) that stores an arbitrary color value.
 * The entity is applied by the highlight_color.js control when a custom color is picked.
 */
(function () {
  const React = window.React;

  // Decorator: renders the entity's highlighted text inline in the editor
  const HighlightColorDecorator = ({ children, contentState, entityKey }) => {
    const entity = contentState.getEntity(entityKey);
    const { color } = entity.getData();
    return React.createElement("span", { style: { backgroundColor: color } }, children);
  };

  // Source: immediately closes (the control handles the UI)
  const HighlightColorSource = ({ onClose }) => {
    onClose();
    return null;
  };

  window.draftail.registerPlugin(
    {
      type: "CUSTOM_HIGHLIGHT_COLOR",
      source: HighlightColorSource,
      decorator: HighlightColorDecorator,
      attributes: ["color"],
    },
    "entityTypes",
  );
})();
