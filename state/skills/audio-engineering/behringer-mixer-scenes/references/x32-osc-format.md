# X32/M32 OSC & Scene-Format Reference

Extracted from the **Unofficial X32/M32 OSC Remote Protocol** (Patrick-Gilles Maillot) — the
authoritative community-standard protocol doc, cross-checked against real scene files.

## Ports & Transport

- X32/M32 OSC: **UDP 10023**. Console receives commands on that port, replies to the caller's port.
- X-Air systems listen on **UDP 10024** (per doc §Discovery: "Using UDP port 10024 (10023 for X32 family members)").
- OSC messages: `/address ,typetags arg arg ...` (standard OSC). The *text/scene format* omits typetags.
- Special probe: send `/info` → console replies with name/version (48 bytes). `/status` → 52-byte status.

## Scene File (.scn) Structure

- Text file, one node command per line; first line is the header.
- Header: `#4.0# "Scene name" "Scene note" %000000000 1`
  - `#4.0#` = file version (older: `#2.7#`, `#3.0#`; tolerant reader).
  - `%000000000` = 9 chars: 8 scene-safety bits + trailing 0 (safes gate recall).
  - Final `1` terminates the header.
- Snippet header: `#2.7# "Snippet name" 31473663 1 66305 449 1`
  - The 4 numbers = eventtyp, channels, auxbuses, maingrps filter masks for that snippet.
- Lines beginning with `#` are comments.
- A boot-time auto-load file can be named `CustomBootState.scn` in the USB root (FW 4.02+).

## Node Groups & What They Carry

| Node | Content |
|---|---|
| `/config/chlink` | 16 ch-links (on/off pairs) |
| `/config/auxlink` | link state for aux sends |
| `/config/fxlink` / `buslink` / `mtxlink` | link state |
| `/config/mute` | mute groups 1-8 |
| `/config/mono` | mono mode |
| `/config/solo` | solo select, dim, mutes |
| `/config/talk` (+ A/B) | talkback |
| `/config/osc` | OSC settings (IP, port, enable) |
| `/config/userrout/in|-/out` | user routing |
| `/config/routing/IN|AES50A|AES50B|CARD|OUT|PLAY` | full routing block |
| `/config/userctrl/{A,B,C}` + `/enc` `/btn` | user button/encoder assignments |
| `/config/tape` | tape recorder params |
| `/ch/01..32/` | **config** (name/icon/color/source), **delay**, **preamp** (trim, phantom, HPF, HFSL), **gate**+`/filter`, **dyn**+`/filter`, **insert**, **eq** + `eq/[1..4]`, **mix** + `mix/[01..16]`, **grp**, **automix** |
| `/auxin/01..08/` | config, preamp, eq + bands, mix, grp |
| `/fxrtn/01..08/` | config, eq, mix, grp |
| `/bus/01..16/` | config, dyn+filter, insert, eq (6-band) + bands, mix (sends), grp |
| `/mtx/01..06/` | performs the matrix |
| `/main/st` + `/main/m` | config, dyn, insert, eq + bands, mix |
| `/dca/1..8` | DCA faders + config |
| `/fx/1..8` | `source` + `par` (31 FX params) |
| `/outputs/main|aux|p16|aes|rec` | output paths + delays |
| `/headamp/000..127` | remote preamp control (S16/S32/DL32 stageboxes) |

## Verified Real Lines (from hope2022-sample.scn)

```
#4.0# "HopeStat2022" " " %000000000 1
/ch/01/config "Solly" 41 WH 32
/ch/01/preamp +4.5 OFF ON 24  73
/ch/01/gate ON GATE -67.5 60.0 1  502  983 0
/ch/01/dync ON COMP PEAK LOG -45.5 2.5 3 2.50 10 5.64  20 PRE 0 100 OFF
/ch/01/eq ON
/ch/01/mix OFF  +3.0 ON +0 OFF   -oo
/ch/01/grp %00000001 %000011
/bus/01/config "Monitor A" 64 YE
/bus/01/mix OFF  -6.9 OFF +0 OFF   -
/main/st/config "MAINS" 66 WH
/dca/1 ON  +3.5
/fx/1/source MIX13 MIX13
```

## Fader /Level Semantics

- Scene-file level values are **dB text**: `-oo` (silence), `0.0`/`+0` (unity), `+3.5`, `-17.4`.
- OSC set to `/ch/NN/mix/fader` uses a **float 0..1** taper: 1.0 = +10 dB, ≈0.75 = 0 dB, ≈0.25 = -30 dB, 0.0 = -60 dB (-oo).
- Pan: int -100..100 (or float -1..1 in some params).
- Enums appear in scene files as text (`ON/OFF`, `YE` color codes, `COMP`, `PEAK`); in OSC as integers.

## Scene recall / save verbs (OSC)

- `/load ,s scene ,i n` — recall scene n
- `/save ,s scene ,i n` — store current to scene n
- `/copy ,s scene ,i src ,i dst`
- `/rename ,s scene ,i n ,s name`
- `/delete ,s scene ,i n`
- `/status` — console status string

(This is the control-channel use; states are also batch-exported in the .scn file format above.)