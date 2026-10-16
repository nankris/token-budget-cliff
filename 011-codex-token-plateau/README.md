# #011 Find your token plateau (Codex CLI)

**Question.** If you give Codex a hard token budget, where does more budget stop buying more passing tests?

**Short answer.** On a 14-package bug-fix suite, the curve isn't a slope, it's a cliff. **0% pass at 3K, 6K and 12K, then 100% at 18K, 25K, 50K, 100K and 200K** (2 runs each). The whole job needs about 20K "weighted" tokens, so all four budgets in the plan (25K/50K/100K/200K) are already on the plateau. Budgets below the cliff didn't produce a partial result. They stopped after the model had read the failing output and before it edited anything: **0 of 13 packages fixed**, and about **$0.03 of estimated spend wasted per run**.

## The knob (what exists in Codex 0.162.1)
Codex has no stable per-run token cap. The closest knob is the under-development feature `features.rollout_budget`. It's documented in the config reference (https://developers.openai.com/codex/config-reference): `enabled`, `limit_tokens`, `prefill_token_weight` (default 1.0), `sampling_token_weight` (default 1.0), `reminder_interval_tokens`. The 0.162.1 binary also requires `reminder_at_remaining_tokens` (a list, e.g. `[5000]`) when the feature is enabled, which I found through `--strict-config` errors. What I observed:
- The model gets a developer message: `<rollout_budget> You have 25000 weighted tokens left in the shared session token budget. </rollout_budget>`. A second one comes later with the remainder.
- **Cached input tokens don't seem to count.** In the 25K run the model was told "4618 left" after about 20.4K tokens of *uncached input + output*, while the run had already used 84K+ cached tokens. (Inferred from the reminder values; the docs don't say.)
- **It is enforced, softly.** When the budget runs out, the turn ends with `turn.failed: "shared rollout token budget exhausted"`. The check happens after a model call, so runs overshoot: the 3K budget runs spent 10–12K weighted tokens before they were stopped.
- An exhausted budget isn't the same as a failed task. Both 18K runs hit "budget exhausted", but only on the final summary message, after every fix had landed. All 14 packages pass.

Other token knobs I checked and didn't use: `goals.max_goal_token_budget` (for `/goal` sessions, not `exec`), and `model_context_window` / `model_auto_compact_token_limit` (context size, not spend; those are #012).

## Setup
- Codex CLI 0.162.1, `gpt-6.1-sol`, default reasoning effort, ChatGPT Plus sign-in, `codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C <fresh copy>`.
- Task: `scripts/harness/fixtures/SUITE14`. That's the 11 edit-tool fixtures (T01–T11) plus my 3 noisy-log fixtures (N01–N03), each in its own folder, with `run_all.js` running every `test.js`. 13 packages are broken; T05_stale already passes before any edit. Prompt (`scripts/prompt.txt`): "This directory holds 14 small JavaScript packages. `node run_all.js` runs every package's test.js. Make `node run_all.js` pass by fixing the code. Do not edit any test.js or run_all.js."
- Pass = `node run_all.js` exits 0 and no `test.js` changed (hash check). I also count packages passing.
- Budgets: 3K, 6K, 12K, 18K, 25K, 50K, 100K, 200K, plus no budget. 2 runs each, 18 runs total, 2026-10-14 14:08–14:20 UTC (19:38–19:50 IST). The plan's four values came first. 3K/6K/12K were added after 25K turned out not to bind, and 18K was added to find the edge.
- Est. cost: gpt-6.1-sol API list price, $2/M uncached input, $0.10/M cached, $10/M output (https://developers.openai.com/api/docs/models/gpt-6.1-sol). It's an estimate. Plus isn't billed per token.

## Exact commands
```bash
source /workspace/tools/setup.sh
B=25000
python3 scripts/harness/run_one.py --exp . --cond budget25k --task scripts/harness/fixtures/SUITE14 --rep 1 \
  --cfg features.rollout_budget.enabled=true --cfg features.rollout_budget.limit_tokens=$B \
  --cfg "features.rollout_budget.reminder_at_remaining_tokens=[$((B/5))]" --cfg suppress_unstable_features_warning=true \
  --check 'node run_all.js' --prompt "$(cat scripts/prompt.txt)" --timeout 1200
# full sweep
scripts/harness/driver.sh scripts/jobs.txt 2 results/driver.log        # 25K/50K/100K/200K/none
scripts/harness/driver.sh scripts/jobs_low.txt 2 results/driver_low.log # 3K/6K/12K
scripts/harness/driver.sh scripts/jobs_knee.txt 1 results/driver_knee.log # 18K
/workspace/tools/mlenv/bin/python scripts/analyze.py
```

## Results (18 runs)

| Budget | Runs | Full pass | Packages fixed (of 13) | Weighted tokens used* | Total tokens (min–max) | Model calls | Est. cost / run |
|---|---|---|---|---|---|---|---|
| 3K | 2 | 0/2 | 0 | 11.2K | 36.2K–37.1K | 2.0 | $0.026 |
| 6K | 2 | 0/2 | 0 | 12.7K | 38.2K–38.2K | 2.0 | $0.029 |
| 12K | 2 | 0/2 | 0 | 12.9K | 40.0K–62.0K | 2.5 | $0.031 |
| 18K | 2 | 2/2 | 13 | 21.2K | 73.5K–73.7K | 3.0 | $0.058 |
| 25K | 2 | 2/2 | 13 | 21.4K | 106.1K–127.8K | 6.0 | $0.064 |
| 50K | 2 | 2/2 | 13 | 25.0K | 113.4K–148.9K | 5.0 | $0.072 |
| 100K | 2 | 2/2 | 13 | 24.1K | 112.3K–138.1K | 4.5 | $0.069 |
| 200K | 2 | 2/2 | 13 | 25.1K | 112.3K–113.3K | 4.0 | $0.070 |
| none | 2 | 2/2 | 13 | 18.3K | 94.8K–123.0K | 4.5 | $0.056 |

\* weighted = uncached input + output, which is what the budget appears to count.

Chart: `results/chart.png`. Left: pass rate vs budget (log x). Right: weighted tokens each run actually used against the budget line. Red = fail, green = pass.

### Reading it
- **The plateau starts somewhere between 12K and 18K weighted tokens** for this suite, and it's flat from there. The model batches the whole fix into 2–3 calls, so there's no middle ground where half the packages get fixed.
- **Budget runs cost about the same as no budget, or a bit more.** Runs at 25K–200K averaged $0.064–$0.072 against $0.056 with no budget. With 2 runs per arm I can't tell if that's real. One possibility is that the injected budget messages break the prompt cache prefix a little (cached tokens were similar, though).
- **Under-budgeting is pure waste.** The failed low-budget runs still spent 36–62K total tokens (about $0.03 each) and left the code untouched.
- One 18K run took 268 s, mostly 429 retries (11 transient 429/503 "Reconnecting…" retries across all runs). Wall time here is noisy.

## Caveats
- 2 runs per budget. The cliff is sharp in both reps, but where exactly it falls (12K–18K) depends on this suite and on how much test output the model chose to read.
- `rollout_budget` is marked under development. Its accounting (cached tokens excluded) is my inference from the reminder text, and the overshoot happens because the check runs after each model call.
- These are tiny bugs. A task that needs many sequential steps would probably show a gradual curve instead of a cliff.
- Another Codex experiment was sharing this ChatGPT account at the same time, so the rate-limit % columns in `runs.csv` reflect both.
- For rows whose turn failed (budget exhausted), token usage comes from the session rollout's cumulative counter, because `codex exec --json` emits no usage for a failed turn. The `usage_src` column says which source was used.

## Files
- `scripts/harness/` (runner, driver, fixtures incl. SUITE14), `scripts/jobs*.txt`, `scripts/prompt.txt`, `scripts/analyze.py`
- `results/runs.csv` (one row per run, incl. `budget_exhausted`), `results/summary.csv`, `results/chart.png`
- `results/raw/*.jsonl`: raw `codex exec --json` streams
