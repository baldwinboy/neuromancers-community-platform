/**
 * Custom text color entity for Draftail.
 * Registers an entity type (CUSTOM_TEXT_COLOR) that stores an arbitrary color value.
 * The entity is applied by the text_color.js control when a custom color is picked.
 */
(function () {
  const React = window.React;

  // Decorator: renders the entity's colored text inline in the editor
  const TextColorDecorator = ({ children, contentState, entityKey }) => {
    const entity = contentState.getEntity(entityKey);
    const { color } = entity.getData();
    return React.createElement("span", { style: { color: color } }, children);
  };

  // Source: immediately closes (the control handles the UI)
  const TextColorSource = ({ onClose }) => {
    onClose();
    return null;
  };

  window.draftail.registerPlugin(
    {
      type: "CUSTOM_TEXT_COLOR",
      source: TextColorSource,
      decorator: TextColorDecorator,
      attributes: ["color"],
    },
    "entityTypes",
  );
})();
