# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

This is a **Jupyter Book** (Sphinx-based) that compiles scientific Jupyter Notebooks analyzing Arctic sea ice thickness from ICESat-2 satellite data. The live site is at http://www.icesat-2-sea-ice-state.info. It is not a Python package — there are no tests, no `setup.py`, and no CI pipeline.

## Key Commands

**Build the book** (run from the *parent* directory of `icesat2-book`):
```bash
jb build icesat2-book
```

**Deploy to GitHub Pages** (run from inside `icesat2-book`):
```bash
ghp-import -n -p -c www.icesat-2-sea-ice-state.info _build/html
```

**Environment setup (UV — preferred):**
```bash
# From parent directory
uv venv --python 3.9 is2book_uv_env
source ../is2book_uv_env/bin/activate  # from inside icesat2-book
uv pip install -r requirements.txt
python -m ipykernel install --user --name is2book_uv_env --display-name "ICESat-2 Book (UV)"
```

**Legacy Conda environment:**
```bash
conda env create -f environment_021425.yml
conda activate is2book_p39_env
```

## Architecture

### Configuration
- `_config.yml` — Jupyter Book / Sphinx settings (execution policy, theme, analytics, excluded notebooks)
- `_toc.yml` — Book structure / table of contents (defines which notebooks appear and in what order)

### Content (`content/`)
Notebooks are grouped into thematic series by filename prefix:
- `1_*` — Introduction to the IS2SITMOGR4 dataset
- `2_*` — Annual winter Arctic sea ice thickness update notebooks (one per winter season)
- `3–5_*` — Comparisons with CryoSat-2, PIOMAS, BGEP, and atmospheric reanalysis (Petty et al. 2023)
- `6_*` — Interactive visualizations
- `7–9_*` — Data wrangling and interpolation demos
- `10_*` — All-season (summer + winter) analysis
- `11_*` — IS2-SMOS-SMAP data fusion notebooks

### Utilities (`content/utils/`)
Three shared Python modules imported by most notebooks:
- **`read_data_utils.py`** — All data loading. `read_IS2SITMOGR4()` is the main entry point; supports local netcdf, S3 netcdf download, or S3 Zarr (v3/v4). `read_is2smgpsitv1_zarr()` loads IS2-SMOS-SMAP fused data. Data is never bundled in the repo — it is fetched from S3 anonymously via `s3fs`.
- **`plotting_utils.py`** — Cartopy/Matplotlib map generation, `get_winter_data()` for seasonal subsetting, `compute_gridcell_winter_means()` for seasonal averaging.
- **`extra_funcs.py`** — All-season counterpart to `plotting_utils`: `get_summer_data()`, `compute_gridcell_summer_means()`, interpolation/smoothing helpers.

### Data flow
1. Notebooks call `read_IS2SITMOGR4()` → returns an `xarray.Dataset` backed by Dask (Zarr) or in memory (netcdf).
2. All datasets are regridded to the **NSIDC North Polar Stereographic** grid (IS2SITMOGR4's native grid) before comparison.
3. Figures are written to `content/figs/` (gitignored); data cached to `content/data/` (gitignored).

### Notebook execution at build time
Most notebooks are **excluded from execution** in `_config.yml` (their pre-run outputs are committed). Only notebooks missing a cache entry are re-executed. Execution timeout is 1000 s. The cache lives in `.jupyter_cache/`.

## Active Paper (paper/)

The `paper/` directory (gitignored) contains a draft manuscript targeting *The Cryosphere* (Copernicus):

> **"A daily gridded Arctic sea ice thickness and volume dataset from fused ICESat-2 and SMOS/SMAP observations using Gaussian process regression"**
> Petty, Cardinale, Tsamados, Spreen

The paper describes **IS2SMGPSIT-V1** — the dataset that the `11_*` notebooks analyze. Key details:
- Pan-Arctic, 25 km, daily gridded sea ice thickness spanning Nov 2018–Apr 2025 (7 growth seasons, Sep–Apr only)
- Produced by fusing ICESat-2 along-track thickness with SMOS/SMAP thin-ice thickness using Gaussian process (GP) regression in the [GPSat](https://github.com/...) framework
- GPSat uses a local-expert architecture: 200 km expert grid, ±30-day temporal window, Matérn-3/2 kernel with SGPR (500 inducing points)
- SMOS/SMAP data coarsened ×4, clipped to 0–0.5 m, Central Arctic excluded; CDR SIC pseudo-observations added at ice edge
- Output: per-grid-cell thickness + uncertainty; monthly NetCDF and single Zarr store on S3
- Validated against BGEP ULS moorings: $r^2=0.89$, RMSE=0.21 m (vs. IS2SITMOGR4-V4: $r^2=0.84$, RMSE=0.25 m)
- Several `\todo{}` items remain in the paper (SMOS/SMAP coarsen factor confirmation, CDR version, figure insertion, S3 URLs)

Compile the paper with: `pdflatex → bibtex → pdflatex → pdflatex` (uses `copernicus.cls` in `paper/`).

## V4 Data Notes
IS2SITMOGR4 V4 has static variables (`grid_cell_area`, `region_mask`, etc.) without a time dimension. `read_IS2SITMOGR4()` drops the time coordinate from those variables and shifts the time coordinate from the 15th to the 1st of each month for consistency with V3.
