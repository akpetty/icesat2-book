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
If you find any typos or errors in the code or have any suggestions for the book, feel free to open an issue, which you can find by mousing over the GitHub icon at the top of each page. If you are familiar with GitHub, you can also fork the book's repository and suggest an edit that way. 
 - 9/4/2020: Version 1
 - 11/18/2020: Updated with version 2 ICESat-2 data product for [AGU Fall 2020 poster highlighting the book](https://ui.adsabs.harvard.edu/abs/2020AGUFMC014.0012K/abstract). 
 - 6/14/2021: Transitioned from Google Colab interactivity to Binder. 
 - 10/25/2021: Added interactive plotting using hvplot. Improved interpolation/smoothing method for ICESat-2 data and added notebook to demonstrate steps. 
 - 01/24/2022: Updated notebooks to reflect new data variables in ICESat-2 data v2. Added drift vectors. 
 - 08/15/2022: Forked to akpetty and linked to a new domain (icesat-2-sea-ice-state.info). Re-designed to reflect continued analysis of both the gridded and along-track thickness data. 
 - 11/01/2022: included new CryoSat-2 and BGEP comparison notebooks.
  - 12/01/2022: upgraded the conda environment and included a new AWS S3 bucket data link, including zarr data (no download needed)

# Activating the conda environment 
This book has an associated conda environment stored in the file environment.yml. This file can be downloaded and used to set up the environment on your local computer so that you have all the required dependencies needed to run the notebooks. You'll need anaconda and python installed on your computer first. The environment file is also required by Binder in order to set up the computational environment for running the notebooks in the book interactively. <br><br> 
To create the environment, run the following in the command line: 
```
conda env create -f environment.yml
```
To activate the environment, run the following in the command line: 
```
conda activate is2book_p39_env
```

note there was an issue with ipykernal in the 6.18.1 upgrade hence our use of ipykernel=6.17.1 in the conda environment.

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
