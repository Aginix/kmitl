# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


def migrate(cr, version):
    """Carry the AR-specific ``returned_to_approval`` flag over to the generic
    ``returned_to_source`` field (now owned by the ``disbursement`` module), so
    any in-flight returns keep their banner and validation guard after the
    return-to-source refactor. ``disbursement`` upgrades first (dependency), so
    ``returned_to_source`` already exists here."""
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'disbursement_request'
          AND column_name = 'returned_to_approval'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        UPDATE disbursement_request
        SET returned_to_source = TRUE
        WHERE returned_to_approval IS TRUE
        """
    )
