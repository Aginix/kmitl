from odoo import fields as odoo_fields
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.http import request


class WebsiteJobsKmitl(WebsiteHrRecruitment):
    def _get_kmitl_filter_url(
        self, base_url, role="", employee_type="", education_level=0, **override
    ):
        """Build query string preserving all KMITL filter params."""
        params = {
            "role": override.get("role", role),
            "employee_type": override.get("employee_type", employee_type),
            "education_level": override.get("education_level", education_level),
        }
        qs = "&".join("%s=%s" % (k, v) for k, v in params.items() if v)
        return "%s?%s" % (base_url, qs) if qs else base_url

    def _get_base_url(self, country_id, department_id, office_id, contract_type_id):
        """Build URL path from base route filters."""
        from odoo.addons.http_routing.models.ir_http import slug

        url = "/jobs"
        if country_id:
            url += "/country/%s" % slug(country_id)
        if department_id:
            url += "/department/%s" % slug(department_id)
        if office_id:
            url += "/office/%s" % office_id
        if contract_type_id:
            url += "/employment_type/%s" % contract_type_id
        return url

    def jobs(
        self,
        country=None,
        department=None,
        office_id=None,
        contract_type_id=None,
        **kwargs,
    ):
        response = super().jobs(
            country, department, office_id, contract_type_id, **kwargs
        )
        qcontext = response.qcontext

        jobs = qcontext.get("jobs", [])
        search = kwargs.get("search", "")
        role = kwargs.get("role", "")
        employee_type = kwargs.get("employee_type", "")
        education_level = int(kwargs.get("education_level") or 0)
        category_id = int(kwargs.get("category_id") or 0)

        if search:
            jobs = [j for j in jobs if search.lower() in (j.name or "").lower()]
        if role:
            jobs = [j for j in jobs if j.role == role]
        if employee_type:
            jobs = [j for j in jobs if j.kmitl_employee_type == employee_type]
        if education_level:
            jobs = [j for j in jobs if education_level in j.education_level_ids.ids]
        if category_id:
            jobs = [j for j in jobs if category_id in j.category_ids.ids]

        # Hide expired jobs in real-time
        now = odoo_fields.Datetime.now()
        jobs = [j for j in jobs if not j.date_close or j.date_close > now]

        degrees = request.env["hr.recruitment.degree"].sudo().search([])
        categories = request.env["hr.job.category"].sudo().search([])

        # Build base URL for filter links
        base_url = self._get_base_url(
            qcontext.get("country_id"),
            qcontext.get("department_id"),
            qcontext.get("office_id"),
            qcontext.get("contract_type_id"),
        )

        qcontext.update(
            {
                "jobs": jobs,
                "search": search,
                "role": role,
                "employee_type": employee_type,
                "education_level": education_level,
                "education_levels": degrees,
                "category_id": category_id,
                "categories": categories,
                "kmitl_base_url": base_url,
            }
        )
        return response
