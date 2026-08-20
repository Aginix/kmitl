# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    disbursement_request_ids = fields.Many2many(
        comodel_name="disbursement.request",
        string="Disbursement Requests",
        compute="_compute_disbursement_request_ids",
        help="The ใบขอเบิก this file pays. A file is assembled from vouchers, and "
        "a voucher is one payee's slice of a request — so one file commonly spans "
        "several requests, and one request whose payees bank at four places "
        "produces four files.",
    )
    disbursement_request_count = fields.Integer(
        compute="_compute_disbursement_request_ids",
    )
    # Only filled when there is exactly one, because that is the only case where a
    # number is the answer rather than a guess at which of several to show. A Char
    # and not the Many2one for the reason given on account.payment: Odoo 16 has no
    # read mode, so a Many2one in a stat button is drawn as a text box to type in.
    disbursement_request_name = fields.Char(
        compute="_compute_disbursement_request_ids",
        string="Disbursement Request Number",
    )

    @api.depends("export_line_ids.payment_id.disbursement_request_id")
    def _compute_disbursement_request_ids(self):
        """Follow the file's rows back to the requests they were raised for.

        Every row counts, including the ones the bank rejected. A rejected row was
        released and may already be in another file, but it is still something this
        file carried — and "why is this payee here" is exactly the question the
        trail is opened to answer.

        ``sudo`` on the requests: an e-payment officer holds the file and is not
        guaranteed read on the ใบขอเบิก, and a form that raises AccessError while
        rendering is unusable. The real check fires when the button is pressed.
        """
        for rec in self:
            requests = rec.export_line_ids.payment_id.disbursement_request_id.sudo()
            rec.disbursement_request_ids = requests
            rec.disbursement_request_count = len(requests)
            rec.disbursement_request_name = (
                requests.name if len(requests) == 1 else False
            )

    def action_view_disbursement_requests(self):
        """Open the ใบขอเบิก this file pays."""
        self.ensure_one()
        requests = self.disbursement_request_ids
        action = {
            "type": "ir.actions.act_window",
            "name": _("Disbursement Requests"),
            "res_model": "disbursement.request",
            "target": "current",
        }
        if len(requests) == 1:
            action.update({"view_mode": "form", "res_id": requests.id})
        else:
            action.update(
                {"view_mode": "tree,form", "domain": [("id", "in", requests.ids)]}
            )
        return action
