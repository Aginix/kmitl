# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Todo pushed to the approver while a submission waits to be accepted.
APPROVAL_ACTIVITY = "invoice_kmitl.mail_activity_type_submission_approval"


class InvoiceSubmission(models.Model):
    _name = "kmitl.invoice.submission"
    _description = "KMITL Invoice Submission"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Submission Number",
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
            ("accepted", "Accepted"),
            ("done", "Sent to Accounting"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        required=True,
        domain=[("root_plan_id.code", "=", "departments"), ("parent_id", "=", False)],
        tracking=True,
    )
    invoice_ids = fields.One2many(
        "kmitl.invoice",
        "submission_id",
        string="Invoices",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    note = fields.Text(string="Notes")
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
            (
                "groups_id",
                "in",
                [self.env.ref("invoice_kmitl.group_invoice_kmitl_approver").id],
            )
        ],
        tracking=True,
    )
    accepted_by = fields.Many2one(
        "res.users", string="Accepted By", readonly=True, copy=False
    )
    accepted_date = fields.Datetime(string="Accepted On", readonly=True, copy=False)
    invoice_count = fields.Integer(
        string="# Invoices", compute="_compute_invoice_count"
    )
    move_count = fields.Integer(string="# Entries", compute="_compute_move_count")

    # -------------------------------------------------------------------------
    # Computes & constraints
    # -------------------------------------------------------------------------
    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends("invoice_ids.move_id")
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.invoice_ids.move_id)

    @api.depends("invoice_ids.amount_total")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.invoice_ids.mapped("amount_total"))

    @api.constrains("department_analytic_id")
    def _check_department_is_root(self):
        for rec in self:
            if rec.department_analytic_id.parent_id:
                raise ValidationError(
                    _("A submission must be filed under a top-level department.")
                )

    def _check_approver(self):
        self.ensure_one()
        if self.env.user != self.approver_id and not self.env.user.has_group(
            "invoice_kmitl.group_invoice_kmitl_manager"
        ):
            raise UserError(_("Only the assigned approver can act on this submission."))

    @api.model
    def _get_sequence(self, date):
        return self.env["kmitl.invoice"]._get_fiscal_year_sequence(
            "kmitl.invoice.submission", "Invoice Submission", "IS", date
        )

    # -------------------------------------------------------------------------
    # Invoices of the submission
    # -------------------------------------------------------------------------
    def _validate_invoices(self, expected_state):
        self.ensure_one()
        invoices = self.sudo().invoice_ids
        if not invoices:
            raise ValidationError(_("Add at least one invoice."))
        for invoice in invoices:
            if invoice.state != expected_state:
                raise ValidationError(
                    _("Invoice %(invoice)s is not in '%(state)s' state.")
                    % {"invoice": invoice.name, "state": expected_state}
                )

    def _get_pending_invoice_domain(self):
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("department_analytic_id", "child_of", self.department_analytic_id.id),
            ("state", "=", "draft"),
            ("submission_id", "=", False),
            ("date", "<=", self.date),
        ]

    def _check_invoice_consistency(self, invoices):
        self.ensure_one()
        valid_ids = set(
            self.env["account.analytic.account"]
            .search([("id", "child_of", self.department_analytic_id.id)])
            .ids
        )
        for invoice in invoices:
            if invoice.department_analytic_id.id not in valid_ids:
                raise ValidationError(
                    _("Invoice %s does not belong to this department's subtree.")
                    % invoice.name
                )
            if invoice.company_id != self.company_id:
                raise ValidationError(
                    _("Invoice %s belongs to a different company.") % invoice.name
                )

    def action_pull_pending_invoices(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Can only pull invoices on draft submissions."))
            invoices = self.env["kmitl.invoice"].search(
                rec._get_pending_invoice_domain()
            )
            if not invoices:
                raise UserError(_("No pending invoices found for this department."))
            rec.write({"invoice_ids": [Command.link(id_) for id_ in invoices.ids]})

    # -------------------------------------------------------------------------
    # Workflow
    # -------------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft submissions can be submitted."))
            if not rec.approver_id:
                raise UserError(_("Please set an approver before submitting."))
            rec._validate_invoices("draft")
            invoices = rec.sudo().invoice_ids
            rec._check_invoice_consistency(invoices)
            rec.date = fields.Date.context_today(rec)
            if rec.name == "/":
                rec.name = rec._get_sequence(rec.date).next_by_id()
            invoices.write({"state": "submitted"})
            rec.state = "submitted"
            rec.activity_schedule(
                APPROVAL_ACTIVITY,
                user_id=rec.approver_id.id,
                summary=_("Invoice submission %s awaiting acceptance") % rec.name,
            )

    def action_accept(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted submissions can be accepted."))
            rec._check_approver()
            rec._validate_invoices("submitted")
            rec.activity_feedback([APPROVAL_ACTIVITY])
            rec.sudo().invoice_ids.write({"state": "accepted"})
            rec.write(
                {
                    "state": "accepted",
                    "accepted_by": self.env.user.id,
                    "accepted_date": fields.Datetime.now(),
                }
            )

    def action_reject(self):
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Only submitted submissions can be rejected."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.invoice.submission.reject",
            "view_mode": "form",
            "target": "new",
            "context": {"default_submission_id": self.id},
        }

    def action_done(self):
        """Send the accepted invoices to accounting: one draft receivable entry each,
        raised with the user's own accounting rights — a treasury officer raises
        them, the accounting office submits and approves."""
        for rec in self:
            if rec.state != "accepted":
                raise UserError(
                    _("Only accepted submissions can be sent to accounting.")
                )
            rec._validate_invoices("accepted")
            invoices = rec.sudo().invoice_ids
            # Refuse rather than silently skip invoices hidden by record rules.
            if self.env["kmitl.invoice"].search_count(
                [("id", "in", invoices.ids)]
            ) != len(invoices):
                raise UserError(
                    _(
                        "Some invoices on this submission are not accessible to "
                        "you and cannot be sent to accounting."
                    )
                )
            for invoice in invoices.with_env(self.env):
                invoice._create_move()
            invoices.write({"state": "issued"})
            rec.state = "done"
        return True

    def _reset(self):
        """Back to draft, the invoices handed back to the department. A cancelled
        invoice is history, not part of a batch that starts over: it leaves the
        submission rather than blocking its next Submit."""
        self.activity_unlink([APPROVAL_ACTIVITY])
        invoices = self.sudo().invoice_ids
        cancelled = invoices.filtered(lambda invoice: invoice.state == "cancelled")
        cancelled.write({"submission_id": False})
        (invoices - cancelled).write({"state": "draft"})
        self.write({"state": "draft", "accepted_by": False, "accepted_date": False})

    def _reset_done(self):
        """Take back what ``action_done`` raised, possible only while every entry it
        created is still an untouched draft."""
        self.ensure_one()
        if not self.env.user.has_group("invoice_kmitl.group_invoice_kmitl_manager"):
            raise UserError(
                _("Only managers can reset a submission sent to accounting.")
            )
        invoices = self.sudo().invoice_ids.filtered(lambda i: i.state != "cancelled")
        moved_on = invoices.filtered(
            lambda i: i.state != "issued" or i.move_id.state not in ("draft", False)
        )
        if moved_on:
            raise UserError(
                _(
                    "Invoices %s are already in accounting's hands or paid. "
                    "Cancel them one by one instead."
                )
                % ", ".join(moved_on.mapped("name"))
            )
        moves = invoices.move_id
        invoices.write({"move_id": False})
        moves.with_context(force_delete=True).unlink()

    def action_draft(self):
        for rec in self:
            if rec.state == "done":
                rec._reset_done()
            elif rec.state not in ("submitted", "accepted", "cancelled"):
                raise UserError(_("Cannot reset to draft from this state."))
            rec._reset()
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(
                    _("Submissions sent to accounting cannot be cancelled.")
                )
            rec.activity_unlink([APPROVAL_ACTIVITY])
            rec.sudo().invoice_ids.write({"submission_id": False, "state": "draft"})
            rec.state = "cancelled"
        return True

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "cancelled"):
                raise UserError(
                    _("Only draft or cancelled submissions can be deleted.")
                )
        return super().unlink()

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------
    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "kmitl.invoice",
            "view_mode": "tree,form",
            "views": [(False, "tree"), (False, "form")],
            "domain": [("id", "in", self.invoice_ids.ids)],
            "target": "current",
        }

    def action_view_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Receivable Entries"),
            "res_model": "account.move",
            "view_mode": "tree,form",
            "views": [(False, "tree"), (False, "form")],
            "domain": [("id", "in", self.invoice_ids.move_id.ids)],
            "target": "current",
        }
