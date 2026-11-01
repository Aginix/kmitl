========================================
Disbursement Approver (Finance Director)
========================================

The Finance Division Director (ผอ.กองคลัง) approves a disbursement request. The act
needs no prior validation.

The act code ``disbursement.approve_director`` is the one stations list as allowed or required (see
``disbursement/CONTEXT.md`` for the terms). The act changes no state: it stamps
``finance_approver_id`` / ``finance_approve_date`` and leaves one ``finance_approve`` signature row, and a reset to draft clears both.

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
