==========================
Disbursement Payment Audit
==========================

The payment auditor's ตรวจจ่าย act. Once the accounting office has posted the bills of a
disbursement request, the auditor chooses the payment subject (เรื่องที่จ่าย) and checks
that every payee has a paying account and usable banking coordinates. The act needs
nothing before it besides the posted bills, and the authorization does not need it
first: the route says what normally happens.

The act code ``disbursement.audit_payment`` is the one stations list as allowed or
required (see ``disbursement_finance_kmitl/CONTEXT.md`` for the terms). The act changes
no state: it stamps ``payment_auditor_id`` / ``payment_audit_date`` and leaves one
``payment_audit`` signature row, and a reset to draft clears both. Where the audit is
offered is also where the payment subject may be chosen.

Upgrading
=========

``disbursement_finance_kmitl`` used to declare the audit's stamp fields and signature
step, and this module kept the same names. An upgrade of ``disbursement_finance_kmitl``
without this module drops the stamp columns and deletes the ``payment_audit`` signature
rows, so install it in the same command as the upgrade::

    odoo -d <db> -u disbursement_finance_kmitl -i disbursement_payment_audit \
        --stop-after-init
