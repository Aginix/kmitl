# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pending_wa_count = fields.Integer(
        compute="_compute_pending_wa_count",
    )

    @api.depends("wa_ids.state", "wa_ids.is_disbursed")
    def _compute_pending_wa_count(self):
        for order in self:
            order.pending_wa_count = self.env["work.acceptance"].search_count([
                ("purchase_id", "=", order.id),
                ("is_disbursed", "=", False),
            ])

    def _get_pending_wa(self):
        """คืน WA ใบเดียวที่ accept แล้วและยังไม่ถูก disburse"""
        self.ensure_one()
        return self.env["work.acceptance"].search([
            ("purchase_id", "=", self.id),
            ("state", "=", "accept"),
            ("is_disbursed", "=", False),
        ], order="date_accept asc", limit=1)

    def _prepare_disbursement_request_vals(self):
        """Override: ใช้ WA lines แทน PO lines"""
        vals = super()._prepare_disbursement_request_vals()
        wa = self._get_pending_wa()
        if not wa:
            return vals
        vals["line_ids"] = [
            Command.create(line._prepare_disbursement_line_vals())
            for line in wa.wa_line_ids
        ]
        vals["fines_late"] = self.wa_ids.fines_late
        return vals

    def _create_disbursement_request(self):
        """Override: link WA หลังสร้าง disbursement และเพิ่ม line ค่าปรับถ้ามี"""
        wa = self._get_pending_wa()
        if not wa:
            raise UserError(
                _("No accepted Work Acceptance pending disbursement for PO '%s'.")
                % self.name
            )

        disbursement = super()._create_disbursement_request()
        wa.write({"disbursement_request_id": disbursement.id})

        if wa.fines_late > 0:
            analytic_distribution = self.order_line[:1].analytic_distribution or False

            fine_account = self.env["account.account"].search(
                [
                    ("code", "=", "4310000003"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if not fine_account:
                raise UserError(
                    _("Account with code '4310000003' not found. Please check your chart of accounts.")
                )

            disbursement.write({
                "line_ids": [
                    Command.create({
                        "name": _("ค่าปรับ"),
                        "quantity": 1,
                        "price_unit": -wa.fines_late,
                        "account_id": fine_account.id,
                        "analytic_distribution": analytic_distribution or False,
                    })
                ]
            })

            disbursement.message_post(
                body=_("Added fine line: <b>%.2f</b> (from WA %s)") % (wa.fines_late, wa.name),
                subtype_xmlid="mail.mt_note",
            )

        # Log cross-links
        dr_link = "/web#id=%d&model=disbursement.request&view_type=form" % disbursement.id
        wa.message_post(
            body=_(
                'Disbursement Request <a href="%(link)s">%(name)s</a> created.'
            ) % {"link": dr_link, "name": disbursement.name},
            subtype_xmlid="mail.mt_note",
        )

        return disbursement

    @api.depends(
        "state",
        "is_disbursement_request_allowed",
        "disbursement_request_ids.state",
        "pending_wa_count",
    )
    def _compute_hide_create_disbursement_request_button(self):
        for order in self:
            has_unfinished_disbursement = any(
                d.state not in ("validated", "cancel")
                for d in order.disbursement_request_ids
            )
            order.hide_create_disbursement_request_button = (
                order.state != "purchase"
                or not order.is_disbursement_request_allowed
                or order.pending_wa_count == 0
                or has_unfinished_disbursement
            )
