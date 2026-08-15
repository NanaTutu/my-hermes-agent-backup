---
name: storyboard-creation
description: Use when planning a video — storyboard and shot list.
---

# Storyboard Creation

Plan a video before you build it: turn a script into a sequence of framed
shots, then into a shot list you can shoot, generate with AI, or assemble in
CapCut. A storyboard is a "trial run" of the film in comic-book form — it lets
everyone see the sequence before production.

## Storyboard vs shot list (know the difference)

- **Storyboard** — a visual sequence of frames/panels showing how the scene
  reads, panel by panel. Answers "how does this scene read?"
- **Shot list** — a written table of every shot to capture (size, angle,
  movement, lens, subject, audio, notes). Answers "what do I actually capture?"

Most narrative/commercial work uses both. The storyboard is optional for many
projects; the shot list almost never is — you can shoot without knowing the
exact frame, but not efficiently without knowing what to get. Documentary /
run-and-gun often skips the board and lives on the shot list alone.

A storyboard is built from three layers:
1. **Frame** — the composition: what is in the shot, and how it is framed.
2. **Annotation** — arrows for camera/subject movement, notes on the action,
   sometimes the line of dialogue.
3. **Dialogue / audio** — what is said or heard.

## Anatomy of a storyboard panel

Each panel = one shot / one beat. Capture at minimum:

1. **Shot number** (sequential)
2. **Shot size / framing** (see vocabulary below)
3. **Camera angle** (eye-level, high, low, Dutch…)
4. **Camera movement** (static, pan, tilt, dolly, zoom, tracking…)
5. **Action** — what happens in frame (subject, movement, props)
6. **Dialogue / VO / on-screen text**
7. **Audio / SFX / music**
8. **Duration** (seconds)
9. **Transition** (cut, fade, dissolve…)
10. **Visual / prompt** — sketch (stick figures OK) or an AI image/video prompt

## Shot size / framing vocabulary

| Shot | Shows | Use for |
|---|---|---|
| Extreme wide (EWS) | vast landscape, tiny subject | establish scale/context |
| Wide (WS) | full subject + environment | establish location |
| Full (FS) | subject head-to-toe | action, body language |
| Medium (MS) | waist up | the workhorse — balance |
| Medium close-up (MCU) | chest up | dialogue, expression |
| Close-up (CU) | face | emotion, reaction |
| Extreme close-up (ECU) | eyes / detail | emphasis, tension |
| Over-the-shoulder (OTS) | subject over another's shoulder | conversation |
| POV | what the character sees | immersion |

## Camera angle vocabulary

Eye-level (neutral); high angle (camera above → subject small/vulnerable);
low angle (camera below → subject powerful); Dutch/tilted (unease); bird's-eye
/ overhead; worm's-eye; aerial.

## Camera movement vocabulary

Static (stability/focus), pan (follow action horizontally), tilt (reveal
height/depth), dolly/tracking (smooth forward/back or follow), zoom (change
focal length), orbit (circle subject), handheld (raw energy), crane/jib
(rise/fall), whip pan. Each movement serves a storytelling purpose — choose
deliberately; don't default to movement.

## The process (step by step)

1. **Script first.** Storyboard from a script/outline, not vibes. Mark the
   beats (setup, conflict, payoff).
2. **Beat breakdown.** Split the script into discrete beats — one beat → one
   or more shots.
3. **Choose shots per beat.** Pick size/angle/movement that best tells each
   beat. Vary framing (wide↔close) for rhythm.
4. **Sketch/describe panels.** Stick figures are fine. Add arrows for movement.
5. **Annotate.** Dialogue, VO, on-screen text, SFX, duration, transition per
   panel.
6. **Build the shot list.** Extract panels into a table (shot #, size, angle,
   movement, lens, subject, audio, notes).
7. **Review with collaborators.** Include the director AND the editor — they
   see coverage needs you'll miss.

## AI video generation storyboards

For AI video tools (CapCut, Seedance, Sora, Runway), each panel doubles as a
generation prompt. Write scene descriptions that name:

`subject + action + camera movement + lighting + mood + style + duration`

Example: "Medium close-up of a man in a blue shirt, slight smile, lit by warm
window light from the left, gentle dolly-in, cinematic, shallow depth of field,
photorealistic, 5s."

Keep each panel's prompt self-contained — don't rely on cross-panel context.
AI tools stay consistent within a scene but drift across cuts, so lock
lighting, color, and character description across every panel.

## Annotation conventions

- Arrows inside/around the panel show camera or subject movement direction.
- Note transitions explicitly (cut, fade, dissolve).
- Number every panel; keep shot-list rows matched to panel numbers.

## Best practices & common mistakes

- Artistic quality doesn't matter — clarity does. Stick figures beat pretty-but-vague.
- Think in shots, not scenes: one panel per shot/beat.
- Vary framing for rhythm; don't shoot everything at medium.
- Indicate light source + quality + color temperature in every panel (mood consistency).
- Time each shot: setup + action + safety buffer = total duration.
- Mistake: storyboarding dialogue without visuals (what do we SEE?).
- Mistake: no shot list → coverage gaps on the day.
- Mistake: ignoring audio/SFX/music in the plan.

## Templates

- `templates/storyboard.md` — panel-by-panel markdown storyboard.
- `templates/shot-list.md` — tabular shot list.

## CapCut handoff

A finished shot list maps 1:1 onto the CapCut automation pipeline (see the
`capcut-automation` skill): each shot becomes a video/text/subtitle element on
the timeline; durations, transitions, and text carry straight over. Storyboard
first, then automate the assembly.
