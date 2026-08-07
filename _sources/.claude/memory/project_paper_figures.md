---
name: Paper figure inventory and LaTeX labels
description: Mapping of paper/figures/ PNGs (from 11-series notebooks) to LaTeX figure labels, plus placeholder figures for methods, in the IS2SMGPSIT-V1 paper
type: project
---

All figures in paper/paper.tex are either (a) notebook-generated PNGs from paper/figures/, or
(b) placeholder \todo environments for figures not yet made. Compiles cleanly (25 pages).

**Rule:** Only include PNGs that were saved by the 11_* notebooks via `plt.savefig('../paper/figures/...')`.
Non-notebook figures (GPSat_*, combined_thickness_map_*, expert_location_*, prediction_expert_*) should NOT have \includegraphics commands — they use \todo placeholders instead.

**Placeholder figures (no file yet, \todo in body):**
- `fig:expert_grid` — local-expert architecture schematic (Section 3.2)
- `fig:hyperparameters` — spatially distributed GP hyperparameters (Section 3.2)
- `fig:data_fusion_illustration` — IS2 + SMOS/SMAP fusion illustration (Section 3.3)
- `fig:timeseries_panArctic` — pan-Arctic mean SIT time series (Section 4.1); save from 11a Cell 16 with `plt.savefig('../paper/figures/timeseries_panArctic.png', dpi=300)`
- `fig:bgep_anomaly_ts` — currently uses BGEP_V4_vs_V1_timeseries.png (raw drafts); proper BGEP anomaly figure is in 11c `./figs/BGEP_V4_fused_daily_timeseries_subseasonal.png` — copy to paper/figures/ when ready

**Notebook-generated figures (label → filename → source notebook):**
- `fig:spatial_comparison` → inner_arctic_seasonal_thickness_comparison_nov2019 + march2020 (11a, Section 4.1)
- `fig:snow_comparison` → inner_arctic_seasonal_snow_depth_comparison_march2020 (11a, Section 4.1)
- `fig:timeseries_IAO` → inner_arctic_seasonal_thickness_freeboard_snowdepth_comparison (11a, Section 4.1)
- `fig:thickness_anomalies` → pan_arctic_seasonal_thickness_anomalies (11a, Section 4.1)
- `fig:bgep_anomaly_ts` → BGEP_V4_vs_V1_timeseries (11b, Section 4.2) — raw drafts, update later
- `fig:bgep_scatter_monthly` → BGEP_V4_vs_V1_scatter (11b, Section 4.3)
- `fig:bgep_scatter_daily` → BGEP_V4_vs_V1_daily_scatter (11c, Section 4.3)
- `fig:bgep_scatter_anomaly` → BGEP_V4_vs_V1_daily_scatter_subseasonal (11c, Section 4.3)
- `tab:windows` → `paper/tables/bgep_validation_by_window_rows.tex` (11c; monthly rows from 11b). Retired weekly notebook: `11d_comparisons_with_BGEP_weekly.ipynb`
- `fig:window_sweep` → BGEP_anomaly_r2_vs_window (11c; promoted from supplement)
- `fig:mosaic_scatter` → MOSAIC_V4_vs_V1_daily_scatter_thickness + snow (11x1)
- `fig:volume` → arctic_sea_ice_volume_timeseries (11d, Section 4.5) — verify CAA mask applied
- `fig:volume_anomalies` → arctic_sea_ice_volume_anomalies (11d, Section 4.5)
