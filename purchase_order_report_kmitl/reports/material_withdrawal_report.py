# -*- coding: utf-8 -*-
from odoo import api, models


class POMaterialWithdrawalReport(models.AbstractModel):
    _name = "report.purchase_order_report_kmitl.report_material_withdrawal"
    _description = "Material Withdrawal (พ.43) Report Values from PO"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        Employee = self.env["hr.employee"]
        orders = self.env["purchase.order"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "purchase.order",
            "docs": orders,
            "requester": Employee.browse(data.get("requester_id") or []),
            "dept_head": Employee.browse(data.get("dept_head_id") or []),
            "disburser": Employee.browse(data.get("disburser_id") or []),
        }
