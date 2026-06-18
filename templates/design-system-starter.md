---
template: design-system-starter
used_by: [design-system-persist]
purpose: Empty MASTER.md a project populates from a design-system-gen result.
---

# Design System — {{project_name}}

_Generated {{date}} · source: designer-pro-and-seo:design-system-gen_

## Foundations
- **Pattern / layout:** {{pattern}}
- **Style:** {{style}}

## Color
| Token | Hex | Use |
|---|---|---|
| primary | {{primary}} | actions, links, emphasis |
| secondary | {{secondary}} | supporting accents |
| accent | {{accent}} | highlights, focus |
| bg | {{bg}} | page background |
| surface | {{surface}} | cards, panels |
| text | {{text}} | body copy |
| success | {{success}} | positive states |
| warning | {{warning}} | caution states |
| error | {{error}} | error states |

Body text contrast (text on bg): {{contrast}} — AA: {{aa}}

## Typography
- Heading: **{{heading_font}}** @ {{heading_weight}}
- Body: **{{body_font}}** @ {{body_weight}}
- Type scale: {{scale}}

## Effects
- Radius: {{radius}}
- Shadow: {{shadow}}
- Motion: {{motion}}

## Anti-patterns (do not do)
{{anti_patterns}}

## Pre-delivery checklist
{{checklist}}

---
## Per-page overrides
> Add a section per page that deviates from the master. Keep deviations minimal —
> the master is the source of truth.

### {{page_name}}
- Override: {{override}}
- Reason: {{reason}}
