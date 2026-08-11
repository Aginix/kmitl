odoo.define("hr_recruitment_kmitl.onboarding_family", function () {
    "use strict";

    function init() {
        var container = document.querySelector(".family-rows-container");
        var templateHost = document.querySelector(".family-row-template");
        var addButton = document.querySelector(".btn-add-family-row");
        if (!container || !templateHost || !addButton) return;

        var templateRow = templateHost.querySelector(".family-row");
        if (!templateRow) return;

        var DOC_PREFIXES = [
            "family_house_registration",
            "family_id_card",
            "family_other_attachment",
            "delete_family_house_registration",
            "delete_family_id_card",
            "delete_attachment_family_other_attachment",
        ];

        function reindexRowInputs(row, idx) {
            row.querySelectorAll("[name]").forEach(function (el) {
                var name = el.getAttribute("name");
                DOC_PREFIXES.forEach(function (prefix) {
                    if (name.indexOf(prefix + "___INDEX__") === 0) {
                        name =
                            prefix +
                            "_" +
                            idx +
                            name.slice((prefix + "___INDEX__").length);
                    } else if (name.indexOf(prefix + "_") === 0) {
                        var rest = name.slice((prefix + "_").length);
                        // Strip the leading numeric segment (the old index)
                        rest = rest.replace(/^\d+/, idx);
                        name = prefix + "_" + rest;
                    }
                });
                el.setAttribute("name", name);
            });
            var heading = row.querySelector("h6.fw-bold");
            if (heading && heading.textContent.indexOf("สมาชิก") !== -1) {
                heading.textContent = "สมาชิกครอบครัวคนที่ " + (idx + 1);
            }
        }

        function renumberRows() {
            var rows = container.querySelectorAll(".family-row");
            rows.forEach(function (row, idx) {
                reindexRowInputs(row, idx);
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

        // Initial pass so any rendered rows get sequential indexes
        renumberRows();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
});
