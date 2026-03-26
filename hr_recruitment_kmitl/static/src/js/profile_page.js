odoo.define("hr_recruitment_kmitl.profile_page", function (require) {
  "use strict";

  function initProfilePage() {
    // Marital -> spouse fields
    var maritalEl = document.getElementById("marital");
    var spouseFieldsEl = document.getElementById("spouse_fields");
    if (maritalEl && spouseFieldsEl) {
      var toggleSpouseFields = function () {
        spouseFieldsEl.style.display =
          maritalEl.value === "married" ? "" : "none";
      };
      maritalEl.addEventListener("change", toggleSpouseFields);
      toggleSpouseFields();
    }

    // OCSC exam details
    var hasOcscExamEl = document.getElementById("has_ocsc_exam");
    var ocscExamDetailsEl = document.getElementById("ocsc_exam_details");
    if (hasOcscExamEl && ocscExamDetailsEl) {
      var toggleOcscFields = function () {
        ocscExamDetailsEl.classList.toggle("d-none", !hasOcscExamEl.checked);
      };
      hasOcscExamEl.addEventListener("change", toggleOcscFields);
      toggleOcscFields();
    }

    // Restore active tab from sessionStorage
    var savedTab = sessionStorage.getItem("profileActiveTab");
    if (savedTab) {
      sessionStorage.removeItem("profileActiveTab");
      var savedTabBtn = document.querySelector(
        '[data-bs-target="' + savedTab + '"]',
      );
      if (savedTabBtn && window.bootstrap && bootstrap.Tab) {
        new bootstrap.Tab(savedTabBtn).show();
      }
    }

    // Update URL hash on tab switch
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

    // Work history: add/remove rows
    var whTbody = document.getElementById("wh-tbody");
    var whAddBtn = document.getElementById("btn-wh-add");
    if (whAddBtn && whTbody) {
      whAddBtn.addEventListener("click", function () {
        var tr = document.createElement("tr");
        tr.innerHTML =
          '<td><input type="hidden" name="wh_id" value="0"/>' +
          '<input type="text" name="wh_company_name" class="form-control form-control-sm" required="required"/></td>' +
          '<td><input type="text" name="wh_job_title" class="form-control form-control-sm" required="required"/></td>' +
          '<td><input type="number" name="wh_salary" class="form-control form-control-sm" step="0.01" required="required"/></td>' +
          '<td><input type="date" name="wh_date_start" class="form-control form-control-sm" required="required"/></td>' +
          '<td><input type="date" name="wh_date_end" class="form-control form-control-sm"/></td>' +
          '<td><button type="button" class="btn btn-sm btn-outline-danger btn-wh-remove">' +
          '<i class="fa fa-trash"></i></button></td>';
        whTbody.appendChild(tr);
      });

      whTbody.addEventListener("click", function (e) {
        var btn = e.target.closest(".btn-wh-remove");
        if (btn) {
          btn.closest("tr").remove();
        }
      });
    }

    // Compute age from birthday
    var birthdayInput = document.getElementById("birthday");
    var ageDisplay = document.getElementById("age-display");

    function computeAge() {
      if (!birthdayInput || !ageDisplay) return;

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

    if (birthdayInput && ageDisplay) {
      computeAge();
      birthdayInput.addEventListener("change", computeAge);
    }

    // Cross-tab validation
    document
      .querySelectorAll('form[action="/my/profile"] [required]')
      .forEach(function (field) {
        field.addEventListener("invalid", function () {
          var pane = this.closest(".tab-pane");
          if (pane && !pane.classList.contains("active")) {
            var tabBtn = document.querySelector(
              '[data-bs-target="#' + pane.id + '"]',
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
      var hashTabBtn = document.querySelector(
        '[data-bs-target="' + hash + '"]',
      );
      if (hashTabBtn && window.bootstrap && bootstrap.Tab) {
        new bootstrap.Tab(hashTabBtn).show();
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initProfilePage);
  } else {
    initProfilePage();
  }
});
