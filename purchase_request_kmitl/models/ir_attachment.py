# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    attachment_type = fields.Selection(
        [
            ("tor", "Specification (TOR)"),
            ("rfq", "Quotation"),
            ("etc", "Etc"),
        ],
        string="Attachment Type",
    )
    sequence = fields.Integer(string="Sequence")
