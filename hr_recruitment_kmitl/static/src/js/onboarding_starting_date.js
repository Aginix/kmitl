odoo.define("hr_recruitment_kmitl.onboarding_starting_date", function () {
    "use strict";

    function init() {
        var radios = document.querySelectorAll('input[name="can_start_on_time"]');
        var details = document.querySelector(".js-starting-date-details");
        if (!radios.length || !details) return;

        function sync() {
            var checked = document.querySelector(
                'input[name="can_start_on_time"]:checked'
            );
            details.style.display = checked && checked.value === "no" ? "" : "none";
        }

        radios.forEach(function (radio) {
            radio.addEventListener("change", sync);
        });
        sync();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
});
