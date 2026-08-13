# # Functions for reading data
# For the Jupyter Book - this is a markdown rendering of the `read_data_utils` module used in the notebooks. It is provided here for user reference, and may not reflect any changes to the code after 12/15/2021. The code can be viewed and downloaded from the github repository.

# +
""" read_data_utils.py 

Helper functions for reading ICESat2 data from a local drive and the book netcdf file from the google storage bucket

"""

import os 
import time
import shutil
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

def read_IS2SITMOGR4(data_type='zarr-s3-v4', version='V4', local_data_path="./data/IS2SITMOGR4/", 
                     zarr_path='s3://icesat-2-sea-ice-us-west-2/IS2SITMOGR4_V4/zarr/IS2SITMOGR4_V4_201811-202604.zarr',
                     netcdf_s3_path='s3://icesat-2-sea-ice-us-west-2/IS2SITMOGR4_V4/netcdf/', 
                     persist=True): 
    """ Read in IS2SITMOGR4 monthly gridded thickness dataset from local netcdf files, 
    download the netcdf files from S3 storage, or read in the aggregated zarr dataset from S3. 
    Currently supports either Version 2 (V2) or Version 3 (V3) data. 
    
    Args: 
        data_type (str, required): (default to "zarr-s3-v4", but also "netcdf-s3" or "netcdf-local" which is a local version of the netcdf files)
        version (str, required): dataset version, the default is V3 but V2 has some little changes we need to adapt for.
        local_data_path (str, required): local data directory
        zarr_path (str): path to zarr file
        netcdf_s3_path (str): path to netcdf files stored on s3
        persist (boleen): if zarr option decide if you want to persist (load) data into memory

    Returns: 
        is2_ds (xr.Dataset): aggregated IS2SITMOGR4 xarray dataset, dask chunked/virtually allocated in the case of the zarr option (or allocated to memory if persisted). 
        
    Version History: 
        January 2026: 
            - Added V4 data support (zarr-s3-v4 and netcdf-s3)
            - Made zarr-s3-v4 the default option for V4 data

        February 2025:
            - hard-coded the datapaths as mostly just V3 at this point and the V2/V3 stuff was getting confusing
            - now you just provide the path to the zarr or netcdf files as desired which I think is easier. 
     
        November 2023 (for V3 data release):  
            - Moved the download code to it's own section at the start of the function
            - Changed local paths
            - Baked in the date_str label as that is just a function of the dataset version anyway
            - Adapted the netcdf reader to use open_mfdataset, required a preprocessing data dimension step. Much more elegant!
            Note than in Version 3 there was a change in the xgrid/ygrid coordinates to x/y.
    """
            
    if data_type=='zarr-s3-v3':

        print('load zarr from S3 bucket')

        print('zarr_path:', zarr_path)
        s3 = s3fs.S3FileSystem(anon=True)
        store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
        is2_ds = xr.open_zarr(store=store)
        #print(is2_ds)
        # Had a problem with these being loaded as dask arrays which cartopy doesnt love
        is2_ds = is2_ds.assign_coords(longitude=(["y","x"], is2_ds.longitude.values))
        is2_ds = is2_ds.assign_coords(latitude=(["y","x"], is2_ds.latitude.values))

        if persist==True:
            is2_ds = is2_ds.persist()
        
        return is2_ds
    
    if data_type=='zarr-s3-v4':

        print('load zarr from S3 bucket')

        print('zarr_path:', zarr_path)
        s3 = s3fs.S3FileSystem(anon=True)
        store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
        is2_ds = xr.open_zarr(store=store)
        #print(is2_ds)
        # Had a problem with these being loaded as dask arrays which cartopy doesnt love
        #is2_ds = is2_ds.assign_coords(longitude=(["y","x"], is2_ds.longitude.values))
        #is2_ds = is2_ds.assign_coords(latitude=(["y","x"], is2_ds.latitude.values))

        # Drop time dimension from grid-cell area, longitude, latitude, and region mask
        # These are static variables that shouldn't have a time dimension
        if 'grid_cell_area' in is2_ds.data_vars:
            is2_ds['grid_cell_area'] = is2_ds['grid_cell_area'].isel(time=0, drop=True)
        if 'longitude' in is2_ds.data_vars:
            is2_ds['longitude'] = is2_ds['longitude'].isel(time=0, drop=True)
        if 'latitude' in is2_ds.data_vars:
            is2_ds['latitude'] = is2_ds['latitude'].isel(time=0, drop=True)
        if 'region_mask' in is2_ds.data_vars:
            is2_ds['region_mask'] = is2_ds['region_mask'].isel(time=0, drop=True)

        # Had a problem with these being loaded as dask arrays which cartopy doesnt love
        is2_ds = is2_ds.assign_coords(longitude=(["y","x"], is2_ds.longitude.values))
        is2_ds = is2_ds.assign_coords(latitude=(["y","x"], is2_ds.latitude.values))

        # Move time from 15th of the month to the 1st
        # Convert time to pandas datetime, extract year and month, then create new datetime for 1st of month
        time_pd = pd.to_datetime(is2_ds.time.values)
        new_time = pd.to_datetime([f"{t.year}-{t.month:02d}-01" for t in time_pd])
        is2_ds = is2_ds.assign_coords(time=new_time)

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
    print('Searching for files in: ', local_data_path+version+'/*.nc')
    
    filenames = glob.glob(local_data_path+version+'/*.nc')
    if len(filenames) == 0: 
        raise ValueError("No files, exit")
        return None
    
    
    # Add a dummy time then add the dates I want, seemed the easiest solution
    if version=='V2':
        is2_ds = xr.open_mfdataset(filenames, preprocess = add_time_dim_v2, engine='netcdf4')
    elif version=='V3':
        is2_ds = xr.open_mfdataset(filenames, preprocess = add_time_dim_v3, engine='netcdf4')
    else:
        is2_ds = xr.open_mfdataset(filenames, engine='netcdf4')
    
    #dates = [pd.to_datetime(file.split("IS2SITMOGR4_01_")[1].split("_")[0], format = "%Y%m")  for file in filenames]
    #is2_ds["time"] = dates

    # Sort by time as glob file list wasn't!
    is2_ds = is2_ds.sortby("time")
    if version=='V2':
        is2_ds = is2_ds.set_coords(["latitude","longitude","xgrid","ygrid"]) 
    else:
        is2_ds = is2_ds.set_coords(["latitude","longitude","x","y"])
    
    # Drop time dimension from longitude and latitude if they have it
    # These are static variables that shouldn't have a time dimension
    if 'time' in is2_ds.longitude.dims:
        is2_ds['longitude'] = is2_ds['longitude'].isel(time=0, drop=True)
    if 'time' in is2_ds.latitude.dims:
        is2_ds['latitude'] = is2_ds['latitude'].isel(time=0, drop=True)
    
    is2_ds = is2_ds.assign_coords(longitude=(["y","x"], is2_ds.longitude.values))
    is2_ds = is2_ds.assign_coords(latitude=(["y","x"], is2_ds.latitude.values))
    
    is2_ds = is2_ds.assign_attrs(description="Aggregated IS2SITMOGR4 "+version+" dataset.")

    return

# Variables kept in the trimmed local cache. Chosen to cover everything the
# analysis notebooks actually use while dropping large, unused 3-D fields
# (freeboard_unc, snow_depth_unc, sea_ice_conc, sea_ice_volume,
# ice_volume_per_grid_cell_area) — this cuts the cache from ~2.7 GB to ~0.9 GB.
# The static latitude/longitude are also collapsed to 2-D on write (see
# collapse_latlon), saving a further ~1 GB.
IS2SMGPSITV1_CACHE_VARS = [
    'ice_thickness',
    'freeboard',
    'snow_depth',
    'ice_thickness_unc',
    'grid_cell_area',
    'region_mask',
    'crs',
    'total_sea_ice_volume',
    'total_sea_ice_volume_regions_1_5',
    'mean_sea_ice_thickness_regions_1_5',
    'mean_freeboard_regions_1_5',
    'mean_snow_depth_regions_1_5',
    'mean_sea_ice_conc_regions_1_5',
]


def is2smgpsit_monthly_midmonth(da):
    """Resample a daily scalar time series to monthly means at mid-month timestamps."""
    import pandas as pd

    out = da.resample(time='1ME').mean()
    ft = pd.to_datetime(out.time.values)
    return out.assign_coords(
        time=(ft.to_period('M').to_timestamp(how='start') + pd.Timedelta(days=14)).values
    )


def static_grid_cell_area(area):
    """Return 2-D ``grid_cell_area``, dropping a leading time dimension if present."""
    if 'time' in area.dims:
        area = area.isel(time=0, drop=True)
    return area


def area_weighted_spatial_mean(field, mask, area):
    """Area-weighted spatial mean of *field* over cells where *mask* is True.

    Computes sum(field × grid_cell_area) / sum(grid_cell_area) over valid
    field values within *mask*. Missing field values are excluded from both the
    numerator and denominator.
    """
    area = static_grid_cell_area(area)
    valid = mask & field.notnull()
    weighted = field.where(valid)
    w = area.where(valid)
    return (weighted * w).sum(dim=['y', 'x']) / w.sum(dim=['y', 'x'])


def is2smgpsit_domain_masks(ds, inner_arctic=(1, 2, 3, 4, 5), caa_region=12):
    """Boolean masks for pan-Arctic (excl. CAA) and Inner Arctic Ocean (regions 1–5).

    The fused Zarr now includes Canadian Arctic Archipelago (NSIDC region 12) grid
    cells, but pan-Arctic diagnostics in the book exclude them from area/volume
    totals. IAO follows the NOAA Arctic Report Card domain (regions 1–5).
    """
    rm = ds['region_mask']
    if 'time' in rm.dims:
        rm = rm.isel(time=0, drop=True)
    ocean = rm.isin(list(range(1, 19)))
    return {
        'region_mask': rm,
        'pan_arctic': ocean & (rm != caa_region),
        'iao': rm.isin(list(inner_arctic)),
    }


def read_is2smgpsitv1_zarr(
    zarr_path=(
        's3://icesat-2-sea-ice-us-west-2/is2smsitgp/dev_v7/zarr/'
        'GPSat_multivar_20181101-20250430.zarr'
    ),
    persist=False,
    cache=False,
    load_cache=False,
    cache_dir='./data/cache',
    cache_path=None,
    cache_time_chunk=100,
    cache_vars=IS2SMGPSITV1_CACHE_VARS,
    collapse_latlon=True,
    cache_refresh=False,
):
    """Read the ICESat-2–SMOS–SMAP fused daily gridded product (Zarr).

    The dataset is the GPSat multivar product: daily fields from ICESat-2
    combined with SMOS/SMAP (e.g. thickness, concentration). Stored as a single
    Zarr on AWS (~2.7 GB, chunked one time step per object, so repeated S3
    reads are slow because of per-object latency).

    Local caching (recommended for the analysis notebooks): the S3 store can be
    mirrored to a single local Zarr once and reused. On write the store is
    re-chunked into larger time chunks (`cache_time_chunk`), which collapses the
    ~29k tiny S3 objects into a few hundred local files and makes subsequent
    reads dramatically faster.

    Typical usage:
      * "Producer" notebook (runs first, e.g. 11a): ``cache=True`` — build the
        local cache from S3 if it is missing, then read from it.
      * "Consumer" notebooks (11b, 11c, ...): ``load_cache=True`` — read the
        local cache if it exists; if it does not, fall back to S3, build the
        cache, then read from it (self-healing).

    Rebuilding the cache means re-downloading the whole store from S3, which is
    slow (tens of minutes). An existing, complete cache is therefore reused even
    when ``cache=True``; pass ``cache_refresh=True`` to force a rebuild, which is
    what you want after the upstream S3 store has been regenerated.

    Args:
        zarr_path (str): S3 path to the Zarr store (default: flat
            ``dev_v7/zarr/GPSat_multivar_20181101-20250430.zarr``,
            reuploaded 30 Jul 2026; history ``Created 2026-07-29``). Includes
            CAA grid cells and IAO scalars ``mean_*_regions_1_5`` /
            ``total_sea_ice_volume_regions_1_5``.
        persist (bool): If True, load lazy arrays into memory (default False).
        cache (bool): If True, build the local cache from S3 (if not already
            present) and read from it.
        load_cache (bool): If True, read from the local cache when present;
            otherwise read from S3 and build the cache for next time.
        cache_dir (str): Directory for the local cache (default './data/cache').
        cache_path (str): Explicit local cache path. Defaults to
            ``cache_dir/<zarr basename>``.
        cache_time_chunk (int): Time-chunk size used when writing the cache.
        cache_vars (list): Data variables to keep in the cache (default: the
            trimmed set used by the notebooks). Set to None to cache all vars.
        collapse_latlon (bool): If True, store the static latitude/longitude as
            2-D (drop the redundant time dimension) in the cache.
        cache_refresh (bool): If True, discard any existing local cache and
            rebuild it from S3. Needed when the upstream store has changed.

    Returns:
        xr.Dataset: Dataset opened from Zarr (dask-backed unless persist=True).
    """
    def _finalize(ds):
        # Promote lat/lon to coordinates if present as data variables (for plotting)
        if 'latitude' in ds.data_vars and 'latitude' not in ds.coords:
            ds = ds.set_coords('latitude')
        if 'longitude' in ds.data_vars and 'longitude' not in ds.coords:
            ds = ds.set_coords('longitude')
        if persist:
            ds = ds.persist()
        return ds.assign_attrs(
            description='ICESat-2–SMOS–SMAP fused daily gridded product (GPSat multivar).'
        )

    if cache_path is None:
        cache_path = os.path.join(cache_dir, os.path.basename(zarr_path.rstrip('/')))
    cache_exists = os.path.isdir(cache_path) and os.path.exists(
        os.path.join(cache_path, '.zmetadata')
    )

    # Read straight from a valid local cache. Rebuilding means re-downloading the
    # whole store from S3, so an existing cache is reused unless explicitly refreshed.
    if (load_cache or cache) and cache_exists and not cache_refresh:
        print('Loading IS2-SMOS-SMAP (is2smsitgp) Zarr from local cache')
        print('cache_path:', cache_path)
        ds = xr.open_zarr(cache_path)
        if cache_vars is not None:
            missing = [v for v in cache_vars if v not in ds.data_vars]
            if missing:
                print('Cache missing vars; checking S3 for:', missing)
                s3 = s3fs.S3FileSystem(
                    anon=True,
                    config_kwargs={'retries': {'max_attempts': 10, 'mode': 'adaptive'}},
                )
                store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
                ds_s3 = xr.open_zarr(store)
                available = [v for v in missing if v in ds_s3.data_vars]
                absent = [v for v in missing if v not in ds_s3.data_vars]
                if absent:
                    print('  not present on S3 (skipped):', absent)
                if available:
                    print('  loading from S3:', available)
                    ds = xr.merge([ds, ds_s3[available]])
        return _finalize(ds)

    # Otherwise read from S3. Use adaptive retries so transient connection
    # drops during the (slow, ~2.7 GB) read are retried rather than aborting.
    print('Loading IS2-SMOS-SMAP (is2smsitgp) Zarr from S3')
    print('zarr_path:', zarr_path)
    s3 = s3fs.S3FileSystem(
        anon=True,
        config_kwargs={'retries': {'max_attempts': 10, 'mode': 'adaptive'}},
    )
    store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
    ds = xr.open_zarr(store=store)

    # Build the local cache (either forced via cache=True, or lazily via load_cache=True).
    if cache or load_cache:
        # Promote coords before writing so the cache stores them as coordinates.
        if 'latitude' in ds.data_vars and 'latitude' not in ds.coords:
            ds = ds.set_coords('latitude')
        if 'longitude' in ds.data_vars and 'longitude' not in ds.coords:
            ds = ds.set_coords('longitude')

        # Collapse the static latitude/longitude to 2-D (drop redundant time dim).
        if collapse_latlon:
            for _c in ('latitude', 'longitude'):
                if _c in ds.coords and 'time' in ds[_c].dims:
                    ds = ds.assign_coords({_c: ds[_c].isel(time=0, drop=True)})

        # Keep only the requested data variables (coords are carried through).
        if cache_vars is not None:
            _keep = [v for v in cache_vars if v in ds.data_vars]
            ds = ds[_keep]

        os.makedirs(os.path.dirname(cache_path) or '.', exist_ok=True)
        # Remove any existing cache dir first: to_zarr(mode='w') overwrites the
        # arrays it writes but leaves behind stale variable directories from a
        # previous (possibly aborted) build, so wipe the target for a clean store.
        if os.path.isdir(cache_path):
            shutil.rmtree(cache_path, ignore_errors=True)
        ds_to_write = ds.chunk({'time': cache_time_chunk})
        # Clear source encoding to avoid chunk-encoding conflicts on write.
        for _v in ds_to_write.variables:
            ds_to_write[_v].encoding = {}
        _nvar = len(ds_to_write.data_vars)
        print(f'Writing local cache ({_nvar} vars, time chunks of {cache_time_chunk}) to: {cache_path}')
        print('  (one-time download; subsequent reads use the local cache)')
        # Retry the whole build a few times in case a transient S3 error still
        # bubbles up despite the per-request retries above.
        _n_attempts = 4
        for _attempt in range(1, _n_attempts + 1):
            try:
                ds_to_write.to_zarr(cache_path, mode='w', consolidated=True)
                break
            except Exception as _err:  # noqa: BLE001 - re-raised below on final attempt
                print(f'  cache build attempt {_attempt}/{_n_attempts} failed: {_err}')
                if _attempt == _n_attempts:
                    raise
                time.sleep(10)
        return _finalize(xr.open_zarr(cache_path))

    return _finalize(ds)


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
