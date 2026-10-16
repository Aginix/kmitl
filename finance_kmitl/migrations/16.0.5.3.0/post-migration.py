def migrate(cr, version):
    """Archive the two guarantee-receipt operation types.

    Guarantee money is now received by issuing a guarantee receipt
    (``purchase_guarantee_receipt_kmitl``), which books the deposit liability
    from the guarantee method's own account. Leaving these two selectable would
    keep a second, unnumbered way to book the same money that nothing
    reconciles against the first.

    Done here rather than in the data file because that file is ``noupdate``:
    the records already exist in every installed database, so the XML only
    reaches a fresh install. Payments raised the old way keep pointing at them —
    an archived record still resolves.
    """
    cr.execute(
        """
        UPDATE kmitl_payment_type kpt
           SET active = FALSE
          FROM ir_model_data imd
         WHERE imd.model = 'kmitl.payment.type'
           AND imd.module = 'finance_kmitl'
           AND imd.res_id = kpt.id
           AND imd.name IN (
                'payment_type_guarantee_receive',
                'payment_type_bid_guarantee_receive'
           )
        """
    )
