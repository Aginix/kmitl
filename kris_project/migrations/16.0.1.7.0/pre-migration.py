# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: rename column contract_number → project_code.

The historical kris_project.contract_number column stored KRIS internal
project codes (label "เลขที่สัญญา"), never the external employer's contract
number. The field is being split: rename it to project_code, and reuse the
name `contract_number` for a brand-new Employer Contract Number field.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        ALTER TABLE kris_project
        RENAME COLUMN contract_number TO project_code
        """
    )
    cr.execute(
        """
        UPDATE ir_model_fields
        SET name = 'project_code'
        WHERE model = 'kris.project' AND name = 'contract_number'
        """
    )
