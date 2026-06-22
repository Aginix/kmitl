odoo.define("hr_recruitment_kmitl.profile_page", function () {
    "use strict";
    /* global bootstrap */

    function setupToggle(selectId, targetId, showWhen) {
        var select = document.getElementById(selectId);
        var target = document.getElementById(targetId);
        if (!select || !target) return;
        var toggle = function () {
            target.style.display = showWhen(select) ? "" : "none";
        };
        select.addEventListener("change", toggle);
        toggle();
    }

    function setupEducationSections() {
        var highestEduSelect = document.getElementById("highest_education");
        var container = document.getElementById("education_sections");
        if (!highestEduSelect || !container) return;
        var visibilityMap = {
            doctor: [70, 80, 90],
            master: [70, 80],
            bachelor: [70],
            under_bachelor: ["sub"],
        };
        var allSections = container.querySelectorAll(".edu-section");
        var toggle = function () {
            var val = highestEduSelect.value;
            var visible = visibilityMap[val] || [];
            container.style.display = val ? "" : "none";
            allSections.forEach(function (sec) {
                var level = sec.getAttribute("data-edu-level");
                var key = level === "sub" ? "sub" : parseInt(level, 10);
                sec.style.display = visible.indexOf(key) >= 0 ? "" : "none";
            });
        };
        highestEduSelect.addEventListener("change", toggle);
        toggle();
    }

    function setupWorkHistory() {
        var whList = document.getElementById("wh-list");
        var whAddBtn = document.getElementById("btn-wh-add");
        if (!whAddBtn || !whList) return;
        whAddBtn.addEventListener("click", function () {
            var card = document.createElement("div");
            card.className = "card border rounded-4";
            card.innerHTML =
                '<div class="card-body p-4">' +
                '<div class="d-flex justify-content-between align-items-center mb-4">' +
                '<h5 class="fw-bold text-dark mb-0">ประวัติการทำงาน</h5>' +
                '<button type="button" class="btn btn-outline-danger btn-sm rounded-pill btn-wh-remove">' +
                '<i class="fa fa-trash me-1"></i> ลบ</button>' +
                "</div>" +
                '<input type="hidden" name="wh_id" value="0"/>' +
                '<div class="row g-3 mb-1">' +
                '<div class="col-lg-6">' +
                '<label class="col-form-label">Company</label><span class="text-danger ms-1">*</span>' +
                '<input type="text" name="wh_company_name" class="form-control" placeholder="ชื่อบริษัท" required />' +
                "</div>" +
                '<div class="col-lg-6">' +
                '<label class="col-form-label">Job Title / Description</label><span class="text-danger ms-1">*</span>' +
                '<input type="text" name="wh_job_title" class="form-control" placeholder="ตำแหน่ง / ลักษณะงาน"/>' +
                "</div>" +
                "</div>" +
                '<div class="row g-3">' +
                '<div class="col-lg-4">' +
                '<label class="col-form-label">เงินเดือนสุดท้าย (Last Salary)</label><span class="text-danger ms-1">*</span>' +
                '<input type="number" name="wh_salary" class="form-control" step="0.01" placeholder="เงินเดือนสุดท้าย"/>' +
                "</div>" +
                '<div class="col-lg-4">' +
                '<label class="col-form-label">Start Date</label><span class="text-danger ms-1">*</span>' +
                '<input type="date" name="wh_date_start" class="form-control"/>' +
                "</div>" +
                '<div class="col-lg-4">' +
                '<label class="col-form-label">End Date</label>' +
                '<input type="date" name="wh_date_end" class="form-control"/>' +
                "</div>" +
                "</div>" +
                "</div>";
            whList.appendChild(card);
        });
        whList.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-wh-remove");
            if (btn) {
                btn.closest(".card").remove();
            }
        });
    }

    function setupAgeCompute() {
        var birthdayInput = document.getElementById("birthday");
        var ageDisplay = document.getElementById("age-display");
        if (!birthdayInput || !ageDisplay) return;

        function computeAge() {
            var val = birthdayInput.value;
            if (!val) {
                ageDisplay.value = "";
                return;
            }
            var birth = new Date(val);
            var today = new Date();
            var age = today.getFullYear() - birth.getFullYear();
            var m = today.getMonth() - birth.getMonth();
            if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
                age--;
            }
            ageDisplay.value = age + " ปี";
        }

        computeAge();
        birthdayInput.addEventListener("change", computeAge);
    }

    function setupTabNavigation() {
        var savedTab = sessionStorage.getItem("profileActiveTab");
        if (savedTab) {
            sessionStorage.removeItem("profileActiveTab");
            var savedTabBtn = document.querySelector(
                '[data-bs-target="' + savedTab + '"]'
            );
            if (savedTabBtn && window.bootstrap && bootstrap.Tab) {
                new bootstrap.Tab(savedTabBtn).show();
            }
        }

        document
            .querySelectorAll('#profileTabs button[data-bs-toggle="tab"]')
            .forEach(function (btn) {
                btn.addEventListener("shown.bs.tab", function (e) {
                    var target = e.target.getAttribute("data-bs-target");
                    if (target) {
                        history.replaceState(null, null, target);
                    }
                });
            });

        // Cross-tab validation
        document
            .querySelectorAll('form[action*="/my/profile"] [required]')
            .forEach(function (field) {
                field.addEventListener("invalid", function () {
                    var pane = this.closest(".tab-pane");
                    if (pane && !pane.classList.contains("active")) {
                        var tabBtn = document.querySelector(
                            '[data-bs-target="#' + pane.id + '"]'
                        );
                        if (tabBtn && window.bootstrap && bootstrap.Tab) {
                            new bootstrap.Tab(tabBtn).show();
                        }
                    }
                });
            });

        // Restore from URL hash
        var hash = window.location.hash;
        if (hash && !savedTab) {
            var hashTabBtn = document.querySelector('[data-bs-target="' + hash + '"]');
            if (hashTabBtn && window.bootstrap && bootstrap.Tab) {
                new bootstrap.Tab(hashTabBtn).show();
            }
        }
    }

    function setupFileInputs() {
        document.querySelectorAll(".js-file-input").forEach(function (input) {
            input.addEventListener("change", function () {
                var wrapper = this.closest(".js-file-upload-wrapper");
                if (!wrapper) return;
                var status = wrapper.querySelector(".js-file-status");
                var removeBtn = wrapper.querySelector(".js-file-remove");
                var uploadBtn = wrapper.querySelector(".js-upload-btn");
                var deleteFlag = wrapper.querySelector(".js-delete-flag");
                if (!status) return;
                if (this.files && this.files.length > 0) {
                    status.innerHTML =
                        '<i class="fa fa-paperclip me-1"></i>' + this.files[0].name;
                    status.className = "small js-file-status text-success";
                    if (removeBtn) removeBtn.style.display = "";
                    if (uploadBtn) uploadBtn.style.display = "none";
                    if (deleteFlag) deleteFlag.value = "0";
                } else {
                    status.textContent = "ยังไม่ได้เลือกไฟล์";
                    status.className = "small js-file-status text-muted";
                    if (removeBtn) removeBtn.style.display = "none";
                    if (uploadBtn) uploadBtn.style.display = "";
                }
            });
        });

        document.querySelectorAll(".js-file-remove").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var wrapper = this.closest(".js-file-upload-wrapper");
                if (!wrapper) return;
                var fileInput = wrapper.querySelector(".js-file-input");
                var status = wrapper.querySelector(".js-file-status");
                var uploadBtn = wrapper.querySelector(".js-upload-btn");
                var deleteFlag = wrapper.querySelector(".js-delete-flag");
                if (fileInput) fileInput.value = "";
                if (status) {
                    status.textContent = "ยังไม่ได้เลือกไฟล์";
                    status.className = "small js-file-status text-muted";
                }
                if (deleteFlag) deleteFlag.value = "1";
                if (uploadBtn) uploadBtn.style.display = "";
                this.style.display = "none";
            });
        });
    }

    function setupMultiFileInputs() {
        document.querySelectorAll(".js-multi-file-input").forEach(function (input) {
            input.addEventListener("change", function () {
                var wrapper = this.closest(".js-multi-file-upload-wrapper");
                if (!wrapper || !this.files || !this.files.length) return;
                var names = Array.from(this.files)
                    .map(function (f) {
                        return f.name;
                    })
                    .join(", ");
                var preview = wrapper.querySelector(".js-pending-files-preview");
                if (!preview) {
                    preview = document.createElement("div");
                    preview.className =
                        "small text-muted mt-2 js-pending-files-preview";
                    this.closest("label").after(preview);
                }
                preview.textContent = names;
            });
        });

        document.querySelectorAll(".js-file-remove-item").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var item = this.closest(".js-uploaded-item");
                if (!item) return;
                var flag = item.querySelector(".js-delete-attachment-flag");
                if (flag) flag.value = "1";
                item.style.display = "none";
            });
        });
    }

    function setupSameAsRegisteredAddress() {
        var cb = document.getElementById("same_as_registered_address");
        var fields = document.getElementById("current_address_fields");
        if (!cb || !fields) return;
        var toggle = function () {
            fields.style.display = cb.checked ? "none" : "";
        };
        cb.addEventListener("change", toggle);
        toggle();
    }

    function initProfilePage() {
        setupToggle("academic_standing_id", "academic_position_details", function (el) {
            return Boolean(el.value);
        });
        setupEducationSections();
        setupToggle("has_ocsc_exam", "ocsc_exam_details", function (el) {
            return el.checked;
        });
        setupWorkHistory();
        setupAgeCompute();
        setupFileInputs();
        setupMultiFileInputs();
        setupSameAsRegisteredAddress();
        setupTabNavigation();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initProfilePage);
    } else {
        initProfilePage();
    }
});
