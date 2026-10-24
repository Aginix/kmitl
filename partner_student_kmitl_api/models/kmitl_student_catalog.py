# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_URL = "https://api.kmitl.ac.th/student-catalog/v1"
# Student IDs travel in the query string (?student_id=..&student_id=..).
CHUNK_SIZE = 50
TIMEOUT = 10


class KmitlStudentCatalog(models.AbstractModel):
    """The institute's student register, read over its student-catalog API.

    Identity only — names, faculty, curriculum, status; never a bank account
    or a national ID (ADR 0001).
    """

    _name = "kmitl.student.catalog"
    _description = "KMITL Student Catalog"

    @api.model
    def fetch(self, student_codes):
        """``{student_code: row}`` for the codes the catalog knows; an unknown
        code is simply absent. Raises ``UserError`` when the catalog cannot be
        reached."""
        codes = list(dict.fromkeys(c.strip() for c in student_codes if c and c.strip()))
        if not codes:
            return {}
        params = self.env["ir.config_parameter"].sudo()
        url = (
            params.get_param("partner_student_kmitl_api.api_url") or DEFAULT_URL
        ).rstrip("/")
        key = params.get_param("partner_student_kmitl_api.api_key")
        if not key:
            raise UserError(
                _(
                    "The KMITL student catalog API key is not set "
                    "(Settings > General Settings > Integrations)."
                )
            )
        found = {}
        for start in range(0, len(codes), CHUNK_SIZE):
            try:
                response = requests.get(
                    "%s/students" % url,
                    params={"student_id": codes[start : start + CHUNK_SIZE]},
                    headers={"apikey": key},
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except (requests.RequestException, ValueError) as error:
                _logger.warning("KMITL student catalog lookup failed: %s", error)
                raise UserError(
                    _(
                        "Cannot reach the KMITL student catalog, please try again later.\n%s"
                    )
                    % error
                ) from error
            # The spec wraps the list in {"students": [...]}; the live API
            # answers a bare list.
            rows = (data.get("students") or []) if isinstance(data, dict) else data
            for row in rows:
                found[str(row.get("student_id") or "").strip()] = row
        return found
