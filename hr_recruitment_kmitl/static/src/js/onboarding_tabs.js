odoo.define("hr_recruitment_kmitl.onboarding_tabs", function () {
    "use strict";
    /* global bootstrap */

    // Keep the URL hash in sync with the active onboarding-form tab so tabs are
    // bookmarkable / deep-linkable. The nav uses href-based tabs (#nav-...).

    function activateTab(target) {
        var link = document.querySelector('#form-tabs a[href="' + target + '"]');
        var pane = document.querySelector(target);
        if (!link || !pane) return;
        if (window.bootstrap && bootstrap.Tab) {
            bootstrap.Tab.getOrCreateInstance(link).show();
        } else {
            // Fallback when the Bootstrap JS API is not ready on load (clicks
            // still work via Bootstrap's data-api regardless).
            var nav = link.closest(".nav, [role='tablist']");
            if (nav) {
                nav.querySelectorAll(".nav-link").forEach(function (l) {
                    l.classList.remove("active");
                    l.setAttribute("aria-selected", "false");
                });
            }
            link.classList.add("active");
            link.setAttribute("aria-selected", "true");
            var content = pane.closest(".tab-content");
            if (content) {
                content.querySelectorAll(".tab-pane").forEach(function (p) {
                    p.classList.remove("active", "show");
                });
            }
            pane.classList.add("active", "show");
        }
        history.replaceState(null, "", target);
    }

    function init() {
        var nav = document.getElementById("form-tabs");
        if (!nav) return;

        nav.querySelectorAll('a[data-bs-toggle="tab"]').forEach(function (link) {
            link.addEventListener("shown.bs.tab", function (e) {
                var target = e.target.getAttribute("href");
                if (target) {
                    history.replaceState(null, "", target);
                }
            });
        });

        // Remember the active tab across "save draft": the POST redirect drops
        // the URL hash, so stash it and re-apply it after the reload.
        var form = document.querySelector('form[action^="/my/onboarding/form/"]');
        if (form) {
            form.addEventListener("submit", function () {
                var activeLink = nav.querySelector(".nav-link.active");
                var target = activeLink && activeLink.getAttribute("href");
                if (target) {
                    sessionStorage.setItem("onboardingActiveTab", target);
                }
            });
        }

        // Restore the tab: the saved-draft tab takes priority over the URL hash.
        var savedTab = sessionStorage.getItem("onboardingActiveTab");
        if (savedTab) {
            sessionStorage.removeItem("onboardingActiveTab");
            activateTab(savedTab);
        } else if (window.location.hash) {
            activateTab(window.location.hash);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
});
