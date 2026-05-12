import base64
from odoo import fields, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class PortalOnboardingHome(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "onboarding_count" in counters:
            partner = request.env.user.partner_id
            domain = [
                "|",
                ("applicant_id.partner_id", "=", partner.id),
                ("applicant_id.email_from", "=ilike", partner.email or ""),
            ]
            values["onboarding_count"] = (
                request.env["hr.onboarding"].sudo().search_count(domain)
            )
        return values


class PortalOnboardingController(http.Controller):
    def _get_onboarding_domain(self):
        partner = request.env.user.partner_id
        return [
            "|",
            ("applicant_id.partner_id", "=", partner.id),
            ("applicant_id.email_from", "=ilike", partner.email or ""),
        ]

    def _get_onboarding_for_user(self, onboarding_id):
        onboarding = request.env["hr.onboarding"].sudo().browse(onboarding_id)
        if not onboarding.exists():
            return None
        partner = request.env.user.partner_id
        partner_match = (
            onboarding.applicant_id.partner_id
            and onboarding.applicant_id.partner_id.id == partner.id
        )
        email_match = (
            onboarding.applicant_id.email_from
            and partner.email
            and onboarding.applicant_id.email_from.lower() == partner.email.lower()
        )
        if not partner_match and not email_match:
            return None
        return onboarding

    def _compute_age(self, birthday):
        if not birthday:
            return ""
        today = fields.Date.today()
        years = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            years -= 1
        return str(years)

    def _selection_label(self, record, field_name, value):
        if not record or not value:
            return value or ""
        field = record._fields.get(field_name)
        if not field or not field.selection:
            return value or ""
        return dict(field.selection).get(value, value)

    def _prepare_values(self, onboarding):
        applicant = onboarding.applicant_id
        # partner = applicant.partner_id or request.env.user.partner_id

        # Prepare education items from applicant
        education_items = []
        if applicant.education_history_ids:
            for edu in applicant.education_history_ids:
                education_items.append(
                    {
                        "level": edu.education_level_id.name
                        if edu.education_level_id
                        else "-",
                        "program": edu.program or "-",
                        "major": edu.major or "-",
                        "institution": edu.institution or "-",
                        "country": edu.country_id.name if edu.country_id else "-",
                        "graduation_date": fields.Date.to_string(edu.graduation_date)
                        if edu.graduation_date
                        else "-",
                        "certificate_url": (
                            f"/web/content?model=hr.applicant.education.history&id={edu.id}&field=certificate_file&filename_field=certificate_filename&download=true"
                            if edu.certificate_file
                            else False
                        ),
                        "certificate_filename": edu.certificate_filename or "",
                        "transcript_url": (
                            # f"/web/content/hr.applicant.education.history/{edu.id}/transcript_file/{edu.transcript_filename or 'transcript'}?download=true"
                            f"/web/content?model=hr.applicant.education.history&id={edu.id}&field=transcript_file&filename_field=transcript_filename&download=true"
                            if edu.transcript_file
                            else False
                        ),
                        "transcript_filename": edu.transcript_filename or "",
                    }
                )

        # Prepare attachment items for Many2many groups
        def prepare_attachment_items(attachment_ids):
            items = []
            for att in attachment_ids:
                items.append(
                    {
                        "id": att.id,
                        "filename": att.name,
                        "download_url": f"/web/content/{att.id}?download=true",
                    }
                )
            return items

        return {
            "onboarding": onboarding,
            "applicant": applicant,
            "age": self._compute_age(applicant.birthday),
            "page_name": "onboarding",
            "education_items": education_items,
            "health_employee_attachments": prepare_attachment_items(
                onboarding.health_employee_attachment_ids
            ),
            "health_family_attachments": prepare_attachment_items(
                onboarding.health_family_attachment_ids
            ),
            "accident_employee_attachments": prepare_attachment_items(
                onboarding.accident_employee_attachment_ids
            ),
            "accident_family_attachments": prepare_attachment_items(
                onboarding.accident_family_attachment_ids
            ),
        }

    def _save_main(self, onboarding, post, files):
        vals = {}

        # Simple fields
        for field in [
            "blood_type",
            "background_check_location_type",
            "krungthai_bank_account",
            "bank_account_name",
            "pdpa_consent",
        ]:
            if field in post:
                vals[field] = post.get(field) or False

        # Boolean field
        vals["final_confirm"] = "final_confirm" in post

        # Date fields
        for field in ["starting_date"]:
            if field in post and post.get(field):
                vals[field] = post.get(field)

        # Text fields
        for field in ["starting_date_note"]:
            if field in post:
                vals[field] = post.get(field) or False

        # Royal decoration fields
        for field in [
            "royal_decoration_level",
            "royal_decoration_year",
            "royal_decoration_agency",
        ]:
            if field in post:
                try:
                    if field.endswith("_year") or field.endswith("_level"):
                        vals[field] = int(post.get(field)) if post.get(field) else False
                    else:
                        vals[field] = post.get(field) or False
                except (ValueError, TypeError):
                    vals[field] = False

        if "royal_decoration_id" in post:
            try:
                vals["royal_decoration_id"] = (
                    int(post.get("royal_decoration_id")) or False
                )
            except (ValueError, TypeError):
                vals["royal_decoration_id"] = False

        if vals:
            onboarding.write(vals)

    def _save_family(self, onboarding, form):
        FamilyModel = request.env["hr.onboarding.family"].sudo()
        family_ids = form.getlist("family_id")
        family_relation_ids = form.getlist("family_relation_id")
        family_identifications = form.getlist("family_identification_id")
        family_prefixes = form.getlist("family_prefix_id")
        family_first_names = form.getlist("family_first_name")
        family_middle_names = form.getlist("family_middle_name")
        family_last_names = form.getlist("family_last_name")
        family_dates_of_birth = form.getlist("family_date_of_birth")
        family_jobs = form.getlist("family_job")
        family_phones = form.getlist("family_phone")
        family_statuses = form.getlist("family_status")

        submitted_ids = set()
        for i in range(len(family_ids)):
            family_id = int(family_ids[i] or 0)
            relation_id = (
                int(family_relation_ids[i] or 0) if i < len(family_relation_ids) else 0
            )

            if not relation_id:
                continue

            vals = {
                "onboarding_id": onboarding.id,
                "relation_id": relation_id,
                "identification_id": family_identifications[i]
                if i < len(family_identifications)
                else "",
                "prefix_id": int(family_prefixes[i])
                if (i < len(family_prefixes) and family_prefixes[i])
                else False,
                "first_name": family_first_names[i]
                if i < len(family_first_names)
                else "",
                "middle_name": family_middle_names[i]
                if i < len(family_middle_names)
                else "",
                "last_name": family_last_names[i] if i < len(family_last_names) else "",
                "date_of_birth": family_dates_of_birth[i]
                if (i < len(family_dates_of_birth) and family_dates_of_birth[i])
                else False,
                "job": family_jobs[i] if i < len(family_jobs) else "",
                "phone": family_phones[i] if i < len(family_phones) else "",
                "status": family_statuses[i] if i < len(family_statuses) else False,
            }

            if family_id:
                rec = FamilyModel.search(
                    [("id", "=", family_id), ("onboarding_id", "=", onboarding.id)],
                    limit=1,
                )
                if rec:
                    rec.write(vals)
                    submitted_ids.add(family_id)
            else:
                new_rec = FamilyModel.create(vals)
                submitted_ids.add(new_rec.id)

        # Unlink removed rows
        for rec in onboarding.family_member_ids:
            if rec.id not in submitted_ids:
                rec.unlink()

    def _save_single_file(self, onboarding, prefix, post, files):
        for file_suffix in ["_file", "_filename"]:
            if (
                f"delete_{prefix}{file_suffix}" in post
                and post.get(f"delete_{prefix}{file_suffix}") == "1"
            ):
                onboarding.write({f"{prefix}{file_suffix}": False})

        file_input_name = f"{prefix}_file"
        if file_input_name in files:
            uploaded = files.get(file_input_name)
            if uploaded and uploaded.filename:
                onboarding.write(
                    {
                        f"{prefix}_file": base64.b64encode(uploaded.read()),
                        f"{prefix}_filename": uploaded.filename,
                    }
                )

    def _save_multi_attachments(self, onboarding, m2m_field, post, files):
        AttachmentModel = request.env["ir.attachment"].sudo()
        delete_prefix = f"delete_attachment_{m2m_field}_"

        # Process deletes
        for key in post:
            if key.startswith(delete_prefix):
                att_id = int(key.replace(delete_prefix, ""))
                current = getattr(onboarding, m2m_field)
                if att_id in current.ids:
                    current -= AttachmentModel.browse(att_id)

        # Process uploads
        file_input_prefix = f"{m2m_field}_attachment"
        if file_input_prefix in files:
            uploaded = files.get(file_input_prefix)
            if uploaded and uploaded.filename:
                attachment = AttachmentModel.create(
                    {
                        "name": uploaded.filename,
                        "datas": base64.b64encode(uploaded.read()),
                        "res_model": "hr.onboarding",
                        "res_id": onboarding.id,
                    }
                )
                getattr(onboarding, m2m_field).add(attachment)

    @http.route(["/my/onboarding"], type="http", auth="user", website=True)
    def portal_my_onboarding_list(self, **kwargs):
        HrOnboarding = request.env["hr.onboarding"].sudo()
        domain = self._get_onboarding_domain()

        pending_onboardings = HrOnboarding.search(
            domain + [("state", "=", "draft")], order="create_date desc"
        )
        submitted_onboardings = HrOnboarding.search(
            domain + [("state", "=", "submitted")], order="submitted_date desc"
        )

        values = {
            "pending_onboardings": pending_onboardings,
            "submitted_onboardings": submitted_onboardings,
            "page_name": "onboarding",
        }
        return request.render("hr_recruitment_kmitl.portal_my_onboarding_list", values)

    @http.route(
        ["/my/onboarding/<int:onboarding_id>"], type="http", auth="user", website=True
    )
    def portal_my_onboarding_detail(self, onboarding_id, **kwargs):
        onboarding = self._get_onboarding_for_user(onboarding_id)
        if not onboarding:
            return request.redirect("/my/onboarding")

        values = self._prepare_values(onboarding)
        return request.render(
            "hr_recruitment_kmitl.portal_my_onboarding_detail", values
        )

    @http.route(
        ["/my/onboarding/form/<int:onboarding_id>"],
        type="http",
        auth="user",
        website=True,
        methods=["GET", "POST"],
    )
    def portal_my_onboarding_form(self, onboarding_id, **post):
        onboarding = self._get_onboarding_for_user(onboarding_id)
        if not onboarding:
            return request.redirect("/my/onboarding")

        # Redirect if submitted
        if onboarding.state == "submitted":
            return request.redirect(f"/my/onboarding/{onboarding_id}")

        if post and request.httprequest.method == "POST":
            self._save_main(onboarding, post, request.httprequest.files)
            self._save_family(onboarding, request.httprequest.form)

            # Save file uploads for single-file fields
            for prefix in [
                "royal_decoration_proof",
                "starting_date_attachment",
                "provident_fund",
                "beneficiary_declaration",
                "letter_of_consent",
                "salary_book",
                "medical_certificate",
            ]:
                self._save_single_file(
                    onboarding, prefix, post, request.httprequest.files
                )

            # Save multi-attachment fields
            for m2m_field in [
                "health_employee_attachment_ids",
                "health_family_attachment_ids",
                "accident_employee_attachment_ids",
                "accident_family_attachment_ids",
            ]:
                self._save_multi_attachments(
                    onboarding, m2m_field, post, request.httprequest.files
                )

            onboarding.action_submit()
            return request.redirect(f"/my/onboarding/{onboarding_id}")

        values = self._prepare_values(onboarding)
        return request.render("hr_recruitment_kmitl.portal_my_onboarding_form", values)
