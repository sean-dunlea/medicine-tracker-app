let frequency_select = document.getElementById("frequency_type");

function update_fields() {
    if (!frequency_select) return;

    let frequency = frequency_select.value;

    // This shows/hides weekday inputs
    document.querySelectorAll(".weekday").forEach(field => {
        let label = document.querySelector(`label[for="${field.id}"]`);
        if (frequency === "weekly") {
            field.style.display = "inline-block";
            if (label) {
                label.style.display = "inline-block";
            }
        } else {
            field.style.display = "none";
            if (label) {
                label.style.display = "none";
            }
        }
    });

    // This shows/hides day_of_month inputs
    document.querySelectorAll(".day_of_month").forEach(field => {
        let label = document.querySelector(`label[for="${field.id}"]`);
        if (frequency === "monthly") {
            field.style.display = "inline-block";
            if (label) {
                label.style.display = "inline-block"
            }
        } else {
            field.style.display = "none";
            if (label) {
                label.style.display = "none"
            }
        }
    });
}

update_fields();

// This updates the field based on user's choice
if (frequency_select) {
    frequency_select.addEventListener("change", update_fields);
}

let add_time_button = document.getElementById("add_time");

if (add_time_button) {
    add_time_button.addEventListener("click", function () {

        let entries = document.querySelectorAll(".time_entry");
        let last_entry = entries[entries.length - 1];
        let new_entry = last_entry.cloneNode(true);
        let newIndex = entries.length;

        new_entry.querySelectorAll("input, select, label").forEach(element => {

            if (element.name) {
                element.name = element.name.replace(/time_entries-\d+-/, `time_entries-${newIndex}-`);
            }

            if (element.id) {
                element.id = element.id.replace(/time_entries-\d+-/, `time_entries-${newIndex}-`);
            }

            if (element.htmlFor) {
                element.htmlFor = element.htmlFor.replace(/time_entries-\d+-/, `time_entries-${newIndex}-`);
            }

            if (element.value) {
                element.value = "";
            }
        });

        last_entry.after(new_entry);

        update_fields();
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

const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");

if (menuToggle) {
  menuToggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });
}