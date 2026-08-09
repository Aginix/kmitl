from odoo import fields, models


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    def write(self, vals):
        """Keep the OU cached on open activities in step with the source record.

        The activity's ``operating_unit_id`` is a denormalised copy of the source
        record's OU (ADR-0002). When the source moves to another operating unit,
        its open group Todos must follow so visibility re-resolves live (role ∩
        *new* OU). Writing the OU onto the activities also fires
        ``mail.activity._todo_notify`` (before + after), so the old and new OU
        members' badges refresh immediately — not only on reload.
        """
        res = super().write(vals)
        if "operating_unit_id" in vals and "operating_unit_id" in self._fields:
            for record in self:
                ou_id = record.operating_unit_id.id
                stale = record.activity_ids.filtered(
                    lambda a: a.operating_unit_id.id != ou_id
                )
                if stale:
                    # sudo: whoever moves the source OU need not own the group
                    # activities (their user_id is empty); syncing the OU cache
                    # is a system action, not a per-user edit.
                    stale.sudo().write({"operating_unit_id": ou_id})
        return res

    def activity_schedule(
        self, act_type_xmlid="", date_deadline=None, summary="", note="", **act_values
    ):
        """Schedule a group Todo (ADR-0002) with no single assignee.

        Going through core ``activity_schedule`` would (1) force ``user_id`` to
        ``env.uid`` (core mail.activity.mixin) and (2) subscribe ``env.user`` as a
        follower of the source record (core mail.activity.create). For a group
        Todo we want neither. So for the group case we create the activity
        directly with ``user_id=False`` and the ``mail_activity_quick_update``
        context, which skips the notify path; ``user_id=False`` skips the
        follower subscription. Personal Todos go through core unchanged.
        """
        is_group = bool(act_values.get("responsible_role_id")) and not act_values.get(
            "user_id"
        )
        if not is_group:
            return super().activity_schedule(
                act_type_xmlid=act_type_xmlid,
                date_deadline=date_deadline,
                summary=summary,
                note=note,
                **act_values,
            )

        if not date_deadline:
            date_deadline = fields.Date.context_today(self)
        if act_type_xmlid:
            activity_type = self.env.ref(act_type_xmlid)
        else:
            activity_type = self.env["mail.activity.type"].browse(
                act_values.get("activity_type_id")
            )
        model_id = self.env["ir.model"]._get(self._name).id
        vals_list = []
        for record in self:
            vals = {
                "activity_type_id": activity_type.id,
                "summary": summary or activity_type.summary,
                "note": note or activity_type.default_note,
                "automated": True,
                "date_deadline": date_deadline,
                "res_model_id": model_id,
                "res_id": record.id,
            }
            vals.update(act_values)
            vals["user_id"] = False
            vals_list.append(vals)
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(vals_list)
        )
