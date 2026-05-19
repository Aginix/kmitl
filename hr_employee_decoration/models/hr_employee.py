from odoo import fields, models, api

CHAKRABARTI_MALA_LEVEL = 58


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    decoration_ids = fields.One2many(
        comodel_name="hr.employee.decoration",
        inverse_name="employee_id",
    )

    highest_decoration_id = fields.Many2one(
        comodel_name="hr.employee.decoration.relation",
        string="Highest Decoration",
        compute="_compute_highest_decoration",
        readonly=True,
        store=True,
    )

    has_chakrabarti_mala_medal = fields.Boolean(
        string="Chakrabarti Mala Medal",
        compute="_compute_chakrabarti_mala_medal",
        readonly=True,
    )

    """
    ลำดับชั้นของเหรียญ  ชั้นสูงสุดคือ 1
    Ref: https://th.wikipedia.org/wiki/รายชื่อเครื่องราชอิสริยาภรณ์ไทย
    """

    def _get_highest_decoration(self):
        self.ensure_one()
        decorations = self.sudo().decoration_ids
        decorations = decorations.filtered(
            lambda d: d.relation_id.level != CHAKRABARTI_MALA_LEVEL
        )
        if len(decorations) == 0:
            return False
        return min(decorations, key=lambda x: x.decoration_level)

    @api.depends("decoration_ids")
    def _compute_highest_decoration(self):
        for employee in self:
            decoration = employee._get_highest_decoration()
            employee.highest_decoration_id = (
                decoration.relation_id if decoration else False
            )

    def _get_chakrabarti_mala_medal(self):
        self.ensure_one()
        decorations = self.sudo().decoration_ids
        medal = decorations.filtered(
            lambda x: x.relation_id.level == CHAKRABARTI_MALA_LEVEL
        )
        if medal:
            return medal[0]
        return False

    @api.depends("decoration_ids")
    def _compute_chakrabarti_mala_medal(self):
        for employee in self:
            decoration = employee._get_chakrabarti_mala_medal()
            if decoration:
                employee.has_chakrabarti_mala_medal = True
            else:
                employee.has_chakrabarti_mala_medal = False
