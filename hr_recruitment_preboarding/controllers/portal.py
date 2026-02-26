# -*- coding: utf-8 -*-
import base64
import json

from odoo import http
from odoo.http import request


class PreboardingPortal(http.Controller):

    @http.route(
        "/preboarding/<string:token>",
        type="http",
        auth="public",
        website=True,
    )
    def preboarding_form(self, token, **kw):
        preboarding = (
            request.env["hr.preboarding"]
            .sudo()
            .search([("token", "=", token)], limit=1)
        )
        if not preboarding:
            return request.not_found()

        if preboarding.state == "draft":
            preboarding.write({"state": "in_progress"})

        countries = request.env["res.country"].sudo().search([], order="name")
        return request.render(
            "hr_recruitment_preboarding.portal_preboarding_form",
            {"preboarding": preboarding, "countries": countries},
        )

    @http.route(
        "/preboarding/<string:token>/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def preboarding_submit(self, token, **post):
        preboarding = (
            request.env["hr.preboarding"]
            .sudo()
            .search([("token", "=", token)], limit=1)
        )
        if not preboarding:
            return request.not_found()

        if preboarding.state in ("submitted", "approved", "rejected"):
            return request.redirect(f"/preboarding/{token}")

        vals = {
            "title": post.get("title") or False,
            "first_name": post.get("first_name"),
            "last_name": post.get("last_name"),
            "nickname": post.get("nickname"),
            "id_card": post.get("id_card"),
            "birthdate": post.get("birthdate") or False,
            "nationality": post.get("nationality"),
            "religion": post.get("religion"),
            "marital_status": post.get("marital_status") or False,
            "ethnicity": post.get("ethnicity"),
            "phone": post.get("phone"),
            "mobile": post.get("mobile"),
            "email": post.get("email"),
            "address": post.get("address"),
            "city": post.get("city"),
            "zip": post.get("zip"),
            "country_id": int(post.get("country_id") or 0) or False,
            "bank_name": post.get("bank_name"),
            "bank_account_number": post.get("bank_account_number"),
            "state": "submitted",
        }
        preboarding.write(vals)

        education_data = post.get("education_data")
        if education_data:
            try:
                educations = json.loads(education_data)
                preboarding.education_ids.unlink()
                for edu in educations:
                    if any(edu.get(k) for k in ("degree", "institution", "field_of_study", "graduation_year", "gpa")):
                        request.env["hr.preboarding.education"].sudo().create(
                            {
                                "preboarding_id": preboarding.id,
                                "degree": edu.get("degree"),
                                "institution": edu.get("institution"),
                                "field_of_study": edu.get("field_of_study"),
                                "graduation_year": edu.get("graduation_year"),
                                "gpa": float(edu.get("gpa") or 0),
                            }
                        )
            except (json.JSONDecodeError, ValueError):
                pass

        return request.redirect(f"/preboarding/{token}/success")

    @http.route(
        "/preboarding/<string:token>/upload",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def preboarding_upload(self, token, document_id=None, ufile=None, **kw):
        def _json_response(data, status=200):
            return request.make_response(
                json.dumps(data),
                headers=[("Content-Type", "application/json")],
                status=status,
            )

        preboarding = (
            request.env["hr.preboarding"]
            .sudo()
            .search([("token", "=", token)], limit=1)
        )
        if not preboarding:
            return _json_response({"error": "Not found"}, 404)

        if not document_id or not ufile:
            return _json_response({"error": "Missing parameters"}, 400)

        document = preboarding.document_ids.filtered(
            lambda d: d.id == int(document_id)
        )
        if not document:
            return _json_response({"error": "Document not found"}, 404)

        attachment = (
            request.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": ufile.filename,
                    "res_model": "hr.preboarding.document",
                    "res_id": document.id,
                    "datas": base64.b64encode(ufile.read()),
                    "mimetype": ufile.content_type,
                }
            )
        )
        document.write(
            {"attachment_ids": [(4, attachment.id)], "state": "uploaded"}
        )
        return _json_response({"success": True, "attachment_id": attachment.id})

    @http.route(
        "/preboarding/<string:token>/success",
        type="http",
        auth="public",
        website=True,
    )
    def preboarding_success(self, token, **kw):
        preboarding = (
            request.env["hr.preboarding"]
            .sudo()
            .search([("token", "=", token)], limit=1)
        )
        if not preboarding:
            return request.not_found()
        return request.render(
            "hr_recruitment_preboarding.portal_preboarding_success",
            {"preboarding": preboarding},
        )
