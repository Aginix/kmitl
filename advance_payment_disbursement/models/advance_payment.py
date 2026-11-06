from odoo import _, api, fields, models
from odoo.osv import expression


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    # ใบเบิกชดใช้เงินยืม clearing this loan (ADR-0032).
    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="advance_payment_id",
        string="ใบเบิกชดใช้เงินยืม",
        readonly=True,
    )

    disbursement_request_count = fields.Integer(
        compute="_compute_disbursement_request_count",
    )

    # A loan officer need not hold any disbursement right: the clearing
    # requests are listed from a sudo render, and only those who may read
    # requests get the smart button.
    disbursement_request_html = fields.Html(
        string="ใบเบิกชดใช้เงินยืม",
        compute="_compute_disbursement_request_html",
        sanitize=False,
    )

    can_view_disbursement_requests = fields.Boolean(
        compute="_compute_can_view_disbursement_requests"
    )

    @api.depends("disbursement_request_ids")
    def _compute_disbursement_request_count(self):
        for rec in self:
            rec.disbursement_request_count = len(rec.sudo().disbursement_request_ids)

    def _compute_disbursement_request_html(self):
        for rec in self:
            requests = rec.sudo().disbursement_request_ids
            rec.disbursement_request_html = (
                self.env["ir.qweb"]._render(
                    "advance_payment_disbursement.disbursement_request_table",
                    {"requests": requests},
                )
                if requests
                else False
            )

    def _compute_can_view_disbursement_requests(self):
        allowed = self.env["disbursement.request"].check_access_rights(
            "read", raise_exception=False
        )
        for rec in self:
            rec.can_view_disbursement_requests = allowed

    def action_view_disbursement_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบเบิกชดใช้เงินยืม"),
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": [("advance_payment_id", "=", self.id)],
            "context": {"create": False},
        }

    def _sync_cleared_amount(self, request):
        """ส่งใช้คืน = what the linked requests consumed (ตัดงบ). Paid off →
        the loan closes itself; a cancelled request that leaves something
        owed again reopens it. Run as sudo: the system records ส่งใช้คืน
        (advance_payment's write guard), and the state moves bypass the loan
        officer/admin gates of action_close/action_reopen."""
        for rec in self:
            cleared = sum(rec.disbursement_request_ids.mapped("budget_consumed_amount"))
            # Only money given back reopens: cancelling a request that
            # cleared nothing must not reopen a loan the officer closed.
            given_back = (
                rec.currency_id.compare_amounts(cleared, rec.actual_expense_amount) < 0
            )
            if rec.actual_expense_amount != cleared:
                rec.actual_expense_amount = cleared
            owed = rec.currency_id.compare_amounts(rec.amount_remaining, 0) > 0
            if not owed and rec.state == "in_progress":
                rec.write({"state": "done", "date_closed": fields.Datetime.now()})
                rec.message_post(
                    body=_(
                        "ปิดสัญญาอัตโนมัติ: ส่งใช้คืนครบตามใบเบิก %(request)s.",
                        request=request.name,
                    ),
                    subtype_xmlid="mail.mt_note",
                )
            elif owed and given_back and rec.state == "done":
                rec.write({"state": "in_progress", "date_closed": False})
                rec.message_post(
                    body=_(
                        "เปิดสัญญาอีกครั้งอัตโนมัติ: ยกเลิกใบเบิก %(request)s.",
                        request=request.name,
                    ),
                    subtype_xmlid="mail.mt_note",
                )

    def name_get(self):
        """In the request's picker: "<contract number> — <borrower>"."""
        if not self.env.context.get("advance_payment_picker"):
            return super().name_get()
        return [
            (
                rec.id,
                "%s — %s" % (rec.contract_number or rec.name, rec.employee_id.name),
            )
            for rec in self
        ]

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        """The request's picker searches every outstanding loan, rights or
        not, by contract number, ADV number or borrower."""
        if not self.env.context.get("advance_payment_picker"):
            return super()._name_search(
                name, args, operator, limit=limit, name_get_uid=name_get_uid
            )
        args = expression.AND([args or [], [("state", "=", "in_progress")]])
        if name and operator not in expression.NEGATIVE_TERM_OPERATORS:
            args = expression.AND(
                [
                    args,
                    [
                        "|",
                        "|",
                        ("contract_number", operator, name),
                        ("name", operator, name),
                        ("employee_id.name", operator, name),
                    ],
                ]
            )
            name = ""
        return super(AdvancePayment, self.sudo())._name_search(
            name, args, operator, limit=limit, name_get_uid=name_get_uid
        )
