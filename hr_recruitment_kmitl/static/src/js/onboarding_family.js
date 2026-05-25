odoo.define("hr_recruitment_kmitl.onboarding_family", function () {
    "use strict";

    function init() {
        var container = document.querySelector(".family-rows-container");
        var templateHost = document.querySelector(".family-row-template");
        var addButton = document.querySelector(".btn-add-family-row");
        if (!container || !templateHost || !addButton) return;

        var templateRow = templateHost.querySelector(".family-row");
        if (!templateRow) return;

        function renumberRows() {
            var rows = container.querySelectorAll(".family-row");
            rows.forEach(function (row, idx) {
                var heading = row.querySelector("h6");
                if (heading) {
                    heading.textContent = "สมาชิกครอบครัวคนที่ " + (idx + 1);
                }
            });
        }

        addButton.addEventListener("click", function (e) {
            e.preventDefault();
            var newRow = templateRow.cloneNode(true);
            container.insertBefore(newRow, addButton.parentElement);
            renumberRows();
        });

        container.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-remove-family-row");
            if (!btn) return;
            e.preventDefault();
            var row = btn.closest(".family-row");
            if (row) {
                row.remove();
                renumberRows();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
});
