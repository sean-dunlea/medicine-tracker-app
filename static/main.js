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

// For getting the user's timezone (to send push notifications)
let timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

fetch("set_timezone", {
    method: "POST",
    headers: {
    "Content-Type": "application/json",
    },
    body: JSON.stringify({ timezone }),
});

// This is for testing email notifications. It's only temporary for testing purposes.
let test_email_notification_button = document.getElementById("test_email_notification")
if (test_email_notification_button) {
        test_email_notification_button.addEventListener("click", async () => {
            try {
                const response = await fetch("/test_email_notification", {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json"
                    }
                });
                if (response.ok) {
                    console.log("Test email sent")
                } else {
                    console.log("Failed to send email")
            }
        } catch (error) {
            console.error("Error:", error);
        }
    });
}

// This is needed for autocompleting medication names in the add_medication form
let medication_name_field = document.getElementById("medication_name_field");
let suggested_medication_names_list = document.getElementById("suggested_medication_names_list");
if (medication_name_field) {
    medication_name_field.addEventListener("input", async () => {
        let query = medication_name_field.value;

        // This clears suggested medication names if the query is less than 2 characters
        if (query.length < 2) {
            suggested_medication_names_list.innerHTML = "";
            return;
        }

        try {
            let response = await fetch(`/query_medications?q=${encodeURIComponent(query)}`);
            let data = await response.json();
            
            suggested_medication_names_list.innerHTML = "";
            
            data.forEach(item => {
                let li = document.createElement("li");
                li.textContent = item.name;
                li.onclick = () => {
                    medication_name_field.value = item.name;
                    suggested_medication_names_list.innerHTML = "";
                }
                suggested_medication_names_list.appendChild(li);
            })

        } catch (error) {
            console.error("Error fetching medication suggestions:", error);
        }
    })
}