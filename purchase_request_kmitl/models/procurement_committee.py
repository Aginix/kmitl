# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProcurementCommittee(models.Model):
    _inherit = 'procurement.committee'

    mobile_phone = fields.Char(
        string="Mobile Phone",
        related="employee_id.mobile_phone",
        store=False,
        readonly=True,
    )
    committee_type = fields.Selection(
        selection_add=[
            ("tor_committee", "TOR Committee"),
            ("price_determine", "Price Determine Committee"),
            ("evaluation", "Evaluation Committee"),
        ],
    )
    approve_role = fields.Selection(
        selection_add=[
            ("secretary", "Secretary"),
        ],
        required=True,
        ondelete={'chairman': 'set default', 'committee': 'set default', 'secretary': 'set default'},
        default="committee",
    )

    _sql_constraints = [
        (
            "employee_request_uniq",
            "unique (employee_id,request_id,committee_type)",
            "Committee member has to be unique within the same committee type.",
        ),
    ]

    @api.constrains("employee_id", "request_id", "committee_type")
    def _check_committee_cross_type_unique(self):
        allowed_overlap = {"tor_committee", "evaluation"}
        for rec in self:
            if not rec.employee_id or not rec.request_id:
                continue
            same_committees = self.env["procurement.committee"].search([
                ("employee_id", "=", rec.employee_id.id),
                ("request_id", "=", rec.request_id.id),
            ])
            types = set(same_committees.mapped("committee_type"))
            if len(types) > 1 and not types.issubset(allowed_overlap):
                raise ValidationError(
                    _(
                        "Employee %s cannot appear in multiple committees "
                        "except TOR and Evaluation committees.",
                        rec.employee_id.name,
                    )
                )
