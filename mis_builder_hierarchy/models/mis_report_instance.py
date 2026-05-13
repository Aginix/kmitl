from odoo import models


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _compute_matrix(self):
        kpi_matrix = super()._compute_matrix()
        kpi_matrix._expand_and_rollup_all()
        return kpi_matrix
