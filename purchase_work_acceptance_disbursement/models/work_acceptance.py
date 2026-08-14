# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class WorkAcceptance(models.Model):
    _name = "work.acceptance"
    _inherit = ["work.acceptance", "disbursement.return.source.mixin"]
    _disbursement_return_state = "accept"

    state = fields.Selection(
        selection_add=[("returned", "Returned")],
        ondelete={"returned": "set default"},
    )
    disbursement_return_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="work_acceptance_dr_return_attachment_rel",
        column1="wa_id",
        column2="attachment_id",
        string="Correction Evidence",
        copy=False,
    )

    is_disbursed = fields.Boolean(
        string="Disbursed",
        default=False,
        copy=False,
        tracking=True,
    )

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    # -- return-to-source contract (disbursement.return.source.mixin) -----
    def _disbursement_get_request(self):
        self.ensure_one()
        return self._disbursement_pick_request(self.disbursement_request_id)

    def _disbursement_evidence_attachments(self):
        return self.disbursement_return_attachment_ids

    def _disbursement_return(self, dr, reason):
        # skip_validation_check: the WA is 'accept' with its tier reviews already
        # cleared; the return (accept -> returned) must not re-trigger the tier
        # write guard.
        return super(
            WorkAcceptance, self.with_context(skip_validation_check=True)
        )._disbursement_return(dr, reason)

    def action_confirm_correction(self):
        # skip_validation_check: returned -> accept must not spawn a new tier
        # review (the acceptance was already validated).
        return super(
            WorkAcceptance, self.with_context(skip_validation_check=True)
        ).action_confirm_correction()

    @api.constrains("state")
    def _check_pending_disbursement_before_accept(self):
        """ห้าม accept WA ใหม่ถ้า PO ยังมี WA ที่ยังไม่ถูก submit disbursement"""
        for wa in self:
            if wa.state != "accept" or not wa.purchase_id:
                continue
            blocking = self.search([
                ("purchase_id", "=", wa.purchase_id.id),
                ("state", "=", "accept"),
                ("is_disbursed", "=", False),
                ("id", "!=", wa.id),
            ])
            if blocking:
                raise UserError(
                    _(
                        "Cannot accept this Work Acceptance.\n"
                        "PO '%s' still has WA '%s' waiting for disbursement submission."
                    ) % (wa.purchase_id.name, blocking[0].name)
                )
            
    def action_force_mark_disbursed(self):
        """Force is_disbursed=True on a WA stuck in accept, unblocking the next
        WA on the same PO. The actual disbursement.request is untouched.
        Admin ERP only."""
        for wa in self:
            if wa.state != "accept":
                continue
            wa.sudo().write({"is_disbursed": True})
            wa.message_post(
                body=_(
                    "Force Mark Disbursed (admin): marked by <b>%(user)s</b>."
                    " Disbursement request may still be pending — check separately.",
                    user=self.env.user.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def _link_to_disbursement(self, disbursement, analytic_distribution=False, fine_tax_ids=None):
        self.ensure_one()
        self.write({"disbursement_request_id": disbursement.id})

        if self.fines_late > 0:
            fine_account = self.env["account.account"].search(
                [
                    ("code", "=", "4310000003"),
                    ("company_id", "=", disbursement.company_id.id),
                ],
                limit=1,
            )
            fine_product = self.env["product.product"].search(
                [
                    ("name", "=", "ค่าปรับ"),
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
                        "price_unit": -self.fines_late,
                        "product_id": fine_product.id,
                        "account_id": fine_account.id,
                        "analytic_distribution": analytic_distribution or False,
                        "tax_ids": [Command.set(fine_tax_ids or [])],
                    })
                ]
            })

            disbursement.message_post(
                body=_("Added fine line: <b>%.2f</b> (from WA %s)") % (self.fines_late, self.name),
                subtype_xmlid="mail.mt_note",
            )

        dr_link = "/web#id=%d&model=disbursement.request&view_type=form" % disbursement.id
        self.message_post(
            body=_(
                'Disbursement Request <a href="%(link)s">%(name)s</a> created.'
            ) % {"link": dr_link, "name": disbursement.name},
            subtype_xmlid="mail.mt_note",
        )
            
class WorkAcceptanceLine(models.Model):
    _inherit = "work.acceptance.line"

    def _prepare_disbursement_line_vals(self):
        """Convert WA line to disbursement request line vals."""
        # ดึง account จาก product เหมือน PO line
        account = (
            self.product_id.property_account_expense_id
            or self.product_id.categ_id.property_account_expense_categ_id
        )
        # ดึง analytic จาก PO line ที่ link อยู่ (ถ้ามี)
        analytic = (
            self.purchase_line_id.analytic_distribution
            if self.purchase_line_id
            else False
        )
        # ดึง taxes จาก PO line ที่ link อยู่ (ถ้ามี)
        tax_ids = (
            self.purchase_line_id.taxes_id.ids
            if self.purchase_line_id
            else []
        )
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "quantity": self.product_qty,
            "price_unit": self.price_unit,
            "account_id": account.id if account else False,
            "tax_ids": [(6, 0, tax_ids)],
            "analytic_distribution": analytic,
        }
