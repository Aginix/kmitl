# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    wa_count = fields.Integer(compute="_compute_wa_ids", string="WA count", default=0)
    wa_ids = fields.One2many(comodel_name="work.acceptance", inverse_name="approval_id", string="Work Acceptances")
    wa_line_ids = fields.One2many(comodel_name="work.acceptance.line", inverse_name="approval_line_id", string="WA Lines", readonly=True)
    wa_accepted = fields.Boolean(string="WA Accepted", compute="_compute_wa_accepted", search="_search_wa_accepted")

    pending_wa_count = fields.Integer(
        compute="_compute_pending_wa_count",
    )

    @api.depends("wa_ids.state", "wa_ids.is_disbursed")
    def _compute_pending_wa_count(self):
        for approval in self:
            approval.pending_wa_count = self.env["work.acceptance"].search_count([
                ("approval_id", "=", approval.id),
                ("is_disbursed", "=", False),
                ("state", "=", "accept"),
            ])

    @api.depends("wa_line_ids")
    def _compute_wa_ids(self):
        for request in self:
            request.wa_count = len(request.wa_ids)

    def action_view_wa(self):
        self.ensure_one()
        act = self.env.ref("purchase_work_acceptance.action_work_acceptance")
        result = act.sudo().read()[0]
        create_wa = self.env.context.get("create_wa", False)
        purchase_requests = self.request_id
        lines = self._get_committee_line(purchase_requests)
        result["context"] = {
            "default_approval_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_company_id": self.company_id.id,
            "default_currency_id": self.currency_id.id,
            "default_date_due": self.approval_date,
            "default_work_acceptance_committee_ids": lines,
            "default_wa_tier_validation": True,
            "default_wa_line_ids": [
                Command.create(
                    {
                        "approval_line_id": line.id,
                        "name": line.name,
                        "product_uom": line.product_uom_id.id,
                        "product_id": line.product_id.id,
                        "price_unit": line.price_unit,
                        "product_qty": line._get_product_qty(),
                    }
                )
                for line in self.request_id.line_ids
                if line._get_product_qty() != 0
            ],
        }
        if len(self.wa_ids) > 1 and not create_wa:
            result["domain"] = "[('id', 'in', " + str(self.wa_ids.ids) + ")]"
        else:
            res = self.env.ref(
                "purchase_work_acceptance.view_work_acceptance_form", False
            )
            result["views"] = [(res and res.id or False, "form")]
            if not create_wa:
                result["res_id"] = self.wa_ids.id or False
        return result

    def _prepare_committee_line(self, line):
        return {
            "employee_id": line.employee_id.id,
            "name": line.name,
            "approve_role": line.approve_role,
            "note": line.note,
        }

    def _get_committee_line(self, approval):
        committees = approval.mapped("work_acceptance_committee_ids")
        lines = [(0, 0, self._prepare_committee_line(line)) for line in committees]
        return lines

    def action_create_invoice(self):
        enable_wa = self.env.user.has_group(
            "purchase_work_acceptance.group_enable_wa_on_invoice"
        )
        ctx = self.env.context.copy()
        if enable_wa and ctx.get("create_bill"):
            wizard = self.env.ref(
                "purchase_work_acceptance.view_select_work_acceptance_wizard"
            )
            return {
                "name": _("Select Work Acceptance"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "select.work.acceptance.wizard",
                "views": [(wizard.id, "form")],
                "view_id": wizard.id,
                "target": "new",
            }
        res = super().action_create_invoice()
        # Set 'ref' to WA
        if (
            ctx.get("wa_id")
            and res.get("res_model") == "account.move"
            and res.get("res_id")
        ):
            wa = self.env["work.acceptance"].browse(ctx["wa_id"])
            invoice = self.env["account.move"].browse(res["res_id"])
            # invoice.ref, adding "/ WA001"
            invoice.ref = (
                "{} / {}".format(invoice.ref, wa.name) if invoice.ref else wa.name
            )
            # invoice.payment_reference, adding "/ <WA's invoice_ref>"
            invoice.payment_reference = (
                "{} / {}".format(invoice.payment_reference, wa.invoice_ref)
                if invoice.payment_reference
                else wa.invoice_ref
            )
        return res

    def _compute_wa_accepted(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda l: l.product_qty > 0 and l.qty_to_accept > 0
            )
            order.wa_accepted = not any(lines)

    @api.model
    def _search_wa_accepted(self, operator, value):
        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        recs = self.search([]).filtered(lambda l: l.wa_accepted is value)
        return [("id", "in", recs.ids)]

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals["wa_id"] = self.env.context.get("wa_id")
        return invoice_vals
    
    def _get_pending_wa(self):
        """คืน WA ใบเดียวที่ accept แล้วและยังไม่ถูก disburse"""
        self.ensure_one()
        return self.env["work.acceptance"].search([
            ("approval_id", "=", self.id),
            ("state", "=", "accept"),
            ("is_disbursed", "=", False),
        ], order="date_accept asc", limit=1)

    def _create_disbursement_request(self):
        wa = self._get_pending_wa()
        if not wa:
            raise UserError(
                _("No accepted Work Acceptance pending disbursement for PA '%s'.")
                % self.name
            )
        disbursement = super()._create_disbursement_request()
        wa._link_to_disbursement(
            disbursement,
            analytic_distribution=self.analytic_distribution or False,
            fine_tax_ids=self.request_id.line_ids.tax_id.ids,
        )
        return disbursement
