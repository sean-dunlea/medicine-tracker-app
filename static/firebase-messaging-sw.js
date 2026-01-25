// Give the service worker access to Firebase Messaging.
importScripts('https://www.gstatic.com/firebasejs/12.8.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/12.8.0/firebase-messaging-compat.js');

// Initialize the Firebase app in the service worker by passing in
// the app's Firebase config object.
firebase.initializeApp({
    apiKey: "AIzaSyAyvB0QXuTqKpcft1PTkLs8JLojunIUz2s",
    authDomain: "medicine-tracker-app-7cfe4.firebaseapp.com",
    projectId: "medicine-tracker-app-7cfe4",
    storageBucket: "medicine-tracker-app-7cfe4.firebasestorage.app",
    messagingSenderId: "259878242247",
    appId: "1:259878242247:web:a6797dc7d90deed322bbe2"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();

// // Handle incoming messages. Called when:
// // - a message is received while the app has focus
// // - the user clicks on an app notification created by a service worker
// //   `messaging.onBackgroundMessage` handler.
// messaging.onMessage((payload) => {
//     console.log('Message received. ', payload);
//     // ...
//   });
messaging.onBackgroundMessage(function(payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);
    // Customize notification here
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
    body: payload.notification.body
    //   icon: '/firebase-logo.png' We don't have a logo yet so we'll save this for later
    };
  
    self.registration.showNotification(notificationTitle, notificationOptions);
  });