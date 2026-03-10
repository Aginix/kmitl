from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


EDUCATION_LEVELS = ["doctor", "master", "bachelor", "under_bachelor"]
EDUCATION_FIELDS = ["program", "major", "institution", "country_id", "graduation_date"]


class PortalProfile(CustomerPortal):
    CHAR_FIELDS = [
        "first_name",
        "middle_name",
        "last_name",
        "first_name_en",
        "middle_name_en",
        "last_name_en",
        "email",
        "phone",
        "street",
        "spouse_prefix",
        "spouse_first_name",
        "spouse_middle_name",
        "spouse_last_name",
        "emergency_contact_name",
        "emergency_contact_relation",
        "emergency_contact_phone",
        "emergency_contact_email",
        "ocsc_exam_number",
    ]

    TEXT_FIELDS = [
        "chronic_disease",
        "foreign_language_skills",
        "computer_skills",
        "other_abilities",
        "interests",
    ]

    SELECTION_FIELDS = [
        "marital",
        "academic_position",
        "ocsc_exam_level",
    ]

    DATE_FIELDS = [
        "birthday",
        "academic_position_date",
        "ocsc_exam_date",
    ]

    M2O_FIELDS = [
        "title",
        "nationality_id",
        "zip_id",
    ]

    BOOLEAN_FIELDS = [
        "has_ocsc_exam",
    ]

    def _prepare_profile_render_values(self, partner, profile, error_message=None):
        """Prepare common render values for the profile page."""
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "profile": profile,
                "partner": partner,
                "titles": request.env["res.partner.title"].sudo().search([]),
                "countries": request.env["res.country"].sudo().search([]),
                "zips": request.env["res.city.zip"].sudo().search([]),
                "education_by_level": {
                    rec.level: rec for rec in profile.education_history_ids
                },
                "page_name": "my_profile",
                "error": {},
                "error_message": error_message or [],
            }
        )
        return values

    @http.route(["/my/profile"], type="http", auth="user", website=True)
    def portal_my_profile(self, **post):
        partner = request.env.user.partner_id
        profile = partner.sudo()._get_or_create_profile()

        if post and request.httprequest.method == "POST":
            if post.get("add_work_history"):
                wh_required = {
                    "wh_company_name": "Company",
                    "wh_job_title": "Job Title / Description",
                    "wh_salary": "Salary",
                    "wh_date_start": "Start Date",
                }
                missing = [
                    label
                    for field, label in wh_required.items()
                    if not post.get(field, "").strip()
                ]
                if missing:
                    values = self._prepare_profile_render_values(
                        partner,
                        profile,
                        ["Please fill required fields: %s" % ", ".join(missing)],
                    )
                    return request.render("portal_profile.portal_my_profile", values)
                wh_vals = {
                    "profile_id": profile.id,
                    "company_name": post["wh_company_name"],
                    "job_title": post["wh_job_title"],
                    "date_start": post["wh_date_start"],
                    "date_end": post.get("wh_date_end") or False,
                }
                try:
                    wh_vals["salary"] = float(post["wh_salary"])
                except (ValueError, TypeError):
                    wh_vals["salary"] = 0
                request.env["portal.work.history"].sudo().create(wh_vals)
            else:
                profile_required = {
                    "first_name": "First Name",
                    "last_name": "Last Name",
                    "email": "Email",
                    "phone": "Phone",
                }
                errors = []
                missing_profile = [
                    label
                    for field, label in profile_required.items()
                    if not post.get(field, "").strip()
                ]
                if missing_profile:
                    errors.append(
                        "Please fill required fields: %s" % ", ".join(missing_profile)
                    )
                errors.extend(self._validate_education_history(post))
                if errors:
                    values = self._prepare_profile_render_values(
                        partner, profile, errors
                    )
                    return request.render("portal_profile.portal_my_profile", values)
                vals = self._prepare_profile_values(post)
                profile.sudo().write(vals)
                self._save_education_history(profile, post)
            return request.redirect("/my/profile")

        values = self._prepare_profile_render_values(partner, profile)
        response = request.render("portal_profile.portal_my_profile", values)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    @http.route(
        ["/my/profile/work_history/delete"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_work_history_delete(self, **post):
        partner = request.env.user.partner_id
        profile = partner.sudo()._get_or_create_profile()
        try:
            wh_id = int(post.get("id", 0))
        except (ValueError, TypeError):
            wh_id = 0
        if wh_id:
            record = (
                request.env["portal.work.history"]
                .sudo()
                .search(
                    [("id", "=", wh_id), ("profile_id", "=", profile.id)],
                    limit=1,
                )
            )
            record.unlink()
        return request.redirect("/my/profile")

    EDUCATION_LEVEL_LABELS = {
        "doctor": "Doctoral Degree",
        "master": "Master's Degree",
        "bachelor": "Bachelor's Degree",
        "under_bachelor": "Under Bachelor's Degree",
    }
    EDUCATION_FIELD_LABELS = {
        "program": "Program",
        "major": "Major",
        "institution": "Institution",
        "country_id": "Country",
        "graduation_date": "Graduation Date",
    }

    def _validate_education_history(self, post):
        errors = []
        for level in EDUCATION_LEVELS:
            prefix = f"edu_{level}_"
            values = {
                f: post.get(f"{prefix}{f}", "").strip()
                for f in self.EDUCATION_FIELD_LABELS
            }
            has_any = any(values.values())
            if not has_any:
                continue
            empty = [self.EDUCATION_FIELD_LABELS[f] for f, v in values.items() if not v]
            if empty:
                label = self.EDUCATION_LEVEL_LABELS[level]
                errors.append("%s: please fill %s" % (label, ", ".join(empty)))
        return errors

    def _save_education_history(self, profile, post):
        EduHistory = request.env["portal.education.history"].sudo()
        existing = {rec.level: rec for rec in profile.education_history_ids}
        for level in EDUCATION_LEVELS:
            prefix = f"edu_{level}_"
            program = post.get(f"{prefix}program", "").strip()
            major = post.get(f"{prefix}major", "").strip()
            institution = post.get(f"{prefix}institution", "").strip()
            country_id = int(post.get(f"{prefix}country_id") or 0) or False
            graduation_date = post.get(f"{prefix}graduation_date") or False
            has_data = any([program, major, institution, country_id, graduation_date])
            rec = existing.get(level)
            if has_data:
                vals = {
                    "program": program or False,
                    "major": major or False,
                    "institution": institution or False,
                    "country_id": country_id,
                    "graduation_date": graduation_date,
                }
                if rec:
                    rec.write(vals)
                else:
                    vals.update({"profile_id": profile.id, "level": level})
                    EduHistory.create(vals)
            elif rec:
                rec.unlink()

    def _prepare_profile_values(self, post):
        vals = {}
        for field in self.CHAR_FIELDS + self.TEXT_FIELDS:
            if field in post:
                vals[field] = post[field] or False

        for field in self.SELECTION_FIELDS:
            if field in post:
                vals[field] = post[field] or False

        for field in self.DATE_FIELDS:
            if field in post:
                vals[field] = post[field] or False

        for field in self.M2O_FIELDS:
            if field in post:
                try:
                    vals[field] = int(post[field])
                except (ValueError, TypeError):
                    vals[field] = False

        for field in self.BOOLEAN_FIELDS:
            vals[field] = field in post

        return vals
