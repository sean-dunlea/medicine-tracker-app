document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("multiStepForm");
    const steps = form.querySelectorAll(".form-step");
    const nextButtons = form.querySelectorAll(".next-btn");
    const backButtons = form.querySelectorAll(".back-btn");
    const circles = document.querySelectorAll(".step-circle");
    const progress = document.querySelector(".progress-steps");

    let currentStep = 0;

    function updateSteps() {

        // Show correct fieldset
        steps.forEach((step, index) => {
            step.classList.toggle("active", index === currentStep);
        });

        // Update progress circles
        circles.forEach((circle, index) => {
            circle.classList.toggle("active", index <= currentStep);
        });

        // Update progress fill line
        const percent = (currentStep / (steps.length - 1)) * 100;
        progress.style.setProperty("--fill-width", percent + "%");
    }

    // Initial state
    updateSteps();

    // Next buttons
    nextButtons.forEach(button => {
        button.addEventListener("click", function () {
            if (currentStep < steps.length - 1) {
                currentStep++;
                updateSteps();
                window.scrollTo({ top: 0, behavior: "smooth" });
            }
        });
    });

    // Back buttons
    backButtons.forEach(button => {
        button.addEventListener("click", function () {
            if (currentStep > 0) {
                currentStep--;
                updateSteps();
                window.scrollTo({ top: 0, behavior: "smooth" });
            }
        });
    });

});