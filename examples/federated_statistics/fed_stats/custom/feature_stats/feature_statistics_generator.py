# from pandas.core.series import Series.ndarray
from typing import Dict, List, Optional
from pandas.core.series import Series
import pandas as pd
import numpy as np

from .feature_entry import DataType, FeatureEntry, EntryDataSet, FeatureEntryGenerator
from .feature_stats_def import (
    BasicNumStats,
    Bucket,
    CommonStatistics,
    DatasetStatistics,
    DatasetStatisticsList,
    FeatureStatistics,
    FreqAndValue,
    Histogram,
    HistogramType,
    NumericStatistics,
    RankBucket,
    RankHistogram,
    StringStatistics,
)


class FeatureStatsGenerator(object):

    def generate_statistics(self,
                            dfs: Dict[str, pd.DataFrame],
                            whitelist_feats=None,
                            hist_cat_levels_count=None) -> DatasetStatisticsList:
        data_entries: List[EntryDataSet] = FeatureEntryGenerator().to_table_entries(dfs)
        return self.gen_feature_stats(data_entries, whitelist_feats, hist_cat_levels_count)

    def gen_feature_stats(self,
                          data_entries: List[EntryDataSet],
                          whitelist_feats: Optional[List[str]],
                          hist_cat_levels_count: Optional[int]) -> DatasetStatisticsList:

        datasets_statistics_list = []
        data_entries = [ds for ds in data_entries if ds is not None and ds.size > 0]
        for index, table_ds in enumerate(data_entries):
            feat_entries: List[FeatureEntry] = [table_ds.entries[f] for f in table_ds.entries if
                                                whitelist_feats is None or f in whitelist_feats]
            print("feat_entries len = ", len(feat_entries))
            feature_statistics = []
            for feat in feat_entries:
                data_type: DataType = feat.data_type
                common_stats: CommonStatistics = self._get_common_stats(table_ds.size, feat)

                if data_type == DataType.INT or data_type == DataType.FLOAT:
                    numeric_stats = self._get_numeric_stats(feature_data=feat, common_stats=common_stats)
                    string_stats: Optional[StringStatistics] = None
                else:
                    numeric_stats: Optional[NumericStatistics] = None
                    string_stats = self._get_string_stats(
                        feature_data=feat,
                        common_stats=common_stats,
                        his_cat_levels_count=hist_cat_levels_count
                    )

                fs = FeatureStatistics(
                    name=feat.feature_name,
                    data_type=data_type,
                    num_stats=numeric_stats,
                    string_stats=string_stats
                )

                feature_statistics.append(fs)

            ds_stats = DatasetStatistics(
                name=table_ds.name,
                num_examples=table_ds.size,
                features=feature_statistics
            )
            datasets_statistics_list.append(ds_stats)

        return DatasetStatisticsList(datasets=datasets_statistics_list)

    def _get_numeric_stats(self, feature_data: FeatureEntry, common_stats: CommonStatistics) -> NumericStatistics:
        values = feature_data.values
        feature_name = feature_data.feature_name
        basic_num_stats = self.get_basic_num_stats(values, feature_name)

        # Remove all non-finite (including NaN) values from the numeric
        # values in order to calculate histogram buckets/counts. The
        # inf values will be added back to the first and last buckets.
        nums = np.array(values)
        nums = nums[np.isfinite(nums)]
        std_histogram = self.get_histogram(nums, num_buckets=10, histogram_type=HistogramType.STANDARD)
        quantile_histogram = self.get_histogram(
            nums=nums, num_buckets=10, histogram_type=HistogramType.QUANTILES
        )

        return NumericStatistics(
            common_stats=common_stats,
            mean=basic_num_stats.mean,
            std_dev=basic_num_stats.std_dev,
            num_zeros=basic_num_stats.num_zeros,
            min=basic_num_stats.min,
            median=basic_num_stats.median,
            max=basic_num_stats.max,
            histograms=[std_histogram, quantile_histogram],
        )

    def _get_common_stats(self, table_data_size: int, feature_data: FeatureEntry) -> CommonStatistics:
        has_data = feature_data is not None and len(feature_data.values) != 0
        feat_lens_hist = None
        num_values_hist = None
        if has_data:
            num_missing = feature_data.missing
            num_non_missing = table_data_size - feature_data.missing
            min_num_values = int(np.min(feature_data.counts).astype(int))
            max_num_values = int(np.max(feature_data.counts).astype(int))
            avg_num_values = float(np.mean(feature_data.counts).astype(float))
            tot_num_values = avg_num_values * num_non_missing
        else:
            num_non_missing = 0
            num_missing = table_data_size
            min_num_values = 0
            max_num_values = 0
            avg_num_values = 0
            tot_num_values = 0

            if feature_data.feature_lens:
                feat_lens_hist = self.get_histogram(
                    np.array(feature_data.feature_lens), num_buckets=10, histogram_type=HistogramType.QUANTILES
                )
                num_values_hist = self.get_histogram(
                    np.array(feature_data.counts), num_buckets=10, histogram_type=HistogramType.QUANTILES
                )

        return CommonStatistics(
            num_non_missing=num_non_missing,
            num_missing=num_missing,
            min_num_values=min_num_values,
            max_num_values=max_num_values,
            avg_num_values=avg_num_values,
            tot_num_values=tot_num_values,
            num_values_histogram=num_values_hist,
            feature_list_length_histogram=feat_lens_hist,
        )

    @staticmethod
    def _get_std_histogram_buckets(nums: np.ndarray, num_buckets: int = 10):
        # duplicate calculations, but make code cleaner
        num_posinf = len(nums[np.isposinf(nums)])
        num_neginf = len(nums[np.isneginf(nums)])
        counts, buckets = np.histogram(nums, bins=num_buckets)
        histogram_bucket: List[Bucket] = []
        for bucket_count in range(len(counts)):
            # Add any negative or positive infinities to the first and last
            # buckets in the histogram.
            bucket_low_value = buckets[bucket_count]
            bucket_high_value = buckets[bucket_count + 1]
            bucket_sample_count = counts[bucket_count]
            if bucket_count == 0 and num_neginf > 0:
                bucket_low_value = float("-inf")
                bucket_sample_count += num_neginf
            elif bucket_count == len(counts) - 1 and num_posinf > 0:
                bucket_high_value = float("inf")
                bucket_sample_count += num_posinf

            histogram_bucket.append(
                Bucket(low_value=bucket_low_value, high_value=bucket_high_value, sample_count=bucket_sample_count)
            )

        if buckets is not None and len(buckets) > 0:
            bucket = None
            if num_neginf:
                bucket = Bucket(low_value=float("-inf"), high_value=float("-inf"), sample_count=num_neginf)
            if num_posinf:
                bucket = Bucket(low_value=float("inf"), high_value=float("inf"), sample_count=num_posinf)

            if bucket:
                histogram_bucket.append(bucket)

        return histogram_bucket

    @staticmethod
    def get_basic_num_stats(values: Series, feature_name: str) -> BasicNumStats:
        nums = values
        stats_std_dev = np.std(nums).item()
        stats_mean = np.mean(nums).item()
        stats_min = np.min(nums).item()
        stats_max = np.max(nums).item()
        stats_median = np.median(nums).item()
        stats_num_zeros = len(nums) - np.count_nonzero(nums)

        # Converting Python sequences to NumPy Arrays
        nums = np.array(nums)
        stats_num_nan = len(nums[np.isnan(nums)])
        stats_num_posinf = len(nums[np.isposinf(nums)])
        stats_num_neginf = len(nums[np.isneginf(nums)])

        return BasicNumStats(
            name=feature_name,
            num_count=len(nums),
            num_nan=stats_num_nan,
            num_zeros=stats_num_zeros,
            num_posinf=stats_num_posinf,
            num_neginf=stats_num_neginf,
            std_dev=stats_std_dev,
            mean=stats_mean,
            min=stats_min,
            median=stats_median,
            max=stats_max,
        )

    def get_histogram(self, nums: np.ndarray, num_buckets: int, histogram_type: HistogramType) -> Histogram:
        num_nan = len(nums[np.isnan(nums)])
        if histogram_type == HistogramType.QUANTILES:
            buckets = self._get_quantiles_histogram_buckets(nums, num_quantile_buckets=num_buckets)
        else:
            buckets = self._get_std_histogram_buckets(nums, num_buckets)

        return Histogram(num_nan=num_nan, num_undefined=0, buckets=buckets, hist_type=histogram_type, hist_name=None)

    @staticmethod
    def _get_quantiles_histogram_buckets(nums: np.ndarray, num_quantile_buckets: int = 10) -> List[Bucket]:
        histogram_bucket: List[Bucket] = []
        if not nums.tolist():
            return histogram_bucket

        quantiles_to_get = [x * 100 / num_quantile_buckets for x in range(num_quantile_buckets + 1)]
        quantiles = np.percentile(nums, quantiles_to_get)
        quantiles_sample_count = float(len(nums)) / num_quantile_buckets
        for low, high in zip(quantiles, quantiles[1:]):
            histogram_bucket.append(Bucket(low_value=low, high_value=high, sample_count=quantiles_sample_count))

        return histogram_bucket

    @staticmethod
    def _convert_to_str_list(values: Series) -> List[str]:
        strs = []
        for item in values:
            str_value = (
                item if hasattr(item, "__len__") else item.encode("utf-8") if hasattr(item, "encode") else str(item)
            )
            strs.append(str_value)
        return strs

    @staticmethod
    def _get_printable_value(str_like_value) -> str:
        try:
            if isinstance(str_like_value, (bytes, bytearray)):
                printable_val = str_like_value.decode("UTF-8", "strict")
            else:
                printable_val = str_like_value
        except (UnicodeDecodeError, UnicodeEncodeError):
            printable_val = "__BYTES_VALUE__"

        return printable_val

    def _get_str_rank_histogram_and_top_values(
            self, unique_vals: np.ndarray, unique_counts: np.ndarray, hist_cat_levels_count
    ) -> (Histogram, List[FreqAndValue]):
        sorted_vals = sorted(zip(unique_counts, unique_vals), reverse=True)
        sorted_vals = sorted_vals[:hist_cat_levels_count]
        buckets: List[RankBucket] = []
        top_values: List[FreqAndValue] = []
        for val_index, val in enumerate(sorted_vals):
            printable_val = self._get_printable_value(val[1])
            bucket = RankBucket(
                low_rank=val_index, high_rank=val_index, sample_count=val[0], label=printable_val
            )
            buckets.append(bucket)

            if val_index < 2:
                fv = FreqAndValue(value=bucket.label, frequency=bucket.sample_count)
                top_values.append(fv)

        histogram = RankHistogram(buckets=buckets)
        return histogram, top_values

    def _get_string_stats(
            self, feature_data: FeatureEntry, common_stats: CommonStatistics, his_cat_levels_count: int
    ) -> StringStatistics:

        values: Series.ndarray = feature_data.values
        has_data = values is not None and len(values) > 0
        if not has_data:
            unique_vals = 0
            top_values = []
            avg_length = 0
            rank_histogram = RankHistogram(buckets=[])
        else:
            strs = self._convert_to_str_list(values)
            avg_length = float(np.mean(np.vectorize(len)(strs)).astype(float))
            vals, counts = np.unique(strs, return_counts=True)
            unique_vals = len(vals)
            rank_histogram, top_values = self._get_str_rank_histogram_and_top_values(
                unique_vals=vals, unique_counts=counts, hist_cat_levels_count=his_cat_levels_count
            )

        return StringStatistics(
            common_stats,
            unique_vals=unique_vals,
            top_values=top_values,
            avg_length=avg_length,
            rank_histogram=rank_histogram,
        )
