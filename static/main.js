const add_time_button = document.getElementById("add_time");

if (add_time_button) {
    add_time_button.addEventListener('click', function() {
    const timeInputs = document.querySelectorAll('input[name^="time_of_day"]');
    const lastInput = timeInputs[timeInputs.length - 1];
    const newInput = lastInput.cloneNode(true);
    newInput.value = '';
    const nextIndex = timeInputs.length;
    newInput.name = `time_of_day-${nextIndex}`;
    newInput.id = '';
    lastInput.after(newInput);
});
}