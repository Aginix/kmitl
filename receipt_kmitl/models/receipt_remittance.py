# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ReceiptRemittance(models.Model):
    _name = "kmitl.receipt.remittance"
    _description = "KMITL Receipt Remittance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Remittance Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        required=True,
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    receipt_ids = fields.One2many(
        "kmitl.receipt",
        "remittance_id",
        string="Receipts",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    note = fields.Text()
    user_id = fields.Many2one(
        "res.users",
        string="Created By",
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True,
        copy=False,
    )
    approver_id = fields.Many2one(
        "res.users",
        string="Approver",
        domain=lambda self: [
            ("groups_id", "in",
             [self.env.ref("receipt_kmitl.group_receipt_kmitl_remittance_approver").id])
        ],
        default=lambda self: self._default_approver_id(),
        tracking=True,
    )
    approved_by = fields.Many2one("res.users", readonly=True, copy=False)
    approved_date = fields.Datetime(readonly=True, copy=False)

    receipt_count = fields.Integer(
        compute="_compute_receipt_count",
        string="# Receipts",
    )
    move_count = fields.Integer(
        compute="_compute_move_count",
        string="# Journal Entries",
    )

    @api.model
    def _default_approver_id(self):
        group = self.env.ref(
            "receipt_kmitl.group_receipt_kmitl_remittance_approver",
            raise_if_not_found=False,
        )
        if group and group.users:
            return group.users[0].id
        return False

    @api.depends("receipt_ids")
    def _compute_receipt_count(self):
        for rec in self:
            rec.receipt_count = len(rec.receipt_ids)

    @api.depends("receipt_ids.move_id")
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.receipt_ids.mapped("move_id"))

    @api.depends("receipt_ids.amount_total")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.receipt_ids.mapped("amount_total"))

    def _get_fy_be(self):
        self.ensure_one()
        return self.env["kmitl.receipt"]._get_fiscal_year_be(self.date)

    def _get_sequence(self):
        self.ensure_one()
        fy_be = self._get_fy_be()
        seq_code = "kmitl.receipt.remittance.%s" % fy_be
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "Receipt Remittance FY%s" % fy_be,
                    "code": seq_code,
                    "prefix": "RM/%s/" % fy_be,
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    def _validate_receipts(self, expected_state):
        self.ensure_one()
        if not self.receipt_ids:
            raise ValidationError(_("Add at least one receipt."))
        for receipt in self.receipt_ids:
            if receipt.state != expected_state:
                raise ValidationError(
                    _("Receipt %s is not in '%s' state.")
                    % (receipt.name, expected_state)
                )

    def action_pull_pending_receipts(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Can only pull receipts on draft remittances."))
            receipts = self.env["kmitl.receipt"].search(
                [
                    ("company_id", "=", rec.company_id.id),
                    (
                        "department_analytic_id",
                        "child_of",
                        rec.department_analytic_id.id,
                    ),
                    ("state", "=", "to_submit"),
                    ("remittance_id", "=", False),
                    ("date", "<=", rec.date),
                ]
            )
            if not receipts:
                raise UserError(
                    _("No pending receipts found for this department.")
                )
            rec.write({"receipt_ids": [(6, 0, receipts.ids)]})

    def _schedule_approver_activity(self):
        self.ensure_one()
        activity_type = self.env.ref(
            "receipt_kmitl.mail_activity_type_remittance_approval",
            raise_if_not_found=False,
        )
        if activity_type and self.approver_id:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=self.approver_id.id,
                summary=_("Remittance %s awaiting approval") % self.name,
            )

    def _complete_approver_activity(self):
        self.ensure_one()
        activity_type = self.env.ref(
            "receipt_kmitl.mail_activity_type_remittance_approval",
            raise_if_not_found=False,
        )
        if activity_type:
            activities = self.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
            )
            activities.action_done()

    def _cancel_approver_activity(self):
        self.ensure_one()
        activity_type = self.env.ref(
            "receipt_kmitl.mail_activity_type_remittance_approval",
            raise_if_not_found=False,
        )
        if activity_type:
            activities = self.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
            )
            activities.unlink()

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft remittances can be submitted."))
            if not rec.approver_id:
                raise UserError(_("Please set an approver before submitting."))
            rec._validate_receipts("to_submit")
            for receipt in rec.receipt_ids:
                if not self.env["account.analytic.account"].search_count(
                    [
                        ("id", "=", receipt.department_analytic_id.id),
                        ("id", "child_of", rec.department_analytic_id.id),
                    ]
                ):
                    raise ValidationError(
                        _("Receipt %s does not belong to this department's subtree.")
                        % receipt.name
                    )
                if receipt.company_id != rec.company_id:
                    raise ValidationError(
                        _("Receipt %s belongs to a different company.")
                        % receipt.name
                    )
            rec.date = fields.Date.context_today(rec)
            if rec.name == "/" or not rec.name:
                rec.name = rec._get_sequence().next_by_id()
            rec.receipt_ids.write({"state": "submitted"})
            rec.state = "submitted"
            rec._schedule_approver_activity()

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted remittances can be approved."))
            rec._validate_receipts("submitted")
            rec._complete_approver_activity()
            rec.receipt_ids.write({"state": "approved"})
            rec.write(
                {
                    "state": "approved",
                    "approved_by": self.env.user.id,
                    "approved_date": fields.Datetime.now(),
                }
            )

    def action_reject(self):
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Only submitted remittances can be rejected."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.receipt.remittance.reject",
            "view_mode": "form",
            "target": "new",
            "context": {"default_remittance_id": self.id},
        }

    def action_post(self):
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("Only approved remittances can be posted."))
            if not rec.receipt_ids:
                raise UserError(
                    _("Cannot post a remittance with no receipts.")
                )
            rec.receipt_ids._action_post()
            rec.state = "posted"

    def action_draft(self):
        for rec in self:
            if rec.state == "posted":
                if not self.env.user.has_group(
                    "receipt_kmitl.group_receipt_kmitl_manager"
                ):
                    raise UserError(
                        _("Only managers can reset posted remittances to draft.")
                    )
                for receipt in rec.receipt_ids:
                    if receipt.move_id:
                        receipt.move_id._reverse_moves(
                            default_values_list=[{
                                "date": fields.Date.context_today(rec),
                                "ref": _("Reversal of: %s") % receipt.move_id.name,
                            }],
                            cancel=True,
                        )
                        receipt.write({"move_id": False})
            if rec.state in ("draft", "cancelled"):
                pass
            elif rec.state not in ("submitted", "approved", "posted"):
                raise UserError(
                    _("Cannot reset to draft from this state.")
                )
            rec._cancel_approver_activity()
            rec.receipt_ids.write({"state": "to_submit"})
            rec.write(
                {
                    "state": "draft",
                    "approved_by": False,
                    "approved_date": False,
                }
            )

    def action_cancel(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Posted remittances cannot be cancelled."))
            rec.receipt_ids.write({"remittance_id": False, "state": "to_submit"})
            rec.state = "cancelled"

    def action_view_journal_entries(self):
        self.ensure_one()
        move_ids = self.receipt_ids.mapped("move_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Entries"),
            "res_model": "account.move",
            "view_mode": "tree,form",
            "views": [(False, "tree"), (False, "form")],
            "domain": [("id", "in", move_ids)],
            "target": "current",
        }

    def action_view_receipts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Receipts"),
            "res_model": "kmitl.receipt",
            "view_mode": "tree,form",
            "views": [(False, "tree"), (False, "form")],
            "domain": [("id", "in", self.receipt_ids.ids)],
            "target": "current",
        }

    def unlink(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Posted remittances cannot be deleted."))
        return super().unlink()
