=====================================
Account Payment - WHT Counterpart Leg
=====================================

.. |badge_devstat| image:: https://img.shields.io/badge/maturity-beta-brightgreen.png
   :target: https://odoo-community.org/page/development-status
   :alt: Beta

.. |badge_license| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :alt: LGPL-3

|badge_devstat| |badge_license|

A payment voucher that withheld tax books one lump debit on the payable against two
credits - the amount the bank paid and the tax withheld - so reading what actually
cleared the payable means reading the withholding-tax line beside it.

This module gives each withholding-tax line its own debit on the payable
(ขาเจ้าหนี้คู่ภาษี), so the entry says on its own that the payable was cleared by the
amount paid *and* the amount withheld. Nothing else changes: the amount the bank is
told, the withholding-tax line, the certificate and the ภ.ง.ด. report are exactly what
they were, and ``finance_kmitl`` behaves as before with this module uninstalled.

See ``docs/adr/0001-every-credit-on-a-voucher-has-its-own-debit.md`` for why the design
deliberately works around Odoo's one-receivable/payable-line-per-payment rule.

Credits
=======

Authors
-------

* Aginix Technologies
* KMITL
