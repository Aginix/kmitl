============================================
Purchase Work Acceptance Digital Signature
============================================

Automatic signature capture for Work Acceptance documents.

Features
========

* Snapshot procurement officer signature (``responsible_signature``) on document acceptance
* Snapshot committee member signatures (``committee.signature_image``) when they approve
* Immutable signature storage ensures audit trail and PDF consistency
* Automatic fallback to dotted signature lines for users without signatures
* Supports both paperless (tier validation) and paper-based approval workflows

Installation
============

Install in order:

#. ``digital_signature_kmitl``
#. ``purchase_work_acceptance_signature_kmitl``

Configuration
=============

No additional configuration required. Signatures are automatically captured from user profiles
when committee members or procurement officers approve the work acceptance.

Usage
=====

#. Ensure users have digital signatures set in their profiles
#. Create a work acceptance with committee members
#. Committee members approve via tier validation or wizard
#. Signatures are automatically captured into the document
#. Print PDF to see signature images (or dotted lines if signature not set)

PDF Reports
===========

* ``report_work_acceptance`` — Work Acceptance (พ.36) with committee signatures
* ``report_committee_acceptance`` — Committee Acceptance (ใบตรวจการรับพัสดุ) with committee signatures

Contributors
============

* Aginix Technologies
