<!-- #region -->
ICESat-2 Sea Ice State Analysis Jupyter Book
=============================================

**View this Jupyter Book (including options to run the code interactively!) in our Jupyter Book:** http://www.icesat-2-sea-ice-state.info

## Contributors

**Alek Petty (Current repository lead, summer 2022 onwards)**<br>
[![GitHub](https://badgen.net/badge/icon/github?icon=github&label)](https://github.com/akpetty) 

**Nicole Keeney (Original repository creator)**<br>
[![GitHub](https://badgen.net/badge/icon/github?icon=github&label)](https://github.com/nicolejkeeney)


# Update history  

 - 9/4/2020: Version 1
 - 11/18/2020: Updated with version 2 ICESat-2 data product for [AGU Fall 2020 poster highlighting the book](https://ui.adsabs.harvard.edu/abs/2020AGUFMC014.0012K/abstract). 
 - 6/14/2021: Transitioned from Google Colab interactivity to Binder. 
 - 10/25/2021: Added interactive plotting using hvplot. Improved interpolation/smoothing method for ICESat-2 data and added notebook to demonstrate steps. 
 - 01/24/2022: Updated notebooks to reflect new data variables in ICESat-2 data v2. Added drift vectors. 
 - 08/15/2022: Forked to akpetty and linked to a new domain (icesat-2-sea-ice-state.info). Re-designed to reflect continued analysis of both the gridded and along-track thickness data. 
 - 11/01/2022: included new CryoSat-2 and BGEP comparison notebooks.
 - 12/01/2022: upgraded the conda environment and included a new AWS S3 bucket data link, including zarr data (no download needed)
 - 12/06/2023: Added the new 2022-2023 winter analysis notebook which also describes the new Version 3 IS2SITMOGR4 dataset. Updated the read dataset function. A few other little minor bug fixes.
 - 02/14/2025: Added the new 2023-2024 winter analysis notebook. More updates to the read dataset function (mainly hard-coding the zarr links). A few other little minor bug fixes.
 - 09/25/2025: Update the books based on peer review (added in MERRA-2/SM-LG snow loading and derived thicknesses, bug fixes etc).

If you find any issues in the code or have any suggestions for the book, feel free to open an issue, which you can find by mousing over the GitHub icon at the top of each page. If you are familiar with GitHub, you can also fork the book's repository and suggest an edit that way. 

# New Virtual Env approach: UV (a better faster package manager)
For faster package installation and better dependency resolution compared to conda, I've now switched to UV. UV is significantly faster than conda and handles Python package management more efficiently.

## Prerequisites
Install UV first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Creating the UV Environment
NB: It's best to make this in the directory above the jupyter book as I've had issues with the build executing the notebooks in that env folder..
```bash
# Navigate to the parent directory (one level above icesat2-book)
cd ..

# Create environment with Python 3.9
uv venv --python 3.9 is2book_uv_env

# Activate the environment
# If you're in the parent directory:
source is2book_uv_env/bin/activate  # On macOS/Linux
# or
is2book_uv_env\Scripts\activate    # On Windows

# If you're in the icesat2-book directory, use:
source ../is2book_uv_env/bin/activate  # On macOS/Linux
# or
..\is2book_uv_env\Scripts\activate    # On Windows

# Install packages (from icesat2-book directory)
cd icesat2-book
uv pip install -r requirements.txt

# Verify jupyter-book is installed
uv run jb --help
```

## Adding as Jupyter Kernel
To use this environment in Jupyter notebooks:
```bash
# Activate the environment first
# If in parent directory:
source is2book_uv_env/bin/activate
# If in icesat2-book directory:
source ../is2book_uv_env/bin/activate

# Install as Jupyter kernel
python -m ipykernel install --user --name is2book_uv_env --display-name "ICESat-2 Book (UV)"
```

**Note**: Some geospatial packages (cartopy, rasterio) may require system-level libraries (GEOS, PROJ, GDAL). Install these with your system package manager if needed.

## Building the Book
To build the Jupyter Book using the UV environment:
```bash
# Activate the environment
# If in parent directory:
source is2book_uv_env/bin/activate
# If in icesat2-book directory:
source ../is2book_uv_env/bin/activate

# Build the book (from parent directory)
jb build icesat2-book

# Or use uv run (if jb is available)
uv run jb build icesat2-book
```

# OG ENV approach: Conda environments
This book still has an associated conda environment stored in the file environment.yml. This file can be downloaded and used to set up the environment on your local computer so that you have all the required dependencies needed to run the notebooks. You'll need anaconda and python installed on your computer first. The environment file is also required by Binder in order to set up the computational environment for running the notebooks in the book interactively. <br><br> 
To create the environment, run the following in the command line: 
```
conda env create -f environment.yml
```
To activate the environment, run the following in the command line: 
```
conda activate is2book_p39_env
```
Note that there was an issue with ipykernal in the 6.18.1 upgrade hence our use of ipykernel=6.17.1 in the conda environment. Users have also noted some issues with conda and the boto3/s3fs packages. I'm still working on that so either try and fix yourself with further conda installs or drop the s3 imports/read options from your cloned repository.

Update (02/14/25): I noticed some issues with cartopy and needed to reinstall shapely. Unsure what exactly changed, but I now also provide the complete conda environment I am currently using if that helps:
```
conda env create -f environment_021425.yml
```
I'm trying to move away from conda now, so these methods are no longer supported..!

# Updating the Jupyter Book
Simple instructions for how to construct/update this book are pasted below for the author's benefit, but don't go into detail on any of the steps. For a more detailed description on Jupyter Books and how to build one of your own, see their page: https://jupyterbook.org/intro.html. <br>

1. **Activate the UV environment:**
   ```bash
   # If in parent directory:
   source is2book_uv_env/bin/activate
   # If in icesat2-book directory:
   source ../is2book_uv_env/bin/activate
   ```
2. **Update the GitHub repository with any changes:**
   ```bash
   # Commit and push any changes to the repository
   git add .
   git commit -m "Your commit message"
   git push
   ```
3. **Build the book (from parent directory):**
   ```bash
   # Navigate to parent directory if not already there
   cd ..
   
   # Build the book - each notebook will be executed and outputs cached in the build folder
   jb build icesat2-book
   ```

4. **Update the GitHub Pages site:**
   ```bash
   # Navigate back to the book directory
   cd icesat2-book
   
   # Deploy the built HTML to GitHub Pages
   ghp-import -n -p -c www.icesat-2-sea-ice-state.info _build/html
   ```
   The `-c` flag automatically creates/updates the CNAME file with your custom domain, so you won't need to manually update the DNS settings in GitHub anymore.
