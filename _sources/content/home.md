<!-- #region -->
ICESat-2 Sea Ice State Analysis
============================================= 

## Background 

NASA's Ice, Cloud, and Land Elevation Satellite-2 ([ICESat-2](https://icesat-2.gsfc.nasa.gov/)) has been providing high resolution laser altimetry profiling of the entire Earth's surface - particularly over the fast-changing Polar Regions - since its launch in the fall of 2018. 

The ICESat-2 Project Science Office has produced and disseminated a number of official datasets through the National Snow and Ice Data Center [(NSIDC)](https://nsidc.org/data/icesat-2) including the Arctic and Southern Ocean sea ice freeboard dataset [(ATL10)](https://nsidc.org/data/ATL10)  dataset, which provides along-track estimates of the extension of sea ice above the local sea surface for each of the six beams of ICESat-2. 

Using assumptions regarding the depth and density of the snow layer on top of the ice, along with estimates of the density of the sea ice itself,  ICESat-2 freeboard data can be converted to an estimate of sea ice thickness. Estimates of Winter Arctic sea ice thickness using snow loading from the NASA Eulerian Snow on Sea Ice Model [(NESOSIM)](https://github.com/akpetty/NESOSIM) have been produced and disseminated through the NSIDC (https://nsidc.org/data/IS2SITMOGR4). More information about the methodology behind this dataset can be found in the [original paper](http://www.alekpetty.com/papers/petty2020). 


Since its launch in 2018, ICESat-2 has now collected and analyzed data over four winter seasons across the entire Arctic Ocean. A [manuscript is currently in review](https://tc.copernicus.org/preprints/tc-2022-39/) regarding the analysis of the first three winters of data collected  which was the original motivation behind the creation of this Jupyter Book.

![ICESat-2 maps](figs/maps_thickness_winter.png "ICESat-2 mean winter Arctic sea ice thickness - REPLACE WITH UPDATED BASIC INTERACTIVE PLOT?")

Our goal going forward is to continue to update this book as new data is produced and to share additional analyses of the sea ice state using the incredible data collected by ICESat-2. 


## Jupyter Book description
[Jupyter Books](https://jupyterbook.org/intro.html) provide a novel means of compiling various related Jupyter Notebooks into one convenient and well-indexed location. Here, a series of Jupyter Notebooks are used to provide a visual demonstration of our efforts to analyze winter Arctic sea ice conditions, primiarly freeboard and thickness, derived from ICESat-2 data, along with other relevant datasets.

We have also set up the book so that users can easily run the code without needing to download anything by using the hosting service called Binder. To run a notebook (chapter pages in the book) in Binder, just click the **Binder** tab under the rocket ship icon at the top of each notebook. This option is configured for all notebooks except the modules in the Helper Functions section and the data wrangling notebook. 

## Accessing the data 
The monthly gridded ICESat-2 winter Arctic sea ice thickness data are archived and made publically available at the NSIDC (https://nsidc.org/data/IS2SITMOGR4). However, to simply our analysis we have also uploaded these same data to a [google cloud storage bucket](https://console.cloud.google.com/storage/browser/sea-ice-thickness-data/IS2SITMOGR4/v002). We have also generated and uploaded a single netcdf file containing all the data presented in this Jupyter Book in the same bucket under the name `icesat2-book-data.nc`. This dataset contains all the gridded ICESat-2 sea ice thickness data along with all other datasets used in the notebook to help contextualize the sea ice and atmospheric conditions through each winter. All datasets included have been regridded to the same NSIDC North Polar Sterographic grid (the native grid of the ICESat-2 sea ice data used), to simplify the mapping and comparisons. See the Data Wrangling page for more information each dataset and on on the regridding process.

## Packages 
All of the notebooks in this notebook utilize [xarray](http://xarray.pydata.org/en/stable/), a python package built for working with multi-dimensional data like the monthly gridded sea ice data. Xarray is especially useful for time series data and allows for easily plotting data on map projections via compatability with the python packages cartopy and hvplot. 

## License

All content in this Jupyter Book is distributed under the MIT license.  

## Contributors

**Alek Petty (Current repository lead, summer 2022 onwards)**<br>
[![GitHub](https://badgen.net/badge/icon/github?icon=github&label)](https://github.com/akpetty) 

**Nicole Keeney (Original repository creator)**<br>
[![GitHub](https://badgen.net/badge/icon/github?icon=github&label)](https://github.com/nicolejkeeney)

## References

Petty, A. A., N. T. Kurtz, R. Kwok, T. Markus, T. A. Neumann (2020), Winter Arctic sea ice thickness from ICESat‐2 freeboards, Journal of Geophysical Research: Oceans, 125, e2019JC015764. doi:10.1029/2019JC015764

Petty A. A., N. Keeney, A. Cabaj, P. Kushner, M. Bagnardi (2022), Winter Arctic sea ice thickness from ICESat-2: upgrades to freeboard and snow loading estimates and an assessment of the first three winters of data collection, The Cryosphere Discuss (preprint), doi: 10.5194/tc-2022-39.
 
