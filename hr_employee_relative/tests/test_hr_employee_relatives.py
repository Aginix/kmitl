from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo.tests import common


class TestHrEmployeeRelatives(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.Employee = self.env["hr.employee"]
        self.EmployeeRelative = self.env["hr.employee.relative"]
        self.relation_sibling = self.env.ref("hr_employee_relative.relation_sibling")

    def test_age_calculation(self):
        employee = self.Employee.create(
            {
                "name": "Employee",
                "relative_ids": [
                    (
                        0,
                        0,
                        {
                            "relation_id": self.relation_sibling.id,
                            "identification_id": "1111111111111",
                            "first_name": "Relative",
                            "last_name": "Last Name",
                            "date_of_birth": datetime.now() + relativedelta(years=-42),
                        },
                    )
                ],
            }
        )
        relative = self.EmployeeRelative.browse(employee.relative_ids[0].id)
        self.assertEqual(int(relative.age), 42)
        self.assertEqual(relative.first_name, "Relative")
        self.assertEqual(relative.last_name, "Last Name")
        self.assertEqual(relative.identification_id, "1111111111111")
