import json

from odoo import http
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.http import request


class WebsiteHrRecruitmentProfile(WebsiteHrRecruitment):
    @http.route()
    def jobs_apply(self, job, **kwargs):
        error = {}
        default = {}
        if "website_hr_recruitment_error" in request.session:
            error = request.session.pop("website_hr_recruitment_error")
            default = request.session.pop("website_hr_recruitment_default")

        education_prefill = []
        countries = request.env["res.country"].sudo().search([])

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

                # Education history pre-fill
                for edu in profile.education_history_ids:
                    education_prefill.append(
                        {
                            "level": edu.level or "",
                            "program": edu.program or "",
                            "major": edu.major or "",
                            "institution": edu.institution or "",
                            "country_id": edu.country_id.id if edu.country_id else "",
                            "graduation_date": str(edu.graduation_date)
                            if edu.graduation_date
                            else "",
                        }
                    )

        return request.render(
            "website_hr_recruitment.apply",
            {
                "job": job,
                "error": error,
                "default": default,
                "education_prefill": json.dumps(education_prefill),
                "countries": countries,
            },
        )


class WebsiteFormEducation(WebsiteForm):
    """Override form handler to process education history from indexed fields."""

    def _handle_website_form(self, model_name, **kwargs):
        # Only intercept hr.applicant forms
        if model_name != "hr.applicant":
            return super()._handle_website_form(model_name, **kwargs)

        # Extract education fields from kwargs before super() processes them
        education_data = self._extract_education_data(kwargs)

        # Remove education fields so they don't end up in custom fields text
        for key in list(kwargs.keys()):
            if key.startswith("education_"):
                del kwargs[key]

        # Let standard flow create the hr.applicant record
        result = super()._handle_website_form(model_name, **kwargs)

        # Create education records if form had education data
        try:
            result_data = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return result

        if result_data.get("id") and education_data:
            applicant = request.env["hr.applicant"].sudo().browse(result_data["id"])
            # Remove any education records created by _prefill_from_profile
            applicant.education_history_ids.unlink()
            # Create from form data
            self._create_education_history(result_data["id"], education_data)

        return result

    def _extract_education_data(self, kwargs):
        """Parse indexed education fields into a list of dicts.

        Form fields are named: education_{field}_{index}
        e.g. education_level_0, education_program_0, education_country_id_0
        """
        entries = {}
        for key, value in kwargs.items():
            if not key.startswith("education_"):
                continue
            parts = key.split("_")
            # Last part is the index
            idx = parts[-1]
            if not idx.isdigit():
                continue
            idx = int(idx)
            # Field name is everything between 'education_' and the index
            field = "_".join(parts[1:-1])
            if idx not in entries:
                entries[idx] = {}
            entries[idx][field] = value
        return [entries[i] for i in sorted(entries.keys())]

    def _create_education_history(self, applicant_id, education_data):
        """Create hr.applicant.education.history records from form data."""
        EduHistory = request.env["hr.applicant.education.history"].sudo()
        for entry in education_data:
            level = (entry.get("level") or "").strip()
            if not level:
                continue  # Skip empty rows
            vals = {
                "applicant_id": applicant_id,
                "level": level,
                "program": (entry.get("program") or "").strip() or False,
                "major": (entry.get("major") or "").strip() or False,
                "institution": (entry.get("institution") or "").strip() or False,
                "country_id": int(entry.get("country_id") or 0) or False,
                "graduation_date": entry.get("graduation_date") or False,
            }
            EduHistory.create(vals)
