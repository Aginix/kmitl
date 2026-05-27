import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

ACADEMIC_ONLY_FIELDS = (
    "academic_standing_id",
    "rank_id",
    "rank_nobility_id",
    "profession_id",
)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    academic_standing_id = fields.Many2one(
        "hr.employee.academic.standing", string="Academic Standing", tracking=True
    )
    rank_id = fields.Many2one("resource.rank", string="Rank", tracking=True)
    rank_nobility_id = fields.Many2one(
        "hr.employee.rank.nobility", string="Rank Nobility", tracking=True
    )
    profession_id = fields.Many2one(
        "hr.employee.profession", string="Profession", tracking=True
    )

    academic_standing_title = fields.Char(
        compute="_compute_academic_standing_title",
        store=True,
        help="If employee is academic role, Academic Standing Title derived from \
            academic standing, rank, profession, rank nobility and education \
            level But if employee is support role, Academic Standing Title derived \
            from job and position level",
    )
    academic_standing_title_abbreviation = fields.Char(
        compute="_compute_academic_standing_title",
        store=True,
    )
    academic_standing_title_en = fields.Char(
        string="Academic Standing Title English",
        compute="_compute_academic_standing_title",
        store=True,
    )
    academic_standing_title_abbreviation_en = fields.Char(
        string="Academic Standing Title Abbreviation English",
        compute="_compute_academic_standing_title",
        store=True,
    )

    @api.depends(
        "academic_standing_id",
        "rank_id",
        "rank_nobility_id",
        "profession_id",
        "education_level_id",
        "role",
        "job_id",
        "position_level_relation_id",
    )
    def _compute_academic_standing_title(self):
        def get_value(value):
            return value + " " if value else ""

        dr_education = self.env.ref(
            "hr_employee_education_history.Q01", raise_if_not_found=False
        )

        def get_academic_standing_for_academic_role(rec):
            title_dr = bool(dr_education and dr_education == rec.education_level_id)

            rec.academic_standing_title = (
                "{academic}{rank}{dr}{profession}{rank_nobility}".format(
                    academic=get_value(rec.academic_standing_id.name),
                    rank=get_value(rec.rank_id.name),
                    dr="ดร. " if title_dr else "",
                    profession=get_value(rec.profession_id.name),
                    rank_nobility=get_value(rec.rank_nobility_id.name),
                )
            ).strip()

            rec.academic_standing_title_abbreviation = (
                "{academic}{rank}{dr}{profession}{rank_nobility}".format(
                    academic=get_value(rec.academic_standing_id.name_abbreviation),
                    rank=get_value(rec.rank_id.name_abbreviation),
                    dr="ดร. " if title_dr else "",
                    profession=get_value(rec.profession_id.name_abbreviation),
                    rank_nobility=get_value(rec.rank_nobility_id.name_abbreviation),
                )
            ).strip()

            rec.academic_standing_title_en = (
                "{academic}{rank}{dr}{profession}{rank_nobility}".format(
                    academic=get_value(rec.academic_standing_id.name_en),
                    rank=get_value(rec.rank_id.name_en),
                    dr="Dr. " if title_dr else "",
                    profession=get_value(rec.profession_id.name_en),
                    rank_nobility=get_value(rec.rank_nobility_id.name_en),
                )
            ).strip()

            rec.academic_standing_title_abbreviation_en = (
                "{academic}{rank}{dr}{profession}{rank_nobility}".format(
                    academic=get_value(rec.academic_standing_id.name_abbreviation_en),
                    rank=get_value(rec.rank_id.name_abbreviation_en),
                    dr="Dr. " if title_dr else "",
                    profession=get_value(rec.profession_id.name_abbreviation_en),
                    rank_nobility=get_value(rec.rank_nobility_id.name_abbreviation_en),
                )
            ).strip()

        def get_academic_standing_for_support_role(rec):
            rec.academic_standing_title = (
                "{jod}{position}".format(
                    jod=get_value(rec.job_id.with_context(lang="th_TH").name),
                    position=get_value(
                        rec.position_level_relation_id.with_context(lang="th_TH").name
                    ),
                )
            ).strip()
            rec.academic_standing_title_abbreviation = ""
            rec.academic_standing_title_en = (
                "{jod}{position}".format(
                    jod=get_value(rec.job_id.with_context(lang="en_US").name),
                    position=get_value(
                        rec.position_level_relation_id.with_context(lang="en_US").name
                    ),
                )
            ).strip()
            rec.academic_standing_title_abbreviation_en = ""

        for rec in self:
            if rec.role == "academic":
                get_academic_standing_for_academic_role(rec)
            elif rec.role == "support":
                get_academic_standing_for_support_role(rec)
            else:
                rec.academic_standing_title = ""
                rec.academic_standing_title_abbreviation = ""
                rec.academic_standing_title_en = ""
                rec.academic_standing_title_abbreviation_en = ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "role" in vals and vals.get("role") != "academic":
                for fname in ACADEMIC_ONLY_FIELDS:
                    vals[fname] = False
        return super().create(vals_list)

    def write(self, vals):
        if "role" in vals and vals.get("role") != "academic":
            vals = {**vals, **{fname: False for fname in ACADEMIC_ONLY_FIELDS}}
        return super().write(vals)
