/**
 * alerts.js — auto-ukrywanie wiadomości Django po 2.5 sekundy.
 * Zastępuje inline <script> w base.html, co pozwala na ścisłą politykę CSP.
 */
document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
        document.querySelectorAll(".alert").forEach(function (el) {
            el.style.transition = "opacity 0.5s ease";
            el.style.opacity = "0";
            setTimeout(function () { el.remove(); }, 500);
        });
    }, 2500);
});
