import { initializeApp } from "https://www.gstatic.com/firebasejs/12.8.0/firebase-app.js";
import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/12.8.0/firebase-messaging.js";

const firebaseConfig = {
    apiKey: "AIzaSyAyvB0QXuTqKpcft1PTkLs8JLojunIUz2s",
    authDomain: "medicine-tracker-app-7cfe4.firebaseapp.com",
    projectId: "medicine-tracker-app-7cfe4",
    storageBucket: "medicine-tracker-app-7cfe4.firebasestorage.app",
    messagingSenderId: "259878242247",
    appId: "1:259878242247:web:a6797dc7d90deed322bbe2"
  };

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Cloud Messaging and get a reference to the service
const messaging = getMessaging(app);

async function syncFcmToken() {
    try {
        const registration =
            await navigator.serviceWorker.getRegistration("/static/firebase-messaging-sw.js")
            || await navigator.serviceWorker.register("/static/firebase-messaging-sw.js");

        const currentToken = await getToken(messaging, {
            vapidKey: "BEsK6dC7_GO_iZ2wtVLQouKCC0RgS2cuMKNWHBOUlk_4vlq1OBDTXb1FqWNOBH4TYBE8sZZpSCwzkYhy6WKIU5I",
            serviceWorkerRegistration: registration
        });

        if (!currentToken) {
            console.log("No registration token available.");
            return;
        }

        console.log("FCM Token:", currentToken);

        const response = await fetch("/save_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: currentToken })
        });

        if (response.ok) {
            console.log("Token sent to server successfully");
        } else {
            console.error("Failed to send token to server");
        }

    } catch (err) {
        console.log("An error occurred while retrieving token.", err);
    }
}

const enable_notifications_button = document.getElementById("enable_notifications");

if (enable_notifications_button) {
    enable_notifications_button.addEventListener("click", async () => {
        console.log("Requesting permission...");
        const permission = await Notification.requestPermission();

        if (permission === "granted") {
            console.log("Notification permission granted.");
            alert("Notification permission granted.");

            await syncFcmToken();

            // Optionally update UI
            enable_notifications_button.style.display = "none";
        } else {
            console.log("Notification permission denied.");
        }
    });
}

const test_push_notification_button = document.getElementById("test_push_notification");

if (test_push_notification_button) {
    test_push_notification_button.addEventListener("click", async () => {
        await fetch("/test_push_notification", { method: "POST" });
        console.log("Received test notification");
    });
}

const push_notifications_enabled = document.getElementById("push_notifications_enabled");

if (push_notifications_enabled) {
    push_notifications_enabled.addEventListener("change", async (event) => {
        if (event.target.checked) {
            if (Notification.permission !== "granted") {
                console.log("Requesting permission...");
                const permission = await Notification.requestPermission();

                if (permission === "granted") {
                    console.log("Notification permission granted.");
                    alert("Notification permission granted.");
                    await syncFcmToken();
                }
            } else {
                // Permission already granted — just sync
                await syncFcmToken();
            }
        }
    });
}

onMessage(messaging, (payload) => {
new Notification(payload.notification.title, {
    body: payload.notification.body,
    // icon: '/static/icon.png' We can add this later when we have an icon for the app
    });
});

if (Notification.permission === "granted") {
    syncFcmToken();
}






// // This block works for the "enable notifications" button
// // I think it would be better to remove this button and just run this code if a user
// // is adding medication and wants push notifications. It works for the test notification
// // though so I'll leave it (at least for now).
// const enable_notifications_button = document.getElementById("enable_notifications");
// if (enable_notifications_button) {
//     enable_notifications_button.addEventListener("click", async () => {
//         console.log("Requesting permission...");
//         const permission = await Notification.requestPermission();
//         if (permission === "granted") {
//             console.log("Notification permission granted.");
//             alert("Notification permission granted.");
//             navigator.serviceWorker.register("/static/firebase-messaging-sw.js").then((registration) => {
//                 getToken(messaging, { 
//                     vapidKey: "BEsK6dC7_GO_iZ2wtVLQouKCC0RgS2cuMKNWHBOUlk_4vlq1OBDTXb1FqWNOBH4TYBE8sZZpSCwzkYhy6WKIU5I",
//                     serviceWorkerRegistration: registration
//                 }).then((currentToken) => {
//                     if (currentToken) {
//                         console.log("FCM Token: ", currentToken);
//                         fetch("/save_token", {
//                             method : "POST",
//                             headers : { "Content-Type" : "application/json" },
//                             body : JSON.stringify({ token : currentToken }) 
//                         }).then(response => {
//                             if (response.ok) {
//                                 console.log("Token sent to server successfully");
//                                 // Optionally update UI
//                                 enable_notifications_button.style.display = "none";
//                             } else {
//                                 console.error("Failed to send token to server");
//                             }
//                         }).catch(err => 
//                             console.error("Error sending token to server"));
//                     } else {
//                         // Show permission request UI
//                         console.log("No registration token available. Request permission to generate one.");
//                         // ...
//                     }
//                     }).catch((err) => {
//                     console.log("An error occurred while retrieving token. ", err);
//                     // ...
//                     });
//             })
//         } else {
//             console.log("Notification permission denied.");
//         }
//     });
// }

// const test_push_notification_button = document.getElementById("test_push_notification");
// if (test_push_notification_button) {
//     test_push_notification_button.addEventListener("click", async () => {
//         await fetch("/test_push_notification", { method: "POST" });
//         console.log("Received test notification");
//     })
// }

// // This is the block that runs if a user is adding medication and opts in for push
// // notifications.
// const push_notifications_enabled = document.getElementById("push_notifications_enabled"); // This selects the button for enabling push notifications
// if (push_notifications_enabled) {
//     push_notifications_enabled.addEventListener("change", async (event) => {
//         if (event.target.checked) {
//             if (Notification.permission != "granted") {
//                 console.log("Requesting permission...");
//                 const permission = await Notification.requestPermission();
//                 if (permission === "granted") {
//                     console.log("Notification permission granted.");
//                     alert("Notification permission granted.");
//                     try {
//                         const registration = await navigator.serviceWorker.register("/static/firebase-messaging-sw.js");
//                         const currentToken = await getToken(messaging, {
//                             vapidKey: "BEsK6dC7_GO_iZ2wtVLQouKCC0RgS2cuMKNWHBOUlk_4vlq1OBDTXb1FqWNOBH4TYBE8sZZpSCwzkYhy6WKIU5I",
//                             serviceWorkerRegistration: registration
//                         })
//                         if (currentToken) {
//                             const response = await fetch("/save_token", {
//                                 method: "POST",
//                                 headers: { "Content-Type": "application/json" },
//                                 body: JSON.stringify({ token: currentToken })
//                             })
//                             if (response.ok) {
//                                 console.log("Token sent to server successfully");
//                             } else {
//                                 console.error("Failed to send token to server");
//                             }
//                         } else {
//                             console.log("No registration token available. Request permission to generate one.");
//                         }

//                     } catch (err) {
//                         console.log("An error occurred while retrieving token. ", err);
//                     }
//                 }
//             }
//         }
//     });
// }

// onMessage(messaging, (payload) => {
// new Notification(payload.notification.title, {
//     body: payload.notification.body,
//     // icon: '/static/icon.png' We can add this later when we have an icon for the app
//     });
// });