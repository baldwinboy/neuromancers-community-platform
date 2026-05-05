(function () {
  const React = window.React;
  const { RichUtils } = window.DraftJS;
  const { ToolbarButton, Tooltip } = window.Draftail;

  const options = window.customFontFamilies || [];
  const customStyleMap = window.customFontStyleMap;

  const FontFamilyControl = ({ getEditorState, onChange }) => {
    const editorState = getEditorState();
    const currentStyle = editorState.getCurrentInlineStyle();
    // Determine active font
    const active = options.find((opt) => {
      return currentStyle.has(opt.type);
    });

    function applyFont(optType) {
      let newState = editorState;

      // Remove all font styles first
      options.forEach((opt) => {
        if (currentStyle.has(opt.type)) {
          newState = RichUtils.toggleInlineStyle(newState, opt.type);
        }
      });

      // Apply selected one
      newState = RichUtils.toggleInlineStyle(newState, optType);

      onChange(newState);

      const el = document.querySelector(".Draftail--font-family-dropdown");
      if (el) {
        el.setAttribute("aria-expanded", false);
      }
    }

    function handleOptionClick(opt) {
      applyFont(opt.type);
    }

    const dropdown = React.createElement(
      "ul",
      { className: "Draftail--font-family-dropdown" },
      options.map((opt) =>
        React.createElement(
          "li",
          {
            key: opt.label,
            onClick: () => handleOptionClick(opt),
            style: { fontFamily: opt.style.fontFamily },
            className: "Draftail--font-family-dropdown-option",
            "aria-selected": active && active.type === opt.type,
          },
          opt.label,
        ),
      ),
    );

    const icon = React.createElement("span", {
      className: "bi bi-fonts",
      title: "Font Family",
      style: {
        fontSize: "1.5rem",
        marginBlockStart: "0.2rem",
      },
    });

    const button = React.createElement(ToolbarButton, {
      onClick: () => {
        const el = document.querySelector(".Draftail--font-family-dropdown");
        if (el) {
          const isExpanded = el.getAttribute("aria-expanded") === "true";
          el.setAttribute("aria-expanded", !isExpanded);
        }
      },
      icon: icon,
    });

    return React.createElement(
      Tooltip,
      { content: active ? active.label : "Font Family" },
      React.createElement(
        "div",
        {
          className: "Draftail--font-family-control",
        },
        dropdown,
        button,
      ),
    );
  };

  window.draftail.registerPlugin(
    {
      type: "font-family",
      inline: FontFamilyControl,
    },
    "controls",
  );
})();
