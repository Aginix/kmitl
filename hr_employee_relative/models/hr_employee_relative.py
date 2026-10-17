import re
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrEmployeeRelative(models.Model):
    _name = "hr.employee.relative"
    _description = "HR Employee Relative"
    _order = "relation_sequence"

    employee_id = fields.Many2one(comodel_name="hr.employee")
    relation_id = fields.Many2one("hr.employee.relative.relation", required=True)
    relation_sequence = fields.Integer(related="relation_id.sequence", store=True)
    identification_id = fields.Char(string="Identification No.")
    prefix_id = fields.Many2one(comodel_name="hr.employee.prefix", string="Prefix")
    firstname = fields.Char(string="First Name", required=True)
    middlename = fields.Char(string="Middle Name")
    lastname = fields.Char(string="Last Name", required=True)
    date_of_birth = fields.Date()
    age = fields.Float(compute="_compute_age")
    job = fields.Char()
    phone = fields.Char()
    identification_id_validation = fields.Boolean(
        string="ID Validation",
        compute="_compute_identification_id_validation",
        default=False,
        readonly=True,
    )
    claim = fields.Boolean()
    status = fields.Selection(
        [("alive", "Alive"), ("pass_away", "Pass Away"), ("divorce", "Divorce")],
    )

    @api.depends("date_of_birth")
    def _compute_age(self):
        for record in self:
            age = relativedelta(datetime.now(), record.date_of_birth)
            record.age = age.years + (age.months / 12)

    @api.depends("identification_id")
    def _compute_identification_id_validation(self):
        for record in self:
            record.identification_id_validation = self._check_identification_id(
                record.identification_id
            )

    def _check_identification_id(self, identification):
        # Check type string and only number 13 digits and not start with 0 or 9
        if (
            not isinstance(identification, str)
            or not re.match("^[0-9]{13}$", identification)
            or re.match("[09]", identification[0])
        ):
            return False

        checksum = 0
        for i in range(12):
            checksum += int(identification[i]) * (13 - i)
        # Checksum
        if (11 - checksum % 11) % 10 != int(identification[12]):
            return False
        return True
