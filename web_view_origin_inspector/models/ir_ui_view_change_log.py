from lxml import etree

from odoo import _, api, fields, models
from odoo.tools import get_diff


class IrUiViewChangeLog(models.Model):
    """Manual view changes made on the database (Edit View, inspector...).

    They are not in any module file: the next deploy may overwrite them or
    break them, so each one is kept here until it is ported to code.
    """

    _name = "ir.ui.view.change.log"
    _description = "View Change Log"
    _order = "id desc"
    _rec_name = "view_name"

    view_id = fields.Many2one("ir.ui.view", ondelete="set null", index=True)
    view_name = fields.Char(required=True)
    view_xmlid = fields.Char("External ID")
    arch_fs = fields.Char("Source File")
    model = fields.Char()
    parent_xmlid = fields.Char("Inherited View")
    operation = fields.Selection(
        [
            ("create", "Created"),
            ("write", "Modified"),
            ("unlink", "Deleted"),
            ("hide", "Hidden by Inspector"),
        ],
        required=True,
    )
    element = fields.Char(help="Element hidden from the inspector")
    target_xpath = fields.Char("XPath")
    arch_before = fields.Text()
    arch_after = fields.Text()
    arch_diff = fields.Html(compute="_compute_arch_diff", sanitize=False)
    xml_snippet = fields.Text(
        "XML to Port", help="Record to paste in a module data file"
    )
    reset_on_upgrade = fields.Boolean(
        help="The view comes from a module file without noupdate: the next "
        "upgrade of that module overwrites this change."
    )
    state = fields.Selection(
        [
            ("pending", "To Port"),
            ("done", "Ported to Code"),
            ("ignored", "Ignored"),
            ("reverted", "Reverted"),
        ],
        default="pending",
        required=True,
    )
    note = fields.Text()

    @api.depends("arch_before", "arch_after")
    def _compute_arch_diff(self):
        for log in self:
            log.arch_diff = get_diff(
                (log.arch_before or "", _("Before")),
                (log.arch_after or "", _("After")),
            )

    @api.model
    def _log_views(self, views, operation, before=None, extra=None):
        vals_list = []
        for view in views:
            arch_before = (before or {}).get(view.id, False)
            arch_after = operation != "unlink" and view._view_change_log_snapshot()
            if operation == "write" and arch_before == arch_after:
                continue
            imd = view.model_data_id
            parent_xmlid = view.inherit_id.xml_id or ""
            snippet = False
            if operation in ("create", "hide") and parent_xmlid:
                root = etree.fromstring(view.arch)
                snippet = view._view_origin_record_xml(
                    view.name,
                    view.name,
                    view.model,
                    parent_xmlid,
                    list(root) if root.tag == "data" else [root],
                )
            vals_list.append(
                dict(
                    view_id=view.id,
                    view_name=view.name,
                    view_xmlid=view.xml_id,
                    arch_fs=view.arch_fs,
                    model=view.model,
                    parent_xmlid=parent_xmlid,
                    operation=operation,
                    arch_before=arch_before,
                    arch_after=arch_after,
                    xml_snippet=snippet,
                    reset_on_upgrade=bool(imd and not imd.noupdate),
                    **(extra or {}),
                )
            )
        return self.sudo().create(vals_list)

    def action_done(self):
        self.state = "done"

    def action_ignore(self):
        self.state = "ignored"

    def action_reset_pending(self):
        self.state = "pending"

    def action_revert_hide(self):
        """Drop the extension view created by the inspector."""
        for log in self.filtered(lambda l: l.operation == "hide" and l.view_id):
            log.view_id.with_context(view_change_log_skip=True).unlink()
        self.state = "reverted"

    def action_open_view(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.ui.view",
            "res_id": self.view_id.id,
            "view_mode": "form",
        }
