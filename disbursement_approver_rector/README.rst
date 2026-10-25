=======================================
Disbursement Approver (Rector Delegate)
=======================================

The Rector-delegated approver (ผู้รับมอบอำนาจอธิการบดี) approves a disbursement
request. The act needs no director approval first and consumes no budget; that is
``disbursement_budget``'s own act.

The act code ``disbursement.approve_rector`` is the one stations list as allowed or required (see
``disbursement_wc/CONTEXT.md`` for the terms). The act changes no state: it stamps
``rector_approver_id`` / ``rector_approve_date`` and leaves one ``rector_approve`` signature row, and a reset to draft clears both.

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
