---
template: blast-template
used_by: [blast-prompt]
purpose: Structured build brief; structure-as-coverage so nothing is forgotten pre-build.
---

# BUILD BRIEF — {{project_name}}

> Five sections. Each has a required-fields checklist. A section is "complete"
> only when every required field is filled (no "TBD"). Incomplete sections are
> the gaps that surface mid-build — fill them now.

## B — Blueprint (what is being built)
- **One-line goal:** {{goal}}
- **Pages / screens:** {{pages}}
- **Per page, key sections:** {{sections_per_page}}
- **Primary user + job-to-be-done:** {{primary_user}}
- **Primary conversion action:** {{primary_cta}}
- **Fidelity:** {{fidelity}}  <!-- prototype | production -->
- **Out of scope (explicit):** {{out_of_scope}}

_Required: goal, pages, primary_cta, fidelity._

## L — Link (integrations & external dependencies)
- **Forms / lead capture → where it sends:** {{forms}}
- **Payments:** {{payments}}
- **Analytics / tracking:** {{analytics}}
- **CRM / email / automation:** {{crm}}
- **Third-party embeds (maps, booking, chat):** {{embeds}}
- **Env vars / API keys needed:** {{secrets}}  <!-- names only, never values -->

_Required: forms destination, analytics. (If "none", state "none".)_

## A — Architect (technical shape)
- **Stack:** {{stack}}  <!-- or "agent picks; constraints: ..." -->
- **Hosting / deploy target:** {{deploy_target}}
- **File / component structure:** {{structure}}
- **Data sources / content model:** {{data}}
- **Performance budget:** LCP < {{lcp}}s, CLS < 0.1, INP < 200ms
- **Browser / device support:** {{support}}

_Required: deploy_target, performance budget._

## S — Stylize (design system reference)
> Paste from `design-system-gen` output, or reference the saved `MASTER.md`.
- **Pattern / layout:** {{pattern}}
- **Style:** {{style}}
- **Palette (hex):** primary {{primary}} · secondary {{secondary}} · accent {{accent}} · bg {{bg}} · text {{text}}
- **Typography:** {{heading_font}} / {{body_font}}
- **Effects:** radius {{radius}} · shadow {{shadow}} · motion {{motion}}
- **Anti-patterns to avoid:** {{anti_patterns}}

_Required: palette, typography, pattern._

## T — Trigger (the actual launch command)
> The exact prompt/command to hand the build agent. Self-contained: it references
> the four sections above so the agent has full context in one paste.

```
{{launch_command}}
```

_Required: a complete, paste-ready launch command._

---
### Completeness gate
- [ ] Blueprint complete
- [ ] Link complete (or explicit "none")
- [ ] Architect complete
- [ ] Stylize complete
- [ ] Trigger is paste-ready
If any box is unchecked, the brief is not ready to launch.
