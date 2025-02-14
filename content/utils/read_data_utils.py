# # Functions for reading data
# For the Jupyter Book - this is a markdown rendering of the `read_data_utils` module used in the notebooks. It is provided here for user reference, and may not reflect any changes to the code after 12/15/2021. The code can be viewed and downloaded from the github repository.

# +
""" read_data_utils.py 

Helper functions for reading ICESat2 data from a local drive and the book netcdf file from the google storage bucket

"""

import os 
import xarray as xr 
import pandas as pd 
import s3fs
import glob
from datetime import datetime

# -

def read_ISSITGR4(version='001', local_data_path="/data/ISSITGR4/"): 
    """ Read in ISSITGR4 campaign gridded thickness dataset from local netcdf files
    
    Args: 
        version (str, required): ISSITGR4 version (default "001")
        local_data_path (str, required): local data directory

    Returns: 
        is_ds (xr.Dataset): aggregated ISSITGR4 xarray dataset.
    
    """

    current_path = os.getcwd()
    print(current_path)
    
    # Read in files for each month as a single xr.Dataset
    filenames = glob.glob(current_path+local_data_path+version+'/*.nc')
    #print('Number of netcdf files available locally:', len(filenames), filenames, current_path+local_data_path+version+'/')

    # Raise error if no files found
    if len(filenames) == 0: 
        raise ValueError("Still not files, exit")
        return None

    print('Load in netcdf files to xarray dataset')
    datasets_list = []
    for file in filenames: 
        print(file)
        ds_campaign = xr.open_dataset(file)
        ds_campaign = ds_campaign.set_coords(["latitude","longitude","x","y"]) # Set data variables as coordinates
        mean_campaign_time_1 = pd.to_datetime(ds_campaign.campaign_dates.first_day, format = "%Y-%m-%d")
        mean_campaign_time_2 = pd.to_datetime(ds_campaign.campaign_dates.last_day, format = "%Y-%m-%d")
        
        mean_campaign_time = mean_campaign_time_1+(mean_campaign_time_2-mean_campaign_time_1)/2
        
        ds_campaign = ds_campaign.assign_coords({"time":mean_campaign_time}) # Add time as coordinate
        ds_campaign = ds_campaign.expand_dims("time") # Set month as a dimension 
        datasets_list.append(ds_campaign)

    is_ds = xr.merge(datasets_list)
    is_ds = is_ds.sortby("time")
    
    return is_ds

def add_time_dim_v2(xda):
    """ dummy function to just set current time as a new dimension to concat files over, change later! """
    xda = xda.set_coords(["latitude","longitude", "xgrid", "ygrid"])
    xda = xda.expand_dims(time = [datetime.now()])
    return xda

def add_time_dim_v3(xda):
    """ dummy function to just set current time as a new dimension to concat files over, change later! """
    xda = xda.set_coords(["latitude","longitude", "x", "y"])
    xda = xda.expand_dims(time = [datetime.now()])
    return xda

def read_IS2SITMOGR4(data_type='zarr-s3', version='V3', local_data_path="./data/IS2SITMOGR4/", 
                     zarr_path='s3://icesat-2-sea-ice-us-west-2/IS2SITMOGR4_V3/IS2SITMOGR4_V3_201811-202404.zarr',
                     netcdf_s3_path='s3://icesat-2-sea-ice-us-west-2/IS2SITMOGR4_V3/netcdf/', 
                     persist=True): 
    """ Read in IS2SITMOGR4 monthly gridded thickness dataset from local netcdf files, 
    download the netcdf files from S3 storage, or read in the aggregated zarr dataset from S3. 
    Currently supports either Version 2 (V2) or Version 3 (V3) data. 
    
    Args: 
        data_type (str, required): (default to "zarr-s3", but also "netcdf-s3" or "netcdf-local" which is a local version of the netcdf files)
        version (str, required): dataset version, the default is V3 but V2 has some little changes we need to adapt for.
        local_data_path (str, required): local data directory
        zarr_path (str): path to zarr file
        netcdf_s3_path (str): path to netcdf files stored on s3
        persist (boleen): if zarr option decide if you want to persist (load) data into memory

    Returns: 
        is2_ds (xr.Dataset): aggregated IS2SITMOGR4 xarray dataset, dask chunked/virtually allocated in the case of the zarr option (or allocated to memory if persisted). 
        
    Version History: 
        February 2025
            - hard-coded the datapaths as mostly just V3 at this point and the V2/V3 stuff was getting confusing
            - now you just provide the path to the zarr or netcdf files as desired which I think is easier. 
     
        November 2023 (for V3 data release):  
            - Moved the download code to it's own section at the start of the function
            - Changed local paths
            - Baked in the date_str label as that is just a function of the dataset version anyway
            - Adapted the netcdf reader to use open_mfdataset, required a preprocessing data dimension step. Much more elegant!
            Note than in Version 3 there was a change in the xgrid/ygrid coordinates to x/y.
    """
            
    if data_type=='zarr-s3':

        print('load zarr from S3 bucket')

        print('zarr_path:', zarr_path)
        s3 = s3fs.S3FileSystem(anon=True)
        store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
        is2_ds = xr.open_zarr(store=store)
        print(is2_ds)
        # Had a problem with these being loaded as dask arrays which cartopy doesnt like
        is2_ds = is2_ds.assign_coords(longitude=(["y","x"], is2_ds.longitude.values))
        is2_ds = is2_ds.assign_coords(latitude=(["y","x"], is2_ds.latitude.values))

        if persist==True:
            is2_ds = is2_ds.persist()
        
        return is2_ds

    if data_type=='netcdf-s3':
        # Download data from S3 to local bucket
        print("download from S3 bucket: ", netcdf_s3_path)

        # Download netCDF data files
        fs = s3fs.S3FileSystem(anon=True)

        #files references the entire bucket.
        files = fs.ls(netcdf_s3_path)
        for file in files:
            print('Downloading file from bucket to local storage...', file)
            fs.download(file, local_data_path+version+'/')

    # Read in files for each month as a single xr.Dataset
    filenames = glob.glob(local_data_path+version+'/*.nc')
    if len(filenames) == 0: 
        raise ValueError("No files, exit")
        return None
    
    dates = [pd.to_datetime(file.split("IS2SITMOGR4_01_")[1].split("_")[0], format = "%Y%m")  for file in filenames]
    # Add a dummy time then add the dates I want, seemed the easiest solution
    if version=='V2':
        is2_ds = xr.open_mfdataset(filenames, preprocess = add_time_dim_v2, engine='netcdf4')
    else:
        is2_ds = xr.open_mfdataset(filenames, preprocess = add_time_dim_v3, engine='netcdf4')
            
    is2_ds["time"] = dates

    # Sort by time as glob file list wasn't!
    is2_ds = is2_ds.sortby("time")
    if version=='V2':
        is2_ds = is2_ds.set_coords(["latitude","longitude","xgrid","ygrid"]) 
    else:
        is2_ds = is2_ds.set_coords(["latitude","longitude","x","y"])
    
    is2_ds = is2_ds.assign_coords(longitude=(["y","x"], is2_ds.longitude.values))
    is2_ds = is2_ds.assign_coords(latitude=(["y","x"], is2_ds.latitude.values))
    
    is2_ds = is2_ds.assign_attrs(description="Aggregated IS2SITMOGR4 "+version+" dataset.")

    
    return is2_ds


def read_book_data(local_path='/data/', CS2=False): 
    """ Read in data for ICESat2 jupyter book. 
    If the file does not already exist on the user's local drive, it is downloaded from our S3 bucket
    The netcdf file is then read in as an xr.Dataset object 

    To do:
     - Add zarr functionality to this to avoid having to download the netcdf.
    
    Args: 
        local_path (str, required): local data directory
        CS2 (boleen, required): choose if we want to also read in the wrangled CS-2 thickness data
    Returns: 
        book_ds (xr.Dataset): data 
    
    """

    if CS2==True:
        filename = "IS2_CS2_jbook_dataset_201811-202104.nc"
    else:
        filename = "IS2_jbook_dataset_201811-202104.nc"
    
    # Check if file exists on local drive
    current_path = os.getcwd()
    exists_locally = os.path.isfile(current_path+local_path+filename) 
    
    if (exists_locally == False): 
        # Download data 
        print("Downloading jupyter book data from the S3 bucket...")
        s3_path = 's3://icesat-2-sea-ice-us-west-2/book_data/'+filename
        fs = s3fs.S3FileSystem(anon=True)
        fs.download(file, current_path+local_data_path)

    book_ds = xr.open_dataset(current_path+local_path+filename)
    return book_ds
