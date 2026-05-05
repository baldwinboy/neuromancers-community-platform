/**
 * Color Picker Widget JavaScript
 * Handles dropdown toggle, color selection, and custom color input
 */

(function() {
    'use strict';

    function initColorPicker(container) {
        const valueInput = container.querySelector('.color-picker-value');
        const preview = container.querySelector('[data-preview]');
        const label = container.querySelector('[data-label]');
        const toggle = container.querySelector('[data-toggle]');
        const dropdown = container.querySelector('[data-dropdown]');
        const swatches = container.querySelectorAll('.color-picker-swatch');
        const customColorInput = container.querySelector('[data-custom-color]');
        const customTextInput = container.querySelector('[data-custom-text]');
        const applyButton = container.querySelector('[data-apply]');

        if (!valueInput || !dropdown) return;

        // Track if picker is open
        let isOpen = false;

        // Toggle dropdown
        function toggleDropdown(show) {
            isOpen = typeof show === 'boolean' ? show : !isOpen;
            dropdown.hidden = !isOpen;
            toggle.setAttribute('aria-expanded', isOpen);
        }

        // Update the display and value
        function selectColor(value, colorValue, labelText) {
            valueInput.value = value;
            preview.style.backgroundColor = colorValue || value;
            label.textContent = labelText || value;
            
            // Update selected state on swatches
            swatches.forEach(swatch => {
                const isSelected = swatch.dataset.value === value;
                swatch.classList.toggle('selected', isSelected);
                swatch.innerHTML = isSelected 
                    ? '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" style="filter: drop-shadow(0 0 1px rgba(0,0,0,0.5));"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>'
                    : '';
            });
            
            // Dispatch change event
            valueInput.dispatchEvent(new Event('change', { bubbles: true }));
            
            toggleDropdown(false);
        }

        // Event: Toggle button click
        container.querySelector('.color-picker-display').addEventListener('click', (e) => {
            e.preventDefault();
            toggleDropdown();
        });

        // Event: Swatch click
        swatches.forEach(swatch => {
            swatch.addEventListener('click', (e) => {
                e.preventDefault();
                const value = swatch.dataset.value;
                const colorValue = swatch.dataset.color;
                const labelText = swatch.getAttribute('title');
                selectColor(value, colorValue, labelText);
            });
        });

        // Event: Custom color input change
        if (customColorInput) {
            customColorInput.addEventListener('input', () => {
                customTextInput.value = customColorInput.value;
            });
        }

        // Event: Apply custom color
        if (applyButton) {
            applyButton.addEventListener('click', (e) => {
                e.preventDefault();
                const customValue = customTextInput.value.trim();
                if (customValue) {
                    selectColor(customValue, customValue, 'Custom: ' + customValue);
                }
            });
        }

        // Event: Custom text input enter key
        if (customTextInput) {
            customTextInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    applyButton.click();
                }
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (isOpen && !container.contains(e.target)) {
                toggleDropdown(false);
            }
        });

        // Close dropdown on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isOpen) {
                toggleDropdown(false);
            }
        });

        // Keyboard navigation for swatches
        dropdown.addEventListener('keydown', (e) => {
            if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) return;
            
            e.preventDefault();
            const focusedSwatch = document.activeElement;
            if (!focusedSwatch.classList.contains('color-picker-swatch')) return;
            
            const swatchArray = Array.from(swatches);
            const currentIndex = swatchArray.indexOf(focusedSwatch);
            let nextIndex;
            
            // Calculate grid columns (approximate)
            const containerWidth = dropdown.querySelector('.color-picker-grid').offsetWidth;
            const swatchWidth = swatches[0].offsetWidth + 6; // Include gap
            const columns = Math.floor(containerWidth / swatchWidth);
            
            switch (e.key) {
                case 'ArrowRight':
                    nextIndex = Math.min(currentIndex + 1, swatchArray.length - 1);
                    break;
                case 'ArrowLeft':
                    nextIndex = Math.max(currentIndex - 1, 0);
                    break;
                case 'ArrowDown':
                    nextIndex = Math.min(currentIndex + columns, swatchArray.length - 1);
                    break;
                case 'ArrowUp':
                    nextIndex = Math.max(currentIndex - columns, 0);
                    break;
            }
            
            if (nextIndex !== undefined) {
                swatchArray[nextIndex].focus();
            }
        });
    }

    // Initialize all color pickers on page load
    function initAllColorPickers() {
        document.querySelectorAll('[data-color-picker]').forEach(initColorPicker);
    }

    // Handle dynamic content (Wagtail StreamField)
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const pickers = node.querySelectorAll 
                            ? node.querySelectorAll('[data-color-picker]') 
                            : [];
                        pickers.forEach(initColorPicker);
                        
                        if (node.matches && node.matches('[data-color-picker]')) {
                            initColorPicker(node);
                        }
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllColorPickers);
    } else {
        initAllColorPickers();
    }
})();
