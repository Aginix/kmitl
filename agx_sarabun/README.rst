=========
e-Sarabun
=========

Electronic correspondence management system (สารบรรณอิเล็กทรอนิกส์) for KMITL.

Features
========

* Manages correspondence documents (หนังสือราชการ) with routing, step actions,
  recall and send workflows.
* Register books (เล่มทะเบียน, ``sarabun.document.sequence``): each owning
  department can keep several register books, each rendering document numbers
  from a ``prefix`` / counter / ``suffix`` pattern (e.g. ``อว 6801.1/``) with
  configurable zero padding.
* Allocated numbers (``sarabun.document.number``) track every number issued from
  a register, including reserved, used and voided states per fiscal year.
* Master data for document types, verbs, addressee prefixes and activities.
* Cover-sheet PDF reports with Thai font rendering and digitized signatures.

Configuration
=============

Register books are maintained under the Registers menu. Set the owning
department, the number prefix/suffix and the padding; the next number is
computed automatically.
