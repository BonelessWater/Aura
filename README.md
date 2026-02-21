# Aura: Medical Symptom Analysis Platform

Aura is a privacy-first, local multi-agent RAG platform designed to analyze complex medical histories and bridge the communication gap between patients and specialists.

## Global Design Language & UX Flow

**Color Palette:**
- Background: `#0A0D14` (Deep space navy)
- Primary Accent: `#7B61FF` (Soft violet - trust, intelligence)
- Secondary Accent: `#3ECFCF` (Clinical teal - precision)
- Highlight/CTA: `#F4A261` (Warm amber - urgency without alarm)
- Text: `#F0F2F8` (Off-white) / `#8A93B2` (Muted slate)
- Error: `#E07070` (Muted rose) / Success: `#52D0A0` (Soft mint)

**Typography & Spacing:**
- Headings: `Clash Display` (64/40/28px, +0.02em tracking).
- Body: `Inter` (16/14/12px, 1.6 line-height).
- Data/Scores: `JetBrains Mono`.
- Spacing: 8px base unit. Cards use 24px padding, 16px radius, 1px border `rgba(123,97,255,0.15)`. Max width 1120px.

**Persistent Background Animation:**
A three-layer system that breathes life into the interface without distracting:
1. **Aurora Mesh:** A slow, 60-second drifting gradient (`#0A0D14`, `#1A1240`, `#0D2A2A`). Shifts hue toward teal on scroll.
2. **Particle Field:** 180 tiny particles (1.5px, 25% opacity) in Brownian motion. Proximity lines connect at 140px.
3. **Radial Depth Glow:** A 900px soft violet glow (7% opacity) tracks the mouse with a 600ms cubic-bezier delay.

---

## 1. The Landing Experience

**Layout:** Full-viewport, two-column split (60% copy / 40% graphic).
- **Left (Copy):** A teal monospace tag reads "PRIVATE. LOCAL. CITED." with a blinking cursor. The H1 ("Your symptoms have a pattern. We find it.") animates word-by-word with a 12px upward fade (80ms stagger). The CTA button `[Upload My Labs]` features a hover state that blooms a violet shadow and nudges the arrow right.
- **Right (Graphic):** A 3D isometric SVG of a human silhouette with a pulsing amber chest glow. Three elements (a PDF card, a hexagonal agent cluster, a SOAP note) orbit slowly on a 20-second loop.

---

## 2. Patient Intake (3-Step Wizard)

A full-screen flow with a top progress rail. The connecting line fills with a gradient sweep on advance.

- **Step 1: Longitudinal Labs:** A 480x280px dashed drop zone. On drag-over, the border turns solid violet and the zone scales to 1.02. Uploaded PDFs appear as horizontal cards with a spring-animated checkmark and a sweeping green parse bar.
- **Step 2: Clinical Interview:** A large textarea. The placeholder text cycles through five guided prompts via a 3-second typewriter crossfade. Below, five tap-chips (e.g., "Fatigue", "Joint Pain") allow quick selection, filling with a violet tint and animating a checkmark on click.
- **Step 3: Visual Evidence:** Two upload tiles (Photos/Videos). A soft amber callout slides up after 600ms explaining the Vision Model's role.

---

## 3. The Engine: Multi-Agent Processing

A dark overlay with a centered card. Four rows animate in sequentially, locking to a teal checkmark before the next begins:
1. **Agent 1 (Extractor & Vision):** Parses PDFs to JSON and translates images to clinical keywords. (Sweeping teal bar).
2. **Agent 2 (RAG Engine):** Queries a local vector database of PubMed journals. (Pulsing search icon).
3. **Agent 3 (Dual-Scorer):** Calculates Category Confidence (broad trends) and Pattern Similarity (specific flags). (Circular arcs building).
4. **Agent 4 (Translator):** Drafts outputs with DOI citations. (Looping pen animation).

---

## 4. Results Dashboard: Bridging the Gap

A two-column layout: 300px left sidebar navigation, right main content area.

**The Layman's Compass (Patient View):**
- **Score Cards:** Two SVG arc gauges animate from 0 to their value over 1.2s. The primary "Category Confidence" is large and bold. The secondary "Pattern Similarity" is visually muted with a permanent disclaimer: "This is a pattern match, not a diagnosis."
- **Translation Panel:** Plain-English explanations. Medical terms have dotted amber underlines; hovering triggers a 150ms slide-up tooltip with definitions.
- **Next Step Script:** A teal callout card providing a verbatim script for the doctor. A `[Copy Script]` button morphs to "Copied" with a scale pulse.

**The Clinical SOAP Note (Doctor View):**
- Transitions via a slide-in from the right.
- Rendered on a pure white card with black text (the only light-mode element) to signal a clinical document.
- Includes Objective Data, Assessment (Dual-Score), Literature Grounding (clickable DOI links), and Plan.

---

## 5. Ecosystem: Action & Support

- **Geographic Specialist Routing:** A dark-themed map (55% width) alongside scrollable specialist cards (45%). Hovering a card pulses the corresponding map pin and draws a glowing arc from the user's location.
- **Clustered Support Forums:** Users are matched to category-based communities. The feed uses abstract generative avatars. A pinned teal banner calmly states moderation rules. A floating `[+]` button expands to `[Share Your Experience]` on hover.

*Micro-interactions: Use skeleton screens with a slow shimmer for loading. Ensure graceful error states with actionable copy. Maintain smooth scrolling and distinct focus states for accessibility.*