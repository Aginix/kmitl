=======================
Disbursement Validation
=======================

An officer validates a signed disbursement request (ตรวจสอบ).

The act code ``disbursement.validate`` is the one stations list as allowed or required (see
``disbursement/CONTEXT.md`` for the terms). The act changes no state: it stamps
``verifier_id`` / ``verify_date`` and leaves one ``verify`` signature row, and a reset to draft clears both.

Upgrading
=========

``disbursement`` used to declare the stamp fields of the three act modules
(``disbursement_validation``, ``disbursement_approver_director``,
``disbursement_approver_rector``) and kept the same column names after they moved. An
upgrade of ``disbursement`` drops every stamp column whose module is not installed in the
same run, taking the existing stamps with it, so install **all three** in the same
command as the upgrade::

    odoo -d <db> -u disbursement \
        -i disbursement_validation,disbursement_approver_director,disbursement_approver_rector \
        --stop-after-init
