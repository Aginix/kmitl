# -*- coding: utf-8 -*-
from odoo import api, models


class MaterialWithdrawalReport(models.AbstractModel):
    _name = "report.purchase_request_approval.report_material_withdrawal"
    _description = "Material Withdrawal (พ.43) Report Values"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        Employee = self.env["hr.employee"]
        approvals = self.env["purchase.request.approval"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "purchase.request.approval",
            "docs": approvals,
            "requester": Employee.browse(data.get("requester_id") or []),
            "dept_head": Employee.browse(data.get("dept_head_id") or []),
            "disburser": Employee.browse(data.get("disburser_id") or []),
        }
