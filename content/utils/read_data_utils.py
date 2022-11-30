# # Functions for reading data
# This is a markdown rendering of the `read_data_utils` module used in the notebooks. It is provided here for user reference, and may not reflect any changes to the code after 12/15/2021. The code can be viewed and downloaded from the github repository.

# +
""" read_data_utils.py 

Helper functions for reading ICESat2 data from a local drive and the book netcdf file from the google storage bucket

"""

import os 
import xarray as xr 
import pandas as pd 
import s3fs
import glob

# -

def read_IS2SITMOGR4(data_type='zarr-s3', version='V2', date_str='201811-202204', local_data_path="/data/IS2SITMOGR4/", 
    bucket_name="icesat-2-sea-ice-us-west-2", persist=False): 
    """ Read in IS2SITMOGR4 monthly gridded thickness dataset from local netcdf files or the S3 Zarr collection
    
    Args: 
        data_type (str, required): (default to "zarr-s3", but also "netcdf-s3" or "netcdf-local" which is a local version of the netcdf files)
        version (str, required): IS2SITMOGR4 version (default "V2")
        date_str (str, required): date string indicating start and end months
        local_data_path (str, required): local data directory
        bucket_name (str, required): S3 bucket name
        persist (boleen, required): if zarr option decide if you want to persist (load) data into memory

    Returns: 
        is2_ds (xr.Dataset): aggregated IS2SITMOGR4 xarray dataset, dask chunked/virtually allocated in the case of the zarr option. 
    
    """
    
    if data_type=='zarr-s3':
        print('load zarr from S3 bucket: ', bucket_name)
        s3_path = 's3://'+bucket_name+'/IS2SITMOGR4_'+version+'/zarr/IS2SITMOGR4_'+version+'_'+date_str+'.zarr/all/'
        s3 = s3fs.S3FileSystem(anon=True)
        store = s3fs.S3Map(root=s3_path, s3=s3, check=False)
        is2_ds = xr.open_zarr(store=store)
        if persist==True:
            is2_ds = is2_ds.persist()

    elif data_type=='netcdf':

        current_path = os.getcwd()
        print(current_path)
        # Read in files for each month as a single xr.Dataset
        filenames = glob.glob(current_path+local_data_path+version+'/*.nc')
        #print('Number of netcdf files available locally:', len(filenames), filenames, current_path+local_data_path+version+'/')

        
        if len(filenames) < 30: 
            print("Dir does not include all netcdf files, download from S3 bucket: ", bucket_name)

            # Download netCDF data files
            s3_path = 's3://'+bucket_name+'/IS2SITMOGR4_'+version+'/netcdf/'
            fs = s3fs.S3FileSystem(anon=True)

            #files references the entire bucket.
            files = fs.ls(s3_path+'*.nc')
            
            for file in files:
                print(file)
                #print(current_path+local_data_path+version+'/test.nc')
                #fs.open(file)
                fs.download(file, current_path+local_data_path+version+'/')
        else:
            print('local netcdf files available, use these')

        filenames = glob.glob(current_path+local_data_path+version+'/*.nc')
        # Raise error if no files found
        if len(filenames) == 0: 
            raise ValueError("Still not files, exit")
            return None

        print('Load in netcdf files to xarray dataset')
        datasets_list = []
        for file in filenames: 
            print(file)
            ds_monthly = xr.open_dataset(file)
            ds_monthly = ds_monthly.set_coords(["latitude","longitude","xgrid","ygrid"]) # Set data variables as coordinates
            time = file.split("IS2SITMOGR4_01_")[1].split("_")[0] # Get time from filename 
            ds_monthly = ds_monthly.assign_coords({"time":pd.to_datetime(time, format = "%Y%m")}) # Add time as coordinate
            ds_monthly = ds_monthly.expand_dims("time") # Set month as a dimension 
            datasets_list.append(ds_monthly)

        is2_ds = xr.merge(datasets_list)
        is2_ds = is2_ds.sortby("time")
    
    return is2_ds

def read_is2_data_gc(data_dir="IS2SITMOGR4/v002", local_dir="/data/", bucket_name="sea-ice-thickness-data"): 
    """ Read in ATLAS/ICESat-2 Monthly Gridded Sea Ice Freeboard dataset. 
    If the file does not already exist on the user's local drive, it is downloaded from the books google storage bucket (https://console.cloud.google.com/storage/browser/is2-pso-seaice)
    The netcdf files for each month are then read in as an xr.Dataset object
    
    Args: 
        data_dir (str, optional): name of data directory containing ICESat-2 data (default to "IS2SITMOGR4/v002", the name of the directory in the bucket)
        bucket_name (str, optional): name of google storage bucket (default to "sea-ice-thickness-data")
    Returns: 
        is2_ds (xr.Dataset): data 
    
    """
    if data_dir.endswith("/"): # Remove slash
        data_dir = data_dir[:-1]
    
    gc_path = bucket_name+"/" + data_dir
    ls_bucket = os.popen("gsutil ls gs://"+gc_path + "/**.nc ").read() # List everything in the bucket 
    netcdf_in_bucket = [file.split("gs://"+gc_path+"/")[1] for file in ls_bucket.split("\n") if file.endswith(".nc")] # Grab the netcdf files from the list 
    
    # Raise error if no files found
    if len(netcdf_in_bucket) == 0: 
        raise ValueError("No netcdf files with extension .nc found in google cloud at path "+gc_path)
    
    local_data_path = os.getcwd()+local_dir+data_dir
    # Check if directory data_dir exists on local drive 
    if local_data_path not in [gc_path for gc_path, subdirs, files in os.walk(os.getcwd())]:  
        os.makedirs(local_data_path) # Download if it doesn't already exist
        print("Created directory "+local_data_path)
    for file in netcdf_in_bucket: # Loop through each file in the bucket, see if it exists in the local drive, download if it doesn't exist
        if file not in os.listdir(local_data_path): 
            os.system("gsutil -m -o 'GSUtil:parallel_process_count=1' cp gs://"+bucket_name+"/"+data_dir+"/"+file+" "+local_data_path) # Make sure theres a space before the final segment, idicating the download directory ./ (i.e. " download dir")

    # Read in files for each month as a single xr.Dataset
    filenames = os.listdir(local_data_path)
    datasets_list = []
    for file in filenames: 
        ds_monthly = xr.open_dataset(local_data_path + "/" + file)
        ds_monthly = ds_monthly.set_coords(["latitude","longitude","xgrid","ygrid"]) # Set data variables as coordinates
        time = file.split("IS2SITMOGR4_01_")[1].split("_")[0] # Get time from filename 
        ds_monthly = ds_monthly.assign_coords({"time":pd.to_datetime(time, format = "%Y%m")}) # Add time as coordinate
        ds_monthly = ds_monthly.expand_dims("time") # Set month as a dimension 
        datasets_list.append(ds_monthly)

    is2_ds = xr.merge(datasets_list)
    is2_ds = is2_ds.sortby("time")
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

def read_cs2_book_data(local_path='./data/'): 
    """ Read in data for ICESat2 jupyter book including CryoSat-2 thickness data.
    If the file does not already exist on the user's local drive, it is downloaded from our S3 bucket
    The netcdf file is then read in as an xr.Dataset object 

    To do:
     - Add zarr functionality to this to avoid having to download the netcdf.
    
    Args: 
        None
    Returns: 
        book_ds (xr.Dataset): data 
    
    """
    
    filename = "IS2_CS2_jbook_dataset_201811-202104.nc"
    exists_locally = os.path.isfile(local_path+filename) # Check if file exists on local drive
    if (exists_locally == False): # Download data 
        print("Downloading jupyter book data from the google storage bucket...")
        os.system("gsutil -m cp gs://sea-ice-thickness-data/icesat2-book-data/"+filename+" "+local_path) # Make sure theres a space before the final ./ (i.e. " ./")
        print("Download complete")

    book_ds = xr.open_dataset(local_path+filename)
    return book_ds
