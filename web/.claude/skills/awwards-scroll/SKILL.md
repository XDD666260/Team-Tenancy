---
name: wcag
description: Audit a page for WCAG 2.1 AA accessibility issues. Traces the render chain, checks structural/semantic HTML, contrast indicators, ARIA, and outputs a prioritized report.
argument-hint: "<page-name or url-path>"
user-invocable: true
disable-model-invocation: true
---

# WCAG 2.1 AA Audit Skill

Audit a page for WCAG 2.1 AA accessibility issues by tracing its render chain and checking source code.

## 1. Identify the Page

Parse `$ARGUMENTS` for a page name or URL path:
- Page names: `homepage`, `about`, `contact`, `login`, `dashboard`, `product-detail`, etc.
- URL paths: `/`, `/about/`, `/products/123/`, `/blog/my-post/`, etc.

Locate the **entry point** for the target page. Look for:
- **Route configuration**: e.g., `routes.php`, `web.php` (Laravel), `urls.py` (Django), route files in `src/routes/` or `app/router/`
- **Page registry or CMS config**: any database-driven or config-driven page lookup
- **Direct file mapping**: e.g., `pages/about.tsx` (Next.js), `src/views/About.vue` (Vue), `public_html/about.php`
- **Catch-all routers**: `router.php`, `index.php`, or framework entry points

From the entry point, identify the **controller/handler**, **view/template**, and **includes/components** for the target page. If the argument is `homepage` or `/`, start from the root index file.

## 2. Ask for External Input

**Before doing any audit work**, use `AskUserQuestion` to ask:

> Do you have external audit results (e.g., WAVE summary) to include?

Options:
- **Yes — I'll paste WAVE results**: Wait for the user to paste their WAVE output. Then proceed.
- **Yes — other input**: Wait for the user to provide their context (focus areas, known issues, etc.). Then proceed.
- **No — run source-only audit**: Skip straight to the render chain trace and run all built-in checks.

### How to use external input

When the user provides input:
- **WAVE results**: Cross-reference each reported issue against the source code. For each WAVE finding, locate the exact `file:line`, confirm the issue, and propose a fix. Promote confirmed WAVE findings to **Critical** severity. Also run the full standard audit — WAVE may have missed structural issues.
- **Focus areas**: Run the full audit but give extra attention to the specified areas. Call out the focused findings in a separate subsection at the top of the report.
- **Known issues**: Verify whether each issue still exists in the current code. Report as "confirmed" or "already fixed".

**Recommended WAVE paste format** (tell the user if they choose WAVE):
> Tip: Summarize the WAVE output rather than pasting raw — e.g.:
> `2 missing form labels, 1 broken skip link, 31 contrast errors, 2 skipped heading levels, 3 very small text`
> WAVE's numbered items (Very low contrast 1, 2, 3...) don't carry element info, so a summary works just as well.

## 3. Trace the Render Chain

Starting from the controller/handler, map **every file** that contributes to the final HTML output:

1. **Controller/Handler** — the file handling the route (PHP controller, Express route handler, React page component, etc.)
2. **View/Template** — the template file rendered by the controller (Blade, Twig, EJS, JSX/TSX, Vue SFC, Svelte, Handlebars, plain HTML, etc.)
3. **Includes/Components** — header, footer, navigation, sidebar, modals, partials, shared components
4. **CSS files** — all stylesheets loaded by the page:
   - Linked stylesheets (`<link>` tags)
   - CSS modules or scoped styles
   - Tailwind/utility classes (check `tailwind.config.js` for custom values)
   - CSS-in-JS (styled-components, emotion) — check the component files themselves
5. **JS files** — all scripts loaded by the page that manipulate the DOM or handle interactions

Read each file. List the full render chain at the top of the report as the audit scope.

## 4. Structural Checks (Source Code Analysis)

Organized by WCAG principle. For each finding, report `file:line`, the WCAG criterion, and a fix suggestion.

### Perceivable (1.x)

| Criterion | Check |
|-----------|-------|
| 1.1.1 Non-text Content | Every `<img>` has a meaningful `alt` attribute. Flag filenames, UUIDs, or empty alt on non-decorative images. Decorative images should have `alt=""` AND `aria-hidden="true"`. |
| 1.3.1 Info and Relationships | Major page sections use semantic elements or landmark roles (`<nav>`, `<main>`, `<aside>`, `<header>`, `<footer>`). Filter sidebar has `role="region"` or equivalent. |
| 1.3.1 Info and Relationships | Active navigation item has `aria-current="page"`. |
| 1.3.1 Info and Relationships | Heading hierarchy: h1 → h2 → h3 with no skipped levels. Exactly one `<h1>` per page. |

### Operable (2.x)

| Criterion | Check |
|-----------|-------|
| 2.4.1 Bypass Blocks | A skip-to-content link exists in the HTML (grep for `skip-link` or `skip-to` class in both HTML and CSS). Must be visible on focus. |
| 2.4.7 Focus Visible | Search all CSS for `outline: none` or `outline: 0` — each MUST have a replacement `:focus-visible` style nearby. |
| 2.4.7 Focus Visible | Confirm `:focus-visible` is used instead of bare `:focus` for outline overrides. |

### Understandable (3.x)

| Criterion | Check |
|-----------|-------|
| 3.1.1 Language of Page | `<html>` tag has a correct `lang` attribute. |
| 3.1.2 Language of Parts | If the page supports multiple languages: verify the `lang` attribute on `<html>` updates when the language changes. Check that language switcher navigation actually changes the page language, not just a UI variable. |

### Robust (4.x)

| Criterion | Check |
|-----------|-------|
| 4.1.1 Parsing | Collect ALL `id="..."` values across every file in the render chain. Flag any duplicates. |
| 4.1.2 Name, Role, Value | Every `<input>`, `<select>`, `<textarea>` has a `<label>`, `aria-label`, or `aria-labelledby`. Placeholders alone do NOT count. |
| 4.1.2 Name, Role, Value | Interactive elements that are not links use `<button>`, not `<a href="#">` or `<a href="javascript:">`. |
| 4.1.2 Name, Role, Value | Any `role="option"` element has a parent with `role="listbox"`. |
| 4.1.2 Name, Role, Value | `title` attributes are helpful context, not noise. Flag any `title` containing a raw URL or duplicating visible text exactly. |
| 4.1.2 Name, Role, Value | Decorative elements (emoji spans, icon elements without text) have `aria-hidden="true"`. |
| 4.1.2 Name, Role, Value | Elements with `aria-expanded` also update their `aria-label` or have descriptive text that changes with state. |
| 4.1.3 Status Messages | Dynamic content areas (AJAX loaders, live search results, notification areas) use `aria-live` regions. |

## 5. Visual / Contrast Flags (Requires Manual Verification)

Claude cannot compute rendered contrast ratios. Flag these patterns for manual verification with WAVE:

### Color contrast indicators
- Any `color` property using light grays (`#666`, `#777`, `#888`, `#999`, `#aaa`, `#bbb`, `#ccc` or equivalent `rgb()`/`rgba()`) on elements likely against white/light backgrounds
- White or light text (`#fff`, `#eee`, `#ddd`) on bright/medium backgrounds (greens, oranges, yellows, light purples, light blues)
- Any `opacity` value < 1 on text elements — this reduces effective contrast

### Inherited colors
- `<a>` tags inside styled containers that do NOT set an explicit `color` property — they inherit browser defaults which may fail contrast
- Pay special attention to: social icon links, mobile menu items, quick action links, footer links

### Font sizes
- Any `font-size` below 11px → flag as "very small text — likely fails WCAG"
- Text at 11-13px → flag as "small text — verify readability and contrast at this size"

### Missing backgrounds
- Icon containers or badge elements that lack `background-color` when sibling elements have one (inconsistency suggesting a missing style)

### Dark mode contrast
- Check that `:focus-visible` indicators have dark-mode variants
- Check that text colors in dark mode rules maintain readable contrast against dark backgrounds
- Check that `opacity` on text doesn't reduce dark-mode contrast below usable levels

## 6. Mobile-Specific Checks

Mobile-only elements are invisible to desktop audits. This section catches them.

1. **Find mobile-only elements**: Search CSS for elements with `display: none` on desktop but visible inside `@media` queries with `max-width` breakpoints. Also search for elements only visible via `@media (max-width: ...)`.

2. **For every mobile-only element found**, apply ALL checks from sections 4 and 5. Specifically:
   - Mobile menu: links have explicit `color`, focus styles work, `aria-expanded` toggles
   - Mobile filter button: sufficient contrast, has accessible name
   - Mobile overlays: focus trapping, close mechanism, `aria-modal`
   - Hamburger menu content: all interactive elements are keyboard accessible

3. **Check mobile `<a>` tags** have explicit `color` set (not relying on inheritance which may fail contrast on mobile backgrounds).

## 7. Output Report

Use this exact structure:

```
## WCAG 2.1 AA Audit — [Page Name]

### Render Chain
- Controller: [path]
- View: [path]
- Includes: [list]
- CSS: [list]
- JS: [list]

### WAVE Cross-Reference (only if WAVE context was provided)
For each issue from the WAVE summary:

1. **[WAVE issue description]** — STATUS: confirmed / already fixed
   - Location: `file:line`
   - Root cause: [explanation]
   - Fix: [suggestion]

### Critical (WCAG AA Failures)
Issues that are definite WCAG 2.1 AA violations.

1. **[Criterion] [Short title]** — `file:line`
   [Description and fix suggestion]

### Major (Should Fix)
Issues that are very likely failures or significant usability problems.

1. **[Criterion] [Short title]** — `file:line`
   [Description and fix suggestion]

### Moderate (Recommended)
Issues that improve accessibility but may not be strict failures.

1. **[Criterion] [Short title]** — `file:line`
   [Description and fix suggestion]

### Contrast Flags (Verify with WAVE)
Items that need manual contrast checking — cannot be computed from source.

1. **[Element description]** — `file:line`
   `color: [value]` on `background: [value or "inherited"]` — [risk level]

### Mobile-Specific Issues
Issues only visible at mobile breakpoints.

1. **[Criterion] [Short title]** — `file:line`
   [Description and fix suggestion]

### Passed Checks
Accessibility features that are correctly implemented.

- [Item that passed]

### Recommended Next Step
Run WAVE (https://wave.webaim.org/) on both desktop and mobile viewports to catch computed contrast failures that source-level auditing cannot detect.
```

## Important Notes

- **Be thorough**: Read every file in the render chain. Don't skip includes or partials.
- **Be precise**: Always cite `file:line` for findings.
- **Don't guess contrast**: Flag suspicious color combinations but mark them for manual verification.
- **Check dark mode separately**: Dark mode CSS often lives in different selectors or files.
- **Mobile is a first-class audit target**: Trace mobile-specific CSS and apply full checks to mobile-only elements.
- **No false positives on decorative images**: `alt=""` is correct for decorative images — only flag it if the image conveys meaning.