# DataLens Phase 6 — Demo v2

Interactive Nexa Retail analytics workflow:

1. Explore raw/dirty CSVs
2. Inspect data quality
3. Apply controlled cleaning operations
4. Engineer derived columns
5. Analyze governed metrics
6. Ask DataLens using controlled analytical functions

The demo intentionally keeps the raw CSVs inside the deployable slice so the experience is reproducible. The LLM layer never receives the raw CSV contents directly. If `ANTHROPIC_API_KEY` is configured, `/api/ask` uses Claude tool-calling against the computed DataLens functions. Without a key, a deterministic grounded demo responder remains available.

_Deploy check v5 — confirming Vercel picks up new commits after reconnecting the GitHub integration._
