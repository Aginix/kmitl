# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """External participants are no longer listed per person: a headcount and a
    note replace them, and students keep their own roster. Runs *before* the
    module update because the update drops the 'external' selection value, so
    no row may still carry it."""
    if not version:
        return
    cr.execute(
        """
        ALTER TABLE approval_request
            ADD COLUMN IF NOT EXISTS external_participant_count integer,
            ADD COLUMN IF NOT EXISTS external_participant_note text
        """
    )

    # 1. Students stay on the roster, retyped.
    cr.execute(
        """
        UPDATE approval_request_participant p
        SET participant_type = 'student'
        FROM res_partner rp, ir_model_data imd
        WHERE p.participant_type = 'external'
          AND rp.id = p.partner_id
          AND imd.model = 'res.partner.type'
          AND imd.module = 'partner_type_kmitl'
          AND imd.name = 'partner_type_student'
          AND rp.partner_type_id = imd.res_id
        """
    )
    _logger.info("agx_approval: %s external rows retyped to student", cr.rowcount)

    # 2. Everyone else external folds into count + note.
    cr.execute(
        """
        UPDATE approval_request ar
        SET external_participant_count = sub.cnt,
            external_participant_note = sub.note
        FROM (
            SELECT p.request_id,
                   COUNT(*) AS cnt,
                   string_agg(
                       rp.name || COALESCE(' — ' || NULLIF(p.description, ''), ''),
                       E'\n' ORDER BY p.sequence, p.id
                   ) AS note
            FROM approval_request_participant p
            JOIN res_partner rp ON rp.id = p.partner_id
            WHERE p.participant_type = 'external'
            GROUP BY p.request_id
        ) sub
        WHERE ar.id = sub.request_id
        """
    )
    _logger.info("agx_approval: folded external rows into %s requests", cr.rowcount)

    # 3. Drop the folded rows.
    cr.execute(
        "DELETE FROM approval_request_participant WHERE participant_type = 'external'"
    )
    _logger.info("agx_approval: deleted %s folded external rows", cr.rowcount)

    # 4. excep_no_participant is noupdate, so the XML change never lands.
    cr.execute(
        """
        UPDATE exception_rule er
        SET code = E'\nif not self.participant_ids and not self.external_participant_count:\n    failed = True\n'
        FROM ir_model_data imd
        WHERE imd.model = 'exception.rule'
          AND imd.module = 'agx_approval'
          AND imd.name = 'excep_no_participant'
          AND er.id = imd.res_id
        """
    )
