odoo.define("hr_recruitment_kmitl.onboarding_validation", function () {
    "use strict";
    /* global bootstrap */

    // Client-side pre-check that mirrors the server's _validate_submit so the
    // user gets immediate feedback and is taken to the first offending tab.
    // The server (controllers/portal_onboarding.py) stays authoritative.

    // Required document uploads (field name -> label). letter_of_consent is
    // conditional on the job type and is left to the server to enforce.
    var REQUIRED_FILES = [
        ["health_employee_file", "เอกสารของตัวพนักงาน (ประกันสุขภาพกลุ่ม)"],
        ["accident_employee_file", "เอกสารของผู้สมัคร (ประกันอุบัติเหตุกลุ่ม)"],
        ["beneficiary_declaration_file", "หนังสือแสดงเจตนาระบุตัวผู้รับประโยชน์"],
        ["salary_book_file", "สำเนาสมุดบัญชีธนาคารกรุงไทย"],
        ["medical_certificate_file", "ใบรับรองแพทย์"],
    ];

    var FAMILY_FIELDS = [
        ["family_relation_id", "ความสัมพันธ์"],
        ["family_prefix_id", "คำนำหน้า"],
        ["family_first_name", "ชื่อ"],
        ["family_last_name", "นามสกุล"],
        ["family_status", "สถานะ"],
        ["family_identification_id", "เลขประจำตัวประชาชน"],
        ["family_date_of_birth", "วันเกิด"],
    ];
    // Extra fields that only mark a row as "active" (not required themselves).
    var FAMILY_OPTIONAL = ["family_middle_name", "family_job", "family_phone"];

    function trimmed(el) {
        return el && el.value ? el.value.trim() : "";
    }

    function paneOf(el) {
        return el ? el.closest(".tab-pane") : null;
    }

    function radioValue(form, name) {
        var checked = form.querySelector('input[name="' + name + '"]:checked');
        return checked ? checked.value : "";
    }

    function isFileSatisfied(form, inputName) {
        var input = form.querySelector('input[type="file"][name="' + inputName + '"]');
        if (input && input.files && input.files.length) return true;
        var wrapper = input ? input.closest(".js-file-upload-wrapper") : null;
        if (wrapper && wrapper.getAttribute("data-has-file") === "1") {
            var del = wrapper.querySelector(".js-delete-flag");
            if (!del || del.value !== "1") return true;
        }
        return false;
    }

    function collectErrors(form) {
        var missing = [];
        var firstPane = null;
        function add(label, pane) {
            missing.push(label);
            if (!firstPane && pane) firstPane = pane;
        }

        // Required files
        REQUIRED_FILES.forEach(function (item) {
            if (!isFileSatisfied(form, item[0])) {
                var input = form.querySelector(
                    'input[type="file"][name="' + item[0] + '"]'
                );
                add(item[1], paneOf(input));
            }
        });

        // Starting date (work tab)
        var canStart = radioValue(form, "can_start_on_time");
        var startRadio = form.querySelector('input[name="can_start_on_time"]');
        if (!canStart) {
            add("ความพร้อมในการเริ่มปฏิบัติงาน", paneOf(startRadio));
        } else if (canStart === "no") {
            var date = form.querySelector('[name="starting_date"]');
            if (!trimmed(date)) {
                add("วันแรกที่เริ่มปฏิบัติงาน", paneOf(date));
            }
            var note = form.querySelector('[name="starting_date_note"]');
            if (!trimmed(note)) {
                add("หนังสือชี้แจงเหตุผล (เรียนอธิการบดี)", paneOf(note));
            }
            if (!isFileSatisfied(form, "starting_date_attachment_file")) {
                var att = form.querySelector(
                    'input[type="file"][name="starting_date_attachment_file"]'
                );
                add("แนบเอกสารชี้แจงเหตุผล", paneOf(att));
            }
        }

        // Confirmation tab
        var locationRadio = form.querySelector(
            'input[name="background_check_location_type"]'
        );
        if (!radioValue(form, "background_check_location_type")) {
            add("สถานที่ตรวจสอบประวัติอาชญากรรม", paneOf(locationRadio));
        }
        var bank = form.querySelector('[name="krungthai_bank_account"]');
        var bankValue = trimmed(bank);
        if (!bankValue) {
            add("เลขที่บัญชีธนาคารกรุงไทย", paneOf(bank));
        } else if (!/^[0-9]+$/.test(bankValue)) {
            add("เลขที่บัญชีธนาคารกรุงไทย (กรอกเฉพาะตัวเลขเท่านั้น)", paneOf(bank));
        }
        var pdpaRadio = form.querySelector('input[name="pdpa_consent"]');
        if (radioValue(form, "pdpa_consent") !== "yes") {
            add(
                "ความยินยอมตามนโยบาย PDPA (ต้องยินยอมเพื่อส่งข้อมูล)",
                paneOf(pdpaRadio)
            );
        }
        var finalConfirm = form.querySelector('input[name="final_confirm"]');
        if (finalConfirm && !finalConfirm.checked) {
            add("ยืนยันความถูกต้องของข้อมูล", paneOf(finalConfirm));
        }

        // Family rows — a row is active once ANY field is filled, so a row
        // with data but no relation gets flagged (relation is now required).
        var rows = form.querySelectorAll(".family-rows-container .family-row");
        rows.forEach(function (row, idx) {
            var active =
                FAMILY_FIELDS.some(function (item) {
                    return trimmed(row.querySelector('[name="' + item[0] + '"]'));
                }) ||
                FAMILY_OPTIONAL.some(function (name) {
                    return trimmed(row.querySelector('[name="' + name + '"]'));
                });
            if (!active) return;
            var rowMissing = [];
            var firstEl = null;
            FAMILY_FIELDS.forEach(function (item) {
                var el = row.querySelector('[name="' + item[0] + '"]');
                if (!trimmed(el)) {
                    rowMissing.push(item[1]);
                    if (!firstEl) firstEl = el;
                }
            });
            if (rowMissing.length) {
                add(
                    "สมาชิกครอบครัวคนที่ " + (idx + 1) + ": " + rowMissing.join(", "),
                    paneOf(firstEl || row)
                );
            }
        });

        return {missing: missing, firstPane: firstPane};
    }

    function showError(form, missing, firstPane) {
        if (firstPane && firstPane.id && window.bootstrap && bootstrap.Tab) {
            var tabBtn = document.querySelector('[href="#' + firstPane.id + '"]');
            if (tabBtn) bootstrap.Tab.getOrCreateInstance(tabBtn).show();
        }
        var alertEl = document.getElementById("onboarding-error-alert");
        if (!alertEl) {
            alertEl = document.createElement("div");
            alertEl.id = "onboarding-error-alert";
            alertEl.className = "alert alert-danger mt-4";
            alertEl.setAttribute("role", "alert");
            alertEl.style.whiteSpace = "pre-line";
            // Show the error below the form, right above the action buttons.
            var actions = form.querySelector("#onboarding-form-actions");
            if (actions) {
                actions.parentNode.insertBefore(alertEl, actions);
            } else {
                form.appendChild(alertEl);
            }
        }
        alertEl.textContent = "กรุณากรอกข้อมูลให้ครบถ้วน:\n• " + missing.join("\n• ");
        // Scroll up to the top of the form so the offending tab's fields are
        // brought into view (instead of leaving the user at the bottom).
        var scrollTarget = document.getElementById("form-tabs") || form;
        scrollTarget.scrollIntoView({behavior: "smooth", block: "start"});
    }

    function init() {
        var form = document.querySelector('form[action^="/my/onboarding/form/"]');
        if (!form) return;
        var submitBtn = form.querySelector('button[name="action"][value="submit"]');
        if (!submitBtn) return;

        submitBtn.addEventListener(
            "click",
            function (e) {
                var result = collectErrors(form);
                if (result.missing.length) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    showError(form, result.missing, result.firstPane);
                }
            },
            true
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
});
