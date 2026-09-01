# `done` is not the last state of an e-payment file

An e-payment file runs **ร่าง → ยืนยันแล้ว → ออกไฟล์แล้ว → จ่ายสำเร็จ**. The third of
those is the base module's `done`, kept with its meaning intact, and a fourth value
`paid` is appended after it.

The base module ends the file at `done`, set by the same press that produces the text
file. What that press actually knows is that the file was rendered and handed to the
browser. Whether anyone then uploaded it to the bank's website, and whether the money
reached the payees, are separate facts that arrive later and only ever from a person —
no result file is imported here. A single terminal state has to stand for all three, and
the office reads it as the last one: an officer opening a file at 15:00 and seeing it
finished concludes the money is on its way, when it may be a file still sitting
undownloaded in a colleague's browser.

So the file gets the step the office already performs. `done` says the file exists;
`paid` says the money arrived, and it is reached by a press — **ยืนยันการโอนเงินสำเร็จ**
— that marks every row paid and closes the file.

**Every** row, including any the bank rejected. That is what the office is asserting:
not that the bank managed it, but that the payee has their money. A payee the bank could
not credit is chased and settled outside the system _before_ this press, so by the time
it happens the statement is true of all of them. Which is why the press asks for two
things the record cannot otherwise hold — the bank's confirmation (`transfer_proof_ids`)
before it may be pressed at all, and a note at the moment of pressing, which is the only
place the exception is written down now that nobody works the file row by row.

## Consequences

- **`done` keeps its meaning, and `paid` is added after it** (`selection_add`), rather
  than `done` being renamed to the new terminal. Everything already reading `done`
  continues to mean what it meant: the gate a disbursement request checks before
  **ยืนยันจ่ายสำเร็จ** is `export_status == 'exported'`, which is still set by
  `action_done`, and the base's per-row Reject button still appears at `done`. Nothing
  downstream waits for `paid`, and no existing record needs migrating.
- **The two lifecycles stay separate.** `paid` on the file is not the voucher's
  `finance_state = paid`. The file says the batch went through; the voucher's Hand-over
  is still pressed on the disbursement request, for the reasons in
  `disbursement_finance_kmitl` ADR-0004.
- **The result buttons are only pressable from `done` onwards**
  (`_check_result_recordable`). They previously carried no state restriction at all, so
  a draft file that had been uploaded nowhere could be marked paid, writing an outcome
  onto vouchers on the strength of nothing.
- **The exported file is kept as an attachment**, which is what makes `ออกไฟล์แล้ว` an
  honest resting place rather than a one-shot. It cannot be re-rendered faithfully — the
  layouts read today's date and SCB prepends a checksum over the body — so the bytes are
  stored at export and handed out again from there.
- **`paid` is not on the status bar's happy path by accident of ordering.**
  `selection_add` appends, so `paid` lands after `cancel` and `reject` in the selection;
  those two are absent from `statusbar_visible`, which leaves the bar reading draft →
  confirm → done → paid.

## Rejected alternatives

- **Renaming `done` to mean "paid" and adding the new state before it.** Truer to the
  words, and it would have silently changed what every existing `done` record asserts
  and what the disbursement gate lets through.
- **Labelling `done` "ส่งธนาคารแล้ว" and stopping there.** One press, three claims; the
  label would assert an upload the system never observed.
- **Closing the file automatically once every row has a result.** It reads well until a
  row is marked failed and then corrected, which would close and reopen the file on its
  own. Closing a file is an assertion, and assertions here are pressed.
- **Requiring every row to carry a result before the file may close.** The office does
  not read a bank's reply row by row — they see which payees bounced, settle those, and
  come back to close the file. Twenty ticks to say what one press says would be answered
  by pressing the blanket button, which is the same thing with more steps.
- **Recording the exception on the row it happened to** (`epayment_note` on
  `bank.payment.export.line`), which is what this originally did. It is the tidier model
  and it is not how the work happens: nobody opens the rows, so the note would be
  written nowhere. It is asked for at the press instead, on the file.
- **Gating the press on "the record has an attachment".** The exported file is kept on
  the record too, so that condition is true from the moment the file is produced and
  would have gated nothing. The proof is the opposite document — what the bank sent back
  — and has a field of its own so the two cannot be confused.
