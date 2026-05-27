# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    state = fields.Selection(
        selection_add=[
            ("bills_posted", "Bills Posted"),
            ("cancel",),
        ],
        ondelete={"bills_posted": "set default"},
    )

    pipeline_status = fields.Selection(
        selection_add=[
            ("bill_draft", "Bill Draft"),
            ("bill_posted", "Bill Posted"),
        ],
        ondelete={
            "bill_draft": "set default",
            "bill_posted": "set default",
        },
    )

    display_status = fields.Selection(
        selection_add=[
            ("bill_draft", "Bill Draft"),
            ("bill_posted", "Bill Posted"),
            ("bills_posted", "Bills Posted"),
        ],
        ondelete={
            "bill_draft": "set default",
            "bill_posted": "set default",
            "bills_posted": "set default",
        },
    )

    bill_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="disbursement_request_id",
        string="Vendor Bills",
        readonly=True,
        copy=False,
    )

    bill_count = fields.Integer(
        string="Bill Count",
        compute="_compute_bill_count",
    )

    bill_draft_count = fields.Integer(
        string="Draft Bill Count",
        compute="_compute_bill_count",
    )

    bill_status_display = fields.Char(
        string="Bill Status",
        compute="_compute_bill_count",
    )

    move_line_count = fields.Integer(
        string="Move Line Count",
        compute="_compute_move_line_count",
    )

    @api.depends("bill_ids", "bill_ids.state")
    def _compute_bill_count(self):
        """Compute the number of bills linked to this request.

        Cancelled bills are excluded so the display reflects active bills.
        """
        for record in self:
            active_bills = record.bill_ids.filtered(
                lambda b: b.state != "cancel"
            )
            total = len(active_bills)
            unposted = len(active_bills.filtered(
                lambda b: b.state in ("draft", "submitted")
            ))
            posted = len(active_bills.filtered(lambda b: b.state == "posted"))
            record.bill_count = total
            record.bill_draft_count = unposted
            record.bill_status_display = (
                _("ตั้งหนี้แล้ว %s/%s", posted, total) if total else ""
            )

    @api.depends("bill_ids", "bill_ids.state", "bill_ids.line_ids")
    def _compute_move_line_count(self):
        for rec in self:
            active = rec.bill_ids.filtered(lambda b: b.state != "cancel")
            rec.move_line_count = len(active.line_ids.filtered(
                lambda l: l.display_type not in ("line_section", "line_note")
            ))

    @api.depends("bill_ids", "bill_ids.state")
    def _compute_pipeline_status(self):
        super()._compute_pipeline_status()
        for rec in self:
            if rec.state not in ("approved", "bills_posted"):
                continue
            active_bills = rec.bill_ids.filtered(lambda b: b.state != "cancel")
            if not active_bills:
                continue
            if all(b.state == "posted" for b in active_bills):
                rec.pipeline_status = "bill_posted"
            else:
                rec.pipeline_status = "bill_draft"

    @api.depends("state", "pipeline_status")
    def _compute_display_status(self):
        super()._compute_display_status()
        for rec in self:
            if rec.state == "bills_posted":
                rec.display_status = "bills_posted"

    # ------------------------------------------------------------------
    # Bill creation
    # ------------------------------------------------------------------
    def _create_bill(self):
        """Create vendor bill(s) from disbursement request."""
        self.ensure_one()

        if self.state != "approved":
            raise UserError(
                _("Only approved requests can be used to create bills.")
            )

        if self.partner_type == "single":
            bills = self._create_single_bill()
        else:
            bills = self._create_multi_bills()

        for bill in bills:
            bill_link = "/web#id=%d&model=account.move&view_type=form" % bill.id
            self.message_post(
                body=_(
                    'Vendor Bill <a href="%(link)s" target="_blank">'
                    "%(name)s</a> has been created."
                )
                % {"link": bill_link, "name": bill.name},
                subtype_xmlid="mail.mt_note",
            )

        return bills

    def _create_single_bill(self):
        """Create one bill for all lines (single-partner mode)."""
        self.ensure_one()
        invoice_lines = [
            Command.create(self._prepare_bill_line_vals(line))
            for line in self.line_ids
        ]
        bill = self.env["account.move"].with_context(
            auto_submit_on_create=True
        ).create(
            self._prepare_bill_vals(
                self.partner_id, self.partner_bank_id, invoice_lines
            )
        )
        self._apply_wht_to_bill(bill, self.line_ids)
        return bill

    def _create_multi_bills(self):
        """Group lines by partner, create one bill per partner."""
        self.ensure_one()
        partner_lines = {}
        for line in self.line_ids:
            partner_lines.setdefault(
                line.partner_id,
                self.env["disbursement.request.line"],
            )
            partner_lines[line.partner_id] |= line

        bills = self.env["account.move"]
        for partner, lines in partner_lines.items():
            invoice_lines = [
                Command.create(self._prepare_bill_line_vals(line))
                for line in lines
            ]
            partner_bank = lines[0].partner_bank_id
            bill = self.env["account.move"].with_context(
            auto_submit_on_create=True
        ).create(
                self._prepare_bill_vals(partner, partner_bank, invoice_lines)
            )
            self._apply_wht_to_bill(bill, lines)
            bills |= bill
        return bills

    def _prepare_bill_vals(self, partner, partner_bank, invoice_lines):
        """Prepare values for creating a vendor bill."""
        return {
            "disbursement_request_id": self.id,
            "partner_id": partner.id,
            "partner_bank_id": partner_bank.id if partner_bank else False,
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "ref": self.ref,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "invoice_line_ids": invoice_lines,
            "analytic_distribution": self.analytic_distribution,
        }

    def _prepare_bill_line_vals(self, line):
        """Prepare values for a single invoice line."""
        return {
            "product_id": line.product_id.id,
            "name": line.name,
            "account_id": line.account_id.id,
            "quantity": line.quantity,
            "price_unit": line.price_unit,
            "tax_ids": [Command.set(line.tax_ids.ids)],
            "analytic_distribution": line.analytic_distribution,
        }

    def _apply_wht_to_bill(self, bill, request_lines):
        """Apply WHT from request lines to the corresponding bill lines."""
        for request_line, invoice_line in zip(
            request_lines, bill.invoice_line_ids
        ):
            if request_line.wht_tax_id:
                invoice_line.wht_tax_id = request_line.wht_tax_id

    # ------------------------------------------------------------------
    # Tier-gated actions
    # ------------------------------------------------------------------
    def action_create_bill(self):
        self.ensure_one()
        existing_bills = self.bill_ids.filtered(lambda b: b.state != "cancel")
        if existing_bills:
            raise UserError(
                _(
                    "Cannot create new bill: existing bill(s) %s are still "
                    "in progress. Cancel them first before creating a new one."
                )
                % ", ".join(existing_bills.mapped("name"))
            )
        bills = self._create_bill()
        if len(bills) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": bills.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bills"),
            "res_model": "account.move",
            "domain": [("id", "in", bills.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_post_bills(self):
        """Post all unposted bills and transition DR state to bills_posted."""
        for record in self:
            if record.state != "approved":
                raise UserError(
                    _("Only approved disbursement requests can post bills.")
                )
            unposted_bills = record.bill_ids.filtered(
                lambda b: b.state in ("draft", "submitted")
            )
            if not unposted_bills:
                raise UserError(_("No bills to post."))
            unposted_bills.action_post()
            record.state = "bills_posted"
        return True

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------
    def action_view_move_lines(self):
        """Open a tree of move.line aggregated from this DR's active bills."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "disbursement_accounting_kmitl."
            "action_disbursement_move_lines"
        )
        action["domain"] = [
            ("move_id", "in", self.bill_ids.ids),
            ("move_id.state", "!=", "cancel"),
            ("display_type", "not in", ("line_section", "line_note")),
        ]
        action["context"] = {
            "default_disbursement_request_id": self.id,
        }
        return action

    def action_view_bill(self):
        """Open the linked vendor bill(s)"""
        self.ensure_one()
        bills = self.bill_ids
        if len(bills) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Vendor Bill"),
                "res_model": "account.move",
                "res_id": bills.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bills"),
            "res_model": "account.move",
            "domain": [("id", "in", bills.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_cancel(self):
        """Block cancel if any bill is posted; cancel draft bills first."""
        for record in self:
            if record.state == "cancel":
                continue
            posted_bills = record.bill_ids.filtered(
                lambda b: b.state == "posted"
            )
            if posted_bills:
                raise UserError(
                    _(
                        "Cannot cancel: bill(s) %s already posted. "
                        "Reverse the bill(s) first."
                    )
                    % ", ".join(posted_bills.mapped("name"))
                )
            draft_bills = record.bill_ids.filtered(
                lambda b: b.state == "draft"
            )
            if draft_bills:
                draft_bills.button_cancel()
        return super().action_cancel()
