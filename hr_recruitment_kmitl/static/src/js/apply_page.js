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

    function showSubmitTabError(form, missing, firstPane) {
        if (firstPane && firstPane.id) {
            var tabBtn = document.querySelector('[href="#' + firstPane.id + '"]');
            if (tabBtn && window.bootstrap && bootstrap.Tab) {
                new bootstrap.Tab(tabBtn).show();
            }
        }
        var resultEl = form.querySelector("#s_website_form_result");
        if (!resultEl) return;
        resultEl.outerHTML =
            '<div id="s_website_form_result" class="alert alert-danger mt-3" role="alert">' +
            "<strong>เกิดข้อผิดพลาด</strong>" +
            '<div class="mt-1" style="white-space: pre-line">' +
            "กรุณากรอกข้อมูลให้ครบถ้วน:\n• " +
            missing.join("\n• ") +
            "</div></div>";
        var newResult = form.querySelector("#s_website_form_result");
        if (newResult) newResult.scrollIntoView({behavior: "smooth"});
    }

    function initApplyValidation() {
        var form = document.getElementById("hr_recruitment_form");
        if (!form) return;

        var submitBtn = form.querySelector(".s_website_form_send");
        if (!submitBtn) return;

        submitBtn.addEventListener(
            "click",
            function (e) {
                var missing = [];
                var firstPane = null;
                var submitPane = form.querySelector("#nav-submit");
                if (submitPane) {
                    submitPane
                        .querySelectorAll("[data-required-label]")
                        .forEach(function (el) {
                            if (
                                !el.value ||
                                !el.value.trim() ||
                                el.value.trim() === "-"
                            ) {
                                missing.push(el.getAttribute("data-required-label"));
                                if (!firstPane) firstPane = submitPane;
                            }
                        });
                }
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
                if (missing.length) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    showSubmitTabError(form, missing, firstPane);
                    return;
                }
                var resultEl = form.querySelector("#s_website_form_result");
                if (resultEl) {
                    resultEl.outerHTML = '<span id="s_website_form_result"></span>';
                }
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

odoo.define("hr_recruitment_kmitl.apply_form_hint", function (require) {
    "use strict";
    require("website.s_website_form");
    var publicWidget = require("web.public.widget");
    if (!publicWidget.registry.s_website_form) return;

    publicWidget.registry.s_website_form.include({
        update_status: function (status) {
            var self = this;
            var ret = this._super.apply(this, arguments);
            if (status !== "error") return ret;
            if (this.$target.data("model_name") !== "hr.applicant") return ret;
            this.__started.then(function () {
                var result = self.$target[0].querySelector("#s_website_form_result");
                if (!result || result.querySelector(".js_profile_hint")) return;
                var extra = document.createElement("div");
                extra.className = "mt-2 js_profile_hint";
                extra.innerHTML =
                    "ข้อมูลส่วนบุคคลบางส่วนยังไม่ครบ กรุณาตรวจสอบ " +
                    '<a href="/my/profile">แฟ้มประวัติ</a> ก่อนส่งใบสมัคร';
                result.appendChild(extra);
            });
            return ret;
        },
    });
});
