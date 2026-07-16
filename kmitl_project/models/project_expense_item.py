# -*- coding: utf-8 -*-
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)

# ประเภทงบ — fixed Thai government budget categories shared by the expense
# master data (project.expense.item) and the project expense lines
# (project.expense). Defined here (imported by project_expense) so both models
# stay in sync.
BUDGET_TYPE_SELECTION = [
    ("personnel", "งบบุคลากร"),
    ("operating", "งบดำเนินงาน"),
    ("subsidy", "งบอุดหนุน"),
]


class ProjectExpenseItem(models.Model):
    """Master data for the selectable expense items (รายการค่าใช้จ่าย). Each item is
    categorised under one budget type (ประเภทงบ) and configured on its own settings
    page; project expense lines pick from these."""

    _name = "project.expense.item"
    _description = "รายการค่าใช้จ่ายโครงการ"
    _order = "budget_type, sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="รายการค่าใช้จ่าย", required=True)
    budget_type = fields.Selection(
        BUDGET_TYPE_SELECTION,
        string="ประเภทงบ",
        required=True,
    )
    active = fields.Boolean(default=True)
