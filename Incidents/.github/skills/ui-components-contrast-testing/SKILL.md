---
name: ui-components-contrast-testing
description: Use when testing UI component contrast accessibility (WCAG 1.4.11 Non-text Contrast).
---

# UI Component Contrast Testing

## Description

Guide for testing UI component contrast accessibility (WCAG 1.4.11 Non-text Contrast).

**WCAG Criterion**: 1.4.11 Non-text Contrast (Level AA)
- [Understanding Success Criterion 1.4.11: Non-text Contrast](https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html)

## Why It Matters

Visual information used to indicate states and boundaries of active UI Components must have sufficient contrast. Most people find it easier to see and use UI Components when they have sufficient contrast against the background. People with low vision, limited color perception, or presbyopia are especially likely to struggle with controls when contrast is too low.

### From a User's Perspective

> "When buttons, form fields, and other controls don't have enough contrast, I can't tell where to click or what state they're in. A subtle border or faint icon might be invisible to me, making the interface unusable."

## Key Concepts

### What Requires 3:1 Contrast

Visual information used to identify active UI components and their states must have a contrast ratio of at least **3:1** against the adjacent background:

- Any visual information that's needed to identify the component
  - Visual information is almost always needed to identify text inputs, checkboxes, and radio buttons.
  - Visual information might not be needed to identify other components if they are identified by their position, text style, or context.
- Any visual information that indicates the component is in its normal state

### Exceptions

No minimum contrast ratio is required if either of the following is true:
- The component is inactive/disabled
- The component's appearance is determined solely by the browser (user agent)

### State Changes Clarification

This success criterion does not require that changes in color that differentiate between states of an individual component meet the 3:1 contrast ratio when they do not appear next to each other. For example, there is not a new requirement that visited links contrast with the default color, or that mouse hover indicators contrast with the default state.

However, the component must not lose contrast with the adjacent colors, and non-text indicators such as the check in a checkbox, or an arrow graphic indicating a menu is selected or open must have sufficient contrast to the adjacent colors.

## Mandatory Execution Steps

**MANDATORY QUALITY REQUIREMENT:** This test must be performed thoroughly. Do not take shortcuts or sacrifice quality for speed. Every element must be tested, every violation must be investigated, and every result must be documented accurately.

### Step 1: Identify UI Components

In the target page, identify all active user interface components in their states, including:
- Buttons and links
- Form controls (text inputs, checkboxes, radio buttons, dropdowns)
- Custom widgets (toggles, sliders, tabs)
- Interactive icons

Examine each component in its **normal state** (not disabled, no mouseover or input focus).

### Step 2: Measure Contrast Ratios

Verify contrast ratios:

1. **Identify the visual boundary or indicator** of the component
2. **Sample the foreground color** (the border, icon, or state indicator)
3. **Sample the adjacent background color**
4. **Calculate the contrast ratio** - must be at least 3:1

### Step 3: Record Results

**✅ Pass** if:
- All visual information needed to identify UI components has at least 3:1 contrast
- All visual state indicators have at least 3:1 contrast
- Focus indicators are clearly visible with at least 3:1 contrast

**❌ Fail** if:
- Component boundaries have less than 3:1 contrast
- Icons or indicators used to identify components have less than 3:1 contrast
- State indicators (focus, hover, selected) have less than 3:1 contrast

## References

### WCAG Success Criteria
- [Understanding Success Criterion 1.4.11: Non-text Contrast](https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html)

### Sufficient Techniques
- [Using an author-supplied, highly visible focus indicator](https://www.w3.org/WAI/WCAG22/Techniques/general/G195)

### Common Failures
- [Failure of Success Criterion 2.4.7 due to styling element outlines and borders in a way that removes or renders non-visible the visual focus indicator](https://www.w3.org/WAI/WCAG22/Techniques/failures/F78)

### Additional Guidance
- [Using a contrast ratio of 3:1 with surrounding text and providing additional visual cues on focus for links or controls where color alone is used to identify them](https://www.w3.org/WAI/WCAG21/Techniques/general/G183)