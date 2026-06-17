from odoo import _, api, fields, models


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

    # --- Report fields: display-only from purchase.order (store=False) ---
    contract_number = fields.Char(related="purchase_id.contract_number", store=False, string="เลขที่สัญญา")
    contract_name = fields.Char(related="purchase_id.contract_name", store=False, string="ชื่องาน")
    contract_type_id = fields.Many2one("purchase.contract.type", related="purchase_id.contract_type_id", store=False, string="ประเภทงาน")
    work_start = fields.Date(related="purchase_id.work_start", store=False, string="วันที่เริ่มสัญญา")
    work_end = fields.Date(related="purchase_id.work_end", store=False, string="วันที่สิ้นสุดสัญญา")
    purchase_state = fields.Selection(related="purchase_id.state", store=False, string="สถานะสัญญา")

    date_due_display = fields.Char(
        string="วันที่สิ้นสุดอายุหลักประกัน",
        compute="_compute_date_due_display",
        store=False,
    )
    guarantee_return_state = fields.Selection(
        selection=[("returned", "คืนแล้ว"), ("pending", "ยังไม่ได้คืน")],
        string="สถานะหลักประกัน",
        compute="_compute_guarantee_return_state",
        store=True,
    )

    @api.depends("date_due_guarantee")
    def _compute_date_due_display(self):
        for rec in self:
            if rec.date_due_guarantee:
                rec.date_due_display = rec.date_due_guarantee.strftime("%d/%m/%Y")
            else:
                rec.date_due_display = "จนกว่าจะพ้นภาระผูกพันธ์"

    @api.depends("date_return")
    def _compute_guarantee_return_state(self):
        for rec in self:
            rec.guarantee_return_state = "returned" if rec.date_return else "pending"

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
