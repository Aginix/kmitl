# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request

from .profile import must_set_email


class HrRecruitmentPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "application_count" in counters:
            domain = self._get_applications_domain()
            values["application_count"] = (
                request.env["hr.applicant"].sudo().search_count(domain)
            )
        return values

    def _get_applications_domain(self):
        partner = request.env.user.partner_id
        return [
            "|",
            ("partner_id", "=", partner.id),
            ("email_from", "=ilike", partner.email or ""),
            ("active", "in", [True, False]),
        ]

    def _format_date(self, value):
        return fields.Date.to_string(value) if value else ""

    def _format_datetime(self, value):
        if not value:
            return ""
        dt = fields.Datetime.context_timestamp(request.env.user, value)
        return dt.strftime("%Y-%m-%d")

    def _selection_label(self, record, field_name, value):
        if not record:
            return value or ""
        field = record._fields.get(field_name)
        if not field or not value or not field.selection:
            return value or ""
        return dict(field.selection).get(value, value)

    def _get_profile(self, partner):
        return (
            request.env["portal.profile"]
            .sudo()
            .search([("partner_id", "=", partner.id)], limit=1)
        )

    def _compute_age(self, birthday):
        if not birthday:
            return ""
        today = fields.Date.today()
        years = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            years -= 1
        return str(years)

    def _first_non_empty(self, *values):
        for value in values:
            if value not in (False, None, "", []):
                return value
        return False

    def _prepare_stage_items(self, application, all_stages):
        items = []
        current_stage = application.stage_id
        current_sequence = current_stage.sequence if current_stage else -1

        for stage in all_stages:
            state = "upcoming"
            if stage.sequence < current_sequence:
                state = "done"
            elif current_stage and stage.id == current_stage.id:
                if application.application_status == "hired":
                    state = "current_hired"
                elif application.application_status == "refused":
                    state = "current_refused"
                else:
                    state = "current"

            items.append(
                {
                    "id": stage.id,
                    "name": stage.name or "-",
                    "state": state,
                }
            )
        return items

    def _prepare_education_items(self, application, profile):
        records = getattr(application, "education_history_ids", False)
        education_model = "hr.applicant.education.history"
        if not records and profile:
            records = profile.education_history_ids
            education_model = "portal.education.history"

        if not records:
            return []

        sorted_records = records.sorted(
            key=lambda r: (
                r.education_level_id.level if r.education_level_id else 0,
                getattr(r, "graduation_date", False)
                or fields.Date.from_string("1900-01-01"),
                r.id,
            ),
            reverse=True,
        )

        items = []
        for rec in sorted_records:
            certificate_filename = getattr(rec, "certificate_filename", "")
            transcript_filename = getattr(rec, "transcript_filename", "")
            items.append(
                {
                    "level": rec.education_level_id.name
                    if rec.education_level_id
                    else "-",
                    "program": getattr(rec, "program", "") or "-",
                    "major": getattr(rec, "major", "") or "-",
                    "institution": getattr(rec, "institution", "") or "-",
                    "country": rec.country_id.name
                    if getattr(rec, "country_id", False)
                    else "-",
                    "graduation_date": self._format_date(
                        getattr(rec, "graduation_date", False)
                    )
                    or "-",
                    "certificate_filename": certificate_filename,
                    "certificate_url": (
                        "/web/content?model=%s&id=%d&field=certificate_file"
                        "&filename_field=certificate_filename&download=true"
                        % (education_model, rec.id)
                    )
                    if certificate_filename
                    else False,
                    "transcript_filename": transcript_filename,
                    "transcript_url": (
                        "/web/content?model=%s&id=%d&field=transcript_file"
                        "&filename_field=transcript_filename&download=true"
                        % (education_model, rec.id)
                    )
                    if transcript_filename
                    else False,
                }
            )
        return items

    def _prepare_work_history_items(self, application, profile):
        records = getattr(application, "work_history_ids", False)
        if not records and profile:
            records = profile.work_history_ids

        items = []
        for rec in (
            records.sorted(
                key=lambda r: (
                    getattr(r, "date_start", False) or fields.Date.today(),
                    r.id,
                ),
                reverse=True,
            )
            if records
            else []
        ):
            items.append(
                {
                    "company_name": getattr(rec, "company_name", "") or "-",
                    "job_title": getattr(rec, "job_title", "") or "-",
                    "salary": getattr(rec, "salary", 0) or 0,
                    "date_start": self._format_date(getattr(rec, "date_start", False))
                    or "-",
                    "date_end": self._format_date(getattr(rec, "date_end", False))
                    or "-",
                }
            )
        return items

    def _prepare_academic_tab(self, application, academic_source):
        english_test_type_map = {
            "toefl_paper": "TOEFL (Paper-Based)",
            "toefl_computer": "TOEFL (Computer-Based)",
            "toefl_internet": "TOEFL (Internet-Based)",
            "ielts": "IELTS",
            "cutep": "CU-TEP",
            "kmitl_tep": "KMITL-TEP",
        }
        english_test_type = getattr(academic_source, "english_test_type", False)

        def _file(field_name, filename_field):
            filename = getattr(application, filename_field, "")
            if not filename:
                return {"filename": "", "download_url": False}
            return {
                "filename": filename,
                "download_url": self._applicant_file_url(
                    application, field_name, filename_field
                ),
            }

        return {
            "job_role": application.job_id.role if application.job_id else False,
            "academic_standing_id": academic_source.academic_standing_id.name
            if getattr(academic_source, "academic_standing_id", False)
            else "-",
            "academic_position_date": self._format_date(
                getattr(academic_source, "academic_position_date", False)
            )
            or "-",
            "academic_position_institution": getattr(
                academic_source, "academic_position_institution", ""
            )
            or "-",
            "academic_position_file": _file(
                "academic_position_file", "academic_position_filename"
            ),
            "has_ocsc_exam": "ผ่าน"
            if getattr(academic_source, "has_ocsc_exam", False)
            else "ไม่ผ่าน / ไม่มีข้อมูล",
            "ocsc_exam_level": self._selection_label(
                academic_source,
                "ocsc_exam_level",
                getattr(academic_source, "ocsc_exam_level", False),
            )
            or "-",
            "ocsc_exam_date": self._format_date(
                getattr(academic_source, "ocsc_exam_date", False)
            )
            or "-",
            "ocsc_exam_number": getattr(academic_source, "ocsc_exam_number", "") or "-",
            "ocsc_exam_file": _file("ocsc_exam_file", "ocsc_exam_filename"),
            "english_test_type": english_test_type_map.get(english_test_type, "-"),
            "english_test_score": getattr(academic_source, "english_test_score", "")
            or "-",
            "english_test_date": self._format_date(
                getattr(academic_source, "english_test_date", False)
            )
            or "-",
            "english_test_certificate_number": getattr(
                academic_source, "english_test_certificate_number", ""
            )
            or "-",
            "english_score_file": _file("english_score_file", "english_score_filename"),
        }

    def _applicant_file_url(self, application, field_name, filename_field):
        return (
            "/web/content?model=hr.applicant&id=%d&field=%s"
            "&filename_field=%s&download=true"
            % (application.id, field_name, filename_field)
        )

    def _prepare_document_items(self, application):
        role = application.job_id.role if application.job_id else False
        gender = application.gender

        document_specs = [
            ("photo_file", "photo_filename", "รูปถ่าย (Photo)", True),
            (
                "id_card_file",
                "id_card_filename",
                "สำเนาบัตรประจำตัวประชาชน",
                True,
            ),
            (
                "household_registration_file",
                "household_registration_filename",
                "สำเนาทะเบียนบ้าน",
                True,
            ),
            (
                "military_certificate_file",
                "military_certificate_filename",
                "สำเนาหนังสือรับรองผ่านการเกณฑ์ทหาร หรือได้รับการยกเว้นการเกณฑ์ทหาร "
                "(ใบ สด.8 สด.9 หรือ สด.43 หรือหลักฐานทางทหารอื่น ๆ)",
                gender == "male",
            ),
            (
                "resume_file",
                "resume_filename",
                "ประวัติการทำงาน (Resume)",
                role == "academic",
            ),
            (
                "work_certificate_file",
                "work_certificate_filename",
                "หนังสือรับรองการทำงาน",
                role == "academic",
            ),
            (
                "other_documents_file",
                "other_documents_filename",
                "สำเนาเอกสารอื่น ๆ เช่น การเปลี่ยนชื่อ นามสกุล",
                True,
            ),
        ]

        documents = []
        for field_name, filename_field, label, include in document_specs:
            if not include:
                continue
            if field_name not in application._fields:
                continue
            filename = getattr(application, filename_field, "")
            documents.append(
                {
                    "label": label,
                    "filename": filename or "-",
                    "download_url": self._applicant_file_url(
                        application, field_name, filename_field
                    )
                    if filename
                    else False,
                }
            )
        return documents

    def _prepare_view_data(self, application, all_stages):
        partner = application.partner_id or request.env.user.partner_id
        profile = self._get_profile(partner)

        status_map = {
            "hired": {"label": "Hired", "class": "success"},
            "refused": {"label": "Not Progressed", "class": "danger"},
        }
        status = status_map.get(
            application.application_status,
            {"label": "In Progress", "class": "primary"},
        )

        birthday = self._first_non_empty(
            getattr(application, "birthday", False),
            profile.birthday if profile else False,
        )
        nationality = self._first_non_empty(
            application.nationality_id.name
            if getattr(application, "nationality_id", False)
            else False,
            profile.nationality_id.name
            if profile and profile.nationality_id
            else False,
            "-",
        )

        phone = self._first_non_empty(
            application.partner_phone,
            getattr(application, "partner_mobile", False),
            profile.phone if profile else False,
            partner.phone if partner else False,
            partner.mobile if partner else False,
            "-",
        )
        email = self._first_non_empty(
            application.email_from,
            partner.email if partner else False,
            "-",
        )

        title_name = (
            application.applicant_title.name if application.applicant_title else ""
        )
        full_name = " ".join(
            part
            for part in [
                title_name or "",
                application.first_name or "",
                application.middle_name or "",
                application.last_name or "",
            ]
            if part
        )
        if not full_name:
            full_name = self._first_non_empty(
                getattr(application, "partner_name", False),
                partner.name if partner else False,
                "-",
            )

        title_name_en = (
            application.applicant_title.with_context(lang="en_US").name
            if application.applicant_title
            else ""
        )
        full_name_en = " ".join(
            part
            for part in [
                title_name_en or "",
                application.first_name_en or "",
                application.middle_name_en or "",
                application.last_name_en or "",
            ]
            if part
        )
        if not full_name_en and profile:
            title_name_en = (
                profile.title.with_context(lang="en_US").name if profile.title else ""
            )
            full_name_en = " ".join(
                part
                for part in [
                    title_name_en or "",
                    profile.first_name_en or "",
                    profile.middle_name_en or "",
                    profile.last_name_en or "",
                ]
                if part
            )

        gender_labels = {"male": "ชาย (Male)", "female": "หญิง (Female)"}
        gender_value = self._first_non_empty(
            application.gender,
            profile.gender if profile else False,
        )
        gender_display = gender_labels.get(gender_value, "")

        registered_address = self._first_non_empty(
            getattr(application, "address_address", False),
            profile.address_address if profile else False,
            "-",
        )
        current_address = self._first_non_empty(
            getattr(application, "current_address", False),
            profile.current_address if profile else False,
            "-",
        )

        academic_source = (
            application
            if (
                getattr(application, "academic_standing_id", False)
                and application.academic_standing_id.id
            )
            or getattr(application, "has_ocsc_exam", False)
            else profile
        )
        skills_source = (
            application
            if (
                getattr(application, "foreign_language_skills", False)
                or getattr(application, "computer_skills", False)
                or getattr(application, "other_abilities", False)
                or getattr(application, "interests", False)
            )
            else profile
        )

        return {
            "summary": {
                "job_position": application.job_id.name or application.name or "-",
                "department": application.department_id.name or "-",
                "application_subject": application.name or "-",
                "current_stage": application.stage_id.name or "-",
                "status": status,
                "date_applied": self._format_datetime(application.create_date) or "-",
                "hire_date": self._format_date(
                    getattr(application, "date_closed", False)
                ),
            },
            "progress": self._prepare_stage_items(application, all_stages),
            "tabs": {
                "personal": {
                    "full_name": full_name or "-",
                    "full_name_en": full_name_en or "-",
                    "gender": gender_display or "-",
                    "identification_id": self._first_non_empty(
                        getattr(application, "identification_id", False),
                        profile.identification_id if profile else False,
                        "-",
                    ),
                    "birthday": self._format_date(birthday) or "-",
                    "age": self._compute_age(birthday) or "-",
                    "nationality": nationality or "-",
                    "address_address": registered_address,
                    "current_address": current_address,
                    "phone": phone or "-",
                    "email": email or "-",
                    "emergency_contact_name": self._first_non_empty(
                        application.emergency_contact_name,
                        profile.emergency_contact_name if profile else False,
                        "-",
                    ),
                    "emergency_contact_relation": self._first_non_empty(
                        application.emergency_contact_relation,
                        profile.emergency_contact_relation if profile else False,
                        "-",
                    ),
                    "emergency_contact_phone": self._first_non_empty(
                        application.emergency_contact_phone,
                        profile.emergency_contact_phone if profile else False,
                        "-",
                    ),
                    "emergency_contact_email": self._first_non_empty(
                        application.emergency_contact_email,
                        profile.emergency_contact_email if profile else False,
                        "-",
                    ),
                    "congenital_disease": self._first_non_empty(
                        application.congenital_disease,
                        profile.congenital_disease if profile else False,
                        "-",
                    ),
                },
                "education": self._prepare_education_items(application, profile),
                "work_history": self._prepare_work_history_items(application, profile),
                "academic": self._prepare_academic_tab(application, academic_source),
                "skills": {
                    "foreign_language_skills": getattr(
                        skills_source, "foreign_language_skills", ""
                    )
                    or "-",
                    "computer_skills": getattr(skills_source, "computer_skills", "")
                    or "-",
                    "other_abilities": getattr(skills_source, "other_abilities", "")
                    or "-",
                    "interests": getattr(skills_source, "interests", "") or "-",
                },
                "documents": self._prepare_document_items(application),
            },
        }

    @http.route(
        ["/my/applications", "/my/applications/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_applications(self, page=1, sortby=None, **kw):
        if must_set_email():
            return request.redirect("/my/profile")
        HrApplicant = request.env["hr.applicant"].sudo()
        domain = self._get_applications_domain()

        sortings = {
            "date": {"label": "Date Applied", "order": "create_date desc"},
            "name": {"label": "Job Position", "order": "job_id asc, name asc"},
            "stage": {"label": "Stage", "order": "stage_id asc"},
        }
        if not sortby or sortby not in sortings:
            sortby = "date"
        order = sortings[sortby]["order"]

        application_count = HrApplicant.search_count(domain)
        pager = portal_pager(
            url="/my/applications",
            url_args={"sortby": sortby},
            total=application_count,
            page=page,
            step=self._items_per_page,
        )
        applications = HrApplicant.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager["offset"],
        )

        values = {
            "applications": applications,
            "page_name": "application",
            "pager": pager,
            "default_url": "/my/applications",
            "sortings": sortings,
            "sortby": sortby,
        }
        return request.render("hr_recruitment_kmitl.portal_my_applications", values)

    @http.route(
        ["/my/application/<int:application_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_application(self, application_id, **kw):
        if must_set_email():
            return request.redirect("/my/profile")
        partner = request.env.user.partner_id
        application = (
            request.env["hr.applicant"]
            .sudo()
            .with_context(active_test=False)
            .browse(application_id)
        )

        if not application.exists():
            return request.redirect("/my")

        partner_match = (
            application.partner_id and application.partner_id.id == partner.id
        )
        email_match = (
            application.email_from
            and partner.email
            and application.email_from.lower() == partner.email.lower()
        )
        if not partner_match and not email_match:
            return request.redirect("/my")

        stage_domain = [
            "|",
            ("job_ids", "=", False),
            ("job_ids", "in", application.job_id.ids if application.job_id else []),
        ]
        all_stages = (
            request.env["hr.recruitment.stage"]
            .sudo()
            .search(stage_domain, order="sequence asc")
        )

        values = {
            "view_data": self._prepare_view_data(application, all_stages),
            "page_name": "application",
        }
        return request.render(
            "hr_recruitment_kmitl.portal_my_application_detail", values
        )
