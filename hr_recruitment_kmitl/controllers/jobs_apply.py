from odoo import http
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.http import request


class WebsiteJobsApply(WebsiteHrRecruitment):
    def _build_address_text(self, profile):
        if not profile:
            return ""
        parts = [
            profile.street or "",
            profile.street2 or "",
            profile.city or "",
            profile.state_id.name if profile.state_id else "",
            profile.zip or "",
            profile.country_id.name if profile.country_id else "",
        ]
        return ", ".join([p for p in parts if p])

    @http.route()
    def jobs_apply(self, job, **kwargs):
        error = {}
        default = {}
        education_by_level = {}
        work_history_ids = request.env["portal.work.history"]

        if "website_hr_recruitment_error" in request.session:
            error = request.session.pop("website_hr_recruitment_error")
            default = request.session.pop("website_hr_recruitment_default")

        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            profile = (
                request.env["portal.profile"]
                .sudo()
                .search([("partner_id", "=", partner.id)], limit=1)
            )
            if profile:
                d = default.setdefault

                name_parts = filter(
                    None,
                    [profile.first_name, profile.middle_name, profile.last_name],
                )
                d("partner_name", " ".join(name_parts))
                d("email_from", profile.email or "")
                d("partner_phone", profile.phone or "")

                # Thai name
                d("applicant_title", profile.title.id if profile.title else "")
                d("first_name", profile.first_name or "")
                d("middle_name", profile.middle_name or "")
                d("last_name", profile.last_name or "")

                # English name
                d("first_name_en", profile.first_name_en or "")
                d("middle_name_en", profile.middle_name_en or "")
                d("last_name_en", profile.last_name_en or "")

                # Personal
                d("age", str(profile.age) if profile.age else "")
                d("address", profile.address or "")
                d("birthday", str(profile.birthday) if profile.birthday else "")
                d(
                    "nationality_id",
                    profile.nationality_id.id if profile.nationality_id else "",
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

                # Address
                d("street", profile.street or "")
                d("street2", profile.street2 or "")
                d("city", profile.city or "")
                d("state_id", profile.state_id.id if profile.state_id else "")
                d("zip", profile.zip or "")
                d("country_id", profile.country_id.name if profile.country_id else "")
                d("address", self._build_address_text(profile))

                # Emergency contact
                d("emergency_contact_name", profile.emergency_contact_name or "")
                d("emergency_contact_relation", profile.emergency_contact_relation or "")
                d("emergency_contact_phone", profile.emergency_contact_phone or "")
                d("emergency_contact_email", profile.emergency_contact_email or "")

                # Health
                d("chronic_disease", profile.chronic_disease or "")

                # Academic
                d("academic_position", profile.academic_position or "")
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

                # Skills
                d("foreign_language_skills", profile.foreign_language_skills or "")
                d("computer_skills", profile.computer_skills or "")
                d("other_abilities", profile.other_abilities or "")
                d("interests", profile.interests or "")

                # Education
                education_by_level = {
                    rec.level: rec for rec in profile.education_history_ids
                }

                # Work Experience
                work_history_ids = profile.work_history_ids.sorted(
                    key=lambda r: (r.date_start or "", r.id), reverse=True
                )

        return request.render(
            "website_hr_recruitment.apply",
            {
                "job": job,
                "error": error,
                "default": default,
                "education_by_level": education_by_level,
                "work_history_ids": work_history_ids,
            },
        )