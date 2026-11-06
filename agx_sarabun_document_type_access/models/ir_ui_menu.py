from odoo import api, models, tools


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @tools.ormcache("frozenset(self.env.user.groups_id.ids)", "debug")
    def _visible_menu_ids(self, debug=False):
        """Hide หนังสือของหน่วยงาน from users who read no document type."""
        visible = super()._visible_menu_ids(debug)
        menu = self.env.ref(
            "agx_sarabun_document_type_access.menu_sarabun_document_unit",
            raise_if_not_found=False,
        )
        if menu and menu.id in visible:
            is_reader = (
                self.env["sarabun.document.type"]
                .sudo()
                .search_count(
                    [("reader_group_ids", "in", self.env.user.groups_id.ids)], limit=1
                )
            )
            if not is_reader:
                visible = visible - {menu.id}
        return visible
