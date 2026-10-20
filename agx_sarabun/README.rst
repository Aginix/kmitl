=========
e-Sarabun
=========

Electronic Correspondence Management System (สารบรรณอิเล็กทรอนิกส์) for KMITL.

The protagonist is the **หนังสือ (Document)**: it is registered, numbered per the
records regulation, and routed through an approval/endorsement chain. Each routing
step carries a verb (ตรวจสอบ / พิจารณา / ลงนาม-อนุมัติ …) and a target (a Position or a
specific person); acting positively on a step signs it and forwards the Document
onward.

Key concepts
============

- **Document (หนังสือ)** — the registered, numbered correspondence record.
- **Routing step** — one link in the dynamic approval chain. Signing a positive
  ``show_signature`` step freezes a per-step snapshot of the signer (name, position,
  signature image) that the endorsement block renders, so later master-data edits
  never rewrite an already-signed document.
- **Position (ตำแหน่ง)** — a purpose-built authority catalog (คณบดี, ผอ.กอง, อธิการบดี),
  distinct from ``hr.job``; the capacity a Document is signed in.
- **Register (เล่มทะเบียน)** — the running-number sequence owned by the sending ส่วนงาน;
  the number is allocated at the issuing sign.

Integration with other modules is a secondary adapter: an origin record (a purchase
request, an office order, …) spawns a Document and receives a hardened callback when
it completes.

Documentation
=============

See ``CONTEXT.md`` for the full glossary, ``DESIGN.md`` for the design, and
``docs/adr/`` for the architecture decisions.
