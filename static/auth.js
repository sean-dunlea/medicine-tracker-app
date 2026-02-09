document.addEventListener("DOMContentLoaded", () => {

  /* FALLING PILLS */
  const pillsContainer = document.querySelector(".pills");

  if (pillsContainer) {
    const colors = [
      "var(--pill-pink)",
      "var(--pill-orange)",
      "var(--pill-brown)"
    ];

    function createPill(startRandom = false) {
      const pill = document.createElement("span");

      const isCircle = Math.random() < 0.35;
      pill.classList.add(isCircle ? "circle" : "capsule");

      pill.style.left = Math.random() * 100 + "vw";
      pill.style.background =
        colors[Math.floor(Math.random() * colors.length)];

      const duration = 18 + Math.random() * 12;
      pill.style.animationDuration = duration + "s";

      pill.style.top = startRandom
        ? Math.random() * 100 + "vh"
        : "-80px";

      pillsContainer.appendChild(pill);
      setTimeout(() => pill.remove(), duration * 1000);
    }

    for (let i = 0; i < 25; i++) createPill(true);
    setInterval(() => createPill(false), 500);
  }

  /* LOGIN / REGISTER SWIPE*/
  const container = document.getElementById("container");
  const registerBtn = document.getElementById("register");
  const loginBtn = document.getElementById("login");

  if (container && registerBtn && loginBtn) {
    registerBtn.addEventListener("click", () => {
      container.classList.add("active");
    });

    loginBtn.addEventListener("click", () => {
      container.classList.remove("active");
    });
  }

});
