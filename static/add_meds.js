document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("multiStepForm");
    const steps = form.querySelectorAll(".form-step");
    const nextButtons = form.querySelectorAll(".next-btn");
    const backButtons = form.querySelectorAll(".back-btn");
    const circles = document.querySelectorAll(".step-circle");

    let currentStep = 0;

    function updateSteps() {
        // Show correct fieldset
        steps.forEach((step, index) => {
            step.classList.toggle("active", index === currentStep);
        });

        // Update progress circles
        circles.forEach((circle, index) => {
            if (index <= currentStep) {
                circle.classList.add("active");
            } else {
                circle.classList.remove("active");
            }
        });
    }

    nextButtons.forEach(button => {
        button.addEventListener("click", function () {
            if (currentStep < steps.length - 1) {
                currentStep++;
                updateSteps();
                window.scrollTo({ top: 0, behavior: "smooth" });
            }
        });
    });

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