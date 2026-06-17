# CivicSurvey Studio Design System

## Product Context

CivicSurvey Studio (问策 Insight) is a survey analytics workspace for uploading questionnaire data, understanding variables, running statistical analysis, generating charts, and exporting formal reports.

The interface should feel like a calm research instrument: precise, trustworthy, data-rich, and intentionally quiet. It should not feel like a generic Streamlit demo, an old government portal, or an AI marketing page.

## Aesthetic Direction

**Direction:** Civic Intelligence Workspace

**Mood:** professional, restrained, document-oriented, analytical. The product should feel comfortable for researchers, teachers, civic teams, and analysts who need clarity more than spectacle.

**Core principles:**
- Data first, chrome second.
- Use color as a status signal, not decoration.
- Build hierarchy with typography, spacing, and alignment before using shadows.
- Treat reports as formal documents, not chat output.
- AI is an assistant, not the product personality.

## Typography

**Primary CJK UI font:** Source Han Sans SC / Noto Sans CJK SC.

**Fallback stack:**

```css
"Source Han Sans SC", "Noto Sans CJK SC", "PingFang SC",
"Microsoft YaHei", "Microsoft JhengHei", sans-serif
```

**Numeric alignment:** use `font-variant-numeric: tabular-nums;` for metrics, p-values, coefficients, tables, and status counts.

**Scale:**

| Role | Size | Line Height | Weight |
|------|------|-------------|--------|
| App title | 24px | 32px | 700 |
| Page title | 22px | 30px | 700 |
| Section title | 17px | 25px | 650 |
| Card title | 14px | 22px | 650 |
| Body | 14px | 22px | 400 |
| Dense body | 13px | 20px | 400 |
| Caption | 12px | 18px | 400 |
| Metric | 28px | 34px | 700 |

**Rules:**
- No hero-scale text inside workspace tabs.
- Keep labels visible; never rely on placeholders as labels.
- Avoid emoji as structural UI. Use plain labels and status dots.
- Chinese copy should be concise and operational.

## Color System

The palette is a mineral civic palette: cool data blue, paper-like neutral surfaces, and a restrained copper accent for AI or recommendations.

```text
Canvas:          #F6F7F4
Canvas Muted:    #EEF1EE
Surface:         #FFFFFF
Surface Raised:  #FCFDFB
Surface Subtle:  #F1F4F2

Ink Strong:      #17212B
Ink:             #344054
Ink Muted:       #667085
Ink Subtle:      #98A2B3

Primary:         #245B7D
Primary Hover:   #183D54
Primary Soft:    #E6F0F4
Primary Line:    #BFD3DE

Accent:          #A65F2B
Accent Hover:    #7D431D
Accent Soft:     #FFF4E8
Accent Line:     #E9C9A5

Success:         #2F6F55
Success Soft:    #E8F3ED
Warning:         #B7791F
Warning Soft:    #FFF7E5
Error:           #B42318
Error Soft:      #FFF1ED
Info:            #2F5F73
Info Soft:       #E8F1F4

Border:          #DDE3E0
Border Strong:   #C7D0CC
Divider:         #E7ECE8
```

**Usage:**
- Primary is for the current workflow step, main buttons, selected tabs, and chart primary series.
- Accent is reserved for AI recommendations, report highlights, or rare calls for attention.
- Semantic colors appear only in status, warnings, privacy review, and validation.
- Avoid large blue blocks. Avoid decorative gradients. Avoid purple/indigo themes.

## Spacing

**Base unit:** 4px.

```text
2xs 2px
xs  4px
sm  8px
md  16px
lg  24px
xl  32px
2xl 48px
3xl 64px
```

**Density:** compact-comfortable. This is a data workspace, so it should support scanning without feeling cramped.

## Layout

**Max content width:** 1280px.

**Workspace structure:**
1. Compact app header with project identity and context.
2. Dataset metric strip.
3. Workflow status rail.
4. Segmented 5-step navigation.
5. Page-specific workspace.

**Sidebar:**
- Sidebar contains global inputs only: data source, variable dictionary, preset, AI settings, status.
- It should feel like a tool rail, not a second page.

**Report workspace:**
- Use a two-column layout where possible: controls on the left, preview/export on the right.
- Report preview should look like a white document sheet on the canvas.

## Shape and Depth

```text
Radius xs: 4px
Radius sm: 6px
Radius md: 8px
Radius lg: 12px
Radius pill: 999px
```

**Depth rules:**
- Prefer borders over shadows.
- Use shadows only for raised panels, document previews, dialogs, and hover elevation.
- Cards should not be nested inside other cards.
- Cards are for grouped information or repeated items, not for every section.

## Components

### Buttons

Primary buttons:
- Background: Primary
- Hover: Primary Hover
- Text: white
- Radius: 6px
- Height: 38-40px

Secondary buttons:
- White background
- Border: Border Strong
- Text: Ink

Ghost buttons:
- Transparent background
- Primary text
- Primary Soft hover

### Tabs

Tabs use segmented navigation:
- Outer rail: Surface, 1px Border, 8px radius
- Active tab: Primary Soft background, Primary text
- No emoji in tab labels

### Metric Cards

Metric cards are compact:
- Label in muted uppercase text
- Value uses tabular numbers
- Optional hint below
- No decorative icons

### Pipeline Status

Pipeline status uses a horizontal rail:
- Each step: dot + label + hint
- Done: Success
- Current: Primary
- Warning: Warning
- Blocked: Error

### Tables

Tables should be dense and readable:
- Header background Surface Subtle
- Thin dividers
- Tabular numbers
- Badges for variable type and privacy risk
- Avoid large row heights

### Empty States

Empty states must include:
- What is missing
- Why it matters
- The next action

No blank pages. No raw Python tracebacks by default.

## Motion

**Approach:** minimal-functional.

Use only subtle transitions:
- Button hover: 120ms
- Tab/segmented hover: 120ms
- Card hover where interactive: 160ms

No ornamental animation, floating objects, or scroll choreography.

## Copy Rules

Use:
- "执行统计分析"
- "生成报告草稿"
- "采用推荐方案"
- "请人工复核关键结论"

Avoid:
- "一键洞察"
- "智能赋能"
- "革命性分析"
- "秒出专业报告"

## Implementation Rules

- Always import colors from `src.ui.theme`.
- Prefer shared components in `src.ui.components`.
- Do not hardcode new hex values in tab files unless adding a token first.
- Keep Streamlit widgets functional and accessible.
- Any visual change should preserve the 5-step workflow.

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-16 | Reframed UI as Civic Intelligence Workspace | Matches the product's analytical, civic, and report-generation purpose |
| 2026-06-16 | Adopted Source Han Sans/Noto CJK stack | Improves Chinese readability and avoids default Streamlit feel |
| 2026-06-16 | Reserved copper accent for AI/recommendations | Gives AI features a distinct but restrained identity |
