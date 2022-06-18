from typing import Dict, List, NamedTuple, Optional

import numpy as np
import pandas as pd
import pytest

from examples.federated_statistics.fed_stats.custom.feature_stats.feature_entry import (
    EntryDataSet,
    FeatureEntry,
    FeatureEntryGenerator,
)
from examples.federated_statistics.fed_stats.custom.feature_stats.feature_statistics_generator import (
    FeatureStatsGenerator,
)
from examples.federated_statistics.fed_stats.custom.feature_stats.feature_stats_def import (
    BasicNumStats,
    Bucket,
    CommonStatistics,
    DatasetStatistics,
    DatasetStatisticsList,
    DataType,
    FeatureStatistics,
    FreqAndValue,
    Histogram,
    HistogramType,
    NumericStatistics,
    RankBucket,
    RankHistogram,
    StringStatistics,
)


class TestFeatureStatisticsGenerator:
    @classmethod
    def setup_class(cls):
        print("starting class: {} execution".format(cls.__name__))

    @classmethod
    def teardown_class(cls):
        print("starting class: {} execution".format(cls.__name__))

    def setup_method(self, method):
        print("starting execution of tc: {}".format(method.__name__))
        self.gen = FeatureStatsGenerator()

    def teardown_method(self, method):
        print("starting execution of tc: {}".format(method.__name__))

    def test_data_stats_with_feature_entries(self):
        entry = FeatureEntry(
            feature_name="test_feature",
            data_type=DataType.INT,
            values=np.array([1, 2, 3]),
            counts=[1, 1, 1],
            missing=0,
        )
        entries: List[EntryDataSet] = []
        dataset = EntryDataSet("entries", size=3, entries={"test_feature": entry})
        entries.append(dataset)

        p = self.gen.gen_feature_stats(data_entries=entries, whitelist_feats=None, hist_cat_levels_count=5)
        assert 1 == len(p.datasets)
        test_data = p.datasets[0]
        assert "entries" == test_data.name

        assert 3 == test_data.num_examples
        assert 1 == len(test_data.features)

        num_feat = test_data.features[0]
        assert "test_feature", num_feat.name
        assert DataType.INT == num_feat.data_type
        assert 1 == num_feat.num_stats.min
        assert 3 == num_feat.num_stats.max

    def test_generate_string_stats(self):
        test_data = [
            "dab4022d3b1712",
            "15f600dbd4b112",
            "10a576ffa35512",
            "0d88d24eed3c12",
            "af83e6a9c50a12",
            "9ba37146763d12",
            "0d4e7ce69f5f12",
            "36a28b58d8a212",
            "6d520efa752312",
            "1db0adb7c49112",
        ]
        arr = np.array(test_data)
        df = pd.DataFrame(arr, columns=["id"])
        dfs = {"train": df}
        data_stats: DatasetStatisticsList = self.gen.generate_statistics(dfs)
        datasets: List[DatasetStatistics] = data_stats.datasets
        for ds in datasets:
            assert ds.name == "train"
            assert ds.num_examples == 10
            for fe in ds.features:
                assert fe.data_type == DataType.STRING
                assert fe.name == "id"
                assert fe.string_stats is not None
                str_stats = fe.string_stats
                assert str_stats.avg_length == 14.0
                assert str_stats.unique_vals == 10

    def test_data_stats_with_whitelist_feature(self):
        df = pd.DataFrame({"num": [1, 2, 3, 4], "str": ["a", "a", "b", None], "float": [1.0, 2.0, None, 4.0]})
        dfs = {"train": df}
        p = self.gen.generate_statistics(dfs=dfs, whitelist_feats=["str", "float"])
        ds = p.datasets[0]
        assert "train" == ds.name
        assert ds.num_examples == 4
        assert 2 == len(ds.features)

    def test_data_stats_wtih_hist_cat_levels_cnt(self):
        arr = ["hi", "good", "hi", "hi", "a", "a"]
        df = pd.DataFrame({"strs": arr})
        dfs = {"testDataSet": df}
        p = self.gen.generate_statistics(dfs, hist_cat_levels_count=2)
        assert 1 == len(p.datasets)
        test_data = p.datasets[0]
        assert "testDataSet" == test_data.name
        assert 6 == test_data.num_examples
        assert 1 == len(test_data.features)
        feat = test_data.features[0]
        assert "strs" == feat.name
        top_values = feat.string_stats.top_values
        assert 3 == top_values[0].frequency
        assert "hi" == top_values[0].value
        assert 3 == feat.string_stats.unique_vals
        assert 2 == feat.string_stats.avg_length
        rank_hist = feat.string_stats.rank_histogram
        assert len(rank_hist.buckets) > 0
        buckets = rank_hist.buckets
        assert 2 == len(buckets)
        assert "hi" == buckets[0].label
        assert 3 == buckets[0].sample_count
        assert "a" == buckets[1].label
        assert 2 == buckets[1].sample_count

    def test_get_feature_histogram(self):
        df = pd.DataFrame({"ints": [1, 2, 3, 4], "counts": [1, 1, 1, 1]})
        dfs: Dict[str, pd.DataFrame] = {"train": df}
        p = self.gen.generate_statistics(dfs)
        num_stats = p.datasets[0].features[0].num_stats
        hist1 = num_stats.histograms[0]
        hist2 = num_stats.histograms[1]
        assert hist1 is not None
        assert hist2 is not None
        assert HistogramType.STANDARD == hist1.hist_type
        assert HistogramType.QUANTILES == hist2.hist_type
        buckets2 = hist2.buckets
        assert 10 == len(buckets2)
        assert 1 == buckets2[0].low_value
        assert 1.3 == buckets2[0].high_value
        assert 0.4 == buckets2[0].sample_count
        assert 3.7 == buckets2[9].low_value
        assert 4 == buckets2[9].high_value
