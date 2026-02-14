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
