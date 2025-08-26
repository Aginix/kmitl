import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    line_seq = fields.Integer(default=50)

    @api.model
    def _search(
        self,
        domain,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        # ใช้ _order แล้วไม่ได้ผล จึงแก้ไขด้วยวิธีนี้แทน
        if not order:
            order = "code asc"
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )
