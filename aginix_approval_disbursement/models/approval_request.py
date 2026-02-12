from odoo import Command, _, api, fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="approval_request_id",
        string="Disbursement Requests",
    )

    disbursement_request_count = fields.Integer(
        string="Disbursement Request Count",
        compute="_compute_disbursement_request",
    )

    billing_status = fields.Selection(
        selection=[
            ("no", "Nothing to Bill"),
            ("partial", "Partially Billed"),
            ("full", "Fully Billed"),
        ],
        string="Billing Status",
        compute="_compute_billing_status",
        store=True,
        tracking=True,
    )

    @api.depends("disbursement_request_ids")
    def _compute_disbursement_request(self):
        for record in self:
            record.disbursement_request_count = len(
                record.disbursement_request_ids
            )

    @api.depends("disbursement_request_ids", "disbursement_request_ids.state")
    def _compute_billing_status(self):
        for record in self:
            disbursements = record.disbursement_request_ids
            if not disbursements:
                record.billing_status = "no"
            elif all(d.state == "validated" for d in disbursements):
                record.billing_status = "full"
            else:
                record.billing_status = "partial"

    def _prepare_disbursement_request_vals(self, partner, lines):
        return {
            "approval_request_id": self.id,
            "partner_id": partner.id,
            "line_ids": [
                Command.create(line._prepare_disbursement_request_line_vals())
                for line in lines
            ],
            "ref": self.name,
            "budget_commitment_id": self.budget_commitment_id.id,
            "budget_account_id": self.budget_account_id.id,
            "analytic_distribution": self.analytic_distribution,
        }

    def action_create_disbursement_request(self):
        self.ensure_one()
        # Group lines by partner
        partner_lines = {}
        for line in self.line_ids:
            partner = line.partner_id
            partner_lines.setdefault(partner, self.env["approval.request.line"])
            partner_lines[partner] |= line

        disbursements = self.env["disbursement.request"]
        for partner, lines in partner_lines.items():
            vals = self._prepare_disbursement_request_vals(partner, lines)
            disbursement = self.env["disbursement.request"].create(vals)
            link = self._get_record_url()
            disbursement.message_post(
                body=_(
                    'This record has been created from: '
                    '<a href="%(link)s" target="_blank">%(name)s</a>',
                    link=link,
                    name=self.name,
                ),
                message_type="comment",
            )
            self.message_post(
                body=_(
                    "Disbursement %(dr_name)s created successfully.",
                    dr_name=disbursement.name,
                ),
                message_type="comment",
            )
            disbursements |= disbursement

        if len(disbursements) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "disbursement.request",
                "view_mode": "form",
                "res_id": disbursements.id,
                "target": "current",
            }
        return self.action_view_disbursement_request()

    def action_view_disbursement_request(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "target": "current",
        }
        if len(self.disbursement_request_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.disbursement_request_ids.id
        else:
            action["view_mode"] = "tree,form"
            action["domain"] = [("id", "in", self.disbursement_request_ids.ids)]
        return action

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)
