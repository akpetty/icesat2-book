# New functions used in the all-season notebooks

""" extra_funcs.py 

 New functions used in the all-season notebooks
"""

# Regular Python library imports 
import xarray as xr 
import numpy as np
import pandas as pd
import pyproj
import scipy.interpolate
import matplotlib.pyplot as plt
import glob
from datetime import datetime
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Interpolating/smoothing packages 
from scipy.interpolate import griddata
from scipy.spatial import KDTree
from astropy.convolution import convolve
from astropy.convolution import Gaussian2DKernel

def get_summer_data(da, year_start=None, start_month="May", end_month="Jul", force_complete_season=False):
    """ Select data for summer seasons corresponding to the input time range 
    
    Args: 
        da (xr.Dataset or xr.DataArray): data to restrict by time; must contain "time" as a coordinate 
        year_start (str, optional): year to start time range; if you want Sep 2019 - Apr 2020, set year="2019" (default to the first year in the dataset)
        start_month (str, optional): first month in winter (default to September)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
        
    Returns: 
        da_summer (xr.Dataset or xr.DataArray): da restricted to winter seasons 
    
    """
    if year_start is None: 
        print("No start year specified. Getting winter data for first year in the dataset")
        year_start = str(pd.to_datetime(da.time.values[0]).year)
    
    start_timestep = start_month+" "+str(year_start) # mon year 
    end_timestep = end_month+" "+str(year_start) # mon year
    summer = pd.date_range(start=start_timestep, end=end_timestep, freq="MS") # pandas date range defining winter season
    months_in_da = [mon for mon in summer if mon in da.time.values] # Just grab months if they correspond to a time coordinate in da

    if len(months_in_da) > 0: 
        if (force_complete_season == True) and (all([mon in da.time.values for mon in summer])==False): 
            da_summer = None
        else: 
            da_summer = da.sel(time=months_in_da)
    else: 
        da_summer = None
        
    return da_summer


def compute_gridcell_summer_means(da, years=None, start_month="May", end_month="Jul", force_complete_season=False): 
    """ Compute summer means over the time dimension. Useful for plotting as the grid is maintained. 
    
    Args: 
        da (xr.Dataset or xr.DataArray): data to restrict by time; must contain "time" as a coordinate 
        years (list of str): years over which to compute mean (default to unique years in the dataset)
        year_start (str, optional): year to start time range; if you want Nov 2019 - Apr 2020, set year="2019" (default to the first year in the dataset)
        start_month (str, optional): first month in winter (default to November)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
    
    Returns: 
        merged (xr.DataArray): DataArray with summer means as a time coordinate
    """
    
    if years is None: 
        years = np.unique(pd.to_datetime(da.time.values).strftime("%Y")) # Unique years in the dataset 

    summer_means = []
    for year in years: # Loop through each year and grab the summer months, compute winter mean, and append to list 
        da_summer_i = get_summer_data(da, year_start=year, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season)
        if da_summer_i is None: 
            continue
        da_mean_i = da_summer_i.mean(dim="time", keep_attrs=True) # Compute mean over time dimension

        # Assign time coordinate 
        time_arr = pd.to_datetime(da_summer_i.time.values)
        da_mean_i = da_mean_i.assign_coords({"time":time_arr[0].strftime("%b %Y")+" - "+time_arr[-1].strftime("%b %Y")})
        da_mean_i = da_mean_i.expand_dims("time")

        summer_means.append(da_mean_i)

    merged = xr.merge(summer_means) # Combine each summer mean Dataset into a single Dataset, with the time period maintained as a coordinate
    merged = merged[list(merged.data_vars)[0]] # Convert to DataArray
    merged.time.attrs["description"] = "Time period over which mean was computed" # Add descriptive attribute 
    return merged 



def add_time_dim_v3(xda):
    """ dummy function to just set current time as a new dimension to concat files over, change later! """
    xda = xda.set_coords(["latitude","longitude", "x", "y"])
    xda = xda.expand_dims(time = [datetime.now()])
    return xda

def read_IS2SITMOGR4S(version='V1', local_data_path="./data/IS2SITMOGR4_SUMMER/"): 
    """ Read in IS2SITMOGR4 summer monthly gridded thickness dataset from local netcdf files

    """
    
    print(local_data_path+version+'/*.nc')
    filenames = glob.glob(local_data_path+version+'/*.nc')
    if len(filenames) == 0: 
        raise ValueError("No files, exit")
        return None
    
    dates = [pd.to_datetime(file.split("IS2SIT_SUMMER_01_")[1].split("_")[0], format = "%Y%m")  for file in filenames]
    # Add a dummy time then add the dates I want, seemed the easiest solution
    is2_ds = xr.open_mfdataset(filenames, preprocess = add_time_dim_v3, engine='netcdf4')
            
    is2_ds["time"] = dates

    # Sort by time as glob file list wasn't!
    is2_ds = is2_ds.sortby("time")
    is2_ds = is2_ds.set_coords(["latitude","longitude","x","y"])
    
    is2_ds = is2_ds.assign_coords(longitude=(["y","x"], is2_ds.longitude.values))
    is2_ds = is2_ds.assign_coords(latitude=(["y","x"], is2_ds.latitude.values))
    
    is2_ds = is2_ds.assign_attrs(description="Aggregated IS2SITMOGR4 summer "+version+" dataset.")

    return is2_ds


def getCS2ubris(mapProj, dataPathCS2, dataset):
    """ Read in the University of Bristol CryoSat-2 sea ice thickness data

    
    Args:
        dataPathCS2 (str): location of data
        
    Returns
        xptsT (2d numpy array): x coordinates on our map projection
        yptsT (2d numpy array): y coordinates on our map projection
        thicknessCS (2d numpy array): monthly sea ice thickness estimates
        

    """
    ubris_f = xr.open_dataset(dataPathCS2+dataset, decode_times=False)

    # Issue with time starting from year 0!
    # Re-set it to start from some other year
    ubris_f = ubris_f.rename({'Time':'time'})
    ubris_f['time'] = ubris_f['time']-679352
    ubris_f.time.attrs["units"] = "days since 1860-01-01"
    decoded_time = xr.decode_cf(ubris_f)

    ubris_f['time']=decoded_time.time
    ubris_f = ubris_f.swap_dims({'t': 'time'})

    # Resample to monthly, note that the S just makes the index start on the 1st of the month
    thicknessCS = ubris_f.resample(time="MS").mean()
    xptsT, yptsT = mapProj(thicknessCS.isel(time=0).Longitude, thicknessCS.isel(time=0).Latitude)
    
    return xptsT, yptsT, thicknessCS


def regridToICESat2(dataArrayNEW, xptsNEW, yptsNEW, xptsIS2, yptsIS2):  
    """ Regrid new data to ICESat-2 grid 
    
    Args: 
        dataArrayNEW (xarray DataArray): Numpy variable array to be gridded to ICESat-2 grid 
        xptsNEW (numpy array): x-values of dataArrayNEW projected to ICESat-2 map projection 
        yptsNEW (numpy array): y-values of dataArrayNEW projected to ICESat-2 map projection 
        xptsIS2 (numpy array): ICESat-2 longitude projected to ICESat-2 map projection
        yptsIS2 (numpy array): ICESat-2 latitude projected to ICESat-2 map projection
    
    Returns: 
        gridded (numpy array): data regridded to ICESat-2 map projection
    
    """
    #gridded = []
    #for i in range(len(dataArrayNEW.values)): 
    #gridded = scipy.interpolate.griddata((xptsNEW.flatten(),yptsNEW.flatten()), dataArrayNEW.flatten(), (xptsIS2, yptsIS2), method = 'nearest')
    try:
        #print('try method 1...')
        gridded = scipy.interpolate.griddata((xptsNEW.flatten(),yptsNEW.flatten()), dataArrayNEW.flatten(), (xptsIS2, yptsIS2), method = 'nearest')
    except:
        try:
            #print('Did not work, try method 2..')
            gridded = scipy.interpolate.griddata((xptsNEW,yptsNEW), dataArrayNEW, (xptsIS2, yptsIS2), method = 'nearest')
        except:
            print('Error interpolating..')
    
    return gridded


def regrid_ubris_to_is2(mapProj, xIS2, yIS2, out_lons, out_lats, date_range, dataPathCS2='/home/jovyan/Data/CS2/UIT/', dataset='ubristol_cryosat2_seaicethickness_nh_80km_v1p7.nc'):
    """
    Regrid UBRIS data to ICESat-2 grid

    Args:
        mapProj (Basemap): Basemap projection object
        xIS2 (numpy array): ICESat-2 x-coordinates
        yIS2 (numpy array): ICESat-2 y-coordinates
        out_lons (numpy array): Output longitudes
        out_lats (numpy array): Output latitudes
        date_range (list of str): List of dates to process
        dataPathCS2 (str, optional): Path to CryoSat-2 data (default is '/home/jovyan/Data/CS2/UIT/')
        dataset (str, optional): Dataset filename (default is 'ubristol_cryosat2_seaicethickness_nh_80km_v1p7.nc')

    Returns:
        cs2_ubris (xarray Dataset): Regridded UBRIS data on ICESat-2 grid
    """


    xptsIS2, yptsIS2 = np.meshgrid(xIS2, yIS2)


    cs2_ubris = []
    valid_dates=[]

    xptsT_ubris, yptsT_ubris, cs2_ubris_raw = getCS2ubris(mapProj, dataPathCS2, dataset)
    
    for date in date_range:
        #print(date)
        try:
            cs2_ubris_temp_is2grid = regridToICESat2(cs2_ubris_raw.Sea_Ice_Thickness.sel(time=date).values, xptsT_ubris, yptsT_ubris, xptsIS2, yptsIS2) 
            ice_conc_is2grid = regridToICESat2(cs2_ubris_raw.Sea_Ice_Concentration.sel(time=date).values, xptsT_ubris, yptsT_ubris, xptsIS2, yptsIS2)     
            #cs2_ubris_temp_is2grid[ice_conc_is2grid<0.5]=np.nan
            
            cs2_ice_type_is2grid = regridToICESat2(cs2_ubris_raw.Sea_Ice_Type.sel(time=date).values, xptsT_ubris, yptsT_ubris, xptsIS2, yptsIS2) 
            cs2_ice_density_is2grid = 917. - (cs2_ice_type_is2grid * (917. - 882.))

        except:
            print(date)
            print('no CS-2 data or issue with gridding, so skipping...')
            continue
        valid_dates.append(date)

        cs2_ubris_temp_is2grid_xr = xr.Dataset({'cs2_sea_ice_thickness_UBRIS': (('y', 'x'), cs2_ubris_temp_is2grid), 
                                'cs2_sea_ice_type_UBRIS': (('y', 'x'), cs2_ice_type_is2grid), 
                                'cs2_sea_ice_density_UBRIS': (('y', 'x'), cs2_ice_density_is2grid)}, 
                                coords = {'latitude': (('y','x'), out_lats), 'longitude': (('y','x'), out_lons), 'x': (('x'), xIS2),  'y': (('y'), yIS2)} 
                                )
        
        cs2_ubris.append(cs2_ubris_temp_is2grid_xr)

    cs2_ubris = xr.concat(cs2_ubris, 'time')
    #cs2_ubris = cs2_ubris.assign_coords(time=valid_dates)
    cs2_ubris_attrs = {'units': 'meters', 'long_name': 'University of Bristol CryoSat-2 Arctic sea ice thickness', 'data_download': 'https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01613', 
            'download_date': '09-2022', 'citation': 'Landy, J.C., Dawson, G.J., Tsamados, M. et al. A year-round satellite sea-ice thickness record from CryoSat-2. Nature 609, 517–522 (2022). https://doi.org/10.1038/s41586-022-05058-5'} 
    cs2_ubris = cs2_ubris.assign_coords(time=valid_dates)
    cs2_ubris = cs2_ubris.assign_attrs(cs2_ubris_attrs)  

    return cs2_ubris

def get_cs2is2_snow(mapProj, xIS2, yIS2, dataPathCS2='./data/uit_cs2-is2-ak_snow_depth_25km_v3.nc'):
    """
    Load, process and regrid CS2-IS2 snow depth data to the IS2 grid for winter months between 2018-2023.
    
    This function:
    1. Creates a time array for winter months (Oct-Apr) from 2018-2023
    2. Loads CS2-IS2 snow depth data from a netCDF file
    3. Regrids the data to match the IS2 grid coordinates
    4. Returns the regridded data as an xarray DataArray
    
    Parameters
    ----------
    mapProj : function
        Map projection function to convert lat/lon to x/y coordinates
    xIS2 : numpy.ndarray
        1D array of x-coordinates for the IS2 grid
    yIS2 : numpy.ndarray
        1D array of y-coordinates for the IS2 grid
    dataPathCS2 : str, optional
        Path to the CS2-IS2 snow depth netCDF file
        Default is './data/uit_cs2-is2-ak_snow_depth_25km_v3.nc'
    
    Returns
    -------
    xarray.DataArray
        Regridded snow depth data with dimensions:
        - time: winter months from 2018-2023
        - y: IS2 grid y-coordinates
        - x: IS2 grid x-coordinates
        
    Notes
    -----
    Winter season is defined as October through April of the following year.
    The data is regridded from the original CS2 grid to the IS2 grid using
    the regridToICESat2 function.
    """
    
    # Create date range for Oct-Apr periods from 2018-2023
    dates = []
    for year in range(2018, 2023):
        # October to December of current year
        dates.extend(pd.date_range(start=f'{year}-10-01', end=f'{year}-12-31', freq='MS'))
        # January to April of next year
        dates.extend(pd.date_range(start=f'{year+1}-01-01', end=f'{year+1}-04-30', freq='MS'))

    # Convert to numpy datetime64 array
    dates_cs2is2 = np.array(dates, dtype='datetime64[ns]')

    # Get the IS-2/CS-2 snow depths
    xptsIS2, yptsIS2 = np.meshgrid(xIS2, yIS2)
    

    cs2is2_snow = xr.open_dataset(dataPathCS2, decode_times=False)
    xptsT_ubris, yptsT_ubris = mapProj(cs2is2_snow.isel(t=0).Longitude, cs2is2_snow.isel(t=0).Latitude)

    cs2is2_snow_regridded = []
    for t in cs2is2_snow.t.values:
        #print(t)
        cs2is2_snow_is2grid = regridToICESat2(cs2is2_snow.sel(t=t).Snow_Depth_KuLa.values, 
                                                xptsT_ubris, yptsT_ubris, xptsIS2, yptsIS2) 
        cs2is2_snow_regridded.append(cs2is2_snow_is2grid)
    # Convert list to numpy array with proper dimensions
    cs2is2_snow_regridded_array = np.array(cs2is2_snow_regridded)

    # Create a new DataArray with the regridded data
    cs2is2_snow_regridded_da = xr.DataArray(
        cs2is2_snow_regridded_array,
        dims=['time', 'y', 'x'],
        coords={
            'time': dates_cs2is2,
            'y': yIS2,
            'x': xIS2
        },
        name='cs2is2_snow_depth'
    ) 
    cs2is2_snow_regridded_da  

    return cs2is2_snow_regridded_da

def apply_interpolation_time(dataset_og, xptsIS2, yptsIS2, variables, force_copy=False, method = "linear"):
    # Apply interpolation to all data for consistency
    # Interpolation settings 
    # Force copy is used to force a copy of the data to be made, otherwise the data will not be overwritten if already exists
    # Create a copy of the dataset to avoid modifying the original
    dataset = dataset_og.copy(deep=True)

    
    for var in variables:
        if var+'_int' not in dataset or force_copy:
            print(f'Creating/forcing new variable {var}_int')
            dataset[var+'_int'] = xr.DataArray(
                data=np.full_like(dataset[var].values, np.nan),
                dims=dataset[var].dims,
                coords=dataset[var].coords
            )
        # Loop over each time step
        for time_index in range(dataset.dims['time']):

            print(var, time_index)# Perform linear interpolation for the current time step
            try:
                is2_to_interp = dataset[var].isel(time=time_index).values
                is2_to_interp[np.where(dataset.sea_ice_conc.isel(time=time_index) < 0.15)] = 0  # Set 15% conc or less to 0 thickness
                np_interpolated = griddata((xptsIS2[(np.isfinite(is2_to_interp))], 
                                            yptsIS2[(np.isfinite(is2_to_interp))]), 
                                            is2_to_interp[(np.isfinite(is2_to_interp))].flatten(),
                                            (xptsIS2, yptsIS2), 
                                            fill_value=np.nan,
                                            method=method)
                np_interpolated[~(np.isfinite(dataset.sea_ice_conc.isel(time=time_index)))] = np.nan  # Remove thickness data where cdr data is nan 
                np_interpolated[np.where(dataset.sea_ice_conc.isel(time=time_index) < 0.5)] = np.nan  # Remove thickness data where cdr data < 50% concentration

                x_stddev = 0.5
                kernel = Gaussian2DKernel(x_stddev=x_stddev)
                np_interpolated_gauss = convolve(np_interpolated, kernel)
                np_interpolated_gauss[~(np.isfinite(dataset.sea_ice_conc.isel(time=time_index)))] = np.nan  # Remove thickness data where cdr data is nan 
                np_interpolated_gauss[np.where(dataset.sea_ice_conc.isel(time=time_index) < 0.5)] = np.nan  # Remove thickness data where cdr data < 50% concentration
                
                #print(np_interpolated_gauss.shape)
                # Ensure the data is in the correct shape
                #np_interpolated_gauss = np_interpolated_gauss[np.newaxis, :, :]  # Add a new axis for time

                # Add the interpolated data to the new dataset
                # Update the data using loc indexer
                #dataset[var+'_int'] = dataset[var+'_int'].copy(deep=True)
                dataset[var+'_int'][dict(time=time_index)] = np_interpolated_gauss
                print('Interpolated.')

            except:
                print('no data or issue with gridding, so skipping...')
                dataset[var+'_int'].isel(time=time_index)[:] = np.full(dataset[var+'_int'].isel(time=time_index)[:].shape, np.nan)
                continue
    print('done, returning new dataset')
    return dataset

def apply_interpolation_timestep(IS2_CS2_allseason, xptsIS2, yptsIS2, variables):
    # Apply interpolation to all data for consistency
    # Interpolation settings 
    method = "linear" 

    # Create a new dataset to store the interpolated values
    IS2_CS2_allseason_int = IS2_CS2_allseason.copy(deep=True)

    for var in variables:
        print(var)# Perform linear interpolation for the current time step
        #try:
        is2_to_interp = IS2_CS2_allseason[var].values.copy()
        is2_to_interp[np.where(IS2_CS2_allseason.sea_ice_conc < 0.15)] = 0  # Set 15% conc or less to 0 thickness
        np_interpolated = griddata((xptsIS2[(np.isfinite(is2_to_interp))], 
                                    yptsIS2[(np.isfinite(is2_to_interp))]), 
                                    is2_to_interp[(np.isfinite(is2_to_interp))].flatten(),
                                    (xptsIS2, yptsIS2), 
                                    fill_value=np.nan,
                                    method=method)
        np_interpolated[~(np.isfinite(IS2_CS2_allseason.sea_ice_conc))] = np.nan  # Remove thickness data where cdr data is nan 
        np_interpolated[np.where(IS2_CS2_allseason.sea_ice_conc < 0.5)] = np.nan  # Remove thickness data where cdr data < 50% concentration

        x_stddev = 0.5
        kernel = Gaussian2DKernel(x_stddev=x_stddev)
        np_interpolated_gauss = convolve(np_interpolated, kernel)
        np_interpolated_gauss[~(np.isfinite(IS2_CS2_allseason.sea_ice_conc))] = np.nan  # Remove thickness data where cdr data is nan 
        np_interpolated_gauss[np.where(IS2_CS2_allseason.sea_ice_conc < 0.5)] = np.nan  # Remove thickness data where cdr data < 50% concentration
        print('Interpolated.')
        print(np_interpolated_gauss.shape)
        # Ensure the data is in the correct shape
        #np_interpolated_gauss = np_interpolated_gauss[np.newaxis, :, :]  # Add a new axis for time

        # Add the interpolated data to the new dataset
        IS2_CS2_allseason_int[var+'_int'][:] = np_interpolated_gauss
        #except:
        #    print('no data or issue with gridding, so skipping...')
        #    #IS2SITMOGR4_v3[var].isel(time=time_index)[:] = np.full(np_interpolated_gauss.shape, np.nan)
        #    continue
    return IS2_CS2_allseason_int