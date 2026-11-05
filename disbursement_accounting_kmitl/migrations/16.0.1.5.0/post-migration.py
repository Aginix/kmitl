# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration for 16.0.1.5.0 (disbursement ADR-0009).

Back-fill ``account.move.line.disbursement_request_line_id`` on existing bills,
only where the match is unambiguous: one request line and one bill line sharing
the request, the payee, the account and the amount. Anything else stays empty.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        WITH cand AS (
            SELECT aml.id AS aml_id, l.id AS line_id
            FROM account_move_line aml
            JOIN account_move m ON m.id = aml.move_id
            JOIN disbursement_request_line l
                ON l.request_id = m.disbursement_request_id
               AND l.partner_id = m.partner_id
               AND l.account_id = aml.account_id
               AND round(l.amount, 2) = round(aml.price_unit, 2)
            WHERE aml.display_type = 'product'
              AND l.display_type IS NULL
              AND aml.disbursement_request_line_id IS NULL
        ),
        uniq AS (
            SELECT aml_id, line_id FROM cand c
            WHERE (SELECT count(*) FROM cand x WHERE x.aml_id = c.aml_id) = 1
              AND (SELECT count(*) FROM cand x WHERE x.line_id = c.line_id) = 1
        )
        UPDATE account_move_line aml
        SET disbursement_request_line_id = uniq.line_id
        FROM uniq
        WHERE uniq.aml_id = aml.id
        """
    )
