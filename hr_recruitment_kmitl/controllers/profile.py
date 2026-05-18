import base64

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


EDUCATION_FIELDS = ["program", "major", "institution", "country_id", "graduation_date"]


def must_set_email():
    """Return True when the current user signed up via Thai ID and their email
    is still the placeholder Thai ID number (not yet a real email)."""
    user = request.env.user
    return bool(user.oauth_uid) and user.partner_id.email == user.oauth_uid


class PortalProfile(CustomerPortal):
    CHAR_FIELDS = [
        "identification_id",
        "first_name",
        "middle_name",
        "last_name",
        "first_name_en",
        "middle_name_en",
        "last_name_en",
        "email",
        "phone",
        "address_street",
        "current_street",
        "spouse_first_name",
        "spouse_middle_name",
        "spouse_last_name",
        "emergency_contact_name",
        "emergency_contact_relation",
        "emergency_contact_phone",
        "emergency_contact_email",
        "ocsc_exam_number",
        "academic_position_institution",
        "english_test_score",
        "english_test_certificate_number",
    ]

    TEXT_FIELDS = [
        "congenital_disease",
        "foreign_language_skills",
        "computer_skills",
        "other_abilities",
        "interests",
    ]

    SELECTION_FIELDS = [
        "gender",
        "marital",
        "ocsc_exam_level",
        "highest_education",
        "english_test_type",
    ]

    DATE_FIELDS = [
        "birthday",
        "academic_position_date",
        "ocsc_exam_date",
        "english_test_date",
    ]

    M2O_FIELDS = [
        "title",
        "spouse_prefix",
        "nationality_id",
        "address_zip_id",
        "current_zip_id",
        "academic_standing_id",
    ]

    BOOLEAN_FIELDS = [
        "has_ocsc_exam",
        "same_as_registered_address",
    ]

    def _is_email_editable(self, profile):
        return must_set_email()

    def _prepare_profile_render_values(self, partner, profile, error_message=None):
        """Prepare common render values for the profile page."""
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "profile": profile,
                "partner": partner,
                "email_editable": self._is_email_editable(profile),
                "titles": request.env["res.partner.title"].sudo().search([]),
                "countries": request.env["res.country"].sudo().search([]),
                "zips": request.env["res.city.zip"].sudo().search([]),
                "academic_standings": request.env["hr.employee.academic.standing"]
                .sudo()
                .search([]),
                "education_levels": request.env["resource.education.level"]
                .sudo()
                .search(
                    [("level", "in", [90, 80, 70])],
                    order="level desc",
                ),
                "sub_bachelor_levels": request.env["resource.education.level"]
                .sudo()
                .search([("level", "<", 70)], order="level desc"),
                "education_by_level": {
                    rec.education_level_id.id: rec
                    for rec in profile.education_history_ids
                },
                "sub_bachelor_edu_rec": next(
                    (
                        rec
                        for rec in profile.education_history_ids
                        if rec.education_level_id.level
                        and rec.education_level_id.level < 70
                    ),
                    False,
                ),
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
            email_editable = self._is_email_editable(profile)
            profile_required = {
                "title": "Title",
                "first_name": "First Name",
                "last_name": "Last Name",
                "first_name_en": "First Name (EN)",
                "last_name_en": "Last Name (EN)",
                "identification_id": "Identification No.",
                "nationality_id": "Nationality",
                "gender": "Gender",
                "birthday": "Birthday",
                "phone": "Phone",
                "address_street": "Registered Address",
                "address_zip_id": "Registered ZIP Location",
                "marital": "Marital Status",
                "emergency_contact_name": "Emergency Contact Name",
                "emergency_contact_relation": "Emergency Contact Relation",
                "emergency_contact_phone": "Emergency Contact Phone",
                "emergency_contact_email": "Emergency Contact Email",
            }
            if email_editable:
                profile_required["email"] = "Email"
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
            if email_editable:
                submitted_email = post.get("email", "").strip()
                if submitted_email and submitted_email == request.env.user.oauth_uid:
                    errors.append(
                        "กรุณาเปลี่ยนอีเมลให้เป็นอีเมลจริง (อีเมลปัจจุบันยังเป็นเลขบัตรประชาชน)"
                    )
                elif submitted_email and "@" not in submitted_email:
                    errors.append("กรุณากรอกอีเมลให้ถูกต้อง")
            errors.extend(self._validate_education_history(post))
            errors.extend(self._validate_work_history(request.httprequest.form))
            if errors:
                values = self._prepare_profile_render_values(partner, profile, errors)
                return request.render("hr_recruitment_kmitl.portal_my_profile", values)
            vals = self._prepare_profile_values(post)
            if not email_editable:
                vals.pop("email", None)
            profile.sudo().write(vals)
            self._save_education_history(profile, post)
            self._save_work_history(profile, request.httprequest.form)
            for doc_name, field_name in [
                ("doc_photo", "photo"),
                ("doc_ocsc_proof", "ocsc_exam"),
                ("doc_academic_position", "academic_position"),
                ("doc_resume", "resume"),
                ("doc_military_certificate", "military_certificate"),
                ("doc_id_card", "id_card"),
                ("doc_household_registration", "household_registration"),
                ("doc_work_certificate", "work_certificate"),
                ("doc_english_score", "english_score"),
                ("doc_other_documents", "other_documents"),
            ]:
                if post.get(f"delete_{doc_name}") == "1":
                    profile.sudo().write(
                        {f"{field_name}_file": False, f"{field_name}_filename": False}
                    )
                else:
                    uploaded = request.httprequest.files.get(doc_name)
                    if uploaded and uploaded.filename:
                        profile.sudo().write(
                            {
                                f"{field_name}_file": base64.b64encode(uploaded.read()),
                                f"{field_name}_filename": uploaded.filename,
                            }
                        )
            if post.get("delete_doc_photo") == "1":
                partner.sudo().write({"image_1920": False})
            else:
                uploaded_photo = request.httprequest.files.get("doc_photo")
                if uploaded_photo and uploaded_photo.filename:
                    partner.sudo().write({"image_1920": profile.photo_file})
            return request.redirect("/my/profile")

        values = self._prepare_profile_render_values(partner, profile)
        response = request.render("hr_recruitment_kmitl.portal_my_profile", values)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    EDUCATION_FIELD_LABELS = {
        "program": "Program",
        "major": "Major",
        "institution": "Institution",
        "country_id": "Country",
        "graduation_date": "Graduation Date",
    }

    def _get_main_education_levels(self):
        return (
            request.env["resource.education.level"]
            .sudo()
            .search([("level", "in", [90, 80, 70])], order="level desc")
        )

    def _validate_education_section(self, post, prefix, label):
        """Validate a single education section by prefix."""
        errors = []
        values = {
            f: post.get(f"{prefix}{f}", "").strip() for f in self.EDUCATION_FIELD_LABELS
        }
        has_any = any(values.values())
        if not has_any:
            return errors
        empty = [self.EDUCATION_FIELD_LABELS[f] for f, v in values.items() if not v]
        if empty:
            errors.append("%s: please fill %s" % (label, ", ".join(empty)))
        return errors

    EDUCATION_VISIBILITY = {
        "doctor": [90, 80, 70],
        "master": [80, 70],
        "bachelor": [70],
        "under_bachelor": [],
    }

    def _validate_education_history(self, post):
        errors = []
        highest = post.get("highest_education", "")
        visible_levels = self.EDUCATION_VISIBILITY.get(highest, [])
        for level in self._get_main_education_levels():
            if level.level in visible_levels:
                errors.extend(
                    self._validate_education_section(
                        post, f"edu_{level.id}_", level.name
                    )
                )
        if highest == "under_bachelor":
            errors.extend(
                self._validate_education_section(post, "edu_sub_", "ต่ำกว่าปริญญาตรี")
            )
        return errors

    def _save_education_section(self, profile, post, prefix, level_id, existing):
        """Save a single education section. Returns the level_id if saved."""
        EduHistory = request.env["portal.education.history"].sudo()
        program = post.get(f"{prefix}program", "").strip()
        major = post.get(f"{prefix}major", "").strip()
        institution = post.get(f"{prefix}institution", "").strip()
        country_id = int(post.get(f"{prefix}country_id") or 0) or False
        graduation_date = post.get(f"{prefix}graduation_date") or False
        has_data = any([program, major, institution, country_id, graduation_date])
        rec = existing.get(level_id)
        if has_data:
            vals = {
                "education_level_id": level_id,
                "program": program or False,
                "major": major or False,
                "institution": institution or False,
                "country_id": country_id,
                "graduation_date": graduation_date,
            }
            if rec:
                rec.write(vals)
            else:
                vals["profile_id"] = profile.id
                rec = EduHistory.create(vals)
            self._save_education_files(rec, prefix)
        elif rec:
            rec.unlink()

    def _save_education_files(self, rec, prefix):
        """Handle certificate and transcript file uploads for an education record."""
        for doc_type in ("certificate", "transcript"):
            delete_flag = f"delete_{prefix}{doc_type}_file"
            file_input = f"{prefix}{doc_type}_file"
            if request.httprequest.form.get(delete_flag) == "1":
                rec.write({f"{doc_type}_file": False, f"{doc_type}_filename": False})
            else:
                uploaded = request.httprequest.files.get(file_input)
                if uploaded and uploaded.filename:
                    rec.write(
                        {
                            f"{doc_type}_file": base64.b64encode(uploaded.read()),
                            f"{doc_type}_filename": uploaded.filename,
                        }
                    )

    def _save_education_history(self, profile, post):
        existing = {
            rec.education_level_id.id: rec for rec in profile.education_history_ids
        }
        highest = post.get("highest_education", "")
        visible_levels = self.EDUCATION_VISIBILITY.get(highest, [])
        for level in self._get_main_education_levels():
            if level.level in visible_levels:
                self._save_education_section(
                    profile, post, f"edu_{level.id}_", level.id, existing
                )
            elif existing.get(level.id):
                existing.pop(level.id).unlink()
        # Sub-bachelor section
        old_sub = next(
            (
                rec
                for lid, rec in existing.items()
                if rec.education_level_id.level and rec.education_level_id.level < 70
            ),
            False,
        )
        if highest == "under_bachelor":
            sub_level_id = int(post.get("edu_sub_education_level_id") or 0) or False
            if old_sub and old_sub.education_level_id.id != sub_level_id:
                old_sub.unlink()
                existing.pop(old_sub.education_level_id.id, None)
            if sub_level_id:
                self._save_education_section(
                    profile, post, "edu_sub_", sub_level_id, existing
                )
        elif old_sub:
            old_sub.unlink()

    WH_REQUIRED_FIELDS = {
        "wh_company_name": "Company",
        "wh_job_title": "Job Title / Description",
        "wh_salary": "Last Salary",
        "wh_date_start": "Start Date",
    }

    def _validate_work_history(self, form):
        errors = []
        wh_company_names = form.getlist("wh_company_name")
        if not wh_company_names:
            return errors
        field_lists = {key: form.getlist(key) for key in self.WH_REQUIRED_FIELDS}
        for i in range(len(wh_company_names)):
            missing = []
            for key, label in self.WH_REQUIRED_FIELDS.items():
                values = field_lists[key]
                val = values[i].strip() if i < len(values) else ""
                if not val:
                    missing.append(label)
            if missing:
                errors.append(
                    "Work History row %d: please fill %s" % (i + 1, ", ".join(missing))
                )
        return errors

    def _save_work_history(self, profile, form):
        """Save work history from multi-value form fields."""
        WorkHistory = request.env["portal.work.history"].sudo()
        wh_ids = form.getlist("wh_id")
        wh_company_names = form.getlist("wh_company_name")
        wh_job_titles = form.getlist("wh_job_title")
        wh_salaries = form.getlist("wh_salary")
        wh_date_starts = form.getlist("wh_date_start")
        wh_date_ends = form.getlist("wh_date_end")

        submitted_ids = set()
        for i in range(len(wh_ids)):
            wh_id = int(wh_ids[i] or 0)
            vals = {
                "company_name": wh_company_names[i]
                if i < len(wh_company_names)
                else "",
                "job_title": wh_job_titles[i] if i < len(wh_job_titles) else "",
                "date_start": wh_date_starts[i] if i < len(wh_date_starts) else False,
                "date_end": wh_date_ends[i] if i < len(wh_date_ends) else False,
            }
            try:
                vals["salary"] = float(wh_salaries[i]) if i < len(wh_salaries) else 0
            except (ValueError, TypeError):
                vals["salary"] = 0
            if not vals["date_start"]:
                vals["date_start"] = False
            if not vals["date_end"]:
                vals["date_end"] = False
            if wh_id:
                rec = WorkHistory.search(
                    [("id", "=", wh_id), ("profile_id", "=", profile.id)], limit=1
                )
                if rec:
                    rec.write(vals)
                    submitted_ids.add(wh_id)
            else:
                if vals.get("company_name"):
                    vals["profile_id"] = profile.id
                    new_rec = WorkHistory.create(vals)
                    submitted_ids.add(new_rec.id)

        # Delete removed rows
        for rec in profile.work_history_ids:
            if rec.id not in submitted_ids:
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
