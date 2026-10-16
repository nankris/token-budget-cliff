# Giving Codex a token budget: it's a cliff, not a curve

*Draft. Tech in General experiment #011. 18 headless Codex runs on 2026-10-14.*

The usual advice on agent spending: quality rises with tokens, then levels off, so find the point where extra spend stops helping. I tried to find that point for Codex CLI.

## The budget knob nobody talks about

Codex (CLI 0.162.1) has an under-development setting, `features.rollout_budget`. Turn it on with a `limit_tokens`, and the model gets a note like "You have 25000 weighted tokens left in the shared session token budget." When the budget runs out, the turn ends with "shared rollout token budget exhausted."

Two things I learned by watching it:
- **Cached tokens don't seem to count.** After about 20K tokens of new input and output, the model was told it had 4,618 of 25,000 left, though the run had read 84K cached tokens by then.
- **It overshoots.** The check runs after each model call, so a 3K budget still spent 10–12K before it stopped.

## The test

One task: a folder of 14 tiny JavaScript packages, 13 of them broken (wrong operators, a CSV parser that splits on quoted commas, a duration parser that ignores seconds, and so on). Codex had to make `node run_all.js` pass without editing any test. I ran it twice at each budget: 3K, 6K, 12K, 18K, 25K, 50K, 100K, 200K, and with no budget.

## The result

| Budget | Suite passes | Packages fixed | Est. cost / run |
|---|---|---|---|
| 3K | 0/2 | 0 of 13 | $0.026 |
| 6K | 0/2 | 0 of 13 | $0.029 |
| 12K | 0/2 | 0 of 13 | $0.031 |
| 18K | 2/2 | 13 of 13 | $0.058 |
| 25K | 2/2 | 13 of 13 | $0.064 |
| 50K | 2/2 | 13 of 13 | $0.072 |
| 100K | 2/2 | 13 of 13 | $0.069 |
| 200K | 2/2 | 13 of 13 | $0.070 |
| none | 2/2 | 13 of 13 | $0.056 |

There's no curve. Somewhere between 12K and 18K it flips from fixing nothing to fixing everything. Codex reads all the test output, then writes all 13 fixes in one or two big batched calls. Cut it off before that call and you get zero, not half.

The budgets in my original plan (25K to 200K) all sit on the flat part. The job only needs about 20K tokens of new input and output (around 110K counting cache reads).

## Two things worth knowing

1. **A too-small budget is wasted money.** The failed runs still burned 36–62K tokens each (about 3¢ at API prices) and left the code exactly as it was.
2. **"Budget exhausted" doesn't mean failed.** At 18K, both runs hit the limit, but only on the final "here's what I did" message. All the fixes had already landed and every test passed.

Budgeted runs above the cliff cost about the same as no budget, maybe slightly more (6.4–7.2¢ against 5.6¢). With two runs each, I wouldn't read anything into that gap.

## Caveats

- Two runs per budget, one suite of small bugs. A task that really needs many steps one after another probably gives a smoother curve.
- The budget feature is marked under development and could change. The "cached tokens don't count" part is my reading of the numbers, not documented behaviour.
- Dollar figures are estimates at gpt-6.1-sol API list prices ($2 / $0.10 / $10 per million new input / cached input / output). On ChatGPT Plus you pay a flat fee.

## Takeaway

Find your task's floor first: run it once without a budget and look at how many new tokens it used. Set the budget comfortably above that, or skip it. A budget below the floor doesn't buy you a cheaper partial answer. It buys you nothing.

*Code, raw logs and full tables: repo `011-codex-token-plateau`.*
