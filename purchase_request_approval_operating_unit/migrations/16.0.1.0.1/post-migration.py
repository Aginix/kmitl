# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Align existing PAs with their PR's operating unit.

PAs used to take the acting user's default OU (e.g. the last sarabun approver)
instead of the PR's, which could hide them from the PR's own OU.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE purchase_request_approval pa
        SET operating_unit_id = pr.operating_unit_id
        FROM purchase_request pr
        WHERE pa.request_id = pr.id
          AND pr.operating_unit_id IS NOT NULL
          AND pa.operating_unit_id IS DISTINCT FROM pr.operating_unit_id
        """
    )
