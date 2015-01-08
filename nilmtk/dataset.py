from __future__ import print_function, division
import os
from collections import OrderedDict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from .building import Building
from .datastore.datastore import join_key
from .utils import get_datastore
from .timeframe import TimeFrame

class DataSet(object):
    """
    Attributes
    ----------
    buildings : OrderedDict
        Each key is an integer, starting from 1.
        Each value is a nilmtk.Building object.

    store : nilmtk.DataStore

    metadata : dict
        Metadata describing the dataset name, authors etc.
        (Metadata about specific buildings, meters, appliances etc.
        is stored elsewhere.)
        See http://nilm-metadata.readthedocs.org/en/latest/dataset_metadata.html#dataset
    """

    def __init__(self, filename=None, format='HDF'):
        """
        Parameters
        ----------
        filename : str
            path to data set
        
        format : str
            format of output. Either 'HDF' or 'CSV'. Defaults to 'HDF'
        """
        self.store = None
        self.buildings = OrderedDict()
        self.metadata = {}
        if filename is not None:
            self.import_metadata(get_datastore(filename, format))
        
    def import_metadata(self, store):
        """
        Parameters
        ----------
        store : nilmtk.DataStore
        """
        self.store = store
        self.metadata = store.load_metadata()
        self._init_buildings(store)
        return self
        
    def save(self, destination):
        for b_id, building in self.buildings.iteritems():
            building.save(destination, '/building' + str(b_id))

    def _init_buildings(self, store):
        buildings = store.elements_below_key('/')
        buildings.sort()

        for b_key in buildings:
            building = Building()
            building.import_metadata(store, '/'+b_key, self.metadata.get('name'))
            self.buildings[building.identifier.instance] = building

    def set_window(self, start=None, end=None):
        """Set the timeframe window on self.store. Used for setting the 
        'region of interest' non-destructively for all processing.
        
        Parameters
        ----------
        start, end : str or pd.Timestamp or datetime or None
        """
        if self.store is None:
            raise RuntimeError("You need to set self.store first!")

        tz = self.metadata.get('timezone')
        if tz is None:
            raise RuntimeError("'timezone' is not set in dataset metadata.")

        self.store.window = TimeFrame(start, end, tz)

    def describe(self, **kwargs):
        """Returns a DataFrame describing this dataset.  
        Each column is a building.  Each row is a feature."""
        keys = self.buildings.keys()
        keys.sort()
        results = pd.DataFrame(columns=keys)
        for i, building in self.buildings.iteritems():
            results[i] = building.describe(**kwargs)
        return results

    def plot_good_sections(self, axes=None, label_func=None, gap=0, **kwargs):
        """Plots all good sections for all buildings.

        Parameters
        ----------
        axes : list of axes or None.
            If None then they will be generated.

        Returns
        -------
        axes : list of axes
        """
        n = len(self.buildings)
        if axes is None:
            n_meters_per_building = [len(elec.all_meters()) 
                                     for elec in self.elecs()]
            gridspec_kw = dict(height_ratios=n_meters_per_building)
            fig, axes = plt.subplots(n, 1, sharex=True, gridspec_kw=gridspec_kw)
                                     
        assert n == len(axes)
        for i, (ax, elec) in enumerate(zip(axes, self.elecs())):
            elec.plot_good_sections(ax=ax, label_func=label_func, gap=gap, 
                                    **kwargs)
            ax.set_title('House {}'.format(elec.building()), y=0.4, va='top')
            ax.grid(False)
            for spine in ax.spines.values():
                spine.set_linewidth(0.5)
            if i == n // 2:
                ax.set_ylabel('Meter', rotation=0, 
                              ha='center', va='center', y=.4)

        ax.set_xlabel('Date')

        plt.tight_layout()
        plt.subplots_adjust(hspace=0.05)
        plt.draw()

        return axes

    def elecs(self):
        return [building.elec for building in self.buildings.values()]

    def clear_cache(self):
        for elec in self.elecs():
            elec.clear_cache()

    def plot_mains_power_histograms(self, axes=None, **kwargs):
        n = len(self.buildings)
        if axes is None:
            fig, axes = plt.subplots(n, 1, sharex=True)
        assert n == len(axes)

        for ax, elec in zip(axes, self.elecs()):
            ax = elec.mains().plot_power_histogram(ax=ax, **kwargs)
            ax.set_title('House {}'.format(elec.building()))
        return axes
