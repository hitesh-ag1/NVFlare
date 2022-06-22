from typing import Dict, List, NamedTuple, Optional

import numpy as np
import pandas as pd
from pandas.core.series import Series

from .feature_stats_def import DataType

# code logic borrowed from
# https://github.com/PAIR-code/facets/blob/master/facets_overview/python/base_generic_feature_statistics_generator.py
# credit should go to Google

nat_as_integer = np.datetime64("NAT").view("i8")


class FeatureEntry(NamedTuple):
    feature_name: str
    data_type: DataType
    values: Series
    counts: List[int]
    missing: int
    feature_lens: Optional[List[int]] = None


class EntryDataSet(NamedTuple):
    name: str
    size: int
    entries: Dict[str, FeatureEntry]


class FeatureEntryGenerator:
    def __init__(self):
        pass

    def to_table_entries(self, dataframes: Dict[str, pd.DataFrame]) -> List[EntryDataSet]:
        datasets: List[EntryDataSet] = []
        for ds_name in dataframes:
            df = dataframes[ds_name]
            df_entries: Dict[str, FeatureEntry] = {}
            for col in df:
                df_entries[col] = self.feature_entry(col, df[col])

            datasets.append(EntryDataSet(ds_name, len(df), df_entries))

        return datasets

    def feature_entry(self, name: str, feature: Series) -> FeatureEntry:
        row_counts = []
        data_type = self.dtype_to_data_type(feature.dtype)
        for row in feature:
            cnt = self._get_count(row, data_type)
            if cnt > 0:
                row_counts.append(self._get_count(row, data_type))

        flattened = feature.ravel()
        orig_size = len(flattened)
        flattened = flattened[flattened != np.array(None)]

        if data_type == DataType.DATETIME:
            # DATETIME is treated as INT
            dt2n_converter = self.dt_to_num_converter(x.dtype)
            flattened = dt2n_converter(flattened)
            data_type = DataType.INT
        elif data_type == DataType.STRING:
            flattened_temp = []
            for x in flattened:
                try:
                    if x is not None and str(x) != "None" and str(x) != "nan":
                        flattened_temp.append(x)
                except UnicodeEncodeError:
                    if x.encode("utf-8") != "nan":
                        flattened_temp.append(x)
            flattened = flattened_temp
        else:
            flattened = flattened[~np.isnan(flattened)].tolist()

        missing = orig_size - len(flattened)

        return FeatureEntry(name, data_type, flattened, row_counts, missing)

    def _get_count(self, row, data_type: DataType) -> int:
        count = 0
        if DataType.INT == data_type or DataType.FLOAT == data_type:
            if row is not None and ~np.isnan(row):
                count = 1
        elif DataType.STRING == data_type:
            if row:
                count = 1
        elif DataType.DATETIME == data_type:
            if row is not None and type(row) != pd._libs.tslibs.nattype.NaTType:
                count = 1
        # todo : handle array structure an

        # try:
        #     print("row=", row)
        #     rc = np.count_nonzero(~np.isnan(row))
        #     print("rc=", rc)
        #     if rc != 0:
        #         count = rc
        # except TypeError as t:
        #     print(f"type error {t}")
        #     try:
        #         count = row.size
        #     except AttributeError as e:
        #         print(f" AttributeError {e}")
        #         count = 1
        return count

    @staticmethod
    def dtype_to_data_type(dtype) -> DataType:
        if dtype.char in np.typecodes["AllFloat"]:
            return DataType.FLOAT
        elif dtype.char in np.typecodes["AllInteger"] or dtype == bool:
            return DataType.INT
        elif np.issubdtype(dtype, np.datetime64) or np.issubdtype(dtype, np.timedelta64):
            return DataType.DATETIME
        else:
            return DataType.STRING

    @staticmethod
    def dt_to_num_converter(dtype):
        if np.issubdtype(dtype, np.datetime64):

            def dt_to_numbers(dt_list):
                return np.array([pd.Timestamp(dt).value for dt in dt_list])

            return dt_to_numbers

        elif np.issubdtype(dtype, np.timedelta64):

            def time_delta_to_numbers(td_list):
                return np.array([pd.Timedelta(td).value for td in td_list])

            return time_delta_to_numbers
        else:
            return None
