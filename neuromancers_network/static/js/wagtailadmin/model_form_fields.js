document.addEventListener('DOMContentLoaded', function() {
    const targetModelSelect = document.querySelector('#id_target_model');
    const modelFieldInputs = document.querySelectorAll('[data-model-field-input]');

    function updateFieldChoices() {
        const [appLabel, modelId] = targetModelSelect.value.split('.');
        if (!appLabel || !modelId) return;
        fetch(`/admin/api/model-form-fields/${appLabel}/${modelId}/`)
            .then(response => response.json())
            .then(fields => {
                modelFieldInputs.forEach(input => {
                    const select = document.createElement('select');
                    select.name = input.name;
                    select.innerHTML = '<option value="">---------</option>' +
                        fields.map(f => `<option value="${f}">${f}</option>`).join('');
                    input.parentNode.replaceChild(select, input);
                });
            });
    }
    targetModelSelect.addEventListener('change', updateFieldChoices);
});