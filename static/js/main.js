// Scroll-reveal animation for elements marked .reveal
document.addEventListener("DOMContentLoaded", () => {
    const revealEls = document.querySelectorAll(".reveal");
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-visible");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });
    revealEls.forEach((el) => observer.observe(el));

    // Dark mode toggle
    const toggle = document.getElementById("darkModeToggle");
    const body = document.body;
    if (localStorage === undefined) {
        // no-op: some sandboxed contexts disallow storage
    }
    try {
        if (document.cookie.includes("dark_mode=1")) {
            body.classList.add("dark-mode");
        }
    } catch (e) { /* ignore */ }

    if (toggle) {
        toggle.addEventListener("click", () => {
            body.classList.toggle("dark-mode");
            const isDark = body.classList.contains("dark-mode");
            document.cookie = `dark_mode=${isDark ? "1" : "0"}; path=/; max-age=31536000`;
            toggle.textContent = isDark ? "☀️ Light" : "🌙 Dark";
        });
        if (body.classList.contains("dark-mode")) {
            toggle.textContent = "☀️ Light";
        }
    }

    // Auto-dismiss bootstrap toasts/alerts after 4s
    document.querySelectorAll(".alert-auto-dismiss").forEach((alertEl) => {
        setTimeout(() => {
            alertEl.classList.remove("show");
            setTimeout(() => alertEl.remove(), 300);
        }, 4000);
    });

    // Confirmation modal helper: any element with data-confirm-form="formId" and data-confirm-message
    document.querySelectorAll("[data-confirm-message]").forEach((el) => {
        el.addEventListener("click", (e) => {
            if (!confirm(el.getAttribute("data-confirm-message"))) {
                e.preventDefault();
            }
        });
    });
});
