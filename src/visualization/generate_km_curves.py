import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sksurv.nonparametric import kaplan_meier_estimator
from sksurv.compare import compare_survival
from sksurv.util import Surv

def generate_km_curves():
    print("=" * 80)
    print("GENERATING KAPLAN-MEIER CURVES FROM OUT-OF-FOLD PREDICTIONS")
    print("=" * 80)

    filename = "model_predictions.csv"
    if not os.path.exists(filename):
        print(f"Error: '{filename}' not found.")
        return

    df = pd.read_csv(filename)
    df_oof = df[df["Model"] == "RSF_OOF"].copy()
    if df_oof.empty:
        print("Error: No RSF_OOF rows found in model_predictions.csv.")
        return

    imputations = ["MICE (pooled)", "missForest", "GAIN", "MIDA"]
    panel_titles = ["MICE", "missForest", "GAIN", "MIDA"]
    eval_times = [0, 30, 60, 90, 120, 150]

    max_t = df_oof["Observed_Time"].max()

    fig, axes = plt.subplots(2, 2, figsize=(14, 12), sharex=True, sharey=True)
    fig.suptitle("Kaplan-Meier curves by median split of RSF out-of-fold risk scores (n=766 training patients)", fontsize=15, y=0.98)

    for idx, (imp, title) in enumerate(zip(imputations, panel_titles)):
        ax = axes[idx // 2, idx % 2]
        sub = df_oof[df_oof["Imputation"] == imp].copy()
        if len(sub) == 0:
            print(f"Warning: No rows for imputation {imp}")
            continue

        median_val = sub["Predicted_Risk"].median()
        high_mask = sub["Predicted_Risk"] >= median_val
        low_mask = ~high_mask

        high_df = sub[high_mask]
        low_df = sub[low_mask]

        n_high = len(high_df)
        events_high = int(high_df["Observed_Status"].sum())
        n_low = len(low_df)
        events_low = int(low_df["Observed_Status"].sum())

        y_surv = Surv.from_arrays(sub["Observed_Status"].astype(bool), sub["Observed_Time"])
        group_indicator = high_mask.astype(int)
        stat_res = compare_survival(y_surv, group_indicator)
        if isinstance(stat_res, (tuple, list)):
            p_val = stat_res[1]
        else:
            p_val = stat_res

        p_str = f"Log-rank p = {p_val:.1e}"

        def get_surv_at(times, prob, t):
            idx_t = np.where(times <= t)[0]
            return prob[idx_t[-1]] if len(idx_t) > 0 else 1.0

        for grp_df, label_prefix, color in [(high_df, f"High risk (n={n_high}, {events_high} events)", "red"),
                                           (low_df, f"Low risk (n={n_low}, {events_low} events)", "blue")]:
            ev = grp_df["Observed_Status"].astype(bool)
            tm = grp_df["Observed_Time"]

            try:
                times, prob, conf_int = kaplan_meier_estimator(ev, tm, conf_type="log-log")
                has_ci = True
            except Exception as e:
                print(f"Warning: conf_type='log-log' unsupported ({e}), plotting without bands.")
                times, prob = kaplan_meier_estimator(ev, tm)
                has_ci = False

            ax.step(times, prob, where="post", color=color, label=label_prefix, linewidth=1.8)
            if has_ci and conf_int is not None:
                ax.fill_between(times, conf_int[0], conf_int[1], alpha=0.18, step="post", color=color)

            censored_times = grp_df[grp_df["Observed_Status"] == 0]["Observed_Time"].values
            if len(censored_times) > 0:
                censored_probs = [get_surv_at(times, prob, ct) for ct in censored_times]
                ax.scatter(censored_times, censored_probs, marker="|", color=color, s=25, zorder=3)

            s30 = get_surv_at(times, prob, 30)
            s60 = get_surv_at(times, prob, 60)
            grp_name = "High" if color == "red" else "Low"
            print(f"[{title}] {grp_name} risk: n={len(grp_df)}, events={grp_df['Observed_Status'].sum()}, Day 30 KM={s30:.4f}, Day 60 KM={s60:.4f}")

        print(f"[{title}] {p_str}")

        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.set_xlim(0, max_t)
        ax.set_ylim(0, 1.05)
        ax.legend(loc="lower left", fontsize=9, frameon=True)
        ax.text(0.96, 0.94, p_str, transform=ax.transAxes, ha="right", va="top",
                fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="gray"))

        at_risk_high = [sum(high_df["Observed_Time"] >= t) for t in eval_times]
        at_risk_low = [sum(low_df["Observed_Time"] >= t) for t in eval_times]

        ax.tick_params(labelbottom=True)
        ax.set_xlabel("Days after admission", fontsize=11)

        y_base = -0.22
        ax.text(-0.04, y_base, "At risk:", transform=ax.transAxes, fontsize=8, fontweight="bold", ha="right", va="center")
        ax.text(-0.04, y_base - 0.05, "High:", transform=ax.transAxes, fontsize=8, color="red", ha="right", va="center")
        ax.text(-0.04, y_base - 0.10, "Low:", transform=ax.transAxes, fontsize=8, color="blue", ha="right", va="center")

        for t_val, rh, rl in zip(eval_times, at_risk_high, at_risk_low):
            x_norm = t_val / max_t
            ax.text(x_norm, y_base, str(t_val), transform=ax.transAxes, fontsize=8, ha="center", va="center", color="gray")
            ax.text(x_norm, y_base - 0.05, str(rh), transform=ax.transAxes, fontsize=8, ha="center", va="center")
            ax.text(x_norm, y_base - 0.10, str(rl), transform=ax.transAxes, fontsize=8, ha="center", va="center")

        if idx % 2 == 0:
            ax.set_ylabel("Survival probability", fontsize=11)

    plt.subplots_adjust(hspace=0.60, wspace=0.15, bottom=0.20, top=0.92)
    plt.savefig("survival_curves_all_subjects1.png", dpi=300, bbox_inches="tight")
    print("Saved 'survival_curves_all_subjects1.png'")

if __name__ == "__main__":
    generate_km_curves()
