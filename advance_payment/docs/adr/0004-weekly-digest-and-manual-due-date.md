# Reminders are a weekly digest; the return due date is set manually

Status: proposed (2026-07 review; UAT-only)

## Context & Decision

Outstanding/overdue-loan reminders are sent as a **weekly digest**, not per-event daily mails: each borrower gets a weekly summary of their own outstanding loan(s) with the due date and outstanding amount, and the loan officers get a weekly aggregate of all outstanding/overdue agreements. The **return due date is entered manually by the loan officer after approval** — it is *not* auto-derived from the activity end date or the effective date.

## Why

- The weekly digest directly addresses the "notification fatigue" pain point from the review (daily mails were ignored).
- A manual due date keeps the base module free of any dependency on activity dates (which live on AR/PR and would otherwise force a bridge); the officer applies the relevant regulation deadline case by case. This deliberately rejects the "activity end + N days" auto-derivation the requirements wording implied.

## Consequences

- Base module carries a `return_due_date` (Date), editable by the officer once the agreement is approved.
- Escalation beyond the weekly digest is deferred (11D).
- No scheduled jobs exist today; this adds a weekly cron / scheduled action.
