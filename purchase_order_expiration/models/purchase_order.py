import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

ACTIVITY_TYPE_XMLID = "purchase_order_expiration.mail_activity_type_po_expiring"

_EXPIRY_TRIGGER_FIELDS = {"state", "work_end", "user_id"}


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
    def _expiry_activity_wanted(self):
        self.ensure_one()
        return self.state == "purchase"

    def _expiry_activity_user(self):
        self.ensure_one()
        return self.user_id

    def _expiry_activity_deadline(self):
        self.ensure_one()
        return self.work_end

    def _expiry_activity_summary(self):
        self.ensure_one()
        return _("Purchase Order %s expires on %s") % (self.name, self.work_end)

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
            if not po._expiry_activity_wanted():
                existing.unlink()
                continue
            owner = po._expiry_activity_user()
            deadline = po._expiry_activity_deadline()
            if not owner or not deadline:
                existing.unlink()
                continue
            summary = po._expiry_activity_summary()
            if existing:
                vals = {}
                if existing.user_id != owner:
                    vals["user_id"] = owner.id
                if existing.date_deadline != deadline:
                    vals["date_deadline"] = deadline
                if existing.summary != summary:
                    vals["summary"] = summary
                if vals:
                    existing.write(vals)
            else:
                po.activity_schedule(
                    act_type_xmlid=ACTIVITY_TYPE_XMLID,
                    user_id=owner.id,
                    date_deadline=deadline,
                    summary=summary,
                )

    def write(self, vals):
        res = super().write(vals)
        if _EXPIRY_TRIGGER_FIELDS & set(vals):
            self._sync_expiry_activity()
        return res
