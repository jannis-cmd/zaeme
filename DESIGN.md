---
name: Zäme
description: Warm paper, personal friendship books and a calm conversation companion.
colors:
  primary: "#116b5b"
  focus-teal: "#19937e"
  conversation-brown: "#7a5c3a"
  conversation-hover: "#6c5032"
  book-violet: "#7e3093"
  warm-background: "#f7f4ef"
  white-paper: "#ffffff"
  memory-sand: "#ede5d6"
  ink: "#2e3830"
  muted: "#5a6360"
  divider: "#e4ddd3"
  danger: "#a23438"
  light-teal: "#e0f2ee"
  logo-blue: "#3ab7cb"
  logo-orange: "#ff674e"
  logo-yellow: "#feca00"
typography:
  headline:
    fontFamily: '"Nunito Sans", "Segoe UI", sans-serif'
    fontSize: "clamp(34px, 4vw, 46px)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.035em"
  body:
    fontFamily: '"Nunito Sans", "Segoe UI", sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: '"Nunito Sans", "Segoe UI", sans-serif'
    fontSize: "15px"
    fontWeight: 600
rounded:
  field: "8px"
  button: "10px"
  paper: "12px"
  icon-button: "13px"
  card: "16px"
  overlay: "20px"
  circle: "50%"
spacing:
  control-gap: "8px"
  list-gap: "16px"
  book-gap: "24px"
  page-padding: "40px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white-paper}"
    rounded: "{rounded.button}"
    padding: "12px 21px"
    height: "52px"
  button-icon:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.icon-button}"
    width: "44px"
    height: "44px"
  field:
    backgroundColor: "{colors.warm-background}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "10px 12px"
  family-nav:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    padding: "8px 4px"
  friendship-book:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white-paper}"
    padding: "62px 28px 64px"
  memory-card:
    backgroundColor: "{colors.memory-sand}"
    textColor: "{colors.ink}"
    rounded: "{rounded.paper}"
    padding: "15px 18px 18px"
---

# Design System: Zäme

## Overview

**Creative North Star: "The Friendship Book"**

The Friendship Book gives Zäme a familiar, personal character: warm paper, readable rounded lettering and controlled colorful covers. Native HTML and CSS provide the aesthetic; there is no official component framework. The approved settings are design variance 3, motion 2 and density 3.

Depth explains objects and transitions. Color identifies a person or an action, while neutral pages keep longer text calm. Preserve the original conversation button, its states and animations, and the colorful Zäme lettering.

**Key Characteristics:**

- Warm paper and dark readable text.
- Persistent teal, brown and violet book identities.
- Neutral open pages and sand memory cards.
- Large controls, clear selection and restrained motion.

## Colors

Dark accents sit on warm neutral paper. The frontmatter records normative values.

### Primary
- **Deep Teal:** Primary actions, input focus and cover zero; brighter focus teal supplies the global keyboard outline.

### Secondary
- **Conversation Brown:** The original conversation button and cover one; the darker brown supplies its hover state.
- **Book Violet:** Cover two and the second wordmark letter.
- **Logo Blue, Orange and Yellow:** Preserve the colorful wordmark. Yellow retains its brown stroke for legibility.
- **Danger Red:** Delete actions and recording discard.

### Neutral
- **Warm Background:** The home, family shell and form fields.
- **White Paper:** The open spread, voice choices, budget and dialogs.
- **Memory Sand:** Memories, quiet actions and disabled save/donation controls.
- **Ink / Muted:** Main text / explanatory text; **Divider** separates surfaces; **Light Teal** marks summary refresh availability.

**The Stable Cover Rule.** Cover color belongs to the person’s persisted bookCover, never to selection. Selection adds an outline and a circled check at the upper left, aligned with the edit pencil at the upper right. Covers show the name and profile details without decorative initials or selection labels.

## Typography

**Display Font:** Nunito Sans, with Segoe UI and sans-serif fallbacks.
**Body Font:** The same family, locally served at weights 400, 600 and 700.

Rounded letterforms feel familiar without weakening hierarchy. Body text uses the frontmatter scale; headings are bold with tighter spacing.

### Hierarchy
- **Headline:** Responsive page titles; editor titles use a slightly smaller clamp (32–44px).
- **Title:** Open-page headings (26–27px), book names (28px), summary headings (24px).
- **Body:** Profile and memory text; persona passages grow to 17px with 1.65 line height. Donation prose uses 17–18px with 1.7 line height and introductory copy is limited to 72ch.
- **Label:** Semibold field labels; primary buttons use weight 700. Supporting dates and captions are smaller (12–14px).

## Layout

The senior home centers one conversation control on a plain warm background, with the colorful wordmark left and a small Angehörige control right. The original conversation states remain intact.

The family area is a scrolling overlay: maximum panel width 1184px, outer inset 24px and viewport height minus 48px. Inner page content uses 40px side margins. The book shelf has three columns with 24px gaps, two columns at 1000px and one at 600px. The open white book uses two equal columns with the profile left and shared memories right; at 820px the pages stack with a horizontal divider. Memories form one column.

At 600px the overlay inset becomes 8px, its height becomes viewport minus 16px, content side margins become 16px and page padding reduces to 32px above / 70px below. The family logo hides to make room for labeled tabs and account/close controls. Field pairs remain two columns, with language and address each spanning the row. Donation support stacks at 760px; partner logos wrap.

## Elevation & Depth

Shadows are structural: page edges under covers, a thin stacked edge under the open spread, and soft elevation around dialogs and the family overlay. Memory cards remain flat. Book opening and closing rotates the cover while moving the paper between shelf and spread; reduced motion disables decorative CSS animation and skips this transition.

### Shadow Vocabulary
- **Book:** Layered white and tan page edges with a soft lower shadow.
- **Open spread:** A low ambient shadow with a three-pixel tan page edge.
- **Overlay:** A broad soft shadow that separates the family panel from the home.
- **Conversation:** The updated brown control uses one organic breathing surface in every idle/listening state. Thinking and talking have distinct restrained motion; no separate halo or recording pulse is used.

## Shapes

Controls and paper use gently curved corners from the frontmatter scale. Closed books have an asymmetric spine silhouette (5px left, 16px right), a fine vertical seam and layered page edges. The conversation button retains the user’s updated organic silhouette in every state. The open spread has a shared outer curve and a central divider.

## Components

### Buttons

Primary controls are solid teal with white text. The labeled Person hinzufügen action anchors the shelf. Fine-pointer hover darkens enabled primary buttons to #0d584b; active buttons scale to .97. Quiet and danger variants use sand and red. Obvious edit, delete, save, record, refresh, account and close actions use Iconoir symbols with accessible names and tooltips. Icon buttons are 44px square; the global focus ring is 3px with a 3px offset.

### Cards / Containers

Friendship books retain their individual covers while selected. A selected book has a 2px outline offset by 5px, a circled check at the upper left, aligned with the edit pencil. Book hover lifts by 3px on fine pointers. Profile editing opens a neutral white spread with equal pages and responsive padding (24–40px). Sand memory cards have a 184px collapsed height and a 92px text excerpt; long text fades at the bottom and expands when activated. New memories settle in over 280ms; no card shadow is applied.

### Inputs / Fields

Fields use a fine neutral border, warm background and readable text; single-line inputs and selects have at least 44px height. Focus uses a 2px dark-teal outline offset by 2px and matching border. The memory composer groups textarea and record/save actions inside a rounded bordered surface. Its focus-within treatment matches fields. Disabled save uses sand and muted text.

### Navigation

Family tabs are labeled, bold and transparent, with a brown active underline. Account and close are 44px icon actions. Angehörige on the home is a small outlined control with sand hover. Back navigation remains labeled. Voice options retain visible native radio indicators, labels and a teal selected border; the group has two equal options and 48px minimum height.

### Friendship Book Motion

Opening rotates the cover to -105 degrees over 300ms, then moves/scales paper over 360ms with a 220ms delay. Closing reverses this sequence with a 260ms cover delay. The target fades in over 140ms. Standard control transitions are 130–180ms. These motion details belong to the existing book metaphor and should remain restrained.

## Do's and Don'ts

### Do:

- **Do** preserve the colorful wordmark and original conversation-button states and animations.
- **Do** retain a person’s persisted bookCover when selecting, editing or deleting another profile.
- **Do** give icon-only actions accessible names, tooltips and 44px targets.
- **Do** keep the primary add-person action labeled; use icons for selection and editing.
- **Do** honor reduced motion and maintain all existing content and functions.

### Don't:

- **Don’t** recolor a cover to indicate selection.
- **Don’t** introduce competing bright colors inside the open book.
- **Don’t** remove keyboard focus or communicate selection through color alone.

## Introduction Funnel

Five guided steps: people and circled selection, voice, profile, shared memories, then summary refresh. Memories precede the summary because they supply its facts. Scroll targets and highlights follow this order. The demonstration never saves a fictional profile; finishing returns to the library to create a real book. Home uses the user’s updated idle/listening, thinking and talking button states. The button starts and ends the conversation.
