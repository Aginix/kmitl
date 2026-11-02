from odoo import SUPERUSER_ID, api

from . import models  # noqa: F401
from .models.related_document_kind import CITED_BY_ACTION_CODE


def uninstall_hook(cr, registry):
    """Drop the ถูกอ้างอิงโดย actions the kinds bound: they carry no xmlid
    and would call related.document once it is gone."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.actions.server"].search([("code", "=", CITED_BY_ACTION_CODE)]).unlink()
