========================================
Disbursement Endorser (Finance Director)
========================================

The Finance Division Director (ผอ.กองคลัง) endorses (เห็นชอบ) a disbursement request.
The Director holds no authority to approve, so this module replaces
``disbursement_approver_director``, which named the same act an approval. Install one
or the other: with both, the Director gets two buttons for the same act. The act needs
no prior validation.

The act code ``disbursement.endorse_director`` is the one stations list as allowed or
required (see ``disbursement/CONTEXT.md`` for the terms). The act changes no state: it
stamps ``finance_endorser_id`` / ``finance_endorse_date`` and leaves one
``finance_approve`` signature row (the Finance Director's line of the signature block),
and a reset to draft clears both.

Replacing disbursement_approver_director
========================================

The module starts from nothing: the stamps of ``disbursement_approver_director`` are not
carried over (its signature rows stay, they belong to ``disbursement``). On a database
that has the old module:

#. Uninstall ``disbursement_approver_director``; its act
   ``disbursement.approve_director`` is archived.
#. Install ``disbursement_endorser_director``.
#. Seat the new act **Endorse (Finance Director)** on the ผอ.กองคลัง station in place of
   the archived one.
