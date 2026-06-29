import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

ACTIVITY_TYPE_XMLID = (
    "purchase_guarantee_expiration.mail_activity_type_guarantee_expiring"
)


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

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
        records = self.search([("date_due_guarantee", "!=", False)])
        records._compute_days_to_expire()
        records._compute_expire_range()

    @api.depends("date_due_guarantee", "days_to_expire")
    def _compute_days_to_expire_display(self):
        for record in self:
            record.days_to_expire_display = (
                str(record.days_to_expire) if record.date_due_guarantee else ""
            )

    @api.depends("date_due_guarantee")
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for record in self:
            if record.date_due_guarantee:
                record.days_to_expire = (record.date_due_guarantee - today).days
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
    def _expiry_activity_user(self):
        self.ensure_one()
        return self.purchase_id.user_id or self.requisition_id.user_id

    def _sync_expiry_activity(self):
        activity_type = self.env.ref(ACTIVITY_TYPE_XMLID, raise_if_not_found=False)
        if not activity_type:
            return
        Activity = self.env["mail.activity"].sudo()
        for guarantee in self:
            existing = Activity.search(
                [
                    ("res_model", "=", guarantee._name),
                    ("res_id", "=", guarantee.id),
                    ("activity_type_id", "=", activity_type.id),
                ],
                limit=1,
            )
            user = guarantee._expiry_activity_user()
            should_exist = (
                guarantee.state == "draft"
                and not guarantee.date_return
                and guarantee.date_due_guarantee
                and user
            )
            if should_exist:
                summary = _("Purchase Guarantee %s expires on %s") % (
                    guarantee.name or "",
                    guarantee.date_due_guarantee,
                )
                if existing:
                    vals = {}
                    if existing.date_deadline != guarantee.date_due_guarantee:
                        vals["date_deadline"] = guarantee.date_due_guarantee
                    if existing.user_id != user:
                        vals["user_id"] = user.id
                    if existing.summary != summary:
                        vals["summary"] = summary
                    if vals:
                        existing.write(vals)
                else:
                    guarantee.activity_schedule(
                        act_type_xmlid=ACTIVITY_TYPE_XMLID,
                        user_id=user.id,
                        date_deadline=guarantee.date_due_guarantee,
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
        watched = {
            "date_due_guarantee",
            "date_return",
            "state",
            "purchase_id",
            "requisition_id",
        }
        if watched & set(vals):
            self._sync_expiry_activity()
        return res
