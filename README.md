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
For faster package installation and better dependency resolution comapred to conda, I've now switched to UV. UV is significantly faster than conda and handles Python package management more efficiently.

## Prerequisites
Install UV first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Creating the UV Environment
```bash
# Create environment with Python 3.9
uv venv --python 3.9 is2book_uv_env

# Activate the environment
source is2book_uv_env/bin/activate  # On macOS/Linux
# or
is2book_uv_env\Scripts\activate    # On Windows

# Install packages
uv pip install -r requirements.txt
```

## Adding as Jupyter Kernel
To use this environment in Jupyter notebooks:
```bash
# Activate the environment first
source is2book_uv_env/bin/activate

# Install as Jupyter kernel
python -m ipykernel install --user --name is2book_uv_env --display-name "ICESat-2 Book (UV)"
```

**Note**: Some geospatial packages (cartopy, rasterio) may require system-level libraries (GEOS, PROJ, GDAL). Install these with your system package manager if needed.

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
1. Activate virtual environment associated with book
2. Update github repository with any changes 
3. cd out of local book directory into the next highest directory
4. Next you'll need to construct the html files that make up the pages in the book. Each notebook will be executed and the outputs will be cached in the build folder. In the commmand line, run: 
```
jb build icesat2-book
```
5. Move back cd local book directory... There must be a way to do this without changing in and out of the book directory, but if there is, it's not very intuitive. 
```
cd icesat2-book
```
7. Next you'll update the github page associated with all the html files. You won't be able to see any of the changes to the webpage hosting the book until you do this. In the command line, run: 
```
ghp-import -n -p -f _build/html
```
I'm having some issues with this so in the latest version I pip installed this package to my base environment and ran this from there.

Finally, if serving onto a custom domain you may need to go into the GitHub settings (Settings/Pages) and make sure it's pointing to the right custom domain and is indicating DNS check successful.
