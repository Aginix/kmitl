odoo.define("website_hr_recruitment_profile.education_rows", function () {
    "use strict";

    var nextIndex = 0;

    function getTemplate() {
        var el = document.querySelector("#education_row_template .education-row");
        return el;
    }

    function getContainer() {
        return $("#education_rows_container");
    }

    function addRow(data) {
        var template = getTemplate();
        if (!template) {
            return;
        }
        var $row = $(template.cloneNode(true));
        var idx = nextIndex++;

        // Set indexed name attributes for form submission
        $row.find("[data-field]").each(function () {
            var field = $(this).data("field");
            $(this).attr("name", "education_" + field + "_" + idx);
        });

        // Pre-fill values
        if (data.level) {
            $row.find("[data-field='level']").val(data.level);
        }
        if (data.program) {
            $row.find("[data-field='program']").val(data.program);
        }
        if (data.major) {
            $row.find("[data-field='major']").val(data.major);
        }
        if (data.institution) {
            $row.find("[data-field='institution']").val(data.institution);
        }
        if (data.country_id) {
            $row.find("[data-field='country_id']").val(data.country_id);
        }
        if (data.graduation_date) {
            $row.find("[data-field='graduation_date']").val(data.graduation_date);
        }

        getContainer().append($row);
    }

    function reindexRows() {
        var $container = getContainer();
        $container.find(".education-row").each(function (idx) {
            $(this)
                .find("[data-field]")
                .each(function () {
                    var field = $(this).data("field");
                    $(this).attr("name", "education_" + field + "_" + idx);
                });
        });
        nextIndex = $container.find(".education-row").length;
    }

    // Use document-level event delegation (works regardless of widget lifecycle)
    $(document).on("click", "#education_add_btn", function (ev) {
        ev.preventDefault();
        addRow({});
    });

    $(document).on("click", ".education-remove-btn", function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest(".education-row").remove();
        reindexRows();
    });

    // Load pre-fill data on DOM ready
    $(function () {
        var prefillEl = document.getElementById("education_prefill_data");
        if (prefillEl && prefillEl.value) {
            try {
                var data = JSON.parse(prefillEl.value);
                for (var i = 0; i < data.length; i++) {
                    addRow(data[i]);
                }
            } catch (e) {
                // Ignore parse errors
            }
        }
    });
});
