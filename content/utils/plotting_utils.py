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
import matplotlib.colorbar as mcbar
from matplotlib.axes import Axes
from cartopy.mpl.geoaxes import GeoAxes
GeoAxes._pcolormesh_patched = Axes.pcolormesh # Helps avoid some weird issues with the polar projection

# Light grey land, drawn above the data. Open-ocean NaNs are filled with 0 so
# they take the colormap's zero color; grey keeps land distinct from that fill.
LAND_FILL = '0.80' 


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
        ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder = 5)    # Land
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
        ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder=5)
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
    ax_large.add_feature(cfeature.LAND, color=LAND_FILL, zorder=5)
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


def staticArcticMaps_2026(da, title=None, dates=[], out_str="out", cmap="viridis", col=None, vmin=None, vmax=None, set_cbarlabel = '', min_lat=50, savefig=True):
    """ Show data on a basemap of the Arctic with a 2026 layout for 8 winters:
    all panels equal size in a 2 rows x 4 columns grid, with a horizontal
    colorbar centered below the figure.

    Args:
        da (xr DataArray): data to plot (should have 8 time periods)
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
    vmin = vmin if vmin is not None else vmin_data
    vmax = vmax if vmax is not None else vmax_data

    if col is None:
        col = "time"
        try:
            da["time"]
        except AttributeError:
            da = da.assign_coords({col:"unknown"})
    col = col if sum(da[col].shape) > 1 else None

    if len(set_cbarlabel)==0:
        set_cbarlabel=da.attrs["long_name"]+' ['+da.attrs["units"]+']'

    n_maps = int(da.sizes[col]) if col is not None else 1
    if n_maps != 8:
        print(f'Warning: staticArcticMaps_2026 expects 8 time panels; got {n_maps}')

    # 2 rows x 4 columns of equal-sized panels
    fig = plt.figure(figsize=(12, 6.5))
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 1], height_ratios=[1, 1])

    axes = []
    im = None
    for i in range(min(n_maps, 8)):
        row, col_idx = divmod(i, 4)
        ax = fig.add_subplot(gs[row, col_idx], projection=ccrs.NorthPolarStereo(central_longitude=0))
        axes.append(ax)

        if col is not None:
            data_to_plot = da.isel({col: i})
        else:
            data_to_plot = da

        im = data_to_plot.plot(ax=ax, x="longitude", y="latitude", transform=ccrs.PlateCarree(),
                               cmap=cmap, zorder=8, vmin=vmin, vmax=vmax, add_colorbar=False)

        ax.coastlines(linewidth=0.15, color='black', zorder=10)
        ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder=5)
        ax.add_feature(cfeature.LAKES, color='grey', zorder=5)
        ax.gridlines(draw_labels=False, linewidth=0.25, color='gray', alpha=0.7, linestyle='--', zorder=6)
        ax.set_extent([-179, 179, 54, 90], crs=ccrs.PlateCarree())

        if len(dates) > i:
            ax.set_title(dates[i], fontsize=10, horizontalalignment="center", verticalalignment="bottom",
                        x=0.5, y=0.97, fontweight='medium')

    # Horizontal colorbar centered below the panels
    plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.08, wspace=0.03, hspace=0.08)
    cbar_ax = fig.add_axes([0.35, 0.045, 0.3, 0.02])
    cbar = fig.colorbar(im, cax=cbar_ax, orientation='horizontal', extend='both')
    cbar.set_label(set_cbarlabel, fontsize=10, labelpad=4)
    cbar.set_ticks(np.linspace(vmin, vmax, 6))
    cbar.ax.tick_params(labelsize=8)

    if title is not None:
        fig.suptitle(title, fontsize=12, horizontalalignment="center", x=0.5, y=0.99, fontweight='medium')

    if savefig:
        plt.savefig('./figs/maps_'+out_str+'.png', dpi=300, facecolor="white", bbox_inches='tight')

    plt.close()
    return fig


def staticArcticMaps_equal_panels(da, title=None, dates=[], out_str="out", cmap="viridis",
                                    col=None, vmin=None, vmax=None, set_cbarlabel='',
                                    min_lat=50, savefig=True, ocean_mask=None):
    """Equal-sized multi-panel Arctic maps (2×4 grid) for seven or eight winters.

    For seven winters, panels 1–7 are identical in size and the unused 8th grid
    slot holds a horizontal colorbar. For eight winters all slots are maps and
    the colorbar sits below the figure.

    Open-ocean / missing cells stay NaN and render white (axes + colormap bad
    color). Pass ``ocean_mask`` so non-ocean cells are excluded from the data;
    land is filled grey from Natural Earth, not from ``~ocean_mask`` (that mask
    also includes extra-Arctic ocean, which would otherwise paint grey).

    Use this for IS2SMGPSIT-V1 map figures; keep ``staticArcticMaps_2025`` for
    the original large-right-panel layout.
    """
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    from matplotlib.colors import ListedColormap
    import matplotlib.path as mpath
    import matplotlib.cm as mcm

    def compute_vmin_vmax(da_in):
        return np.nanpercentile(da_in.values, 1), np.nanpercentile(da_in.values, 99)

    def _circular_boundary(ax):
        """Clip polar maps to a circle so corner artifacts don't look like land fill."""
        theta = np.linspace(0, 2 * np.pi, 361)
        verts = np.vstack([np.sin(theta), np.cos(theta)]).T
        circle = mpath.Path(verts * 0.5 + 0.5)
        ax.set_boundary(circle, transform=ax.transAxes)

    # NSIDC Sea Ice Polar Stereographic North (EPSG:3411) — matches dataset x/y
    _nsidc_globe = ccrs.Globe(semimajor_axis=6378273, semiminor_axis=6356889.449)
    data_crs = ccrs.Stereographic(
        central_latitude=90, central_longitude=-45, true_scale_latitude=70,
        globe=_nsidc_globe,
    )
    map_crs = ccrs.NorthPolarStereo(central_longitude=0)

    vmin_data, vmax_data = compute_vmin_vmax(da)
    vmin = vmin if vmin is not None else vmin_data
    vmax = vmax if vmax is not None else vmax_data

    if col is None:
        col = "time"
        try:
            da["time"]
        except AttributeError:
            da = da.assign_coords({col: "unknown"})
    col = col if sum(da[col].shape) > 1 else None

    if len(set_cbarlabel) == 0:
        set_cbarlabel = da.attrs["long_name"] + ' [' + da.attrs["units"] + ']'

    n_maps = int(da.sizes[col]) if col is not None else 1
    if n_maps not in (7, 8):
        print(f'Warning: staticArcticMaps_equal_panels expects 7 or 8 time panels; got {n_maps}')
    eight = n_maps >= 8

    ocean_mask_arr = None
    if ocean_mask is not None:
        ocean_mask_arr = np.asarray(ocean_mask).astype(bool)
        if ocean_mask_arr.ndim > 2:
            ocean_mask_arr = np.squeeze(ocean_mask_arr)

    # 2×4 equal cells; extra bottom margin when the 8th slot is also a map
    fig = plt.figure(figsize=(10.5, 6.6 if eight else 6.0))
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 1], height_ratios=[1, 1],
                          left=0.01, right=0.99, top=0.93, bottom=0.12 if eight else 0.04,
                          wspace=0.02, hspace=0.08)

    axes = []
    im = None
    use_xy = ('x' in da.coords) and ('y' in da.coords)
    if isinstance(cmap, str):
        plot_cmap = mcm.get_cmap(cmap).copy()
    else:
        plot_cmap = cmap.copy() if hasattr(cmap, 'copy') else cmap
    if hasattr(plot_cmap, 'set_bad'):
        plot_cmap.set_bad('white')

    for i in range(min(n_maps, 8)):
        row, col_idx = divmod(i, 4)
        ax = fig.add_subplot(gs[row, col_idx], projection=map_crs)
        ax.set_facecolor('white')
        axes.append(ax)

        data_to_plot = da.isel({col: i}) if col is not None else da
        data = np.asarray(data_to_plot.values, dtype=float)
        if ocean_mask_arr is not None:
            if ocean_mask_arr.shape != data.shape:
                raise ValueError(
                    f'ocean_mask shape {ocean_mask_arr.shape} != data shape {data.shape}'
                )
            # Keep land / extra-Arctic cells NaN (white); do not fill ocean NaNs
            data = np.where(ocean_mask_arr, data, np.nan)
        data = np.ma.masked_invalid(data)

        if use_xy:
            x = np.asarray(data_to_plot['x'].values)
            y = np.asarray(data_to_plot['y'].values)
            plot_kwargs = dict(transform=data_crs, shading='nearest')
            xy = (x, y)
        else:
            lon = np.asarray(data_to_plot['longitude'].values)
            lat = np.asarray(data_to_plot['latitude'].values)
            plot_kwargs = dict(transform=ccrs.PlateCarree(), shading='nearest')
            xy = (lon, lat)

        im = ax.pcolormesh(
            *xy, data, cmap=plot_cmap, vmin=vmin, vmax=vmax, zorder=1, **plot_kwargs,
        )

        ax.set_extent([-179, 179, 54, 90], crs=ccrs.PlateCarree())
        _circular_boundary(ax)
        ax.set_facecolor('white')
        ax.gridlines(draw_labels=False, linewidth=0.25, color='gray', alpha=0.7,
                     linestyle='--', zorder=2)
        ax.add_feature(
            cfeature.LAND.with_scale('50m'), facecolor=LAND_FILL,
            edgecolor='none', zorder=10,
        )
        ax.add_feature(
            cfeature.LAKES.with_scale('50m'), facecolor='white',
            edgecolor='none', zorder=11,
        )
        ax.coastlines(resolution='50m', linewidth=0.4, color='black', zorder=12)

        if len(dates) > i:
            ax.set_title(
                dates[i], fontsize=9, horizontalalignment="center",
                verticalalignment="bottom", x=0.5, y=0.97, fontweight='medium',
            )

    if im is not None:
        if eight:
            cax = fig.add_axes([0.35, 0.045, 0.30, 0.02])
            cbar = fig.colorbar(im, cax=cax, orientation='horizontal', extend='both')
        elif len(axes) >= 4:
            # Colorbar just under the top-right panel (unused 8th slot)
            cax = inset_axes(
                axes[3], width="88%", height="5%", loc='lower center',
                bbox_to_anchor=(0.0, -0.14, 1.0, 1.0), bbox_transform=axes[3].transAxes,
                borderpad=0,
            )
            cbar = fig.colorbar(im, cax=cax, orientation='horizontal', extend='both')
        else:
            cbar = None
        if cbar is not None:
            cbar.set_label(set_cbarlabel, fontsize=9, labelpad=1)
            cbar.set_ticks(np.linspace(vmin, vmax, 6))
            cbar.ax.tick_params(labelsize=8)

    if title is not None:
        fig.suptitle(title, fontsize=12, horizontalalignment="center", x=0.5, y=0.98,
                     fontweight='medium')

    if savefig:
        plt.savefig('./figs/maps_' + out_str + '.png', dpi=300, facecolor="white",
                    bbox_inches='tight')

    plt.close()
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
            ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder = 5)    # Land
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


def static_winter_comparison_lineplot(da, da_unc=None, years=None, figsize=(6.2, 2.55), start_month="Sep", 
    end_month="Apr", title="", set_ylabel = '', set_units = '', legend=True, savefig=True, save_label='', 
    annotation = '', force_complete_season=False, loc_pos=0, fmts=None,
    reanalysis_option=None, envelope=False, highlight_years=None): 
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
        fmts (list, optional): matplotlib format strings per year; if None, use a
            publication color cycle and emphasize the most recent winter
        reanalysis_option (str, optional): specify which reanalysis to use for snow depth ('m2' or 'e5'). If None, uses the default snow_depth variable.
        envelope (bool, optional): if True, show the min–max range as shading and
            the multi-winter mean as a black line, with only selected winters drawn
        highlight_years (list, optional): winter start years to overlay when
            ``envelope=True`` (default: 2020 and the most recent winter)

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
    xaxis_months = pd.date_range(start_month+"-"+str(yr), end_month+"-"+str(yr_end), freq="MS").strftime("%b")
    
    # Tableau-like hues; last winter is drawn in near-black and slightly thicker
    _colors = ['#4c78a8', '#f58518', '#54a24b', '#e45756',
               '#72b7b2', '#b279a2', '#8c6d31', '#222222']
    _markers = ['o', 's', 'D', '^', 'v', 'P', 'X', 'o']

    month_index = {m: i for i, m in enumerate(xaxis_months)}
    from matplotlib.ticker import MaxNLocator

    rc = {
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'axes.grid': False,
        'xtick.top': False,
        'ytick.right': False,
    }
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_xlim(-0.35, len(xaxis_months) - 0.65)
        ax.set_xticks(range(len(xaxis_months)))
        ax.set_xticklabels(list(xaxis_months))
        ax.grid(False)
        ax.xaxis.grid(False)
        ax.yaxis.grid(True, linestyle='-', linewidth=0.4, color='0.88', zorder=0)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, prune=None))
        ax.minorticks_off()
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for spine in ('left', 'bottom'):
            ax.spines[spine].set_linewidth(0.8)
            ax.spines[spine].set_color('0.15')
        ax.tick_params(axis='x', which='both', top=False, length=3.2, width=0.6)
        ax.tick_params(axis='y', which='both', right=False, length=3.2, width=0.6)

        plotted = 0
        n_months = len(xaxis_months)
        series = []
        labels_by_year = {}
        for year in years:
            winter_da = get_winter_data(da, year_start=year, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season)
            if winter_da is None:
                continue
            y = winter_da.mean(dim=["x","y"], keep_attrs=True)
            x = pd.to_datetime(y.time.values)
            y_month = np.full(n_months, np.nan)
            for m, val in zip(x.strftime("%b"), np.asarray(y.values, dtype=float)):
                if m in month_index:
                    y_month[month_index[m]] = val
            year_int = int(str(year)[:4])
            if reanalysis_option is not None:
                labels_by_year[year_int] = f"{x.year[0]}-{str(x.year[-1])[2:]} ({reanalysis_option.upper()})"
            else:
                labels_by_year[year_int] = f"{x.year[0]}-{str(x.year[-1])[2:]}"
            series.append((year_int, y_month))

            if (not envelope) and (da_unc is not None):
                winter_da_unc = get_winter_data(da_unc, year_start=year, start_month=start_month, end_month=end_month, force_complete_season=force_complete_season)
                if winter_da_unc is not None:
                    yu = winter_da_unc.mean(dim=["x","y"], keep_attrs=True)
                    x_idx = [month_index[m] for m in x.strftime("%b") if m in month_index]
                    ax.fill_between(
                        x_idx, np.asarray(y.values) - np.asarray(yu.values),
                        np.asarray(y.values) + np.asarray(yu.values),
                        facecolor='0.5', alpha=0.12, edgecolor='none', zorder=2,
                    )

        x_idx_all = np.arange(n_months)
        if envelope and series:
            stack = np.vstack([s[1] for s in series])
            y_min = np.nanmin(stack, axis=0)
            y_max = np.nanmax(stack, axis=0)
            y_mean = np.nanmean(stack, axis=0)
            valid = np.isfinite(y_mean)
            year0 = series[0][0]
            year1 = series[-1][0] + 1
            ax.fill_between(
                x_idx_all[valid], y_min[valid], y_max[valid],
                color='0.78', alpha=0.55, linewidth=0, zorder=1,
                label=f'{year0} to {year1} range',
            )
            ax.plot(
                x_idx_all[valid], y_mean[valid], color='0.05', linewidth=1.9,
                linestyle='-', zorder=4, label='Mean',
            )
            plotted += 2

            available = [s[0] for s in series]
            latest = available[-1]
            if highlight_years is None:
                overlay = [2020, latest]
            else:
                overlay = [int(str(y)[:4]) for y in highlight_years] + [latest]
            overlay = list(dict.fromkeys([y for y in overlay if y in available]))
            overlay_styles = {
                2020: dict(color='#4c78a8', marker='o'),
                latest: dict(color='#e45756', marker='s'),
            }
            series_map = {y: ym for y, ym in series}
            for year_int in overlay:
                style = overlay_styles.get(year_int, dict(color='#54a24b', marker='D'))
                ym = series_map[year_int]
                ok = np.isfinite(ym)
                ax.plot(
                    x_idx_all[ok], ym[ok], label=labels_by_year[year_int],
                    color=style['color'], linestyle='-', marker=style['marker'],
                    markersize=4.2, linewidth=1.7,
                    markeredgecolor='white', markeredgewidth=0.35, zorder=5,
                )
                plotted += 1
        else:
            n_years = len(series)
            for i, (year_int, y_month) in enumerate(series):
                ok = np.isfinite(y_month)
                is_latest = (i == n_years - 1)
                if fmts is None:
                    ax.plot(
                        x_idx_all[ok], y_month[ok], label=labels_by_year[year_int],
                        color=_colors[i % len(_colors)], linestyle='-',
                        marker=_markers[i % len(_markers)],
                        markersize=4.0 if is_latest else 3.2,
                        linewidth=1.8 if is_latest else 1.15,
                        markeredgecolor='white', markeredgewidth=0.35,
                        zorder=5 if is_latest else 3,
                    )
                else:
                    ax.plot(
                        x_idx_all[ok], y_month[ok], fmts[i % len(fmts)],
                        label=labels_by_year[year_int], markersize=4,
                        zorder=5 if is_latest else 3,
                    )
                plotted += 1

        ax.margins(y=0.08)
        ax.set_xlim(-0.35, len(xaxis_months) - 0.65)
        ax.xaxis.grid(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        if legend:
            ncol = 2 if plotted > 5 else 1
            legend_kwargs = dict(
                fontsize=7, frameon=False, ncol=ncol, handlelength=1.6,
                columnspacing=1.0, labelspacing=0.25, borderaxespad=0.3,
            )
            if loc_pos > 0:
                ax.legend(loc=loc_pos, **legend_kwargs)
            else:
                ax.legend(loc='best', **legend_kwargs)

        if annotation:
            ax.annotate(
                annotation, xy=(0.02, 0.98), xycoords='axes fraction',
                horizontalalignment='left', verticalalignment='top',
                fontsize=8, fontweight='medium', zorder=6,
            )

        if title:
            ax.set_title(title, fontsize=9, pad=4)

        if len(set_ylabel) > 0:
            ylabel = set_ylabel
            if len(set_units) > 0:
                ylabel = f"{set_ylabel} ({set_units})"
        elif "long_name" in da.attrs:
            ylabel = da.attrs["long_name"]
            if "units" in da.attrs:
                ylabel += " (" + da.attrs["units"] + ")"
            ylabel = "\n".join(wrap(ylabel, 35))
        else:
            ylabel = None

        ax.set_ylabel(ylabel, fontsize=8)
        ax.tick_params(
            axis='both', which='major', labelsize=8, length=3.2, width=0.6,
            color='0.25', top=False, right=False,
        )
        ax.tick_params(axis='x', which='major', pad=2)
        fig.tight_layout()

        if savefig:
            if reanalysis_option is not None:
                filename = f'./figs/{da.attrs.get("long_name", "data")}{start_month}{end_month}{years[0]}-{years[-1]+1}{save_label}_{reanalysis_option}.pdf'
            else:
                filename = f'./figs/{da.attrs.get("long_name", "data")}{start_month}{end_month}{years[0]}-{years[-1]+1}{save_label}.pdf'
            fig.savefig(filename, dpi=300, facecolor="white", bbox_inches='tight')

        plt.show()


def static_winter_comparison_lineplot_with_reanalysis(da, reanalysis_option='m2', da_unc=None, years=None, figsize=(5,3), start_month="Sep", 
    end_month="Apr", title="", set_ylabel = '', set_units = '', legend=True, savefig=True, save_label='', 
    annotation = '', force_complete_season=False, loc_pos=0, fmts=None): 
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


def _time_from_dataarray(da: xr.DataArray):
    """Get a single datetime from a DataArray's time coordinate (scalar or 0-d)."""
    t = da.coords.get("time")
    if t is None:
        raise ValueError("DataArray must have a 'time' coordinate")
    val = np.atleast_1d(pd.to_datetime(t.values))
    return val.flat[0]


def _panel_letter_triple(start: str) -> list:
    """``(a)``, ``(b)``, ``(c)`` from ``start='a'``; ``(d)``…``(f)`` from ``'d'``, etc."""
    s = start.strip().lower()
    if len(s) != 1 or not ("a" <= s <= "x"):
        raise ValueError("panel_letters_start must be a single lowercase letter a–x")
    o = ord(s)
    return [f"({chr(o + i)})" for i in range(3)]


def plot_is2_v4_vs_fused_three_panel(
    dataarray1: xr.DataArray,
    dataarray2: xr.DataArray,
    title1: str = "",
    title2: str = "",
    vmin_thick: float = 0.0,
    vmax_thick: float = 4.0,
    diff_range: tuple = (-2.5, 2.5),
    central_longitude: float = -45.0,
    min_lat: float = 55.0,
    cbarlabels=None,
    cmaps=("viridis", "viridis", "RdBu"),
    panel_letters_start: str = "a",
):
    """
    Three-panel Arctic map: two fields and their difference.

    Panels (letters set by ``panel_letters_start``, default ``a`` → (a)(b)(c);
    use e.g. ``d`` for (d)(e)(f) when stacking rows for one date):

        First panel: ``title1`` (default IS2SITMOGR4-V4) with month–year from ``dataarray1``.
        Second: ``title2`` (default IS2SMGPSIT-V1).
        Third: difference field, captioned with the third letter and
        ``(second letter) − (first letter)`` (panel 2 minus panel 1), e.g. ``(i) (h) − (g)``
        when ``panel_letters_start='g'``.

    All panels use a North Polar Stereographic projection with per-panel colorbars.
    Each DataArray must have coordinates ``time``, ``latitude``, and ``longitude``;
    the function uses ``dataarray1`` time for the month in the first panel caption.

    Parameters
    ----------
    dataarray1 : xr.DataArray
        First field (2D with coords ``time``, ``latitude``, ``longitude``).
    dataarray2 : xr.DataArray
        Second field (same requirement).
    title1 : str, default ""
        Product name for the first panel; default ``IS2SITMOGR4-V4``.
    title2 : str, default ""
        Product name for the second panel; default ``IS2SMGPSIT-V1``.
    vmin_thick, vmax_thick : float
        Color scale limits for the first two panels.
    diff_range : (float, float)
        (vmin, vmax) for the difference (third) panel.
    central_longitude : float, optional
        Central longitude for the North Polar Stereographic projection.
    min_lat : float, optional
        Southern latitude limit for the map extent (default 55°N).
    cbarlabels : list of str or None, optional
        Labels for the three colorbars. If None, sensible defaults are used.
    cmaps : sequence of three matplotlib colormaps, optional
        Colormaps for panels (a), (b), and (c). Default is
        ``("viridis", "viridis", "RdBu")``. Use ``("YlOrRd", "YlOrRd", "RdBu")``
        for freeboard and ``("inferno", "inferno", "RdBu")`` for snow depth to
        match the colour conventions in the chapter-2 winter notebooks.
    panel_letters_start : str, default ``\"a\"``
        First panel letter (lowercase ``a``–``x``). The three panels use this letter
        and the next two (e.g. ``d`` → (d), (e), (f); ``g`` → (g), (h), (i)).

    Returns
    -------
    fig : matplotlib.figure.Figure
    axes : numpy.ndarray of cartopy.mpl.geoaxes.GeoAxes
    """
    time1 = _time_from_dataarray(dataarray1)
    lon1 = dataarray1.coords["longitude"]
    lat1 = dataarray1.coords["latitude"]
    lon2 = dataarray2.coords["longitude"]
    lat2 = dataarray2.coords["latitude"]

    # Difference: panel 2 minus panel 1
    diff = (dataarray2 - dataarray1).rename("difference")

    name1 = title1 if title1 else "IS2SITMOGR4-V4"
    name2 = title2 if title2 else "IS2SMGPSIT-V1"
    month_str = pd.to_datetime(time1).strftime("%B %Y")

    # Match manuscript width; height chosen so 3× polar row + bottom colorbars
    # fill the canvas (slightly wider aspect than 15/5.75 to trim vertical slack).
    fig_width = 15.0
    fig_height = 5.45
    proj = ccrs.NorthPolarStereo(central_longitude=central_longitude)

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(fig_width, fig_height),
        subplot_kw={"projection": proj},
    )

    vmins = [vmin_thick, vmin_thick, diff_range[0]]
    vmaxs = [vmax_thick, vmax_thick, diff_range[1]]
    cmaps = list(cmaps)

    maps = [dataarray1, dataarray2, diff]
    lons = [lon1, lon2, lon2]
    lats = [lat1, lat2, lat2]

    panel_letters = _panel_letter_triple(panel_letters_start)
    panel_captions = [
        f"{panel_letters[0]} {name1} ({month_str})",
        f"{panel_letters[1]} {name2}",
        f"{panel_letters[2]} {panel_letters[1]} \u2212 {panel_letters[0]}",
    ]

    ims = []
    for i, (ax, data, lon, lat) in enumerate(zip(axes, maps, lons, lats)):
        im = ax.pcolormesh(
            lon,
            lat,
            data,
            transform=ccrs.PlateCarree(),
            cmap=cmaps[i],
            vmin=vmins[i],
            vmax=vmaxs[i],
        )
        ims.append(im)

        ax.coastlines(linewidth=0.15, color="black", zorder=2)
        ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder=1)
        ax.gridlines(
            draw_labels=False,
            linewidth=0.25,
            color="gray",
            alpha=0.7,
            linestyle="--",
            zorder=3,
        )
        ax.set_extent([-179, 179, min_lat, 90], crs=ccrs.PlateCarree())

        ax.annotate(
            panel_captions[i],
            xy=(0.98, 0.98),
            xycoords="axes fraction",
            va="top",
            ha="right",
            color="k",
            fontsize=8,
        )
        ax.set_title("")

    # Per-panel colorbars below each panel (looped)
    if cbarlabels is None:
        cbarlabels = [
            "Sea ice thickness (m)",
            "Sea ice thickness (m)",
            "Thickness difference (m)",
        ]
    tick_n = 5

    # Adjust layout before creating colorbars (tight margins + slight overlap:
    # polar stereo leaves corner wedges; negative wspace pulls panels together.)
    plt.subplots_adjust(
        left=0.008,
        right=0.998,
        bottom=0.068,
        top=0.994,
        wspace=-0.028,
    )

    # Create a bottom colorbar for each panel using the final axes positions
    for i, ax in enumerate(axes):
        cax, kw = mcbar.make_axes(ax, location="bottom", pad=0.006, shrink=0.52)
        cb = fig.colorbar(ims[i], cax=cax, extend="both", **kw)
        cb.set_ticks(np.linspace(vmins[i], vmaxs[i], tick_n))
        cb.set_label(cbarlabels[i], labelpad=2, fontsize=8)

    return fig, axes


def plot_is2_v4_vs_fused_nine_panel(
    dataarrays1,
    dataarrays2,
    title1: str = "",
    title2: str = "",
    row_labels=("Sea ice thickness", "Total freeboard", "Snow depth"),
    value_ranges=((0.0, 4.0), (0.0, 0.6), (0.0, 0.4)),
    diff_ranges=((-2.5, 2.5), (-0.2, 0.2), (-0.2, 0.2)),
    value_cbarlabels=(
        "Sea ice thickness (m)",
        "Total freeboard (m)",
        "Snow depth (m)",
    ),
    diff_cbarlabels=(
        "Thickness difference (m)",
        "Freeboard difference (m)",
        "Snow depth difference (m)",
    ),
    cmaps=("viridis", "YlOrRd", "inferno"),
    diff_cmap="RdBu",
    central_longitude: float = -45.0,
    min_lat: float = 55.0,
    panel_letters_start: str = "a",
    figsize=(10.5, 10.0),
):
    """Compact nine-panel comparison of three V4 and fused variables.

    Rows contain sea ice thickness, total freeboard, and snow depth by default.
    Columns contain IS2SITMOGR4-V4, IS2SMGPSIT-V1, and fused minus V4. Panel
    letters run row-wise from ``(a)`` to ``(i)``. Compact inset colorbars sit in
    the unused upper-right corner of each polar panel (label below ticks), with
    a small gutter between panels.

    Parameters
    ----------
    dataarrays1, dataarrays2 : sequence of three xr.DataArray
        V4 and fused fields, respectively. Each field must be two-dimensional
        with scalar ``time`` and ``latitude``/``longitude`` coordinates. All six
        fields must represent the same calendar month.
    title1, title2 : str, optional
        Column product names. Defaults are ``IS2SITMOGR4-V4`` and
        ``IS2SMGPSIT-V1``.
    row_labels : sequence of three str
        Kept for API compatibility; not drawn on the figure (row identity is
        conveyed by the per-panel colorbar labels).
    value_ranges, diff_ranges : sequence of three (float, float) pairs
        Row-specific limits for the product fields and difference fields.
    value_cbarlabels, diff_cbarlabels : sequence of three str
        Row-specific colorbar labels.
    cmaps : sequence of three matplotlib colormaps
        Row-specific colormaps used for both product columns.
    diff_cmap : matplotlib colormap
        Colormap used for all three difference panels.
    central_longitude, min_lat : float
        North Polar Stereographic central longitude and southern map limit.
    panel_letters_start : str
        First lowercase panel letter. The default produces ``(a)``--``(i)``.
    figsize : (float, float)
        Figure size in inches.

    Returns
    -------
    fig : matplotlib.figure.Figure
    axes : numpy.ndarray
        A 3-by-3 array of Cartopy GeoAxes.
    """
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    dataarrays1 = list(dataarrays1)
    dataarrays2 = list(dataarrays2)
    row_labels = list(row_labels)
    value_ranges = list(value_ranges)
    diff_ranges = list(diff_ranges)
    value_cbarlabels = list(value_cbarlabels)
    diff_cbarlabels = list(diff_cbarlabels)
    cmaps = list(cmaps)

    row_options = {
        "dataarrays1": dataarrays1,
        "dataarrays2": dataarrays2,
        "row_labels": row_labels,
        "value_ranges": value_ranges,
        "diff_ranges": diff_ranges,
        "value_cbarlabels": value_cbarlabels,
        "diff_cbarlabels": diff_cbarlabels,
        "cmaps": cmaps,
    }
    for option_name, values in row_options.items():
        if len(values) != 3:
            raise ValueError(f"{option_name} must contain exactly three items")

    panel_start = panel_letters_start.strip().lower()
    if len(panel_start) != 1 or not ("a" <= panel_start <= "r"):
        raise ValueError("panel_letters_start must be a single lowercase letter a–r")
    panel_letters = [f"({chr(ord(panel_start) + i)})" for i in range(9)]

    month_periods = {
        pd.Timestamp(_time_from_dataarray(da)).to_period("M")
        for da in dataarrays1 + dataarrays2
    }
    if len(month_periods) != 1:
        raise ValueError("All six DataArrays must represent the same calendar month")
    month_str = next(iter(month_periods)).strftime("%B %Y")

    name1 = title1 if title1 else "IS2SITMOGR4-V4"
    name2 = title2 if title2 else "IS2SMGPSIT-V1"
    column_titles = [f"{name1}\n{month_str}", name2, f"{name2} − {name1}"]

    proj = ccrs.NorthPolarStereo(central_longitude=central_longitude)
    fig, axes = plt.subplots(
        3,
        3,
        figsize=figsize,
        subplot_kw={"projection": proj},
    )

    # Keep a small gutter between polar panels while still using the unused
    # corner wedges for inset colorbars.
    fig.subplots_adjust(
        left=0.01,
        right=0.995,
        bottom=0.01,
        top=0.955,
        wspace=0.08,
        hspace=0.10,
    )

    for row, (data1, data2) in enumerate(zip(dataarrays1, dataarrays2)):
        difference = (data2 - data1).rename("difference")
        maps = (data1, data2, difference)
        lons = (
            data1.coords["longitude"],
            data2.coords["longitude"],
            data2.coords["longitude"],
        )
        lats = (
            data1.coords["latitude"],
            data2.coords["latitude"],
            data2.coords["latitude"],
        )
        limits = (value_ranges[row], value_ranges[row], diff_ranges[row])
        row_cmaps = (cmaps[row], cmaps[row], diff_cmap)
        cbarlabels = (
            value_cbarlabels[row],
            value_cbarlabels[row],
            diff_cbarlabels[row],
        )

        for col, (data, lon, lat, limits_i, cmap_i) in enumerate(
            zip(maps, lons, lats, limits, row_cmaps)
        ):
            ax = axes[row, col]
            vmin, vmax = limits_i
            im = ax.pcolormesh(
                lon,
                lat,
                data,
                transform=ccrs.PlateCarree(),
                cmap=cmap_i,
                vmin=vmin,
                vmax=vmax,
                shading="auto",
            )

            ax.coastlines(linewidth=0.15, color="black", zorder=2)
            ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder=1)
            ax.gridlines(
                draw_labels=False,
                linewidth=0.25,
                color="gray",
                alpha=0.7,
                linestyle="--",
                zorder=3,
            )
            ax.set_extent([-179, 179, min_lat, 90], crs=ccrs.PlateCarree())
            ax.set_title(column_titles[col] if row == 0 else "", fontsize=9, pad=1)

            ax.annotate(
                panel_letters[row * 3 + col],
                xy=(0.025, 0.965),
                xycoords="axes fraction",
                va="top",
                ha="left",
                fontsize=8.5,
                fontweight="bold",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 1},
                zorder=5,
            )

            # Put each colorbar in the unused upper-right corner of its polar
            # axes: more room for the bar, ticks, and label underneath.
            cax = inset_axes(
                ax,
                width="48%",
                height="3.2%",
                loc="upper right",
                bbox_to_anchor=(0.0, 0.0, 0.985, 0.955),
                bbox_transform=ax.transAxes,
                borderpad=0,
            )
            cb = fig.colorbar(im, cax=cax, orientation="horizontal", extend="both")
            cb.set_ticks(np.linspace(vmin, vmax, 5))
            cb.ax.xaxis.set_ticks_position("bottom")
            cb.ax.xaxis.set_label_position("bottom")
            cb.set_label(cbarlabels[col], labelpad=1.5, fontsize=6.5)
            cb.ax.tick_params(labelsize=6, length=1.5, pad=1)

    return fig, axes


def plot_is2smgpsit_thickness_unc_three_months(
    da_oct: xr.DataArray,
    da_jan: xr.DataArray,
    da_mar: xr.DataArray,
    central_longitude: float = -45.0,
    min_lat: float = 55.0,
    vmin: float = 0.0,
    vmax: float = 0.65,
    cmap: str = "viridis",
    panel_letters_start: str = "a",
    product_name: str = "IS2SMGPSIT-V1",
):
    """
    One-row, three-panel Arctic map of GP ice-thickness uncertainty for three months
    (typically October, January, March) shown side-by-side.
    """
    fig_width = 15.0
    fig_height = 5.45
    proj = ccrs.NorthPolarStereo(central_longitude=central_longitude)

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(fig_width, fig_height),
        subplot_kw={"projection": proj},
    )

    months = [da_oct, da_jan, da_mar]
    panel_letters = _panel_letter_triple(panel_letters_start)

    ims = []
    for i, (ax, da) in enumerate(zip(axes, months)):
        time0 = _time_from_dataarray(da)
        month_str = pd.to_datetime(time0).strftime("%B %Y")
        lon = da.coords["longitude"]
        lat = da.coords["latitude"]

        im = ax.pcolormesh(
            lon,
            lat,
            da,
            transform=ccrs.PlateCarree(),
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
        )
        ims.append(im)

        ax.coastlines(linewidth=0.15, color="black", zorder=2)
        ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder=1)
        ax.gridlines(
            draw_labels=False,
            linewidth=0.25,
            color="gray",
            alpha=0.7,
            linestyle="--",
            zorder=3,
        )
        ax.set_extent([-179, 179, min_lat, 90], crs=ccrs.PlateCarree())

        ax.annotate(
            f"{panel_letters[i]} {month_str}",
            xy=(0.98, 0.98),
            xycoords="axes fraction",
            va="top",
            ha="right",
            color="k",
            fontsize=8,
        )
        ax.set_title("")

    plt.subplots_adjust(
        left=0.008,
        right=0.998,
        bottom=0.068,
        top=0.994,
        wspace=-0.028,
    )

    tick_n = 5
    for i, ax in enumerate(axes):
        cax, kw = mcbar.make_axes(ax, location="bottom", pad=0.006, shrink=0.52)
        cb = fig.colorbar(ims[i], cax=cax, extend="max", **kw)
        cb.set_ticks(np.linspace(vmin, vmax, tick_n))
        cb.set_label("Thickness uncertainty (m)", labelpad=2, fontsize=8)

    return fig, axes


def plot_is2smgpsit_uncertainty_three_panel(
    da_freeboard_unc: xr.DataArray,
    da_snow_unc: xr.DataArray,
    da_thickness_unc: xr.DataArray,
    central_longitude: float = -45.0,
    min_lat: float = 55.0,
    vmins: tuple = (0.0, 0.0, 0.0),
    vmaxs: tuple = (0.2, 0.15, 0.65),
    cbarlabels=None,
    cmaps=("viridis", "viridis", "viridis"),
    panel_letters_start: str = "a",
    product_name: str = "IS2SMGPSIT-V1",
):
    """
    Three-panel Arctic maps of GP predictive uncertainty (standard deviation) for
    the fused product: freeboard, snow depth, and ice thickness (single time slice).

    Layout matches ``plot_is2_v4_vs_fused_three_panel`` (polar stereo row + colorbars).
    """
    time0 = _time_from_dataarray(da_freeboard_unc)
    month_str = pd.to_datetime(time0).strftime("%B %Y")

    lon = da_freeboard_unc.coords["longitude"]
    lat = da_freeboard_unc.coords["latitude"]

    fig_width = 15.0
    fig_height = 5.45
    proj = ccrs.NorthPolarStereo(central_longitude=central_longitude)

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(fig_width, fig_height),
        subplot_kw={"projection": proj},
    )

    maps = [da_freeboard_unc, da_snow_unc, da_thickness_unc]
    vmins = list(vmins)
    vmaxs = list(vmaxs)
    cmaps = list(cmaps)

    if cbarlabels is None:
        cbarlabels = [
            "Freeboard uncertainty (m)",
            "Snow depth uncertainty (m)",
            "Thickness uncertainty (m)",
        ]

    panel_letters = _panel_letter_triple(panel_letters_start)
    names = ["Total freeboard", "Snow depth", "Sea ice thickness"]
    panel_captions = [
        f"{panel_letters[i]} {product_name}: {names[i]} uncertainty ({month_str})"
        for i in range(3)
    ]

    ims = []
    for i, (ax, data) in enumerate(zip(axes, maps)):
        im = ax.pcolormesh(
            lon,
            lat,
            data,
            transform=ccrs.PlateCarree(),
            cmap=cmaps[i],
            vmin=vmins[i],
            vmax=vmaxs[i],
        )
        ims.append(im)

        ax.coastlines(linewidth=0.15, color="black", zorder=2)
        ax.add_feature(cfeature.LAND, color=LAND_FILL, zorder=1)
        ax.gridlines(
            draw_labels=False,
            linewidth=0.25,
            color="gray",
            alpha=0.7,
            linestyle="--",
            zorder=3,
        )
        ax.set_extent([-179, 179, min_lat, 90], crs=ccrs.PlateCarree())

        ax.annotate(
            panel_captions[i],
            xy=(0.98, 0.98),
            xycoords="axes fraction",
            va="top",
            ha="right",
            color="k",
            fontsize=8,
        )
        ax.set_title("")

    tick_n = 5
    plt.subplots_adjust(
        left=0.008,
        right=0.998,
        bottom=0.068,
        top=0.994,
        wspace=-0.028,
    )

    for i, ax in enumerate(axes):
        cax, kw = mcbar.make_axes(ax, location="bottom", pad=0.006, shrink=0.52)
        cb = fig.colorbar(ims[i], cax=cax, extend="max", **kw)
        cb.set_ticks(np.linspace(vmins[i], vmaxs[i], tick_n))
        cb.set_label(cbarlabels[i], labelpad=2, fontsize=8)

    return fig, axes
