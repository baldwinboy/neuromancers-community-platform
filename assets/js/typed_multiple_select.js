const initializedInputs = new WeakSet();

const createSelectedButton = (callback, textContent, title) => {
    const selectedButton = document.createElement('button');
    selectedButton.className = "typed_select_multiple__selected_button";
    selectedButton.type = "button";
    selectedButton.onclick = () => callback(selectedButton);
    selectedButton.textContent = textContent;
    selectedButton.title = title;
    return selectedButton;
}

var toggleSelectedOptions = (button) => {
    const selectName = button.dataset.selectName;
    const outputId = button.dataset.outputId;
    const value = button.dataset.value;
    const select = document.querySelector(`select[name="${selectName}"]`);
    const selected = document.getElementById(outputId);
    if (!(select && selected)) {
        return;
    }

    const option = select.querySelector(`option[value="${value}"]`);

    if (option.selected) {
        option.removeAttribute('selected');
    } else {
        option.setAttribute('selected', 'true');
    }

    selected.replaceChildren();

    Array.from(select.querySelectorAll('option[selected]')).map(opt => {
        const _button = createSelectedButton(toggleSelectedOptions, opt.textContent, select.dataset.removeTitle);
        const dropdown = button.closest(".typed_select_multiple__options_group");
        _button.dataset.selectName = select.name;
        _button.dataset.outputId = selected.id;
        _button.dataset.value = opt.value;
        if (dropdown && !dropdown.classList.contains("hidden")) dropdown.classList.add("hidden");
        selected.appendChild(_button);
    });
}

const searchInput = (event, groups) => {
    const search = event.target.value;
    console.log(search);

    // Find value in groups
    groups.forEach((group) => {
        if (!search) {
            group.classList.add('hidden');
            group.querySelectorAll('li').forEach(item => item.classList.add('hidden'));
            return;
        }

        const matchingElements = group.querySelectorAll(`li[data-label*="${search}"]`);
        if (matchingElements.length) {
            const matchingArr = Array.from(matchingElements)
            group.classList.remove('hidden');
            group.querySelectorAll('li').forEach(checkItem => checkItem.classList.toggle('hidden', !matchingArr.some(item => item.id === checkItem.id)));
        } else {
            group.classList.add('hidden');
            group.querySelectorAll('li').forEach(item => item.classList.add('hidden'));
        }
    });
}

const inputKeySelect = (event, groups) => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        try {
            groups.forEach((group) => {
                if (group.classList.contains('hidden')) return;

                const visibleItems = Array.from(group.querySelectorAll('li:not(.hidden)'));
                if (visibleItems.length > 0) {
                    const firstButton = visibleItems[0].querySelector('button');
                    if (firstButton) {
                        firstButton.click(); // Trigger selection
                        group.classList.add("hidden");
                    }
                    throw new Error("Match found")
                }
            });
        } catch {
            // noop
        }
        return;
    }

    searchInput(event, groups);
}

const renderSelectedButtons = (wrapperEl) => {
    const select = wrapperEl.querySelector('select');
    const selected = wrapperEl.querySelector('.typed_select_multiple__selected');
    if (!(select && selected)) return;

    selected.replaceChildren();

    Array.from(select.querySelectorAll('option[selected]')).forEach(opt => {
        const button = createSelectedButton(toggleSelectedOptions, opt.textContent, select.dataset.removeTitle);
        button.dataset.selectName = select.name;
        button.dataset.outputId = selected.id;
        button.dataset.value = opt.value;
        selected.appendChild(button);
    });
}

const initializeInput = (inputEl) => {
    if (initializedInputs.has(inputEl)) return;
    initializedInputs.add(inputEl);

    const wrapperEl = inputEl.parentElement;
    const groups = wrapperEl.querySelectorAll('.typed_select_multiple__options_group');

    renderSelectedButtons(wrapperEl);

    inputEl.addEventListener("input", (event) => {
        searchInput(event, groups);
        renderSelectedButtons(wrapperEl);
    }, { passive: true });

    inputEl.addEventListener("keyup", (event) => inputKeySelect(event, groups));
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-id="typed_select_multiple__input"]').forEach(inputEl => {
        initializeInput(inputEl);
    });
});

document.addEventListener('input', function(event) {
    const inputEl = event.target;
    if (!inputEl.matches('[data-id="typed_select_multiple__input"]')) return;

    initializeInput(inputEl);
});