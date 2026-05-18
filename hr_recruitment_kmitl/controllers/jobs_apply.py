import json

from odoo import http
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.http import request


class WebsiteJobsApply(WebsiteHrRecruitment):
    def _build_address_text(self, profile, prefix="address"):
        if not profile:
            return ""
        street = getattr(profile, f"{prefix}_street", "") or ""
        city = getattr(profile, f"{prefix}_city", "") or ""
        state = getattr(profile, f"{prefix}_state_id", False)
        zip_code = getattr(profile, f"{prefix}_zip", "") or ""
        country = getattr(profile, f"{prefix}_country_id", False)
        parts = [
            street,
            city,
            state.name if state else "",
            zip_code,
            country.name if country else "",
        ]
        return ", ".join([p for p in parts if p])

    @http.route(
        """/jobs/apply/<model("hr.job"):job>""",
        type="http",
        auth="user",
        website=True,
        sitemap=True,
    )
    def jobs_apply(self, job, **kwargs):
        error = {}
        default = {}
        education_by_level = {}
        education_json = "{}"
        work_history_ids = request.env["portal.work.history"]
        profile = request.env["portal.profile"]

        if "website_hr_recruitment_error" in request.session:
            error = request.session.pop("website_hr_recruitment_error")
            default = request.session.pop("website_hr_recruitment_default")

        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            profile = (
                request.env["portal.profile"]
                .sudo()
                .with_context(lang="th_TH")
                .search([("partner_id", "=", partner.id)], limit=1)
            )

            if profile:
                d = default.setdefault

                name_parts = filter(
                    None,
                    [
                        profile.with_context(lang="th_TH").title.name,
                        profile.first_name,
                        profile.middle_name,
                        profile.last_name,
                    ],
                )

                name_en_parts = filter(
                    None,
                    [
                        profile.with_context(lang="en_US").title.name,
                        profile.first_name_en,
                        profile.middle_name_en,
                        profile.last_name_en,
                    ],
                )

                d("partner_name", " ".join(name_parts))
                d("partner_name_en", " ".join(name_en_parts))
                d("email_from", profile.email or "")
                d("partner_phone", profile.phone or "")

                # Thai name
                d("applicant_title", profile.title.id if profile.title else "")
                d("applicant_title_name", profile.title.name if profile.title else "")
                d("first_name", profile.first_name or "")
                d("middle_name", profile.middle_name or "")
                d("last_name", profile.last_name or "")

                # English name
                d("first_name_en", profile.first_name_en or "")
                d("middle_name_en", profile.middle_name_en or "")
                d("last_name_en", profile.last_name_en or "")

                # Personal
                d("identification_id", profile.identification_id or "")
                d("age", str(profile.age) if profile.age else "")
                gender_labels = {"male": "ชาย (Male)", "female": "หญิง (Female)"}
                d("gender", gender_labels.get(profile.gender, ""))
                d("address_address", profile.address_address or "")
                d("birthday", str(profile.birthday) if profile.birthday else "")
                d(
                    "nationality_id",
                    profile.nationality_id.name if profile.nationality_id else "",
                )
                d("marital", profile.marital or "")

                # Spouse
                d(
                    "spouse_prefix",
                    profile.spouse_prefix.name if profile.spouse_prefix else "",
                )
                d("spouse_first_name", profile.spouse_first_name or "")
                d("spouse_middle_name", profile.spouse_middle_name or "")
                d("spouse_last_name", profile.spouse_last_name or "")

                # Registered address
                d("address_street", profile.address_street or "")
                d("address_city", profile.address_city or "")
                d(
                    "address_state_id",
                    profile.address_state_id.id if profile.address_state_id else "",
                )
                d("address_zip", profile.address_zip or "")
                d(
                    "address_country_id",
                    profile.address_country_id.name
                    if profile.address_country_id
                    else "",
                )
                d("address_address", self._build_address_text(profile, "address"))

                # Current address
                d("current_street", profile.current_street or "")
                d("current_city", profile.current_city or "")
                d(
                    "current_state_id",
                    profile.current_state_id.id if profile.current_state_id else "",
                )
                d("current_zip", profile.current_zip or "")
                d(
                    "current_country_id",
                    profile.current_country_id.name
                    if profile.current_country_id
                    else "",
                )
                d("current_address", self._build_address_text(profile, "current"))

                # Emergency contact
                d("emergency_contact_name", profile.emergency_contact_name or "")
                d(
                    "emergency_contact_relation",
                    profile.emergency_contact_relation or "",
                )
                d("emergency_contact_phone", profile.emergency_contact_phone or "")
                d("emergency_contact_email", profile.emergency_contact_email or "")

                # Health
                d("congenital_disease", profile.congenital_disease or "")

                # Academic
                d(
                    "academic_standing_id",
                    profile.academic_standing_id.name
                    if profile.academic_standing_id
                    else "",
                )
                d(
                    "academic_position_date",
                    str(profile.academic_position_date)
                    if profile.academic_position_date
                    else "",
                )
                d(
                    "academic_position_institution",
                    profile.academic_position_institution or "",
                )

                # OCSC exam
                d("has_ocsc_exam", "true" if profile.has_ocsc_exam else "")
                d("ocsc_exam_level", profile.ocsc_exam_level or "")
                d(
                    "ocsc_exam_date",
                    str(profile.ocsc_exam_date) if profile.ocsc_exam_date else "",
                )
                d("ocsc_exam_number", profile.ocsc_exam_number or "")

                # English test
                d("english_test_type", profile.english_test_type or "")
                d("english_test_score", profile.english_test_score or "")
                d(
                    "english_test_date",
                    str(profile.english_test_date) if profile.english_test_date else "",
                )
                d(
                    "english_test_certificate_number",
                    profile.english_test_certificate_number or "",
                )

                # Skills
                d("foreign_language_skills", profile.foreign_language_skills or "")
                d("computer_skills", profile.computer_skills or "")
                d("other_abilities", profile.other_abilities or "")
                d("interests", profile.interests or "")

                # Education
                edu_sorted = profile.education_history_ids.sorted(
                    key=lambda r: r.education_level_id.level or 0,
                    reverse=True,
                )
                education_by_level = {
                    rec.education_level_id.id: rec for rec in edu_sorted
                }
                education_json = json.dumps(
                    {
                        str(rec.education_level_id.id): {
                            "level_id": rec.education_level_id.id,
                            "level_name": rec.education_level_id.name,
                            "program": rec.program or "",
                            "major": rec.major or "",
                            "institution": rec.institution or "",
                            "graduation_date": str(rec.graduation_date)
                            if rec.graduation_date
                            else "",
                            "country_id": rec.country_id.id if rec.country_id else "",
                        }
                        for rec in edu_sorted
                    }
                )

                # Work Experience
                work_history_ids = profile.work_history_ids.sorted(
                    key=lambda r: (r.date_start or "", r.id), reverse=True
                )

        # Remove role-irrelevant defaults
        _ACADEMIC_DEFAULTS = [
            "academic_standing_id",
            "academic_position_date",
            "academic_position_institution",
            "english_test_type",
            "english_test_score",
            "english_test_date",
            "english_test_certificate_number",
        ]
        _SUPPORT_DEFAULTS = [
            "has_ocsc_exam",
            "ocsc_exam_level",
            "ocsc_exam_date",
            "ocsc_exam_number",
            "foreign_language_skills",
            "computer_skills",
            "other_abilities",
            "interests",
        ]
        if job.role == "academic":
            for f in _SUPPORT_DEFAULTS:
                default.pop(f, None)
        elif job.role == "support":
            for f in _ACADEMIC_DEFAULTS:
                default.pop(f, None)

        return request.render(
            "website_hr_recruitment.apply",
            {
                "job": job,
                "error": error,
                "default": default,
                "profile": profile,
                "education_by_level": education_by_level,
                "education_json": education_json,
                "work_history_ids": work_history_ids,
            },
        )
