# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: the header payee becomes a required payee *type*.

``partner_type_id`` (ประเภทผู้รับเงิน) replaces the header ``partner_id`` /
``partner_type`` (single/multi); payees now live on the lines only. Create and
fill the column before the module loads so Odoo can make it NOT NULL:

1. the type most of the request's line payees have (ties: lowest id);
2. else the old header partner's type;
3. else ``partner_type_kmitl.partner_type_other`` (อื่น ๆ).

A request whose lines mix types keeps them: the submit-time exception rule only
stops drafts, and historical requests are left as they are.
"""


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        ALTER TABLE disbursement_request
        ADD COLUMN IF NOT EXISTS partner_type_id integer
        """
    )
    cr.execute(
        """
        UPDATE disbursement_request dr
        SET partner_type_id = top.partner_type_id
        FROM (
            SELECT DISTINCT ON (l.request_id) l.request_id, p.partner_type_id
            FROM disbursement_request_line l
            JOIN res_partner p ON p.id = l.partner_id
            WHERE p.partner_type_id IS NOT NULL
            GROUP BY l.request_id, p.partner_type_id
            ORDER BY l.request_id, count(*) DESC, p.partner_type_id
        ) top
        WHERE top.request_id = dr.id AND dr.partner_type_id IS NULL
        """
    )
    if _column_exists(cr, "disbursement_request", "partner_id"):
        cr.execute(
            """
            UPDATE disbursement_request dr
            SET partner_type_id = p.partner_type_id
            FROM res_partner p
            WHERE p.id = dr.partner_id
              AND p.partner_type_id IS NOT NULL
              AND dr.partner_type_id IS NULL
            """
        )
    cr.execute(
        """
        UPDATE disbursement_request
        SET partner_type_id = (
            SELECT res_id FROM ir_model_data
            WHERE module = 'partner_type_kmitl' AND name = 'partner_type_other'
        )
        WHERE partner_type_id IS NULL
        """
    )
