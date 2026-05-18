odoo.define("hr_recruitment_kmitl.apply_page", function () {
    "use strict";
    /* global bootstrap */

    function switchToTabWithError(form) {
        var errorField = form.querySelector(".tab-pane .o_has_error");
        if (!errorField) return;
        var pane = errorField.closest(".tab-pane");
        if (!pane) return;
        var tabBtn = document.querySelector('[href="#' + pane.id + '"]');
        if (tabBtn && window.bootstrap && bootstrap.Tab) {
            new bootstrap.Tab(tabBtn).show();
        }
    }

    function showValidationError(form, missing, hasProfileMissing) {
        var result = form.querySelector("#s_website_form_result");
        if (!result) return;
        var html =
            '<div class="alert alert-danger mt-3" role="alert">' +
            "<strong>กรุณากรอกข้อมูลให้ครบถ้วน:</strong><ul class='mb-0 mt-2'>";
        for (var i = 0; i < missing.length; i++) {
            html += "<li>" + missing[i] + "</li>";
        }
        html += "</ul>";
        if (hasProfileMissing) {
            html +=
                '<p class="mb-0 mt-2">ข้อมูลส่วนบุคคลบางส่วนยังไม่ครบ กรุณาตรวจสอบ ' +
                '<a href="/my/profile">แฟ้มประวัติ</a> ก่อนส่งใบสมัคร</p>';
        }
        html += "</div>";
        result.innerHTML = html;
        result.scrollIntoView({behavior: "smooth"});
    }

    function navigateToPane(pane) {
        if (!pane) return;
        var tabBtn = document.querySelector('[href="#' + pane.id + '"]');
        if (tabBtn && window.bootstrap && bootstrap.Tab) {
            new bootstrap.Tab(tabBtn).show();
        }
    }

    function checkRequiredLabels(form) {
        var missing = [];
        var firstPane = null;
        form.querySelectorAll("[data-required-label]").forEach(function (el) {
            if (!el.value || !el.value.trim() || el.value.trim() === "-") {
                missing.push(el.getAttribute("data-required-label"));
                if (!firstPane) firstPane = el.closest(".tab-pane");
            }
        });
        return {missing: missing, firstPane: firstPane};
    }

    function checkCertification(form) {
        var el = form.querySelector("#certifyCheck");
        if (el && !el.checked) {
            return {label: "การรับรองข้อมูล", pane: el.closest(".tab-pane")};
        }
        return {};
    }

    function checkPdpaConsent(form) {
        var agreed = form.querySelector('input[name="pdpa_consent"][value="true"]');
        var disagreed = form.querySelector('input[name="pdpa_consent"][value=""]');
        if (!agreed || agreed.checked) return {};
        var label =
            disagreed && disagreed.checked
                ? "ข้อตกลง PDPA — กรุณายินยอมเพื่อส่งใบสมัคร"
                : "ข้อตกลง PDPA";
        return {label: label, pane: agreed.closest(".tab-pane")};
    }

    function collectMissing(form) {
        var result = checkRequiredLabels(form);
        var missing = result.missing;
        var firstPane = result.firstPane;
        var hasProfileMissing = missing.length > 0;

        var cert = checkCertification(form);
        if (cert.label) {
            missing.push(cert.label);
            if (!firstPane) firstPane = cert.pane;
        }
        var pdpa = checkPdpaConsent(form);
        if (pdpa.label) {
            missing.push(pdpa.label);
            if (!firstPane) firstPane = pdpa.pane;
        }
        return {
            missing: missing,
            firstPane: firstPane,
            hasProfileMissing: hasProfileMissing,
        };
    }

    function initApplyValidation() {
        var form = document.getElementById("hr_recruitment_form");
        if (!form) return;

        var submitBtn = form.querySelector(".s_website_form_send");
        if (!submitBtn) return;

        submitBtn.addEventListener(
            "click",
            function (e) {
                var result = collectMissing(form);
                if (result.missing.length) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    navigateToPane(result.firstPane);
                    showValidationError(form, result.missing, result.hasProfileMissing);
                    return;
                }
                // Clear previous errors
                var resultEl = form.querySelector("#s_website_form_result");
                if (resultEl) resultEl.innerHTML = "";
                // After Odoo's validation runs, check for o_has_error in hidden tabs
                setTimeout(function () {
                    switchToTabWithError(form);
                }, 100);
            },
            true
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initApplyValidation);
    } else {
        initApplyValidation();
    }
});
