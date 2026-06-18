---
name: client-outreach
description: Generate cold-outreach messages, follow-up sequences, and niche-authority positioning for landing the first clients in a service business. Trigger when the user says "client outreach", "cold email", "first client", "outreach sequence", "niche positioning", "follow-up sequence", "lemlist / instantly / mailshake", or is starting (or restarting) sales motion for an agency or service.
---

# client-outreach

**Family:** business-and-gtm
**Status:** Stable

## Purpose

An end-to-end outreach kit for landing the first clients in a service business
(agencies selling websites + automation + SEO especially). Niche-anchored,
problem-led, and compliant — the first client is about experience + testimonial +
referral pipeline, not the money.

## Triggers

- "client outreach" / "cold email" / "first client"
- "outreach sequence" / "follow-up sequence" / "niche positioning"
- "lemlist" / "instantly" / "mailshake" / "land my first client"

## Inputs

- Service offering (one sentence) and target niche (e.g. "HVAC commercial")
- Current testimonials / case studies (or "none yet")
- Outreach tool preference and weekly send volume

## Steps

1. **Niche-anchor.** Identify the ONE operational trigger this niche actually cares
   about (annual inspections / emergency dispatch / recurring schedules). Generic
   "we do SEO" gets deleted — anchor everything on the trigger.
2. **Write the opener** from `templates/outreach-message-starter.md`: problem-led
   open, a real specific observation, a free-value offer, a low-friction yes/no CTA.
   (Use `copywriting` for the lines.)
3. **Build the cadence** from `templates/outreach-followup-sequence.md`: a 4–7 touch
   sequence where every touch adds value (never "just bumping"). Stop on any reply.
4. **Niche-authority positioning** — a short specialist POV for the site, LinkedIn,
   and calls (specialist beats generalist for first clients).
5. **Tool import** — produce the import file in the user's tool's format (CSV for
   Instantly, etc.).
6. **Compliance pass (required).** Real sender identity + physical address +
   one-click opt-out; honor CAN-SPAM / GDPR / CASL (see `PRIVACY.md`). Don't suggest
   buying lists or deceptive subject lines.

## Outputs

- `outreach/opening-message.md`, `outreach/follow-up-sequence.md`,
  `outreach/niche-positioning.md`
- `outreach/import-{tool}.csv`

## Dependencies

- `templates/outreach-message-starter.md`, `templates/outreach-followup-sequence.md`
- Optional: `copywriting` (sharper lines)

## Notes

Anchor every pitch on the specific operational trigger the niche cares about — that's
the difference between getting opened and getting deleted. Compliance is not
optional; it protects the sender's domain reputation and is the law.
