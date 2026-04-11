window.toggleHelp = function () {
    const dropdown = document.getElementById("helpDropdown");
    if (dropdown) {
        dropdown.classList.toggle("show");
    }
};

document.addEventListener("DOMContentLoaded", function () {
    const topBtn = document.getElementById("topBtn");
    const navToggle = document.querySelector("[data-nav-toggle]");
    const navContainer = navToggle ? navToggle.closest(".super-container") : null;

    function updateTopButton() {
        if (!topBtn) {
            return;
        }

        topBtn.style.display = window.scrollY > 200 ? "block" : "none";
    }

    function setNavOpen(isOpen) {
        if (!navToggle || !navContainer) {
            return;
        }

        navContainer.classList.toggle("nav-open", isOpen);
        navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }

    updateTopButton();
    window.addEventListener("scroll", updateTopButton, { passive: true });

    if (navToggle && navContainer) {
        navToggle.addEventListener("click", function () {
            const nextState = !navContainer.classList.contains("nav-open");
            setNavOpen(nextState);
        });
    }

    document.addEventListener("click", function (event) {
        const helpDropdown = document.getElementById("helpDropdown");

        if (
            helpDropdown &&
            !event.target.closest(".help-btn") &&
            !event.target.closest("#helpDropdown")
        ) {
            helpDropdown.classList.remove("show");
        }

        if (
            navContainer &&
            navContainer.classList.contains("nav-open") &&
            window.innerWidth <= 768 &&
            !event.target.closest(".super-container")
        ) {
            setNavOpen(false);
        }
    });

    window.addEventListener("resize", function () {
        if (window.innerWidth > 768) {
            setNavOpen(false);
        }
    });
});
