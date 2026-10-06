# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError
from odoo.fields import Command


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    # ------------------------------------------------------------------
    # Bill creation
    # ------------------------------------------------------------------
    def _create_bill(self):
        """Create vendor bill(s) from disbursement request."""
        self.ensure_one()
        if self.station_code != "bill":
            raise UserError(
                _("Bills can only be created while the request is at the billing station.")
            )

        bills = self._create_bills()

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

    def _create_bills(self):
        """Group lines by partner, create one bill per partner.

        Every disbursement request pays a name list (multi-partner), so bills
        are always split per recipient partner.
        """
        self.ensure_one()
        partner_lines = {}
        for line in self.line_ids:
            partner_lines.setdefault(
                line.partner_id,
                self.env["disbursement.request.line"],
            )
            partner_lines[line.partner_id] |= line

        bills = self.env["account.move"]
        for lines in partner_lines.values():
            bills |= self.env["account.move"].create(self._prepare_bill_vals(lines))
        return bills

    def _prepare_bill_vals(self, lines):
        """Prepare values for creating one vendor bill out of ``lines``.

        Takes the lines rather than the payee they happen to share today, so a
        new way of splitting bills changes this method and not every override.
        """
        self.ensure_one()
        partner = lines[0].partner_id
        partner_bank = lines[0].partner_bank_id
        return {
            "disbursement_request_id": self.id,
            "partner_id": partner.id,
            "partner_bank_id": partner_bank.id if partner_bank else False,
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "ref": self.ref,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "invoice_line_ids": [
                Command.create(self._prepare_bill_line_vals(line)) for line in lines
            ],
            "analytic_distribution": self.analytic_distribution,
        }

    def _prepare_bill_line_vals(self, line):
        """Prepare values for a single invoice line.

        The request line's withholding tax is stamped directly at create time
        so it cannot be mis-assigned by a positional match against the created
        bill lines.
        """
        return {
            "product_id": line.product_id.id,
            "name": line.name,
            "account_id": line.account_id.id,
            "quantity": line.quantity,
            "price_unit": line.price_unit,
            "tax_ids": [Command.set(line.tax_ids.ids)],
            "wht_tax_id": line.wht_tax_id.id,
            "analytic_distribution": line.analytic_distribution,
        }

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

    def _station_check(self, code):
        super()._station_check(code)
        if code == "bill":
            active = self.bill_ids.filtered(lambda b: b.state != "cancel")
            if not active or any(b.state != "posted" for b in active):
                raise UserError(
                    _("Every bill of the request must be posted before billing is done.")
                )

    def _on_bills_posted(self):
        """The last active bill is posted: the billing station is done.

        The posting itself (account.move approval) is the authority, so the step
        is completed without the button-press group check.
        """
        super()._on_bills_posted()
        step = self.current_step_id
        if step.station_code == "bill":
            step.sudo()._do_complete()
