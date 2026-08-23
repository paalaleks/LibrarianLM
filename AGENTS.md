# Root repo rules

## Source tree

- All epub → HTML reader code lives under `src/epub-html`. Do not add those files at the repo root or under other `src/` packages.

- All i18n pipeline code lives under `src/i18n-pipeline`. Do not add those files at the repo root or under other `src/` packages.

## Subagent model routing

- Spec planning: use the latest available Sol model (`gpt-5.6-sol` when available) at **medium effort**.
- Research workflows: use the latest available Terra model (`gpt-5.6-terra` when available) at **high effort**.
- Implementation: use the latest available Terra model (`gpt-5.6-terra` when available) at **high effort**.
- Code review: use the latest available Terra model (`gpt-5.6-terra` when available) at **medium effort**.
- Do not use Terra for spec planning, and do not use Sol for implementation or code review.

## Context7

Always use Context7 when I need library/API documentation, code generation, setup or configuration steps without me
having to explicitly ask. It is wired up through the `ctx7` CLI (installed globally; `npx ctx7@latest ...` works as a
fallback). The `find-docs` skill (`.claude/skills/find-docs`) carries the full workflow; the short form is:

- Resolve the library: `ctx7 library <name> "<what to look up>"`
- Fetch docs: `ctx7 docs <libraryId> "<what to look up>"` — IDs look like `/vercel/next.js` or `/websites/ai-sdk_dev`

Prefer this over web search for library/API docs — training data may be stale. Max 3 commands per question.

<!-- ## Shadcn

- Use the `shadcn` skill for all shadcn work.
- Add missing primitives via CLI (don't hand-roll overlays/menus):
  ```bash
  pnpm dlx shadcn@latest add <component> -c src/packages/ui
  ```
- Prefer registry primitives over custom approximations. Product chrome may live in the app; menus/overlays must use design-system primitives.
 -->
