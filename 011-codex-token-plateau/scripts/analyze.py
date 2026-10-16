#!/usr/bin/env python3
"""Summarise #011 (rollout_budget sweep on SUITE14) and draw results/chart.png."""
import os, re
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(HERE, "results", "runs.csv"))


def budget(cfg):
    m = re.search(r"limit_tokens=(\d+)", str(cfg))
    return int(m.group(1)) if m else None


df["budget"] = df.cfg.apply(budget)
# weighted tokens the budget counts (observed: uncached input + output; cached input not counted)
df["weighted_tokens"] = df.uncached_input_tokens + df.output_tokens
df["broken_fixed"] = df.subtests_passed - 1  # T05_stale already passes before any edit; 13 packages are broken
g = df.groupby("cond")
summ = pd.DataFrame({
    "budget_tokens": g.budget.first(),
    "runs": g.size(),
    "full_pass": g.passed.sum(),
    "pass_rate": g.passed.mean(),
    "packages_fixed_mean_of_13": g.broken_fixed.mean().round(2),
    "weighted_tokens_mean": g.weighted_tokens.mean().round(0),
    "total_tokens_mean": g.total_tokens.mean().round(0),
    "total_tokens_min": g.total_tokens.min(),
    "total_tokens_max": g.total_tokens.max(),
    "cached_mean": g.cached_input_tokens.mean().round(0),
    "model_calls_mean": g.model_calls.mean().round(2),
    "cost_mean_usd": g.est_cost_usd.mean().round(4),
    "wall_s_mean": g.wall_s.mean().round(1),
})
summ = summ.sort_values("budget_tokens", na_position="last")
summ.to_csv(os.path.join(HERE, "results", "summary.csv"))
print(summ.to_string())

b = summ.dropna(subset=["budget_tokens"])
none = summ[summ.budget_tokens.isna()]
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
ax[0].plot(b.budget_tokens / 1000, b.pass_rate * 100, "o-", color="#4c72b0", label="full suite passes (%)")
ax[0].plot(b.budget_tokens / 1000, b.packages_fixed_mean_of_13 / 13 * 100, "s--", color="#dd8452", label="packages fixed (% of 13)")
if len(none):
    ax[0].axhline(none.pass_rate.iloc[0] * 100, color="gray", ls=":", label="no budget (pass %)")
ax[0].set_xscale("log")
ax[0].set_xticks(b.budget_tokens / 1000)
ax[0].set_xticklabels([f"{int(v)}K" if v >= 1 else str(v) for v in b.budget_tokens / 1000], fontsize=8)
ax[0].set_xlabel("features.rollout_budget.limit_tokens (log scale)")
ax[0].set_ylabel("%")
ax[0].set_ylim(-5, 105)
ax[0].set_title("Pass rate vs token budget", fontsize=11)
ax[0].legend(fontsize=8, loc="center right")
ax[0].grid(alpha=0.3)
for _, r in df.iterrows():
    x = r.budget / 1000 if pd.notna(r.budget) else None
    if x:
        ax[1].scatter(x, r.weighted_tokens / 1000, color="#55a868" if r.passed else "#c44e52", s=22, zorder=3)
ax[1].plot(b.budget_tokens / 1000, b.budget_tokens / 1000, color="gray", ls=":", label="budget line")
if len(none):
    ax[1].axhline(none.weighted_tokens_mean.iloc[0] / 1000, color="#4c72b0", ls="--", label="no-budget mean")
ax[1].set_xscale("log")
ax[1].set_yscale("log")
ax[1].set_xticks(b.budget_tokens / 1000)
ax[1].set_xticklabels([f"{int(v)}K" for v in b.budget_tokens / 1000], fontsize=8)
ax[1].minorticks_off()
ax[1].set_xlabel("budget (log scale)")
ax[1].set_ylabel("weighted tokens used (K) = uncached input + output")
ax[1].set_title("What each run actually spent (green = pass, red = fail)", fontsize=11)
ax[1].legend(fontsize=8)
ax[1].grid(alpha=0.3)
fig.suptitle("Codex 0.162.1 (gpt-6.1-sol), 14-package suite (13 broken), one headless exec per run, 2 runs per budget", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "results", "chart.png"), dpi=130)
print("wrote chart")
