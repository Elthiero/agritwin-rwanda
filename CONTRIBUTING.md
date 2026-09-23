# Contributing

Internal notes for the two-person AgriTwin Rwanda team. See `CLAUDE.md` for the full
development method (trunk-based, local gates before commit, no CI).

## Before every commit

- Run `make lint && make test`. Fix failures before committing, don't commit past a red result.
- If the change touches `data/public/`, also run `/privacy-check`.
- Every AI-assisted session that produces significant code or text adds a row to
  `docs/ai-usage-log.md` in the same PR/commit set, per `CLAUDE.md` rule 9. Use the
  `/log-ai-use` skill. Do this before the change lands on `main`, not retroactively — see
  `docs/ai-usage-log.md`'s own note on why a batch backfill was needed once already.
- Record any methodological or architectural decision in `docs/decisions.md` (date, decision,
  reason, alternatives), per `CLAUDE.md` rule 6.

## Commit style

Small commits, Conventional Commit messages (`feat:`, `fix:`, `data:`, `docs:`, `test:`,
`chore:`). Work directly on `main` unless a change is large enough to risk breaking something
the other person depends on that day.
