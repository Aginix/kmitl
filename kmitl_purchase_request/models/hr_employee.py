from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    user_id = fields.Many2one('res.users', string='Related User', ondelete='set null')
