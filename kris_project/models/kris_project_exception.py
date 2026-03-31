import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KrisProject(models.Model):
    _name = "kris.project"
    _inherit = ["kris.project", "base.exception"]
    _order = "main_exception_id asc, name desc"

    @api.model
    def _reverse_field(self):
        return "kris_project_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "kris_project.action_kris_project_exception_confirm"
        )

    def _popup_exceptions(self):
        action = super()._popup_exceptions()
        action["context"]["kris_exception_action"] = self.env.context.get(
            "kris_exception_action", "action_confirm"
        )
        return action

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("สามารถยืนยันได้เฉพาะโครงการที่อยู่ในสถานะร่างเท่านั้น")
                )
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                kris_exception_action="action_confirm"
            )._popup_exceptions()
        self.write({"state": "confirmed", "ignore_exception": False})

    def action_done(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(
                    _("สามารถปิดได้เฉพาะโครงการที่ยืนยันแล้วเท่านั้น")
                )
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                kris_exception_action="action_done"
            )._popup_exceptions()
        self.write({"state": "done", "ignore_exception": False})

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(
                    _("ไม่สามารถยกเลิกโครงการที่เสร็จสิ้นแล้วได้")
                )
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                kris_exception_action="action_cancel"
            )._popup_exceptions()
        self.write({"state": "cancel", "ignore_exception": False})

    def action_draft(self):
        for rec in self:
            if rec.state != "cancel":
                raise UserError(
                    _("สามารถรีเซ็ตได้เฉพาะโครงการที่ถูกยกเลิกเท่านั้น")
                )
        self.write({
            "state": "draft",
            "exception_ids": [(5,)],
            "main_exception_id": False,
            "ignore_exception": False,
        })
