---
name: fx-trading
description: Use when analyzing FX trades, developing/testing trading strategies, teaching FX trading concepts, sizing positions, reviewing or building a trade plan, or coaching trading psychology/discipline. Complete reference for technical analysis, indicators, market structure, risk management, mindset, and strategy validation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, forex, fx, technical-analysis, indicators, risk-management, psychology, strategies]
    related_skills: []
---

# FX Trading

## Overview

Forex (FX) is the world's largest financial market (~$7–8 trillion/day turnover), a 24-hour, ~5-day macro-driven market where every trade is a **pair** — two economies, interest-rate expectations, and capital flows. Most retail FX traders lose money: EU broker disclosures (ESMA/MiFID II, published since 2018) show **~60–83% of retail clients losing money** across major brokers (FXOpen 60% … ActivTrades 83%); aggregate claims of "70–90% lose" are approximations, not a single authoritative figure. The failure is rarely one "secret" — it is a combination of thin edge, no plan, poor risk sizing, and psychology.

This skill encodes the full discipline: market mechanics → technical analysis → strategy design → risk/money management → validation → mindset. Reference briefs from 3 research passes were synthesized here.

**Ground truth to hold:** No indicator is inherently profitable. Settings are *conventions* (14 RSI, 12/26/9 MACD, 50/200 EMA), not proven optima. The edge comes from a **tested, repeatable process** + **risk control** + **discipline** — not from any single charting tool.

## When to Use

- Analyzing a specific FX setup / pair for bias and entry.
- Designing, improving, or testing a trading strategy.
- Sizing positions, setting stop-losses / targets, or reviewing R:R.
- Teaching FX concepts to Tutu (indicators, market structure, pips/lots/leverage).
- Reviewing a trade plan, journal, or performance metrics.
- Coaching on trading psychology, discipline, and cognitive biases.

**Don't use for:** giving financial advice, predicting guaranteed outcomes, or legitimizing unvalidated "smart money" folklore as certainty — treat it as an organizing lens, not proven edge.

## FX Mechanics (know these cold)

- **Pip** = unit of movement. Most pairs: 4th decimal (0.0001); JPY pairs: 2nd decimal (0.01). Pipette = 1/10 pip.
- **Lot** = position size unit. Standard = 100,000 units (~$10/pip on USD-quote pairs); mini = 10,000 (~$1/pip); micro = 1,000 (~$0.10/pip).
- **Leverage**: $1 controls $N. Magnifies gains and losses *equally*. Retail caps (e.g., ESMA 30:1 on majors) exist because excessive leverage is the #1 account killer.
- **Margin call**: if equity < required margin, broker closes positions.
- **Golden rule: size by risk, never by available leverage.**

### Market drivers
- **Interest-rate expectations** (the single dominant driver): rate differential + expected change, not absolute rates. Central banks: Fed (USD), ECB (EUR), BoE (GBP), BoJ (JPY), RBA (AUD), RBNZ (NZD), BoC (CAD), SNB (CHF).
- **Economic data**: interest decisions, CPI, NFP/unemployment, GDP, retail sales, PMI. *Surprises vs consensus* move price more than raw values.
- **Risk sentiment**: risk-on (equities up, AUD/NZD/JPY crosses active) vs risk-off (JPY, CHF, USD, gold). Overrides fundamentals day-to-day.

### Sessions (UTC)
Sydney ~22:00 (quiet) → Tokyo ~00:00 (JPY pairs) → Frankfurt ~06:00 → **London ~07:00 (biggest volatility burst, ~40% of turnover)** → NY ~13:00 → **London–NY overlap ~12:00–16:00 = the optimal window** (highest liquidity, tightest spreads). Asian range ~00:00–06:00 = tight consolidation, mean-reversion territory. Know the economic calendar before entering; be flat or small into high-impact releases.

## 1. Technical Analysis — Price Action First

TA rests on: price discounts everything, prices trend, history repeats. **Leading value comes from price/structure/divergence; indicators are lagging confirmations/filters.** In spot FX there is no central volume; use tick volume / COT as proxies.

### Candlesticks (bias, not a command)
- **Single**: Marubozu (full-range body = conviction), Doji (indecision — meaningful at extremes), Hammer/Hanging Man (long lower wick ≥2x body; hammer@support bullish, hanging-man@high bearish), Shooting star (mirror), Spinning top (indecision).
- **Multi**: Bullish/bearish Engulfing (one of the most-watched reversals), Morning/Evening Star (3-candle), Piercing/dark-cloud, Harami, **Inside bar** (compression → breakout/follow-through), Tweezer, Three Soldiers/Crows.
- **Discipline**: patterns *alone* have low win rate. They only matter in context — at S/R, aligned with HTF trend, after a trend leg. **Confirmation (follow-through close/break) > the pattern itself.**

### Support/Resistance & structure
- **Horizontal S/R**: zones of institutional order. Longer price held, more touches (2–3 clean) = more meaningful. Levels decay into **zones**. **Role-flip** + **break-and-retest** (broken resistance becomes support; retest = high-prob entry) is a core concept.
- **Trendlines/Channels**: validity rises with touches & time sweep.
- **Supply/Demand zones**: origin of a strong impulsive "displacement" move. Drawn over the *base candle* before the move, not the peak. Subjective — traders differ.
- **Market structure (predictable core)**: uptrend = HH+HL; downtrend = LL+LH. **BOS** (break of most recent counter-trend swing) = continuation. **CHoCH/MSS** (first break of prevailing structure) = early turning-point hint.

### Smart Money Concepts — treat as folklore
Order blocks, FVGs, liquidity sweeps, premium/discount are **real visual descriptions of price but NOT mathematically derivable or peer-validated**. The jMathFX critique: descriptive, subjective, no predictive formula. Use as a **labeling/organizing lens** for liquidity/structure — not as a guaranteed institutional edge.

### Trend & momentum (lagging)
- **MA/EMA**: 20 (short/medium), **50 EMA / 200 SMA = classic trend filter**; Golden cross (50>200) vs Death cross (50<200) = late confirming. Slope = trend strength. Used best as dynamic S/R + filter.
- **MACD (12,26,9)**: Line = 12EMA−26EMA; Signal = 9 EMA of line; Histogram = MACD−Signal. Crossover vs signal (lagging); **zero-line cross = more robust trend shift**; **divergence = early higher-prob reversal hint**; rising histogram = acceleration.
- **ADX (14)**: 0–100, non-directional. **<20 = range** (favor mean-rev), **>25 = strong trend** (favor trend-follow). Slope matters. Doesn't give direction (±DI lines do).
- **Ichimoku**: 5 components + cloud (Kumo). Price above cloud bullish, below bearish; strongest on H4/Daily as trend map.

### Oscillators
- **RSI (14)**: 0–100; >70 overbought / <30 oversold (*best in ranges*). **Divergence more valuable than thresholds**. In strong trends RSI can sit overbought long — don't fade blindly.
- **Stochastic (14,3,3)**: %K/%D; >80/<20; noisy, pair with trend/RSI.
- **CCI (14)**: >+100 strong, <−100 weak.

### Volatility
- **Bollinger (20,2)**: middle=20SMA ±2 σ. Touch of band = vol extreme; **squeeze (bandwidth narrowing) → breakout often follows**; band-walk = trend.
- **ATR (14)**: true range per bar. Use for **stop placement (1–1.5–2×ATR)** and **position sizing** (volatility-adjusted risk). No direction.
- **Keltner**: EMA ± 2×ATR; less spike-sensitive than Bollinger.

### Patterns & Fibonacci
- Reversals: Head&Shoulders (+ measured target = neckline), Double/Triple top/bottom, Cup&Handle. Continuation: Flags, Pennants, Triangles.
- **Fibonacci retracement**: 0.236/0.382/0.5/0.618/0.786 (watch 0.618–0.786 "golden pocket"); extensions 1.272/1.618/2.618 for targets. **0.5 is NOT a true fib but universally used.** No genuine predictive power — it's a "herd coordinate" + target/stop convenience.

### Multi-timeframe & confluence
- **Top-down**: higher timeframe (HTF) = bias/direction; intermediate = setup/zone; lower (LTF) = trigger. Use ~3 timeframes spaced 4–6× (Daily/4H/1H or 4H/1H/15m).
- **Confluence rule**: 2–3+ independent confirmations aligning at a level (trend + structure zone + momentum + trigger + session) = meaningful; disagreement = no trade.

## 2. Strategy Design & Selection

Pick **one** strategy and master it across many trades — strategy-jumping is a top beginner killer.

| Style | Timeframe | Time needed | Stress |
|---|---|---|---|
| Scalping | seconds–min | full-time | very high (heavy cost drag) |
| Day trading | intraday | 4–6h | medium-high |
| Swing | days–weeks | 1–2h | low-med (part-time friendly) |
| Trend following | all | 30–60m | low (high RR, many small losers) |
| Range/mean-rev | sideways | low | low |

**Breakout note:** most breakouts are false (~60–70%) — require confirmation and risk limit.

### Position sizing (the core)
```
Position Size (lots) = (Account × Risk%) / (Stop Loss in pips × Pip Value per standard lot)
```
- **Risk 0.5–2% per trade** (pros 0.5–1%). Stop FIRST, then size to keep risk fixed.
- **Example**: $5,000, 2% = $100 risk, 50-pip stop, $10/pip → $100/(50×10) = **0.20 lots**.
- **Fixed-fractional** (% of current equity — grows/shrinks with account) > fixed lot.
- Use **ATR-based stop** (1×ATR) so stops adapt to volatility, then feed into size.

### Stop loss & targets
- **Stop where the thesis is invalidated** (below a structural level, a swing pivot), never at arbitrary distance.
- **R-multiple accounting**: every trade in units of initial risk R (+2R = won 2× risk; −1R = full loss). The currency of expectancy.
- Break-even: 1:2 target needs ~⅓ win rate; 1:3 needs ~¼. Partial closes (e.g., close 50% at 1R, trail a runner) bank progress.
- **Never widen a stop** after entry to avoid a small loss (that turns a survivable streak into a blow-up).

## 3. Mindset, Discipline & Psychology

**Anchor: Mark Douglas, *Trading in the Zone*.** The psychological framework is the precondition for profitability; the failure is rarely strategy.

Core mindset:
- **Think in probabilities**: single trades are draws from a distribution; judge outcomes in 50-trade batches, not one trade.
- **Process > outcome**: a trade that followed the rules but lost is a *good* trade. Track process-adherence (1/0) as the primary metric — not P/L.
- **Accept risk in advance**: if the loss makes you uncomfortable, reduce size until it's acceptable. On entry, a loss is not a surprise.
- **Market is neutral** — respond to price, not predictions.
- **Douglas's 5 Truths**: (1) anything can happen; (2) you don't need to predict to make money; (3) wins/losses are randomly distributed given an edge; (4) an edge is only a probability, not a guarantee; (5) every moment is unique.

Cognitive biases & counters:
- **Loss aversion** (Kahneman/Tversky): losses ~2×painful → hold losers, cut winners (disposition effect). Counter: pre-defined stops.
- **Confirmation bias**: seek disconfirming evidence; write the case *against* the trade.
- **Overconfidence**: bigger positions after wins. Counter: fixed size regardless of recent P/L.
- **Anchoring / recency / FOMO / hindsight / revenge trading**: batch review, pre-defined levels, mandatory post-loss reset (step away after N losses or max daily loss), no chasing; a missed setup is no trade, never a late entry.

### Regulation
- Pre-trade checklist (entry, stop, target, size, invalidation, emotional rating ≤3).
- Max daily loss limit = hard stop for the day.
- Journal emotional states + choices; follow Steenbarger's progression Mechanical → Subjective → Intuitive (reach an "intuitive" master only after mechanical is solid).

### Key metrics (from journal)
- **Expectancy (R)**: `(WinRate×AvgWinR) − (LossRate×AvgLossR)`. Positive expectancy = the game.
- **Win rate alone is meaningless** without relative win/loss size (80% win rate with smaller wins than losses → loses money; 30% win rate at +3R/−1R → very profitable).
- **Profit factor** = gross profit ÷ gross loss (≥1.5–2 healthy). **Max drawdown**, **Sharpe/Sortino**, **avg R**, equity-curve steadiness.

## 4. Validation Workflow & Learning Path

### Backtest properly
1. Define a complete, written trading plan first (setup, entry, stop, target, size, timeframe, filters) — you can't backtest an undefined idea.
2. Backtest over a **100+ trade meaningful sample** (30–50 proves little); exercise with realistic costs (spread, commission, slippage, swap).
3. **Avoid curve-fitting**: optimize in-sample, validate out-of-sample; a `Backtest win-rate >60% with zero costs` is likely overfit.
4. **Forward-test on demo** → small live (10–25% of intended capital) → scale. Progress only when demo≈backtest within ~30% and small-live≈demo over 30+ days. If live loses >10% in first week, step back.

### Realistic learning path
0–3 mo basics (pairs, lots, leverage) → 3–9 mo consistency (one strategy, size/risk, kill overtrading) → 9–18+ mo refine execution + journaling. Provide **opinions, not guarantees**. "Profitable in 3 months" is marketing. First real win = stopping large losses; profit is a **delayed result** of better decisions + risk.

### Tools
TradingView (charts/scripting), MetaTrader 4/5 (execution + Strategy Tester/EA), cTrader (cAlgo). Analyze on TradingView, execute on MT. Calendars: Forex Factory, Investing.com, TradingEconomics. Pip calculators: Myfxbook/Babypips. Journal: TradeZella, etc.

### Prop firms (if Tutu goes that route)
FTMO-style: pay fee → pass 2-stage eval (e.g., FTMO: 10% target / 5% daily loss / 10% max drawdown, then 5%) → funded, up to 90% split. These are a **capital + discipline test**, not a shortcut — they reward small sizing and risk control. Most fail by overleveraging to hit targets fast.

## 5. Pitfalls — Why Accounts Blow Up
1. **Overleveraging / over-sizing** (#1 account killer).
2. Trading without a plan (improvised decisions).
3. **Overtrading / revenge trading** / strategy-hopping.
4. **Moving stops** / free-wheeling exits.
5. **Signal-seller scams** & "miracle EA/robot" offers (curve-fitted in disappears — always backtest your own).
6. Ignoring news risk (slippage).
7. Transaction-cost drag with high-frequency styles (scalping).
8. Unrealistic get-rich-quick expectations.

## How to Run the Skill

1. Ask the user for the **context**: instrument (pair), account size, risk % preference, timeframe, and goal (learn / analyze a chart / build strategy / review plan / sizing).
2. Identify which capability applies: **educate** (concepts/indicators), **analyze** (bias) , **design** (strategy/plan), **size** (position math), **coach** (mindset), **validate** (backtest metrics).
3. Apply the *principle* above: state structure-based bias and use indicators as confirmation. Always **attach the risk framing** — never give a trade without risk context.
4. Use honest caveats: label Smart Money as organizing (not proven); label success rates as armchair estimates, not guarantees.
5. If a math request (size/expectancy/risk-of-ruin), either compute from the formula above or recommend the position use a pip calculator.

## Common Pitfalls for the Skill Itself
1. **Indulging inventors on "best indicator/ magic number"** — settings are conventions, not optima. Treat any "perfect parameter" as overfit.
2. **Inflating confidence** — an indicator or pattern is one signal, not a command. Require confluence (>2–3 aligned) and risk framing.
3. **Ignoring risk on a chart question** — every trade recommendation must include stop and size logic.
4. **Tying into unproven claims** — avoid presenting SMC/"institutional narratives" as proven edge.
5. **Glossing costs** — transaction cost drag can eliminate a "winning" system; always scope a scalping or high-frequency strategy to costs.

## Verification Checklist (post-use)
- [ ] Addressed the specific question (learn/analyze/design/validate/coach).
- [ ] Separated facts, conventions, interpretation, and folklore (SMC labeled).
- [ ] Provided risk framing (risk %, stop logic, sizing formula) wherever trade is discussed.
- [ ] Grounded times (not data from the research) — no invented stats; figures cite 60–83% loss-range and 70–90% range only as approximate.
- [ ] Rule data/conventions vs revealed data — reconfirm task-specific numbers independently when time-sensitive.

## One-Shot Recipes
- **"Is this a valid setup?"**: → HTF bias (trend) → structure at level → momentum (RSI/divergence) → trigger (price-action confirmation) → size math → risk note. If any required step disagrees, no trade.
- **"Size this trade for me"**: risk% × account → stop (structural/ATR) → run sizing formula → return lot size + break-even RR.
- **"Teach me X indicator"**: what it measures → standard settings → how to read → its weakness → example (real FX snippet).