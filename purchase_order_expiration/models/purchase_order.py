import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

ACTIVE_STATES = ("draft", "sent", "to approve", "purchase")
ACTIVITY_TYPE_XMLID = "purchase_order_expiration.mail_activity_type_po_expiring"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    days_to_expire = fields.Integer(
        string="Days to Expire", compute="_compute_days_to_expire", store=True
    )

    expire_range = fields.Selection(
        [
            ("0-15", "0-15 Days"),
            ("16-30", "16-30 Days"),
            ("31-60", "31-60 Days"),
            ("60+", "Morethan 60 Days"),
        ],
        string="Expire Range",
        compute="_compute_expire_range",
        store=True,
    )

    days_to_expire_display = fields.Char(
        string="Days to Expire", compute="_compute_days_to_expire_display", store=False
    )

    def action_recompute_expire(self):
        records = self.search([("work_end", "!=", False)])
        records._compute_days_to_expire()
        records._compute_expire_range()

    @api.depends("work_end", "days_to_expire")
    def _compute_days_to_expire_display(self):
        for record in self:
            record.days_to_expire_display = (
                str(record.days_to_expire) if record.work_end else ""
            )

    @api.depends("work_end")
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for record in self:
            if record.work_end:
                record.days_to_expire = (record.work_end - today).days
            else:
                record.days_to_expire = 0

    @api.depends("days_to_expire")
    def _compute_expire_range(self):
        for record in self:
            days = record.days_to_expire
            if days <= 15:
                record.expire_range = "0-15"
            elif days <= 30:
                record.expire_range = "16-30"
            elif days <= 60:
                record.expire_range = "31-60"
            else:
                record.expire_range = "60+"

    # ------------------------------------------------------------------
    # Expiry Todo (mail_activity_todo)
    # ------------------------------------------------------------------
    def _sync_expiry_activity(self):
        activity_type = self.env.ref(ACTIVITY_TYPE_XMLID, raise_if_not_found=False)
        if not activity_type:
            return
        Activity = self.env["mail.activity"].sudo()
        for po in self:
            existing = Activity.search(
                [
                    ("res_model", "=", po._name),
                    ("res_id", "=", po.id),
                    ("activity_type_id", "=", activity_type.id),
                ],
                limit=1,
            )
            should_exist = po.state in ACTIVE_STATES and po.work_end and po.user_id
            if should_exist:
                summary = _("Purchase Order %s expires on %s") % (
                    po.name or "",
                    po.work_end,
                )
                if existing:
                    vals = {}
                    if existing.date_deadline != po.work_end:
                        vals["date_deadline"] = po.work_end
                    if existing.user_id != po.user_id:
                        vals["user_id"] = po.user_id.id
                    if existing.summary != summary:
                        vals["summary"] = summary
                    if vals:
                        existing.write(vals)
                else:
                    po.activity_schedule(
                        act_type_xmlid=ACTIVITY_TYPE_XMLID,
                        user_id=po.user_id.id,
                        date_deadline=po.work_end,
                        summary=summary,
                    )
            elif existing:
                existing.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_expiry_activity()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"work_end", "user_id", "state"} & set(vals):
            self._sync_expiry_activity()
        return res
