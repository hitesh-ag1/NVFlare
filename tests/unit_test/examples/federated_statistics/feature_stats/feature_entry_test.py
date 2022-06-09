import numpy as np
import pandas as pd
import pytest

from examples.federated_statistics.fed_stats.custom.feature_stats.feature_entry import (
    EntryDataSet,
    FeatureEntry,
    FeatureEntryGenerator,
)
from examples.federated_statistics.fed_stats.custom.feature_stats.feature_stats_def import DataType


class TestFeatureEntryGenerator:
    @classmethod
    def setup_class(cls):
        print("starting class: {} execution".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print("starting class: {} execution".format(cls.__name__))

    def setup_method(self, method):
        print("starting execution of tc: {}".format(method.__name__))
        self.gen = FeatureEntryGenerator()

    def teardown_method(self, method):
        print("starting execution of tc: {}".format(method.__name__))

    @pytest.mark.parametrize(
        "test_data, dtype, expected_missing_data ",
        [
            [[None, 1.0, 2.0, None, float("nan"), 3.0], float, 3],
            [[None, "one", "two", None, float("nan"), "three"], str, 3],
        ],
    )
    def test_ndarray_to_feature_entry(self, test_data, dtype, expected_missing_data):
        arr = np.array(test_data, dtype=dtype)
        df = pd.DataFrame(arr, columns=["feature"])
        feature_data = self.gen.feature_entry("hi", feature=df["feature"])
        assert expected_missing_data == feature_data.missing

    @pytest.mark.parametrize(
        "string_dates, expected_times",
        [[["1972-02-01", "2005-02-25", "2006-02-25"], [65750400000000000, 1109289600000000000, 1140825600000000000]]],
    )
    def test_dt_to_num_converter(self, string_dates, expected_times):
        # not handle date time with time zone and hh:mm:ss
        converter = self.gen.dt_to_num_converter(dtype=np.datetime64)
        arr = np.array([np.datetime64(dt) for dt in string_dates], dtype=np.datetime64)
        dts = converter(arr)
        assert dts is not None
        assert dts.tolist() == expected_times

    def test_dtype_to_data_type_conversion(self):
        assert DataType.INT == self.gen.dtype_to_data_type(np.dtype(np.int32))
        # Boolean treated as INT
        assert DataType.INT == self.gen.dtype_to_data_type(np.dtype(bool))
        assert DataType.INT == self.gen.dtype_to_data_type(np.dtype(np.bool_))
        assert DataType.DATETIME == self.gen.dtype_to_data_type(np.dtype(np.timedelta64))
        assert DataType.DATETIME == self.gen.dtype_to_data_type(np.dtype(np.datetime64))
        assert DataType.FLOAT == self.gen.dtype_to_data_type(np.dtype(np.float32))
        assert DataType.STRING == self.gen.dtype_to_data_type(np.dtype(np.str_))
        assert DataType.STRING == self.gen.dtype_to_data_type(np.dtype(str))
        # Unsupported types treated as string for now
        assert DataType.STRING == self.gen.dtype_to_data_type(np.dtype(np.void))

    def test_get_count(self):
        df = pd.DataFrame({"dt": [np.datetime64("2005-02-25"), None, np.datetime64("2006-02-25")]})
        counts = []
        for row in df["dt"]:
            x = self.gen._get_count(row, DataType.DATETIME)
            counts.append(x)
        assert counts == [1, 0, 1]

    def test_feature_entry(self):
        df = pd.DataFrame({"num": [1, 2, 3, 4], "str": ["a", "a", "b", None], "float": [1.0, 2.0, None, 4.0]})
        for c in df:
            xs: FeatureEntry = self.gen.feature_entry(name=c, feature=df[c])
            if xs.feature_name == "num":
                assert np.array(xs.values).tolist() == [1, 2, 3, 4]
                assert xs.data_type == DataType.INT
                assert xs.missing == 0
                assert xs.counts == [1, 1, 1, 1]
            if xs.feature_name == "float":
                assert np.array(xs.values).tolist() == [1.0, 2.0, 4.0]
                assert xs.data_type == DataType.FLOAT
                assert xs.missing == 1
                assert xs.counts == [1, 1, 1]
            elif xs.feature_name == "str":
                assert np.array(xs.values).tolist() == ["a", "a", "b"]
                assert xs.data_type == DataType.STRING
                assert xs.missing == 1
                assert xs.counts == [1, 1, 1]

    def test_get_table_entries(self):
        train_df = pd.DataFrame({"num": [1, 2, 3, 4], "str": ["a", "a", "b", None], "float": [1.0, 2.0, None, 4.0]})
        test_df = pd.DataFrame({"num": [5, 6, 7, 8], "str": ["c", "d", "e", None], "float": [2.0, 4.0, None, 6.0]})

        dfs = {"train": train_df, "test": test_df}
        tbl_datasets: List[EntryDataSet] = self.gen.to_table_entries(dataframes=dfs)
        assert len(tbl_datasets) == 2

        for dataset in tbl_datasets:
            assert dataset.size == 4  # number of rows
            assert len(dataset.entries) == 3
