odoo.define("hr_recruitment_kmitl.form_editor", function (require) {
    "use strict";

    var core = require("web.core");
    var FormEditorRegistry = require("website.form_editor_registry");

    const _lt = core._lt;

    // Extend the apply_job form with all portal profile fields
    var applyJob = FormEditorRegistry.get("apply_job");
    applyJob.formFields.push(
        // Thai name
        {type: "char", name: "applicant_title", string: _lt("Title")},
        {type: "char", name: "first_name", string: _lt("First Name (TH)")},
        {type: "char", name: "middle_name", string: _lt("Middle Name (TH)")},
        {type: "char", name: "last_name", string: _lt("Last Name (TH)")},
        // English name
        {type: "char", name: "first_name_en", string: _lt("First Name (EN)")},
        {type: "char", name: "middle_name_en", string: _lt("Middle Name (EN)")},
        {type: "char", name: "last_name_en", string: _lt("Last Name (EN)")},
        // Personal
        {type: "char", name: "birthday", string: _lt("Birthday")},
        {type: "char", name: "nationality_id", string: _lt("Nationality")},
        {type: "char", name: "marital", string: _lt("Marital Status")},
        // Address
        {type: "char", name: "street", string: _lt("Street")},
        {type: "char", name: "street2", string: _lt("Street 2")},
        {type: "char", name: "city", string: _lt("City")},
        {type: "char", name: "state_id", string: _lt("State")},
        {type: "char", name: "zip", string: _lt("ZIP")},
        {type: "char", name: "country_id", string: _lt("Country")},
        // Emergency contact
        {
            type: "char",
            name: "emergency_contact_name",
            string: _lt("Emergency Contact Name"),
        },
        {type: "char", name: "emergency_contact_relation", string: _lt("Relation")},
        {type: "tel", name: "emergency_contact_phone", string: _lt("Emergency Phone")},
        {
            type: "email",
            name: "emergency_contact_email",
            string: _lt("Emergency Email"),
        },
        // Health
        {type: "text", name: "congenital_disease", string: _lt("Congenital Disease")},
        // Academic
        {type: "char", name: "academic_standing_id", string: _lt("Academic Position")},
        {
            type: "char",
            name: "academic_position_date",
            string: _lt("Academic Position Date"),
        },
        {
            type: "char",
            name: "academic_position_institution",
            string: _lt("Academic Position Institution"),
        },
        // OCSC exam
        {type: "char", name: "has_ocsc_exam", string: _lt("Has OCSC Exam")},
        {type: "char", name: "ocsc_exam_level", string: _lt("OCSC Exam Level")},
        {type: "char", name: "ocsc_exam_date", string: _lt("OCSC Exam Date")},
        {type: "char", name: "ocsc_exam_number", string: _lt("OCSC Exam Number")},
        // Skills
        {
            type: "text",
            name: "foreign_language_skills",
            string: _lt("Foreign Language Skills"),
        },
        {type: "text", name: "computer_skills", string: _lt("Computer Skills")},
        {type: "text", name: "other_abilities", string: _lt("Other Abilities")},
        {type: "text", name: "interests", string: _lt("Interests")}
    );
});
