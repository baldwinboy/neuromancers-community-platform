function createTimeOption(value, label, interval, targetStartEl, targetEndEl) {
    const dateValue = `${value}:00.000+00:00`;
    const input = document.createElement('input');
    const labelEl = document.createElement('label');
    input.id = value;
    input.name = "_";
    input.value = dateValue;
    input.type = "radio";
    input.onchange = () => { 
        try {
            // Should be in minutes
            const durations = JSON.parse(document.getElementById('request_calendar_durations').textContent);
            const startDate = new Date(dateValue);
            const endDate = new Date(startDate.getTime() + interval * 60000);
            const endDateValue = `${endDate.toISOString().split(':00.000Z')[0]}:00.000+00:00`;
            const intervalInput = document.getElementById('id_request_calendar_durations');
            const output = document.getElementById('id_request_calendar_durations_time');

            output.dataset.duration = interval;
            intervalInput.stepDown(durations.length - 1);
            output.innerHTML = interval;

            targetStartEl.value = dateValue;
            targetEndEl.value = endDateValue;
        } catch {
            // noop
        }
    };
    labelEl.className = "request_calendar_active_date_time_option";
    labelEl.textContent = label;
    labelEl.appendChild(input);
    labelEl.tabIndex = 0;
    return labelEl;
}

var chooseDuration = (input) => {
    const durations = JSON.parse(document.getElementById('request_calendar_durations').textContent);
    const output = document.getElementById('id_request_calendar_durations_time');
    const startsAtInput = document.getElementById(input.dataset.startId);
    const endsAtInput = document.getElementById(input.dataset.endId);

    try {
        if (durations && output && startsAtInput && endsAtInput) {
            const interval = durations[input.value];

            if (startsAtInput.value) {
                const startDate = new Date(startsAtInput.value);
                const endDate = new Date(startDate.getTime() + interval * 60000);
                endsAtInput.value = endDate.toISOString().split(':00.000Z')[0];
                endsAtInput.value = `${endsAtInput.value}:00.000+00:00`;
            }

            output.dataset.duration = interval;
            output.innerHTML = interval;
        }
    } catch (error) {
        // noop
    }
}

var setCurrentDateTimes = (button) => {
    if (button.classList.contains('request_calendar__grid_date_selected')) return;

    // Clear all other selected date classes
    document.querySelectorAll('.request_calendar__grid_date_selected').forEach(el => el.classList.remove('request_calendar__grid_date_selected'));
    button.classList.add('request_calendar__grid_date_selected');

    const targetId = button.getAttribute("aria-controls");
    const target = document.getElementById(targetId);
    const targetSelectEl = target.querySelector('fieldset');
    const startsAtInput = document.getElementById(button.dataset.startId);
    const endsAtInput = document.getElementById(button.dataset.endId);

    // Should be in minutes
    const durations = JSON.parse(document.getElementById('request_calendar_durations').textContent);
    const active_date_times = JSON.parse(document.getElementById('request_calendar_active_date_times').textContent);
    const date = button.dataset.date;

    try {
        if (durations && active_date_times && date && target && targetSelectEl && startsAtInput) {
            const dateTimes = active_date_times[date];
            const currentDate = new Date(date);
            const interval = Math.min(...durations);
            const [startDate, endDate] = dateTimes.map(([hour, minute]) => {
                const time = new Date(currentDate);
                time.setUTCHours(hour, minute, 0, 0);
                time.toISOString();
                return time;
            });

            let timeOptions = [];
            let current = new Date(startDate);

            while (current < endDate) {
                const iso = current.toISOString().split(':00.000Z')[0];
                timeOptions.push(createTimeOption(iso, `${iso.split('T')[1]} UTC`, interval, startsAtInput, endsAtInput));
                current.setUTCMinutes(current.getUTCMinutes() + interval);
            }
            targetSelectEl.replaceChildren(...timeOptions);
            target.classList.remove('hidden');
            targetSelectEl.focus();
        }
    } catch (error) {
        // noop
    }
}
