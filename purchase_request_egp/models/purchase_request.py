# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_egp = fields.Boolean(string="e-GP", compute="_compute_is_egp", store=True)

    egp_status = fields.Selection(
        [
            ("waiting_egp", "รอดำเนินการ e-GP"),
            ("in_egp", "อยู่ในกระบวนการ e-GP"),
            ("done", "เสร็จสิ้น"),
        ],
        string="สถานะ e-GP",
        store=True,
        tracking=True,
    )

    egp_project_id = fields.Char(string="เลขที่โครงการ", tracking=True)
    egp_project_url = fields.Char(
        string="ลิงค์", compute="_compute_egp_project_url", readonly=True
    )

    @api.depends("egp_project_id")
    def _compute_egp_project_url(self):
        for record in self:
            if not record.egp_project_id:
                record.egp_project_url = False
                continue
            ts = datetime.now().timestamp()
            project_id = record.egp_project_id
            url = (
                "https://process.gprocurement.go.th/egp2procmainWeb/jsp/FPRO9951A_3.jsp?tor_project_id="
                + project_id
                + "&invite_templateType=D2&invite_announceFlag=A&invite_itemNo=0&invite_seqno=0&invite_methodId=16&intvite_docAnnounceType=D0&invite_announceId=&_=" + ts
            )
            record.egp_project_url = url

    @api.depends("estimated_cost", "state")
    def _compute_is_egp(self):
        for record in self:
            if record.state == "approved":
                record.is_egp = record.estimated_cost > 100000
            else:
                record.is_egp = False
