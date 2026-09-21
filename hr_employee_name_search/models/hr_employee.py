from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _rec_names_search = ["name", "academic_standing_name_search"]

    academic_standing_name_search = fields.Char(
        compute="_compute_academic_standing_name_search",
        store=True,
        index=True,
        help="Hidden search index combining every academic standing title \
            variant with the employee name, so the employee can be found by \
            title prefix or by full name (title + name) in one query.",
    )

    @api.depends(
        "name",
        "name_secondary",
        "academic_standing_title",
        "academic_standing_title_abbreviation",
        "academic_standing_title_en",
        "academic_standing_title_abbreviation_en",
    )
    def _compute_academic_standing_name_search(self):
        for rec in self:
            # Glue each title variant to the matching name so that
            # "<title> <name>" (e.g. "รศ. ดร. ปานวิทย์") matches as a single
            # ilike segment, while a bare title or bare name still hits via
            # substring. Thai titles pair with the Thai name; English titles
            # pair with the English name (name_secondary).
            name = rec.name or ""
            name_en = rec.name_secondary or ""
            title_pairs = (
                (rec.academic_standing_title, name),
                (rec.academic_standing_title_abbreviation, name),
                (rec.academic_standing_title_en, name_en),
                (rec.academic_standing_title_abbreviation_en, name_en),
            )
            segments = [
                "{title} {value}".format(title=title, value=value).strip()
                for title, value in title_pairs
                if title
            ]
            rec.academic_standing_name_search = " | ".join(segments) or name
