# Silent live-position watch — Exness web terminal (Aug 2026, verified working)

Used for cron "trade-status watcher" jobs: check whether a live Exness demo
position is still open or has closed, without stealing the user's desktop.
Verified end-to-end Aug 7, 2026 (position ticket 23958538, GBP/USD Sell 0.01).

## When to use this recipe

- The Hermes `computer_use` tool returns the stale *"this session has ended;
  call start_session explicitly to reuse its label"* error.
- `cua-driver autostart status` reports `registered (running)` — daemon healthy,
  only the tool's session label is stale. **Do not kill the daemon** (it may
  refuse, and that refusal is the signal you're aiming at the real daemon).
- The Exness trading terminal is a TAB inside a regular Chrome window, not a
  standalone `chrome_proxy.exe` PWA window.

## Exact command sequence (git-bash)

```bash
# 1. Fresh CLI session (bypasses the wedged Hermes tool session entirely).
#    Use the STDIN-PIPE form for start_session — it is unambiguous. (The
#    positional form is also fine as a single-quoted JSON literal,
#    '{"session":"..."}', but a bare token like session=watcher errors with
#    "positional JSON arg ... did not parse" — pipe JSON to avoid the trap.)
echo '{"session":"watcher-aug8"}' | cua-driver call start_session
# Success marker: {"active":true,"session":"watcher-aug8","revived":true,...}
# "revived":true is fine — it just reused the id; the session is usable.

# SCOPE: use capture_scope:"window" (NOT desktop) for the pure read-only watchdog.
# Verified Aug 7/8 2026: a window-scoped session ({"session":..., "capture_scope":"window"},
# effective_scope:"window") fully supports list_windows + get_window_state + AX-row grep +
# background TabItem clicks. Desktop scope is ONLY needed to escalate to raw-coordinate /
# whole-desktop gestures; for "is the tracked ticket open or closed" you never need it, and
# window scope sidesteps the desktop-unlock escalation entirely. Omit capture_scope (default
# "auto") and you also start window-only — either is fine; do NOT reach for desktop unless a
# later step actually needs it.

# 2. List windows; save JSON to a path native python can read (NOT /tmp)
echo '{}' | cua-driver call list_windows > /c/Users/<u>/AppData/Local/Temp/winlist.json
# parse: json.load(open('C:/Users/<u>/AppData/Local/Temp/winlist.json'))
# NOTE: response has BOTH 'windows' and '_legacy_windows' keys, identical content.

# 3. Read each candidate Chrome window's AX tree, grep for the trading TabItem
cua-driver call get_window_state '{"pid":31344,"window_id":722668}' > /c/Users/<u>/AppData/Local/Temp/win.json
# grep labels for role 'TabItem' containing 'GBP/USD Bid' -> element_token, e.g. "s0000000a:752"

# 4. Activate the tab (background UIA Invoke via PostMessage — no focus steal)
cua-driver call click '{"pid":31344,"window_id":722668,"element_token":"s0000000a:752","delivery_mode":"background"}'
# -> {"delivery":{"mode":"background"},"effect":"unverifiable","route":"synthetic_events"}
#    effect:unverifiable is NORMAL here. Verify with step 5, not by retrying.

# 5. Re-read the window: terminal DOM now in AX tree; Document label = live quote
cua-driver call get_window_state '{"pid":31344,"window_id":722668}' > /c/Users/<u>/AppData/Local/Temp/ex_term.json
```

## Reading the positions row (all values from AX `elements[]` labels)

**Shortcut: grep `tree_markdown` instead of parsing `elements[]`.** The
`get_window_state` response includes `tree_markdown` (a flat Markdown rendering
of the same tree, e.g. ~38KB for the Exness terminal). Grep it directly for the
row — `GBP/USD`, `Sell`, `0.01`, the open price, `Take Profit`/`Stop Loss`
buttons, `TabItem "Open 1"` — without any JSON parsing. This was the fastest
path in the Aug 8 watch: `grep` the saved JSON for the keywords, print the
matched lines with line numbers, and read the row's state straight off. Only
fall back to `elements[]`/vision when you need values the markdown doesn't show.

Row fields (in table order, matching the Exness web terminal build of Aug 2026):

| Column | AX role | Example label |
|---|---|---|
| Symbol | Text | `GBP/USD` |
| Type | Text | `Sell` |
| Volume, lot | Button | `0.01` |
| Open price | Text | `1.34514` (wrapped in U+2069/U+2066 bidi marks — strip before parsing) |
| Current price | Text | `1.34554` |
| T/P | Button | `1.34000` |
| S/L | Button | `1.34644` |
| Position (ticket) | Text | `23958538` |
| Open time | Text | `Aug 6, 10:14:50 PM` |
| Swap, USD | Text | `0` |
| P/L, USD | Text | `-0.40` |

Tab switcher: `TabItem Open 1` (the `1` = count of open positions) vs
`TabItem Pending` vs `TabItem Closed`.

Account footer (same tree): `Equity`, `Free Margin`, `Balance` (static while a
trade floats — equity is the moving number), `Margin`, `Margin level`. In the
Aug 7 check: `Balance 50.00`, `Equity 49.60`, `Free Margin 48.93`,
`Margin 0.67`.

## Open / closed decision rule (for the silent watcher)

**Trust the settled row over the job brief.** Cron/brief text often carries a
stale or typos'd entry/TP/SL (verified Aug 7, 2026: a brief said entry
`1.08514` while the tree's open price was `1.34514`). Always compute the
close outcome from the tree's real `Open price` + `Close price` vs the tree's
TP/SL levels — never from a figure echoed in the prompt. If a brief number
looks absurd vs the symbol's real range, it is a brief typo, not market data.

- Row present under the Open tab (`TabItem Open 1` active) → trade STILL OPEN →
  output NOTHING / standby.
- Row gone from Open → switch to the Closed tab (`TabItem Closed`) and read the
  close price + realized P/L from the closed-positions row; compare close
  against entry / TP / SL to infer TP-hit vs SL-hit vs manual close.
- Terminal tab missing AND no way to confirm closure → report that the watcher
  lost sight of the position; ask the human to confirm manually. Never invent
  an outcome.

## Reading the CLOSED row (after the trade is gone from Open)

When the tracked ticket no longer appears under the Open tab, switch to
`TabItem Closed` (`get_window_state` then re-grep). The closed table reuses
the same row layout but replaces the live columns with settled ones — verified
on the GBP/USD 23958538 close (Aug 7, 2026):

| Column | Meaning | Example |
|---|---|---|
| Open price | entry | `1.34514` |
| **Close price** | actual fill at close | `1.34745` |
| T/P / S/L | the protective levels as set | `1.34000` / `1.34644` |
| Position | ticket | `23958538` |
| Open time / **Close time** | — | `Aug 6, 10:14:50 PM` / `Aug 7, 12:30:01 PM` |
| Swap, USD | — | `0` |
| **Reason** | TP hit / SL hit / manual | `Stop Loss` (a "close via SL" reason does NOT mean it filled exactly at SL) |
| P/L, USD | realized | `-2.31` |

`Reason` is the authoritative close-type signal — a `Stop Loss` reason means
the stop fired, but **compare Close price to the SL *level*, not the label**:
the fill can slip past it. Verified: SL 1.34644 printed at close price
1.34745 (~10 pts beyond). A large gap between the live bid and the SL is a
strong *prior* the trade stopped out (bid 1.35032 vs SL 1.34644 here), but
the Closed row is the ground truth — never conclude from the quote alone.

Account footer after close: `Balance` becomes static (the realized P/L is
baked in), `Equity` tracks any still-open floats, and a secondary
other-tab TP from a *different* ticket may also appear in Closed — key the
row you report on to the tracked ticket number, not the symbol (two rows can
share GBP/USD).

**Balance reconciliation is the authoritative close cross-check.** Before
reporting a close, reconcile the account footer against the tree's realized
P/Ls: `known_prior_balance + Σ(other closed trades' P/L) − (this trade's
realized P/L) == current footer Balance`. In Aug 7: 50.00 + 4.87 (a separate
USD/JPY TP) − 2.31 = 52.56, matching the footer exactly — independent proof
that the −2.31 row was real. A `Reason: Stop Loss` with the close price ~10
pts past the SL level (here 1.34745 vs 1.34644) is normal slippage, not a
broken stop — report realized R honestly (nominal −1.0R vs realized ~−1.7R)
and flag the slippage, not the discipline.

**A `effect: unverifiable` tab-switch click may not actually switch the
visible table.** Clicking `TabItem Closed`/`Open` returned `effect:
unverifiable` AND the re-read `get_window_state` still showed the prior
table. Don't block the report on getting the tabs to render — if the tracked
ticket is already visible in a Closed-layout row with close-time/Reason/P-L,
that is conclusive on its own; if not, you lost sight and should say so
rather than wait on a tab click that may have landed.

For a normal forced stop, "Reason" reads `Stop Loss` / `Take Profit`; a
manual click exit still lands in Closed but the Reason differs — verify
against close price vs the set levels before assuming.

The `TabItem "Open 2"`, `TabItem "Pending"`, `TabItem "Closed"` nodes are the
tab BAR — all three labels are ALWAYS present in the tree regardless of which
tab is selected. A parser that walks lines and flips `in_open=False` when it
sees the word `Closed` will FALSE-ALARM on a live position, because the Closed
label sits in the tab bar while the visible table below still belongs to the
Open tab. Verified failure: a USD/JPY watcher claimed "position no longer in
Open tab" while ticket 23989608 was visibly live under `Open 2`.

Robust signal (verified): parse the Open-count from the tab label
(`re.search(r'TabItem "Open (\d+)"', line)` → N>0) AND require the ticket
string to be present in the tree. `ticket_present and open_count > 0` → open.
Anything else → unknown (emit a "lost sight, confirm manually" only after
several consecutive misses, so transient capture blips stay silent). Working
example: `C:\Users\bohen\AppData\Local\hermes\scripts\watch_usdjpy.py`
(cron no_agent watcher, ticket 23989608, silent-while-open).

**CORRECTION (verified Aug 7, 2026): `ticket_present and open_count > 0 → open`
MISFIRES when the ticket sits in the CLOSED table while a DIFFERENT position
is still open.** The `Open N` count is ACCOUNT-WIDE, not ticket-specific. In
the 23958538 close: ticket present in tree, `Open 1` label present (another
live position), footer showed `Margin 0.50` / floating `Total P/L -0.42` —
yet the tracked trade was CLOSED. The ticket string alone is NOT enough; you
must determine WHICH table's row set contains the ticket. Disambiguate by
row-layout markers, not tab labels:
- Closed-table row columns: `Close price`, `Close time`, `Reason`, realized
  `P/L` (a closed row has ALL of these; an open row has `Current price`, no
  close time, no Reason).
- The Closed table shows a caption node `Showing closed positions for the
  last 1 day` — a reliable marker that the visible table is the Closed view.
Decision: if the tracked ticket appears in a row WITH close-time/Reason/P-L
columns → CLOSED regardless of the Open-count. If it appears in a row with
`Current price` → OPEN. Only if the ticket is absent from BOTH layouts do you
emit "lost sight, confirm manually".

## Watcher report framing (what the cron delivers when the trade CLOSES)

Keep it tight and disciplined, risk-first. Structure:
1. Outcome — TP hit / SL hit / manual, inferred from the actual fill vs levels
   (never from a brief-echoed entry; trust the settled row).
2. Numbers — entry, exit, pips, $ P/L, % of account (verified against AX nodes).
3. R-multiple — realized (slippage-adjusted) vs nominal (perfect-fill at stop):
   e.g. nominal −1.0R, realized ~−1.7R when the fill ran past the SL level.
   Always report the honest realized R and name the slippage.
4. Process review 3-4 lines — was the stop set first, sized to risk, was the
   R:R sound for the setup? "A losing trade that followed the rules is still
   a good trade" when true; frame without overselling.
5. Base-rate anchor — most retail accounts lose; this is a demo for process,
   and a negative-R result is a cheap, correct data point, not a verdict.
Never predict price; report only settled actual state. (This framing sits in
trading discipline; the detection mechanics live in this reference.)

## Pitfalls

- **`write_file` on a skill reference REPLACES the whole file — it does not
  append.** In Aug 2026 a one-line "append-only note" write clobbered this
  entire recipe; recovery required re-writing the full content from memory.
  Treat `skill_manage(action=write_file)` as destructive-overwrite: always
  read the current file first and include ALL prior content in the new write.
- The tab title itself carries a live quote (`GBP/USD Bid 1.34538 - High
  memory usage - 1.0 GB`): it updates between captures (observed 1.34538 →
  1.34544 within ~2 min). It is a cheap live-price source but NOT proof of
  position status — the positions table decides.
- The Exness Personal Area page (my.exness.com/pa/) balance can be stale
  (showed `49.22 USD` while the terminal footer showed `Balance 50.00`). Trust
  the trading terminal's footer, not the PA page, for account state.
- Open price labels carry bidi control chars (`\u20661.34514\u2069`) — strip
  `\u2066`/`\u2069` before numeric comparison.
- Parse JSON with a `write_file`'d python script run through `terminal`
  (`execute_code` is blocked in cron jobs). Write temp JSON under
  `C:/Users/<u>/AppData/Local/Temp/` — native python cannot read git-bash
  `/tmp`.
- **Once you drop to the CLI, STAY on the CLI for the whole run.** After a
  successful `cua-driver call start_session`, the Hermes `computer_use` tool
  STILL returns the same *"this session has ended"* error (verified Aug 8: a
  `capture(app=Chrome, pid=..., window_id=...)` retried after the fresh CLI
  session failed identically). The CLI session is independent of the Hermes tool's
  stale label — don't re-test the tool mid-run hoping it revived; just finish the
  job via `list_windows` + `get_window_state`.
- A wedged `computer_use` is often NOT a dead daemon — with `2>/dev/null`
  swallowed stderr, `taskkill //F //IM cua-driver.exe` can exit 0 while the
  wedge (and daemon) survive. If `cua-driver status` reports the daemon
  running, go straight to the CLI path; skip the kill entirely.
- If the tree is genuinely canvas-thin (older Exness builds), fall back to
  `screenshot_out_file` + `vision_analyze` (see main SKILL.md) — but always try
  the AX grep first.
