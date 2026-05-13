from odoo import api, models


class MisReportKpiStyle(models.Model):
    _inherit = "mis.report.style"

    @api.model
    def to_xlsx_style(self, var_type, props, no_indent=False):
        result = super().to_xlsx_style(var_type, props, no_indent=no_indent)
        if no_indent:
            return result
        extra = 0
        if isinstance(props, dict):
            extra = props.get("_hierarchy_level", 0) or 0
        if extra:
            result["indent"] = (result.get("indent", 0) or 0) + extra
        return result
