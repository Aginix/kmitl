# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class KmitlCsvReport(models.AbstractModel):
    """Shared plumbing for the KMITL accounting reports' CSV export.

    Each report's CSV class only implements :meth:`_kmitl_csv_rows` (a flat
    table: the first row is the header, every following row is one data record
    with its context columns filled in — ready for pivot/analysis/import). The
    figures come from the same ``get_*_data`` compute as the screen / PDF /
    XLSX, so the CSV never drifts from the other outputs.
    """

    _name = "accounting_kmitl_reports.csv.report"
    _inherit = "report.report_csv.abstract"
    _description = "KMITL CSV report base"

    def csv_report_options(self):
        # We emit whole rows through the raw csv writer (below), so the
        # DictWriter fieldnames are unused — a single dummy keeps it happy.
        res = super().csv_report_options()
        res["fieldnames"] = ["_"]
        return res

    def generate_csv_report(self, file, data, objs):
        options = (data or {}).get("options") or {}
        # ``file`` is a csv.DictWriter; ``file.writer`` is the underlying
        # csv.writer, which takes plain lists (one per row) of any width.
        for row in self._kmitl_csv_rows(options):
            file.writer.writerow(row)

    @api.model
    def _csv_num(self, value):
        """A real number for every amount cell (a flat table wants values it
        can sum/pivot, not blanks) — rounded to 2 dp, no thousands separator."""
        return round(value or 0.0, 2)

    def _kmitl_csv_rows(self, options):
        """Return the CSV as a list of row-lists (header first). Overridden by
        each report's CSV class."""
        raise NotImplementedError()
