# KRIS Project

Module for managing projects run under the KRIS unit (operating unit `99`). KMITL personnel who take on external academic-service or research work must channel it through KRIS; KRIS staff own the project data.

## Language

### People & roles

**Project Manager** (หัวหน้าโครงการ / ผู้จัดการโครงการ):
The internal KMITL employee who leads the project — a **data attribute** of the project record (`manager_id`, `hr.employee`), linked to a login via `hr.employee.user_id`. Has a login and read-only access to their own projects. Distinct namespace from the security tier `group_kris_project_manager` (= KRIS Admin); the same coexistence Odoo's own `project` module ships (`project.project.user_id` is labelled "Project Manager" alongside `group_project_manager`).
_Avoid_: Leader, owner, responsible

**KRIS Officer** (เจ้าหน้าที่ KRIS):
KRIS staff member who creates and manages all project data. The record's `user_id` ("Responsible") is the owning KRIS Officer, not the Project Leader.
_Avoid_: User, responsible person

**KRIS Admin**:
KRIS staff member responsible for module configuration (categories, types, allocation templates, exception rules). The highest security tier — `group_kris_project_manager` (Odoo's `manager` convention). Note: a security tier, not the project's `manager_id`.

**OU Executive** (ผู้บริหารหน่วยงาน) — *future*:
An executive of a faculty/office who needs read-only access to projects belonging to their own Operating Unit.

### Concepts

**Operating Unit (OU)**:
A faculty or office, identified by a numeric code (`01` Engineering … `99` KRIS). Provided by the `operating_unit` module. Intended as the scoping dimension for OU Executive read access.

**Maintenance Deduction** (ค่าบำรุง / ค่าบำรุงสถาบัน):
The institutional fee KRIS deducts from a project's operating expense; the deducted total is the pool that is then allocated to departments. One of three **methods** determines the amount:

- **Tiered** (ขั้นบันได): progressive rate brackets applied to the operating expense.
- **Custom %** (กำหนดเปอร์เซ็นต์เอง): a manually entered percentage of the operating expense.
- **Fixed Amount** (ระบุจำนวนเงิน): a manually entered baht figure used verbatim, independent of the operating expense.

_Avoid_: "Custom" unqualified — ambiguous now that both Custom % and Fixed Amount are manually entered. Name the method (Custom % vs Fixed Amount).

### Project & money

**Installment** (งวดงาน):
A scheduled milestone of contracted work, each with its own due date and payment amount; a project's value is broken down into these. `kris.project.installment`.
_Avoid_: work period, work phase, payment schedule, payment installment

**Receipt** (รายรับ):
A single recorded payment received against a project — one document with a number, date and amount. `kris.project.receipt`. Amendable while the project is `draft`/`in_progress`; frozen once the project is `done`/`cancel`. `project_id` is immutable — a receipt belongs to one project for life. See ADR-0003.
_Avoid_: revenue (a single one is never "a revenue")

**Revenue**:
The aggregate received on a project — the running sum of its Receipts. A total, not a record.

**Project Value** (มูลค่าโครงการ):
The total contracted value of a project; the baseline its operating expense, maintenance deduction and installment totals are derived from or checked against.

**Installment-free project** (ไม่มีงวดงานกำกับ):
A project whose งวด schedule isn't fixed or known up front (typically test/trial work), so it is not governed by งวด targets. Flag `no_installment_tracking`; see ADR-0001 for what this relaxes.
