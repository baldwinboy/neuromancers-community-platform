/**
 * Emoji Picker Widget for Wagtail Admin
 * Vanilla JS implementation - no React/Vue/etc required
 */

(function() {
    'use strict';

    class EmojiPicker {
        constructor(wrapper) {
            this.wrapper = wrapper;
            this.valueInput = wrapper.querySelector('[data-emoji-value]');
            this.trigger = wrapper.querySelector('[data-emoji-trigger]');
            this.display = wrapper.querySelector('[data-emoji-display]');
            this.clearBtn = wrapper.querySelector('[data-emoji-clear]');
            this.panel = wrapper.querySelector('[data-emoji-panel]');
            this.searchInput = wrapper.querySelector('[data-emoji-search]');
            this.tabs = wrapper.querySelectorAll('[data-emoji-tab]');
            this.categories = wrapper.querySelectorAll('[data-emoji-category]');
            this.searchResults = wrapper.querySelector('[data-emoji-results]');
            this.resultsGrid = wrapper.querySelector('[data-emoji-results-grid]');
            this.noResults = wrapper.querySelector('.emoji-picker-no-results');

            // Parse emoji data
            const dataScript = wrapper.querySelector('[data-emoji-data]');
            this.emojiData = dataScript ? JSON.parse(dataScript.textContent) : {};

            this.isOpen = false;
            this.bindEvents();
        }

        bindEvents() {
            // Toggle panel on trigger click
            this.trigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggle();
            });

            // Clear button
            if (this.clearBtn) {
                this.clearBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.clear();
                });
            }

            // Tab switching
            this.tabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.switchTab(tab.dataset.emojiTab);
                });
            });

            // Emoji selection (using event delegation)
            this.panel.addEventListener('click', (e) => {
                const emojiBtn = e.target.closest('[data-emoji]');
                if (emojiBtn) {
                    e.preventDefault();
                    this.selectEmoji(emojiBtn.dataset.emoji);
                }
            });

            // Search functionality
            if (this.searchInput) {
                this.searchInput.addEventListener('input', () => {
                    this.search(this.searchInput.value);
                });
            }

            // Close on outside click
            document.addEventListener('click', (e) => {
                if (this.isOpen && !this.wrapper.contains(e.target)) {
                    this.close();
                }
            });

            // Close on Escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.close();
                }
            });
        }

        toggle() {
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        }

        open() {
            this.panel.hidden = false;
            this.isOpen = true;
            this.trigger.setAttribute('aria-expanded', 'true');

            // Focus search input
            if (this.searchInput) {
                setTimeout(() => this.searchInput.focus(), 50);
            }
        }

        close() {
            this.panel.hidden = true;
            this.isOpen = false;
            this.trigger.setAttribute('aria-expanded', 'false');

            // Clear search
            if (this.searchInput) {
                this.searchInput.value = '';
                this.search('');
            }
        }

        selectEmoji(emoji) {
            this.valueInput.value = emoji;
            this.display.innerHTML = emoji;
            this.display.classList.remove('emoji-picker-placeholder');

            if (this.clearBtn) {
                this.clearBtn.style.display = '';
            }

            // Trigger change event for form handling
            this.valueInput.dispatchEvent(new Event('change', { bubbles: true }));

            this.close();
        }

        clear() {
            this.valueInput.value = '';
            this.display.innerHTML = '<span class="emoji-picker-placeholder">Click to select emoji</span>';

            if (this.clearBtn) {
                this.clearBtn.style.display = 'none';
            }

            // Trigger change event
            this.valueInput.dispatchEvent(new Event('change', { bubbles: true }));
        }

        switchTab(categoryKey) {
            // Update tab states
            this.tabs.forEach(tab => {
                const isActive = tab.dataset.emojiTab === categoryKey;
                tab.classList.toggle('active', isActive);
                tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });

            // Update category visibility
            this.categories.forEach(cat => {
                cat.classList.toggle('active', cat.dataset.emojiCategory === categoryKey);
            });

            // Hide search results when switching tabs
            if (this.searchResults) {
                this.searchResults.hidden = true;
            }
            this.categories.forEach(cat => {
                if (cat.dataset.emojiCategory === categoryKey) {
                    cat.classList.add('active');
                }
            });
        }

        search(query) {
            query = query.toLowerCase().trim();

            if (!query) {
                // Show categories, hide search results
                this.searchResults.hidden = true;
                this.categories.forEach(cat => cat.style.display = '');
                // Restore active category
                const activeTab = this.wrapper.querySelector('[data-emoji-tab].active');
                if (activeTab) {
                    this.switchTab(activeTab.dataset.emojiTab);
                }
                return;
            }

            // Hide all categories, show search results
            this.categories.forEach(cat => cat.style.display = 'none');
            this.searchResults.hidden = false;

            // Search through all emojis
            const matches = [];
            for (const [catKey, category] of Object.entries(this.emojiData)) {
                for (const item of category.emojis) {
                    const nameMatch = item.name.toLowerCase().includes(query);
                    const keywordMatch = item.keywords.some(kw => kw.includes(query));
                    if (nameMatch || keywordMatch) {
                        matches.push(item);
                    }
                }
            }

            // Render results
            this.resultsGrid.innerHTML = '';
            if (matches.length === 0) {
                this.noResults.hidden = false;
            } else {
                this.noResults.hidden = true;
                matches.slice(0, 50).forEach(item => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'emoji-picker-emoji';
                    btn.dataset.emoji = item.emoji;
                    btn.title = item.name;
                    btn.setAttribute('aria-label', item.name);
                    btn.textContent = item.emoji;
                    this.resultsGrid.appendChild(btn);
                });
            }
        }
    }

    // Initialize all emoji pickers on page load
    function initEmojiPickers() {
        document.querySelectorAll('[data-emoji-picker]').forEach(wrapper => {
            if (!wrapper._emojiPickerInit) {
                new EmojiPicker(wrapper);
                wrapper._emojiPickerInit = true;
            }
        });
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEmojiPickers);
    } else {
        initEmojiPickers();
    }

    // Re-initialize when Wagtail adds new blocks dynamically
    // Wagtail uses a MutationObserver pattern for StreamField blocks
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.addedNodes.length) {
                initEmojiPickers();
            }
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Export for manual initialization if needed
    window.EmojiPicker = EmojiPicker;
    window.initEmojiPickers = initEmojiPickers;
})();
