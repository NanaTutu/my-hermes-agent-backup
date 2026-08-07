# Placing an order on the Exness web terminal (demo) — verified working (Aug 2026)

Companion to `exness-tab-watch-recipe.md` (which only watches positions). This is the
**entry** flow: open the SELL/BUY ticket, set the protective legs, confirm, and verify the
fill end-to-end. All via the cua-driver CLI (the Hermes `computer_use` tool session went
wedged with the stale *"session has ended"* label — drop straight to the CLI per the main SKILL.md).

## 0. Size from the real account footer, not a stated number (CRITICAL risk rule)

Before ANY ticket work, read the account **Balance / Equity / Margin** from the terminal
footer (`footerContainer` in tree_markdown — `Text "Equity"`, `Text "Balance"`, etc.),
NOT from a number the user quotes. Real case: the user said "equity = $2,000 / risk 1%" but
the live demo footer showed **Balance 50.00**. Sizing to the stated $2,000 would have been a
**~42% account-risk** order on a $50 account. Always:

`risk_usd = footer_balance * risk_pct`; `lot = risk_usd / (stop_pips * pip_value_per_lot)`
using the REAL footer balance. If the minimum lot (0.01) already exceeds the target USD
risk, say so — don't fudge the stop wider to fake 1%.

## 1. Start a fresh CLI session and click the Sell/Buy button

The top-toolbar **Sell/Buy buttons are custom TradingView controls — NOT exposed in the AX
`elements[]` tree** (they appear in `tree_markdown` as `Button "Sell158.426"` /
`Button "Buy158.436"` but carry NO element_token). So click them by pixel:

```bash
echo '{"session":"exness-order"}' | cua-driver call start_session
cua-driver call get_window_state '{"pid":<PID>,"window_id":<WID>,"screenshot_out_file":"C:/Users/<u>/AppData/Local/Temp/ex.png"}' > /c/Users/<u>/AppData/Local/Temp/ex.json
# crop the order-bar region with PIL and save, then vision_analyze the crop asking for
# the CENTER pixel of the red Sell button and the blue Buy button.
cua-driver call click '{"pid":<PID>,"window_id":<WID>,"x":<px>,"y":<py>}'
```

`effect: "unverifiable"` is NORMAL for the CLI click — verify by re-reading the tree. The
order ticket dialog now opens; its fields ARE in the AX tree with tokens.

## 2. Fill the ticket — focus, then set_value, then READ BACK

Ticket fields in tree_markdown: Volume `Edit "Volume"`, Take Profit `Edit "Take Profit"`,
Stop Loss `Edit "Stop Loss"`, confirm `Button "Confirm Sell <n> lots"`. Default Volume was
already `0.01`; SL/TP start `help="Not set"`.

**Pitfall — `set_value` on an unfocused Edit silently no-ops:** calling `set_value` with the
element_token can return `route: "accessibility", effect: "unverifiable"` while the field
keeps `help="Not set"` — the value did NOT stick. The fix that works every time:

1. `click` the Edit field first (focus it), then
2. `set_value` the value on the token, then
3. **re-`get_window_state` and read back** the field's `[value="..."]` in tree_markdown
   before trusting it. Stop Loss took on the first set_value; Take Profit only after the
   focus click — both verified in the re-read.

Take the fill as BELOW with fresh tokens each time (see section 3).

## 3. Confirm — element tokens go stale after every action

The Confirm button token silently changes after each re-`get_window_state` (e.g.
`s0000001b:461` one read, `s00000017:453` the next). A click on a stale token returns
`effect: unverifiable, route: synthetic_events` and does NOTHING — the dialog stays open.
**Always re-resolve the Confirm token from the freshest snapshot immediately before clicking:**

```bash
# els where role=='Button' and 'Confirm Sell' in label -> element_token (freshest tree)
cua-driver call click '{"pid":<PID>,"window_id":<WID>,"element_token":"<fresh>","delivery_mode":"background"}'
```

## 4. Verify the fill (do NOT trust "unverifiable")

Read the next `get_window_state` and require ALL of:
- `confirm button gone: True` (no `Confirm Sell` line in tree_markdown anymore), AND
- the open-position tab count incremented `TabItem "Open 1"` → `TabItem "Open 2"` (the label
  carries the count), AND
- a fresh position row for the symbol (Symbol / Sell / lot / open price / TP / SL / ticket /
  open time) appears under the Open tab, AND
- a toast `Text "Position opened"` + `Text "Sell 0.01 lot USD/JPY at 158.367"` in the tree.

Read all numbers (balance, equity, margin level, open price, SL/TP) from the AX `text` node
labels — NOT from the auxiliary vision description (it fabricates digits).

## Protective legs: verify BEFORE confirm

When the ticket shows the computed risk summary (e.g. SL distance -> `-25.0 pips`,
`-1.58 USD`, `-3.15%`, and TP -> `+77.2 n pips`, `+9.70%`), the platform has already
validated both legs against the live price. Confirm SL/TP readback `[value="158.62"]` /
`[value="157.60"]` appear in the tree before pressing Confirm.