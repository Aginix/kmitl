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
