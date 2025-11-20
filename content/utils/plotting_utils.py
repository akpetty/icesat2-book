# +
""" plotting_utils.py 

Helper functions for generating maps and plots 

"""

import xarray as xr
import numpy as np 
import numpy.ma as ma
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from textwrap import wrap
import hvplot.xarray
import holoviews as hv
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from cartopy.mpl.geoaxes import GeoAxes
GeoAxes._pcolormesh_patched = Axes.pcolormesh # Helps avoid some weird issues with the polar projection 


# -

def get_winter_data(da, year_start=None, start_month="Sep", end_month="Apr", force_complete_season=False):
    """ Select data for winter seasons corresponding to the input time range 
    
    Args: 
        da (xr.Dataset or xr.DataArray): data to restrict by time; must contain "time" as a coordinate 
        year_start (str, optional): year to start time range; if you want Sep 2019 - Apr 2020, set year="2019" (default to the first year in the dataset)
        start_month (str, optional): first month in winter (default to September)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
        
    Returns: 
        da_winter (xr.Dataset or xr.DataArray): da restricted to winter seasons 
    
    """
    if year_start is None: 
        print("No start year specified. Getting winter data for first year in the dataset")
        year_start = str(pd.to_datetime(da.time.values[0]).year)
    
    start_timestep = start_month+" "+str(year_start) # mon year 
    end_timestep = end_month+" "+str(int(year_start)+1) # mon year
    winter = pd.date_range(start=start_timestep, end=end_timestep, freq="MS") # pandas date range defining winter season
    months_in_da = [mon for mon in winter if mon in da.time.values] # Just grab months if they correspond to a time coordinate in da

    if len(months_in_da) > 0: 
        if (force_complete_season == True) and (all([mon in da.time.values for mon in winter])==False): 
            da_winter = None
        else: 
            da_winter = da.sel(time=months_in_da)
    else: 
        da_winter = None
        
    return da_winter


def compute_gridcell_winter_means(da, years=None, start_month="Nov", end_month="Apr", force_complete_season=False): 
    """ Compute winter means over the time dimension. Useful for plotting as the grid is maintained. 
    
    Args: 
        da (xr.Dataset or xr.DataArray): data to restrict by time; must contain "time" as a coordinate 
        years (list of str): years over which to compute mean (default to unique years in the dataset)
        year_start (str, optional): year to start time range; if you want Nov 2019 - Apr 2020, set year="2019" (default to the first year in the dataset)
        start_month (str, optional): first month in winter (default to November)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
    
    Returns: 
        merged (xr.DataArray): DataArray with winter means as a time coordinate
    """
    
    if years is None: 
        years = np.unique(pd.to_datetime(da.time.values).strftime("%Y")) # Unique years in the dataset 

    winter_means = []
    for year in years: # Loop through each year and grab the winter months, compute winter mean, and append to list 
        #print(year)
        da_winter_i = get_winter_data(da, year_start=year, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season)
        #print(da_winter_i)
        if da_winter_i is None: 
            print('no data')
            continue
        da_mean_i = da_winter_i.mean(dim="time", keep_attrs=True) # Compute mean over time dimension
        #print(da_mean_i)
        # Assign time coordinate 
        time_arr = pd.to_datetime(da_winter_i.time.values)
        da_mean_i = da_mean_i.assign_coords({"time":time_arr[0].strftime("%b %Y")+" - "+time_arr[-1].strftime("%b %Y")})
        da_mean_i = da_mean_i.expand_dims("time")

        winter_means.append(da_mean_i)
    
    #print(winter_means)
    merged = xr.merge(winter_means) # Combine each winter mean Dataset into a single Dataset, with the time period maintained as a coordinate
    merged = merged[list(merged.data_vars)[0]] # Convert to DataArray
    merged.time.attrs["description"] = "Time period over which mean was computed" # Add descriptive attribute 
    return merged 


def staticArcticMaps(da, title=None, dates=[], out_str="out", cmap="viridis", col=None, col_wrap=3, vmin=None, vmax=None, set_cbarlabel = '', min_lat=50, savefig=True): 
    """ Show data on a basemap of the Arctic. Can be one month or multiple months of data. 
    Creates an xarray facet grid. For more info, see: http://xarray.pydata.org/en/stable/user-guide/plotting.html
    
    Args: 
        da (xr DataArray): data to plot
        title (str, optional): title string for plot
        dates (str list, option): dates to assign to subtitles, else defaults to whatever cartopy thinks they are
        out_str (str, optional): output string when saving
        cmap (str, optional): colormap to use (default to viridis)
        col (str, optional): coordinate to use for creating facet plot (default to "time")
        col_wrap (int, optional): number of columns of plots to display (default to 3, or None if time dimension has only one value)
        vmin (float, optional): minimum on colorbar (default to 1st percentile)
        vmax (float, optional): maximum on colorbar (default to 99th percentile)
        min_lat (float, optional): minimum latitude to set extent of plot (default to 50 deg lat)
        set_cbarlabel (str, optional): set colorbar label
        savefig (bool): output figure
    
    Returns:
        Figure displayed in notebook 
    
    """ 
    # Compute min and max for plotting
    def compute_vmin_vmax(da): 
        vmin = np.nanpercentile(da.values, 1)
        vmax = np.nanpercentile(da.values, 99)
        return vmin, vmax
    vmin_data, vmax_data = compute_vmin_vmax(da)
    vmin = vmin if vmin is not None else vmin_data # Set to smallest value of the two 
    vmax = vmax if vmax is not None else vmax_data # Set to largest value of the two 
    
    # All of this col and col_wrap maddness is to try and make this function as generalizable as possible
    # This allows the function to work for DataArrays with multiple coordinates, different coordinates besides time, etc! 
    if col is None: 
        col = "time"
        try: # Assign time coordinate if it doesn't exist
            da["time"]
        except AttributeError: 
            da = da.assign_coords({col:"unknown"})
    col = col if sum(da[col].shape) > 1 else None
    if col is not None: 
        if sum(da[col].shape)<=1: 
            col_wrap = None
    
    # Plot
    if len(set_cbarlabel)==0:
        set_cbarlabel=da.attrs["long_name"]+' ['+da.attrs["units"]+']'

    im = da.plot(x="longitude", y="latitude", col_wrap=col_wrap, col=col, transform=ccrs.PlateCarree(), cmap=cmap, zorder=8, 
             cbar_kwargs={'pad':0.02,'shrink': 0.8,'extend':'both', 'label':set_cbarlabel, 'location':'left'},
             vmin=vmin, vmax=vmax, 
             subplot_kws={'projection':ccrs.NorthPolarStereo(central_longitude=-45)})

    # Iterate through axes and add features 
    ax_iter = im.axes
    if type(ax_iter) != np.array: # If the data is just a single month, ax.iter returns an axis object. We need to iterate through a list or array
        ax_iter = np.array(ax_iter)
    i=0
    for ax in ax_iter.flatten():
        ax.coastlines(linewidth=0.15, color = 'black', zorder = 10) # Coastlines
        ax.add_feature(cfeature.LAND, color ='0.95', zorder = 5)    # Land
        ax.add_feature(cfeature.LAKES, color = 'grey', zorder = 5)  # Lakes
        ax.gridlines(draw_labels=False, linewidth=0.25, color='gray', alpha=0.7, linestyle='--', zorder=6) # Gridlines
        ax.set_extent([-179, 179, min_lat, 90], crs=ccrs.PlateCarree()) # Set extent to zoom in on Arctic
        if len(dates)>0:
            try:
                ax.set_title(dates[i], fontsize=10, horizontalalignment="center",verticalalignment="bottom", x=0.5, y=1.01, fontweight='medium')
            except:
                print('no date')
            i+=1

    # Get figure
    fig = plt.gcf()
    
    # Set title 
    if (sum(ax_iter.shape) == 0) and (title is not None): 
        ax.set_title(title, fontsize=10, horizontalalignment="center", x=0.5, y=1.06, fontweight='medium')
    elif title is not None:
        fig.suptitle(title, fontsize=10, horizontalalignment="center", x=0.5, y=1.06, fontweight='medium')
    
    # save figure
    if savefig:
        plt.savefig('./figs/maps_'+out_str+'.png', dpi=300, facecolor="white", bbox_inches='tight')

    plt.close() # Close so it doesnt automatically display in notebook 
    return fig


def staticArcticMaps_2025(da, title=None, dates=[], out_str="out", cmap="viridis", col=None, vmin=None, vmax=None, set_cbarlabel = '', min_lat=50, savefig=True): 
    """ Show data on a basemap of the Arctic with special 2025 layout for 7 winters.
    Creates a custom layout where the first 6 winters are in regular panels and the 7th winter 
    is larger (spans 2 rows and 2 columns) and positioned on the right side.
    
    Args: 
        da (xr DataArray): data to plot (should have 7 time periods)
        title (str, optional): title string for plot
        dates (str list, option): dates to assign to subtitles, else defaults to whatever cartopy thinks they are
        out_str (str, optional): output string when saving
        cmap (str, optional): colormap to use (default to viridis)
        col (str, optional): coordinate to use for creating facet plot (default to "time")
        vmin (float, optional): minimum on colorbar (default to 1st percentile)
        vmax (float, optional): maximum on colorbar (default to 99th percentile)
        min_lat (float, optional): minimum latitude to set extent of plot (default to 50 deg lat)
        set_cbarlabel (str, optional): set colorbar label
        savefig (bool): output figure
    
    Returns:
        Figure displayed in notebook 
    
    """ 
    # Compute min and max for plotting
    def compute_vmin_vmax(da): 
        vmin = np.nanpercentile(da.values, 1)
        vmax = np.nanpercentile(da.values, 99)
        return vmin, vmax
    vmin_data, vmax_data = compute_vmin_vmax(da)
    vmin = vmin if vmin is not None else vmin_data # Set to smallest value of the two 
    vmax = vmax if vmax is not None else vmax_data # Set to largest value of the two 
    
    # All of this col maddness is to try and make this function as generalizable as possible
    if col is None: 
        col = "time"
        try: # Assign time coordinate if it doesn't exist
            da["time"]
        except AttributeError: 
            da = da.assign_coords({col:"unknown"})
    col = col if sum(da[col].shape) > 1 else None
    
    # Plot
    if len(set_cbarlabel)==0:
        set_cbarlabel=da.attrs["long_name"]+' ['+da.attrs["units"]+']'

    # Create custom subplot layout: 2 rows, 5 columns (optimized for 7 winters)
    # First 3 columns for regular panels (6 panels), last 2 columns for the large panel (1 panel)
    fig = plt.figure(figsize=(15, 6))  # 2 rows × 6 height units
    
    # Create GridSpec for custom layout
    gs = fig.add_gridspec(2, 5, width_ratios=[1, 1, 1, 1, 1], height_ratios=[1, 1])
    
    # Plot regular panels (first 6 winters)
    axes = []
    for i in range(6):  # First 6 winters
        row = i // 3
        col_idx = i % 3
        ax = fig.add_subplot(gs[row, col_idx], projection=ccrs.NorthPolarStereo(central_longitude=0))
        axes.append(ax)
        
        # Plot data
        if col is not None:
            data_to_plot = da.isel({col: i})
        else:
            data_to_plot = da
            
        im = data_to_plot.plot(ax=ax, x="longitude", y="latitude", transform=ccrs.PlateCarree(), 
                               cmap=cmap, zorder=8, vmin=vmin, vmax=vmax, add_colorbar=False)
        
        # Add map features
        ax.coastlines(linewidth=0.15, color='black', zorder=10)
        ax.add_feature(cfeature.LAND, color='0.95', zorder=5)
        ax.add_feature(cfeature.LAKES, color='grey', zorder=5)
        ax.gridlines(draw_labels=False, linewidth=0.25, color='gray', alpha=0.7, linestyle='--', zorder=6)
        ax.set_extent([-179, 179, 54, 90], crs=ccrs.PlateCarree())
        
        # Set title
        if len(dates) > i:
            ax.set_title(dates[i], fontsize=10, horizontalalignment="center", verticalalignment="bottom", 
                        x=0.5, y=0.97, fontweight='medium')
    
    # Plot the large panel (7th winter, spans 2 rows and 2 columns)
    ax_large = fig.add_subplot(gs[:, 3:], projection=ccrs.NorthPolarStereo(central_longitude=0))
    axes.append(ax_large)
    
    # Plot data for the 7th winter
    if col is not None:
        data_to_plot = da.isel({col: 6})  # 7th winter (index 6)
    else:
        data_to_plot = da
        
    im_large = data_to_plot.plot(ax=ax_large, x="longitude", y="latitude", transform=ccrs.PlateCarree(), 
                                 cmap=cmap, zorder=8, vmin=vmin, vmax=vmax, add_colorbar=False)
    
    # Add map features
    ax_large.coastlines(linewidth=0.15, color='black', zorder=10)
    ax_large.add_feature(cfeature.LAND, color='0.95', zorder=5)
    ax_large.add_feature(cfeature.LAKES, color='grey', zorder=5)
    ax_large.gridlines(draw_labels=False, linewidth=0.25, color='gray', alpha=0.7, linestyle='--', zorder=6)
    ax_large.set_extent([-179, 179, 54, 90], crs=ccrs.PlateCarree())
    
    # Set title
    if len(dates) > 6:
        ax_large.set_title(dates[6], fontsize=10, horizontalalignment="center", verticalalignment="bottom", 
                         x=0.5, y=0.99, fontweight='medium')
    
    # Add colorbar inside the large panel (bottom left) without affecting panel position
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    cbar_ax = inset_axes(ax_large, width="30%", height="3%", loc='lower left')
    cbar = fig.colorbar(im_large, cax=cbar_ax, orientation='horizontal', extend='both')
    cbar.set_label(set_cbarlabel, fontsize=10, labelpad=10)
    cbar.ax.xaxis.set_ticks_position('top')
    cbar.ax.xaxis.set_label_position('top')
    cbar.set_ticks(np.linspace(vmin, vmax, 6))  # Set ticks from 0 to 5 in steps of 1
    
    # Set overall title
    if title is not None:
        fig.suptitle(title, fontsize=12, horizontalalignment="center", x=0.5, y=0.95, fontweight='medium')
    
    # Adjust layout with reduced spacing
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.02, wspace=0.03, hspace=0.05)
    
    # Save figure
    if savefig:
        plt.savefig('./figs/maps_'+out_str+'.png', dpi=300, facecolor="white", bbox_inches='tight')
    
    plt.close() # Close so it doesnt automatically display in notebook 
    return fig


def staticArcticMaps_overlayDrifts(da, drifts_x, drifts_y, alpha=1, vector_val=0.1, scale_vec=0.5, res=6, units_vec=r'm s$^{-1}$', title=None, out_str="out", dates=[], cmap="viridis", col=None, col_wrap=3, vmin=None, vmax=None, set_cbarlabel = '', min_lat=50, savefig=True, figsize=(6,6)): 
    """ Show data on a basemap of the Arctic. Can be one month or multiple months of data. Overlay drift vectors on top 
    Creates an xarray facet grid. For more info, see: http://xarray.pydata.org/en/stable/user-guide/plotting.html
    
    Args: 
        da (xr DataArray): data to plot
        drifts_x (xr.DataArray): sea ice drifts along-x component of the ice motion
        drifts_y (xr.DataArray): sea ice drifts along-y component of the ice motion
        alpha (float 0-1, optional): Set this variable if you want da to have a reduced opacity (default to 1)
        res (int, optional): resolution of vectors (default to 6; plot 1 out of every 6 vectors)
        title (str, optional): title string for plot
        out_str (str, optional): output string when saving
        cmap (str, optional): colormap to use (default to viridis)
        col (str, optional): coordinate to use for creating facet plot (default to "time")
        col_wrap (int, optional): number of columns of plots to display (default to 3, or None if time dimension has only one value)
        vmin (float, optional): minimum on colorbar (default to 1st percentile)
        vmax (float, optional): maximum on colorbar (default to 99th percentile)
        min_lat (float, optional): minimum latitude to set extent of plot (default to 50 deg lat)
        set_cbarlabel (str, optional): set colorbar label
        savefig (bool): output figure
    
    Returns:
        Figure displayed in notebook 
    
    """ 
    # Make sure alpha is between 0 and 1 
    if alpha > 1: 
        print("Argument alpha must be between 0 and 1. You inputted " +str(alpha)+ ". Setting alpha to 1.")
        alpha = 1 
    elif alpha < 0: 
        print("Argument alpha must be between 0 and 1. You inputted " +str(alpha)+ ". Setting alpha to 0.5.")
        alpha = 0.5
    elif alpha == 0: 
        print("You set alpha=0. This indicates full transparency of the input data. No data will be displayed on the map.")
    
    # Check that drifts and da have the same time coordinates 
    for drift in [drifts_x,drifts_y]:
        equality = (da.time.values  == drift.time.values)
        if type(equality) == np.ndarray:
            if not all(equality): 
                raise ValueError("Drifts vectors and input DataArray must have the same time coordinates")
        elif (equality==False):
            raise ValueError("Drifts vectors and input DataArray must have the same time coordinates")

    # Compute min and max for plotting
    def compute_vmin_vmax(da): 
        vmin = np.nanpercentile(da.values, 1)
        vmax = np.nanpercentile(da.values, 99)
        return vmin, vmax
    vmin_data, vmax_data = compute_vmin_vmax(da)
    vmin = vmin if vmin is not None else vmin_data # Set to smallest value of the two 
    vmax = vmax if vmax is not None else vmax_data # Set to largest value of the two 
    
    # All of this col and col_wrap maddness is to try and make this function as generalizable as possible
    # This allows the function to work for DataArrays with multiple coordinates, different coordinates besides time, etc! 
    if col is None: 
        col = "time"
        try: # Assign time coordinate if it doesn't exist
            da["time"]
        except AttributeError: 
            da = da.assign_coords({col:"unknown"})
    col = col if sum(da[col].shape) > 1 else None
    if col is not None: 
        if sum(da[col].shape)<=1: 
            col_wrap = None
            
    # Plot
    if len(set_cbarlabel)==0:
        set_cbarlabel=da.attrs["long_name"]+' ['+da.attrs["units"]+']'

    im = da.plot(x="longitude", y="latitude", col_wrap=col_wrap, col=col, transform=ccrs.PlateCarree(), cmap=cmap, 
                 cbar_kwargs={'pad':0.02,'shrink': 0.8,'extend':'both', 'label':set_cbarlabel},
                 vmin=vmin, vmax=vmax, zorder=2, alpha=alpha, 
                 subplot_kws={'projection':ccrs.NorthPolarStereo(central_longitude=-45)})
    
    # Iterate through axes and add features 
    ax_iter = im.axes
    if type(ax_iter) != np.array: # If the data is just a single month, ax.iter returns an axis object. We need to iterate through a list or array
        ax_iter = np.array(ax_iter)
    
    i = 0
    try: 
        num_timesteps = len(da.time.values)
    except: 
        num_timesteps = 1
    for ax, i in zip(ax_iter.flatten(), range(num_timesteps)):

            # Add drifts 
            if num_timesteps == 1: 
                drifts_xi = drifts_x.copy()
                drifts_yi = drifts_y.copy()
            else: 
                drifts_xi = drifts_x.isel(time=i).copy()
                drifts_yi = drifts_y.isel(time=i).copy()
            Q = ax.quiver(drifts_x.xgrid[::res, ::res], drifts_y.ygrid[::res, ::res], 
                          ma.masked_where(np.isnan(drifts_xi[::res, ::res]), drifts_xi[::res, ::res]),
                          ma.masked_where(np.isnan(drifts_yi[::res, ::res]), drifts_yi[::res, ::res]) , units='inches', scale=scale_vec, zorder=10)
            ax.quiverkey(Q, 0.85, 0.88, vector_val, str(vector_val)+' '+units_vec, coordinates='axes', zorder=11)   

            ax.coastlines(linewidth=0.15, color = 'black', zorder = 8) # Coastlines
            ax.add_feature(cfeature.LAND, color ='0.95', zorder = 5)    # Land
            ax.add_feature(cfeature.LAKES, color = 'grey', zorder = 5)  # Lakes
            ax.gridlines(draw_labels=False, linewidth=0.25, color='gray', alpha=0.7, linestyle='--', zorder=6) # Gridlines
            ax.set_extent([-179, 179, min_lat, 90], crs=ccrs.PlateCarree()) # Set extent to zoom in on Arctic
            if len(dates)>0:
                ax.set_title(dates[i], fontsize=10, horizontalalignment="center",verticalalignment="bottom", x=0.5, y=1.01, fontweight='medium')

    # Get figure
    fig = plt.gcf()
    
    # Set title 
    if (sum(ax_iter.shape) == 0) and (title is not None): 
        ax.set_title(title, fontsize=10, horizontalalignment="center", x=0.45, y=1.06, fontweight='medium')
    elif title is not None:
        fig.suptitle(title, fontsize=10, horizontalalignment="center", x=0.45, y=1.06, fontweight='medium')
    
    # save figure
    if savefig:
        plt.savefig('./figs/maps_'+out_str+'.png', dpi=400, facecolor="white", bbox_inches='tight')
        
    plt.close() # Close so it doesnt automatically display in notebook 
    return fig


def interactiveArcticMaps(da, clabel=None, cmap="viridis", colorbar=True, vmin=None, vmax=None, title="", ylim=(60,90), frame_width=500, slider=True, cols=3): 
    """ Generative one or more interactive maps 
    Using the argument "slide", the user can set whether each map should be displayed together, or displayed in the form of a slider 
    To show each map together (no slider), set slider=False
    
    Args: 
        da (xr.Dataset or xr.DataArray): data 
        clabel (str, optional): colorbar label (default to "long_name" and "units" if given in attributes of da)
        cmap (str, optional): matplotlib colormap to use (default to "viridis")
        colorbar (bool, optional): show colorbar? (default to True)
        vmin (float, optional): minimum on colorbar (default to 1st percentile)
        vmax (float, optional): maximum on colorbar (default to 99th percentile)
        title (str, optional): main title to give plot (default to no title)
        ylim (tuple, optional): limits of yaxis in the form min latitude, max latitude (default to (60,90))
        frame_width (int, optional): width of frame. sets figure size of each map (default to 250)
        slider (bool, optional): if da has more than one time coordinate, display maps with a slider? (default to True)
        cols (int, optional): how many columns to show before wrapping, if da has more than one time coordinate (default to 3)
    
    Returns: 
        pl (Holoviews map)
    
    """
    # Compute min and max for plotting
    def compute_vmin_vmax(da): 
        vmin = np.nanpercentile(da.values, 1)
        vmax = np.nanpercentile(da.values, 99)
        return vmin, vmax
    vmin_data, vmax_data = compute_vmin_vmax(da)
    vmin = vmin if vmin is not None else vmin_data # Set to smallest value of the two 
    vmax = vmax if vmax is not None else vmax_data # Set to largest value of the two 
    
    #https://hvplot.holoviz.org/user_guide/Subplots.html
    subplots=False
    shared_axes=False
    show_title=False
    if ("time" in da.coords):
        if (sum(da["time"].shape) > 1): 
            subplots=True
            shared_axes=True
            if slider==True and title=="": 
                show_title=False # We don't want to remove the title for the slider plots since it removes the time from the title 
        
    if clabel is None and ("long_name" in da.attrs): # Add a logical colorbar label 
        clabel=da.attrs["long_name"]
        if "units" in da.attrs: 
            clabel+=" ("+da.attrs["units"]+")"
        
    pl = da.hvplot.quadmesh(y="latitude", x="longitude",
                            projection=ccrs.NorthPolarStereo(central_longitude=-45), 
                            features=["coastline"], # Add coastlines 
                            colorbar=colorbar, clim=(vmin,vmax), cmap=cmap, clabel=clabel, # Colorbar settings 
                            project=True, ylim=ylim, frame_width=frame_width,
                            subplots=subplots, shared_axes=shared_axes,
                            dynamic=False, rasterize=True) 
    if slider==False: # Set number of columns 
        pl = pl.layout().cols(cols)
    
    if show_title==True: 
        pl.opts(title=title) # Add title
    hv.output(widget_location="bottom")
    return pl 


def interactive_winter_mean_maps(da, years=None, end_year=None, start_month="Sep", end_month="Apr", force_complete_season=False, clabel=None, cmap="viridis", colorbar=True, vmin=0, vmax=4, title="", ylim=(60,90), frame_width=250, slider=True, cols=3): 
    """ Generate interactive maps of winter mean data 
    Note: this function builds off the functions get_winter_data and interactiveArcticMaps.
    
    Args: 
        da (xr.Dataset or xr.DataArray): data; must contain "time" coordinate
        years (list of str): years over which to compute mean (default to unique years in the dataset)
        start_month (str, optional): first month in winter (default to September)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
        clabel (str, optional): colorbar label (default to "long_name" and "units" if given in attributes of da)
        cmap (str, optional): matplotlib colormap to use (default to "viridis")
        colorbar (bool, optional): show colorbar? (default to True)
        vmin (float, optional): minimum on colorbar (default to 0)
        vmax (float, optional): maximum on colorbar (default to 4)
        title (str, optional): main title to give plot (default to no title)
        ylim (tuple, optional): limits of yaxis in the form min latitude, max latitude (default to (60,90))
        frame_width (int, optional): width of frame. sets figure size of each map (default to 250)
        slider (bool, optional): if da has more than one time coordinate, display maps with a slider? (default to True)
        cols (int, optional): how many columns to show before wrapping, if da has more than one time coordinate (default to 3)
    
    Returns: 
        pl_means (Holoviews map)
    
    """
    
    winter_means_da = compute_gridcell_winter_means(da, years=years, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season)

    pl_means = interactiveArcticMaps(winter_means_da, 
                                    clabel=clabel, cmap=cmap, colorbar=colorbar, 
                                    vmin=vmin, vmax=vmax, title=title, 
                                    ylim=ylim, frame_width=frame_width, slider=slider, cols=cols)
    hv.output(widget_location="bottom")
    return pl_means


def static_winter_comparison_lineplot(da, da_unc=None, years=None, figsize=(5,3), start_month="Sep", 
    end_month="Apr", title="", set_ylabel = '', set_units = '', legend=True, savefig=True, save_label='', 
    annotation = '', force_complete_season=False, loc_pos=0, fmts = ['mo-.','cs-.','yv-.','k*-','r.-','gD--','b-.'],
    reanalysis_option=None): 
    """ Make a lineplot with markers comparing monthly mean data across winter seasons 
    
    Args: 
        da (xr.DataArray): data to plot and compute mean for; must contain "time" as a coordinate 
        da_unc (xr.DataArray, optional): uncertainty data to plot as error bars
        years (list of str): list of years for which to plot data. 2020 would correspond to the winter season defined by start month 2020 - end month 2021 (default to all unique years in da)
        title (str, optional): title to give plot (default to no title) 
        set_ylabel (str, optional): prescribed y label string
        set_units (str, optional): prescribed y label unit string
        legend (bool): print legend
        savefig (bool): output figure
        save_label (str, optional): additional string for output
        figsize (tuple, optional): figure size to display in notebook (default to (5,3))
        start_month (str, optional): first month in winter (default to September)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
        loc_pos (int, optional): if greater than one use that, if not default to "best"
        fmts (list, optional): list of format strings for different years
        reanalysis_option (str, optional): specify which reanalysis to use for snow depth ('m2' or 'e5'). If None, uses the default snow_depth variable.

       Returns: 
           Figure displayed in notebook
        
    """
    if years is None: 
        years = np.unique(pd.to_datetime(da.time.values).strftime("%Y")) # Unique years in the dataset 
        print("No years specified. Using "+", ".join(years))
    
    # Handle reanalysis option for snow depth
    if reanalysis_option is not None:
        if reanalysis_option.lower() == 'm2':
            # Use M2 reanalysis snow depth
            if hasattr(da, 'snow_depth_sm_m2'):
                da = da.snow_depth_sm_m2
            elif hasattr(da, 'snow_depth_sm_m2_int'):
                da = da.snow_depth_sm_m2_int
            else:
                print(f"Warning: M2 snow depth variable not found in dataset. Using default snow depth.")
        elif reanalysis_option.lower() == 'e5':
            # Use E5 reanalysis snow depth
            if hasattr(da, 'snow_depth_sm_e5'):
                da = da.snow_depth_sm_e5
            elif hasattr(da, 'snow_depth_sm_e5_int'):
                da = da.snow_depth_sm_e5_int
            else:
                print(f"Warning: E5 snow depth variable not found in dataset. Using default snow depth.")
        else:
            print(f"Warning: Invalid reanalysis option '{reanalysis_option}'. Using default snow depth.")
    
    # Set up x-axis 
    # This avoids having a set x-axis of winter months between Sep-Apr, even if there's no data for Sep, Oct etc 
    yr = 2000 
    if end_month not in ["Oct","Nov","Dec"]: 
        yr_end = yr+1
    else: 
        yr_end = yr
    xaxis_months = pd.date_range(start_month+"-"+str(yr), end_month+"-"+str(yr_end), freq="M").strftime("%b")
    
    # Set up plot 
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(xaxis_months, np.empty((len(xaxis_months),1))*np.nan, color=None, label=None) # Set x axis using winter months 
    try:
        gridlines = plt.grid(b = True, linestyle = '-', alpha = 0.2) # Add gridlines 
    except:
        try:
            gridlines = plt.grid(visible = True, linestyle = '-', alpha = 0.2) # Add gridlines 
        except:
            print("No gridlines")
    for year, fmt in zip(years, fmts*100): 
        winter_da = get_winter_data(da, year_start=year, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season) # Get data from that winter 
        if winter_da is None: # In case the user inputs a year that doesn't have data, skip this loop iteration to avoid appending None
            continue
        y = winter_da.mean(dim=["x","y"], keep_attrs=True)
        x = pd.to_datetime(y.time.values)
        
        # Add reanalysis info to legend if specified
        if reanalysis_option is not None:
            label = f"{x.year[0]}-{str(x.year[-1])[2:]} ({reanalysis_option.upper()})"
        else:
            label = f"{x.year[0]}-{str(x.year[-1])[2:]}"
            
        ax.plot(x.strftime("%b"), y, fmt, label=label, markersize=4)

        if da_unc is not None:
            # Get uncertaintiy data from that winter 
            winter_da_unc = get_winter_data(da_unc, year_start=year, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season) 
            if winter_da_unc is None: # In case the user inputs a year that doesn't have data, skip this loop iteration to avoid appending None
                continue
            yu = winter_da_unc.mean(dim=["x","y"], keep_attrs=True)    
            ax.fill_between(x.strftime("%b"), y - yu, y + yu, facecolor = fmt[0], alpha = 0.1, edgecolor = 'none')
    

    # Add legend, title, and axis labels, and display plot in notebook 
    if legend:
        if loc_pos>0:
            plt.legend(fontsize=8, frameon=False,loc=loc_pos)
        else:
            plt.legend(fontsize=8, frameon=False, loc="best")
    
    # Add annotation if provided
    ax.annotate(annotation, xy=(0.02, 0.98),xycoords='axes fraction', horizontalalignment='left', verticalalignment='top', fontsize=8, zorder=2)

    
    plt.title(title, fontsize=9)
    if len(set_ylabel)>0:
        ylabel=set_ylabel
    elif "long_name" in da.attrs: 
        ylabel = da.attrs["long_name"]
        if "units" in da.attrs: 
            ylabel+=" ("+da.attrs["units"]+")"
        ylabel="\n".join(wrap(ylabel, 35))
    else: 
        ylabel=None

    plt.ylabel(ylabel, fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=8)
   
   # reduce white space
    plt.tight_layout()

    # save figure
    if savefig:
        # Include reanalysis option in filename if specified
        if reanalysis_option is not None:
            filename = f'./figs/{da.attrs.get("long_name", "data")}{start_month}{end_month}{years[0]}-{years[-1]+1}{save_label}_{reanalysis_option}.pdf'
        else:
            filename = f'./figs/{da.attrs.get("long_name", "data")}{start_month}{end_month}{years[0]}-{years[-1]+1}{save_label}.pdf'
        plt.savefig(filename, dpi=300, facecolor="white", bbox_inches='tight')

    plt.show()


def static_winter_comparison_lineplot_with_reanalysis(da, reanalysis_option='m2', da_unc=None, years=None, figsize=(5,3), start_month="Sep", 
    end_month="Apr", title="", set_ylabel = '', set_units = '', legend=True, savefig=True, save_label='', 
    annotation = '', force_complete_season=False, loc_pos=0, fmts = ['mo-.','cs-.','yv-.','k*-','r.-','gD--','b-.']): 
    """ Make a lineplot with markers comparing monthly mean data across winter seasons with reanalysis option for snow depth
    
    This is a convenience function that calls static_winter_comparison_lineplot with the reanalysis_option parameter.
    
    Args: 
        da (xr.DataArray): data to plot and compute mean for; must contain "time" as a coordinate 
        reanalysis_option (str): specify which reanalysis to use for snow depth ('m2' or 'e5')
        da_unc (xr.DataArray, optional): uncertainty data to plot as error bars
        years (list of str): list of years for which to plot data. 2020 would correspond to the winter season defined by start month 2020 - end month 2021 (default to all unique years in da)
        title (str, optional): title to give plot (default to no title) 
        set_ylabel (str, optional): prescribed y label string
        set_units (str, optional): prescribed y label unit string
        legend (bool): print legend
        savefig (bool): output figure
        save_label (str, optional): additional string for output
        figsize (tuple, optional): figure size to display in notebook (default to (5,3))
        start_month (str, optional): first month in winter (default to September)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
        loc_pos (int, optional): if greater than one use that, if not default to "best"
        fmts (list, optional): list of format strings for different years

       Returns: 
           Figure displayed in notebook
        
    """
    return static_winter_comparison_lineplot(da, da_unc=da_unc, years=years, figsize=figsize, start_month=start_month,
                                           end_month=end_month, title=title, set_ylabel=set_ylabel, set_units=set_units,
                                           legend=legend, savefig=savefig, save_label=save_label, annotation=annotation,
                                           force_complete_season=force_complete_season, loc_pos=loc_pos, fmts=fmts,
                                           reanalysis_option=reanalysis_option)


def interactive_winter_comparison_lineplot(da, years=None, title="Winter comparison", frame_width=600, frame_height=350, start_month="Sep", end_month="Apr", force_complete_season=False):
    """ Make an interactive lineplot with markers comparing monthly mean data across winter seasons 
    
    Args: 
        da (xr.DataArray): data to plot and compute mean for; must contain "time" as a coordinate 
        years (list of str): list of years for which to plot data. 2020 would correspond to the winter season defined by start month 2020 - end month 2021 (default to all unique years in da)
        title (str, optional): title to give plot (default to "Winter comparison")
        frame_width (int, optional): width of plot frame (default to 600)
        frame_height (int, optional): height of plot frame (default to 350)
        start_month (str, optional): first month in winter (default to September)
        end_month (str, optional): second month in winter; this is the following calender year after start_month (default to April)
        force_complete_season (bool, optional): require that winter season returns data if and only if all months have data? i.e. if Sep and Oct have no data, return nothing even if Nov-Apr have data? (default to False) 
        
    Returns: 
        Interactive plot displayed in notebook
        
    """
    if years is None: 
        years = np.unique(pd.to_datetime(da.time.values).strftime("%Y")) # Unique years in the dataset 
        print("No years specified. Using "+", ".join(years))
    
    # Get winter data for each year
    winter_data = []
    for year in years:
        winter_da = get_winter_data(da, year_start=year, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season)
        if winter_da is not None:
            winter_mean = winter_da.mean(dim=["x","y"], keep_attrs=True)
            winter_data.append(winter_mean)
    
    if len(winter_data) == 0:
        print("No winter data found for the specified years")
        return None
    
    # Combine all winter data
    combined_data = xr.concat(winter_data, dim='year')
    combined_data['year'] = years[:len(winter_data)]
    
    # Create interactive plot
    p = combined_data.hvplot.line(x='time', by='year', title=title, frame_width=frame_width, frame_height=frame_height)
    
    return p
