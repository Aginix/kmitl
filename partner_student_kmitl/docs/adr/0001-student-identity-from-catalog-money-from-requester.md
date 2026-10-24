# Student identity comes from the catalog; bank account and national ID from the payer

The KMITL student catalog API returns who a student is (name, faculty, curriculum,
status) but no bank account and no national ID, while every disbursement payee needs
an account and a taxed one needs the ID for its 50 ทวิ. We take identity from the
catalog and everything about paying the student from the requester's own list: a
contact is matched by **Student ID** first, then by national ID on an existing
นักศึกษา contact (which then gets the Student ID stamped, instead of a duplicate), and
only otherwise created under the catalog's name. A student ID the catalog does not
know is skipped with a warning, never a rejection of the whole list, and the catalog's
status (จบ, พ้นสภาพ, …) is deliberately ignored — paying a just-graduated TA is
legitimate and the system is left open-ended; the requester and verifier judge.

## Considered Options

- **Bank accounts from another institute system / student self-service portal** —
  none exists today; revisit if one appears.
- **Reject the list on any unknown ID** — rejected by the users: one typo would block
  a 200-name scholarship run.
- **Block or warn on non-studying statuses** — rejected for the same open-endedness.
