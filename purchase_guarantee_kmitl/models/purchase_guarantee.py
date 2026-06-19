from datetime import timedelta

from odoo import _, api, fields, models

GUARANTEE_ACT = "purchase_guarantee_kmitl.mail_activity_guarantee_expire"


class PurchaseGuarantee(models.Model):
    _name = "purchase.guarantee"
    _inherit = ["analytic.mixin", "purchase.guarantee"]

    # --- Tracking (from purchase_guarantee_tracking) ---
    reference = fields.Reference(tracking=True)
    reference_model = fields.Char(tracking=True)
    requisition_id = fields.Many2one(tracking=True)
    purchase_id = fields.Many2one(tracking=True)
    guarantee_method_id = fields.Many2one(tracking=True)
    partner_id = fields.Many2one(tracking=True)
    guarantee_type_id = fields.Many2one(tracking=True)
    company_id = fields.Many2one(tracking=True)
    amount = fields.Monetary(tracking=True)
    date_guarantee_receive = fields.Date(tracking=True)
    analytic_distribution = fields.Json(tracking=True)
    amount_received = fields.Monetary(tracking=True)
    document_ref = fields.Char(tracking=True)
    date_return = fields.Date(tracking=True)
    amount_returned = fields.Monetary(tracking=True)
    is_no_expiry = fields.Boolean(
        string="No Expiry",
        store=False,
        compute="_compute_is_no_expiry",
        inverse="_inverse_is_no_expiry",
    )
    date_due_guarantee = fields.Date(tracking=True)
    note = fields.Text(tracking=True)
    active = fields.Boolean(tracking=True)

    # --- Lock state (from purchase_guarantee_lock) ---
    _STATES = [("draft", "Draft"), ("lock", "Lock")]

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)

    # --- Attachment (from purchase_guarantee_attachment) ---
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        tracking=True,
    )

    # --- Purchase Order link (from purchase_guarantee_purchase_order_kmitl) ---
    is_purchase_order = fields.Boolean(
        string="Is Purchase Order",
        compute="_compute_is_purchase_order",
        store=False,
        help="True if reference is purchase.order",
    )

    @api.depends("date_due_guarantee")
    def _compute_is_no_expiry(self):
        for rec in self:
            rec.is_no_expiry = not rec.date_due_guarantee

    def _inverse_is_no_expiry(self):
        for rec in self:
            if rec.is_no_expiry:
                rec.date_due_guarantee = False

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state != "lock"

    def button_draft(self):
        return self.write({"state": "draft"})

    def button_lock(self):
        return self.write({"state": "lock"})

    @api.depends("reference")
    def _compute_is_purchase_order(self):
        for rec in self:
            rec.is_purchase_order = (
                bool(rec.reference) and rec.reference._name == "purchase.order"
            )

    @api.depends("reference")
    def _compute_guarantee_method_id(self):
        GuaranteeMethod = self.env["purchase.guarantee.method"]
        super()._compute_guarantee_method_id()
        for rec in self.filtered("reference"):
            if rec.reference._name == "purchase.order":
                dom = [
                    (
                        "default_for_model",
                        "=",
                        "{}.{}".format(rec.reference._name, "po"),
                    )
                ]
                rec.guarantee_method_id = GuaranteeMethod.search(dom)[:1]

    # --- Expiration notification (mail.activity Todo) ---
    def _domain_guarantee_expiration(self):
        today = fields.Date.today()
        days = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "purchase_guarantee_kmitl.notify_before_days", default=15
            )
        )
        return [
            ("active", "=", True),
            ("date_return", "=", False),  # not yet returned
            ("date_due_guarantee", ">=", today),
            ("date_due_guarantee", "<=", today + timedelta(days=days)),
        ]

    def _cron_notify_guarantee_expire(self):
        act_type = self.env.ref(GUARANTEE_ACT, raise_if_not_found=False)
        if not act_type:
            return
        for rec in self.search(self._domain_guarantee_expiration()):
            user = rec.create_uid
            if not user or rec.activity_ids.filtered(
                lambda a: a.activity_type_id == act_type
            ):
                continue  # no owner, or a Todo is already raised
            rec.activity_schedule(
                GUARANTEE_ACT,
                user_id=user.id,
                date_deadline=rec.date_due_guarantee,
            )

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return
        return {
            "name": _("Purchase Order"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": self.purchase_id.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "current",
            "context": self.env.context,
        }
