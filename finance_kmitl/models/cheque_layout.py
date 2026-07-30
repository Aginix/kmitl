# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ChequeLayout(models.Model):
    """Print calibration for a physical cheque form.

    Cheque layouts differ per bank, so field positions are stored as top/left
    offsets (in millimetres from the top-left of the cheque) and reused across
    the cheque books (journals) that share the same printed form.
    """

    _name = "cheque.layout"
    _description = "Cheque Print Layout"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    journal_ids = fields.One2many(
        comodel_name="account.journal",
        inverse_name="cheque_layout_id",
        string="Cheque Books",
        help="Bank/cash journals whose cheques use this printed form.",
    )

    # Rendering
    font_size = fields.Float(string="Font Size (pt)", default=14.0)
    date_buddhist_year = fields.Boolean(
        string="Buddhist Era Date",
        help="Print the year in the Buddhist Era (พ.ศ.) instead of the "
        "Gregorian year.",
    )
    date_spacing = fields.Float(
        string="Date Digit Spacing (mm)",
        default=2.5,
        help="Letter spacing between the 8 date digits so they line up with "
        "the pre-printed boxes.",
    )

    # Field positions (mm from top-left of the cheque). Grouped in the form
    # view, so each pair is labelled simply "Top"/"Left".
    date_top = fields.Float(string="Top", default=8.0)
    date_left = fields.Float(string="Left", default=135.0)
    payee_top = fields.Float(string="Top", default=22.0)
    payee_left = fields.Float(string="Left", default=22.0)
    amount_figure_top = fields.Float(string="Top", default=22.0)
    amount_figure_left = fields.Float(string="Left", default=138.0)
    amount_text_top = fields.Float(string="Top", default=33.0)
    amount_text_left = fields.Float(string="Left", default=22.0)
    crossing_top = fields.Float(string="Top", default=5.0)
    crossing_left = fields.Float(string="Left", default=12.0)
    bearer_top = fields.Float(string="Top", default=40.0)
    bearer_left = fields.Float(string="Left", default=118.0)
