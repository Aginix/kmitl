# Copyright 2025 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    budget_allow_negative = fields.Boolean(
        string="อนุญาตงบประมาณติดลบ",
        config_parameter="budget.allow_negative",
        help="อนุญาตให้มีรายการที่ทำให้งบประมาณติดลบ",
    )

    budget_overview_enabled = fields.Boolean(
        string="หน้าภาพรวมงบประมาณ",
        default=True,
        help=(
            "แสดงหน้าภาพรวม (การ์ดตามประเภทงบ + การเคลื่อนไหวล่าสุด) "
            "เป็นหน้าแรกของโมดูลงบประมาณ หากปิด เมนูภาพรวมจะถูกซ่อน"
        ),
    )

    def _budget_overview_menu(self):
        return self.env.ref("budget.budget_overview_menu", raise_if_not_found=False)

    def get_values(self):
        res = super().get_values()
        # The overview landing menu's `active` flag is the source of truth, so
        # the toggle round-trips reliably and defaults on. (A boolean
        # config_parameter defaulting to True cannot: unchecking only unlinks
        # the param, and get_param then returns the True default again.)
        menu = self._budget_overview_menu()
        res["budget_overview_enabled"] = bool(menu and menu.active)
        return res

    def set_values(self):
        super().set_values()
        # Show/hide the overview landing menu. Hiding it makes the budget app
        # fall back to its next menu, so there is no overview page.
        # sudo: budget managers may lack write access to ir.ui.menu.
        menu = self._budget_overview_menu()
        if menu and menu.active != self.budget_overview_enabled:
            menu.sudo().active = self.budget_overview_enabled