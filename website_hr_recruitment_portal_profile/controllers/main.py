from odoo import http
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.http import request


class WebsiteHrRecruitmentPortalProfile(WebsiteHrRecruitment):
    @http.route()
    def jobs_apply(self, job, **kwargs):
        error = {}
        default = {}
        if "website_hr_recruitment_error" in request.session:
            error = request.session.pop("website_hr_recruitment_error")
            default = request.session.pop("website_hr_recruitment_default")

        # Pre-fill from portal profile if user is logged in
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            profile = (
                request.env["portal.profile"]
                .sudo()
                .search([("partner_id", "=", partner.id)], limit=1)
            )
            if profile:
                d = default.setdefault
                # Full name for standard partner_name field
                name_parts = filter(
                    None,
                    [profile.first_name, profile.middle_name, profile.last_name],
                )
                d("partner_name", " ".join(name_parts))
                d("email_from", profile.email or "")
                d("partner_phone", profile.phone or "")

                # Thai name
                d("applicant_title", profile.title.name if profile.title else "")
                d("first_name", profile.first_name or "")
                d("middle_name", profile.middle_name or "")
                d("last_name", profile.last_name or "")

                # English name
                d("first_name_en", profile.first_name_en or "")
                d("middle_name_en", profile.middle_name_en or "")
                d("last_name_en", profile.last_name_en or "")

                # Personal
                d("birthday", str(profile.birthday) if profile.birthday else "")
                d(
                    "nationality_id",
                    profile.nationality_id.name if profile.nationality_id else "",
                )
                d("marital", profile.marital or "")

                # Spouse
                d("spouse_prefix", profile.spouse_prefix or "")
                d("spouse_first_name", profile.spouse_first_name or "")
                d("spouse_middle_name", profile.spouse_middle_name or "")
                d("spouse_last_name", profile.spouse_last_name or "")

                # Address
                d("street", profile.street or "")
                d("street2", profile.street2 or "")
                d("city", profile.city or "")
                d("state_id", profile.state_id.name if profile.state_id else "")
                d("zip", profile.zip or "")
                d(
                    "country_id",
                    profile.country_id.name if profile.country_id else "",
                )

                # Emergency contact
                d("emergency_contact_name", profile.emergency_contact_name or "")
                d(
                    "emergency_contact_relation",
                    profile.emergency_contact_relation or "",
                )
                d(
                    "emergency_contact_phone",
                    profile.emergency_contact_phone or "",
                )
                d(
                    "emergency_contact_email",
                    profile.emergency_contact_email or "",
                )

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

        return request.render(
            "website_hr_recruitment.apply",
            {
                "job": job,
                "error": error,
                "default": default,
            },
        )
