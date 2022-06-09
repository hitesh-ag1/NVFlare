import logging

from feature_stats import feature_statistics_pb2 as fs
from feature_stats.feature_statistics_pb2 import (
    DatasetFeatureStatisticsList as ProtoDatasetFeatureStatisticsList,
    FeatureNameStatistics as ProtoFeatureNameStatistics,
    CommonStatistics as ProtoCommonStatistics,
    Histogram as ProtoHistogram,
)
from feature_stats.feature_stats_def import (
    DatasetStatistics,
    CommonStatistics,
    FeatureStatistics,
    Histogram,
    HistogramType,
    DataType
)


def _convert_data_type_to_proto_type(data_type: DataType):
    if DataType.INT == data_type:
        return fs.FeatureNameStatistics.INT
    elif DataType.STRING == data_type:
        return fs.FeatureNameStatistics.STRING
    elif DataType.FLOAT == data_type:
        return fs.FeatureNameStatistics.FLOAT
    elif DataType.BYTES == data_type:
        return fs.FeatureNameStatistics.BYTES
    elif DataType.STRUCT == data_type:
        return fs.FeatureNameStatistics.STRUCT
    else:
        raise ValueError(f"not supported data type {data_type}")


def _convert_hist_type_to_proto_type(hist_type: HistogramType):
    if HistogramType.STANDARD == hist_type:
        return fs.Histogram.HistogramType.STANDARD
    elif HistogramType.QUANTILES == hist_type:
        return fs.Histogram.HistogramType.QUANTILES
    else:
        raise ValueError(f"not supported data type {hist_type}")


def _add_client_stats_to_proto(client_name: str, proto, analytics_data: dict):
    stats = analytics_data[client_name]['stats']
    if stats:
        ds: DatasetStatistics = stats.datasets[0]  # only consider one dataset from one client
        logging.info(f"ds.name = {ds.name}")
        proto_ds = proto.datasets.add(name=ds.name, num_examples=ds.num_examples)
        for f in ds.features:
            _copy_feature_stats(f, proto_ds)
    else:
        logging.error(f"no result returned for client {client_name} ")


def _copy_feature_stats(src: FeatureStatistics, proto_ds: ProtoDatasetFeatureStatisticsList):
    proto_data_type = _convert_data_type_to_proto_type(src.data_type)
    dest = proto_ds.features.add(type=proto_data_type, name=src.name)
    if src.num_stats:
        _copy_num_stats(src, dest)
    if src.string_stats:
        _copy_str_stats(src, dest)


def _copy_proto_histogram(src: Histogram, dest: ProtoHistogram):
    dest.type = _convert_hist_type_to_proto_type(src.hist_type)
    dest.num_nan = src.num_nan
    for bk in src.buckets:
        dest.buckets.add(
            low_value=bk.low_value,
            high_value=bk.high_value,
            sample_count=bk.sample_count
        )


def _copy_common_stats(src: CommonStatistics, dest: ProtoCommonStatistics):
    dest.num_missing = src.num_missing
    dest.num_non_missing = src.num_non_missing
    dest.min_num_values = src.min_num_values
    dest.max_num_values = src.max_num_values
    dest.avg_num_values = src.avg_num_values
    if src.feature_list_length_histogram:
        _copy_proto_histogram(src.feature_list_length_histogram,
                              dest.feature_list_length_histogram)
        _copy_proto_histogram(src.num_values_histogram, dest.num_values_histogram)


def _populate_gloabl_common_stats(src: CommonStatistics, dest: ProtoCommonStatistics):
    dest.num_missing += src.num_missing
    dest.num_non_missing += src.num_non_missing
    if dest.min_num_values > src.min_num_values:
        dest.min_num_values = src.min_num_values

    if dest.max_num_values < src.max_num_values:
        dest.max_num_values = src.max_num_values
    dest.tot_num_values += src.tot_num_values

    if src.feature_list_length_histogram:
        _copy_proto_histogram(src.feature_list_length_histogram,
                              dest.feature_list_length_histogram)
        _copy_proto_histogram(src.num_values_histogram, dest.num_values_histogram)


def _copy_num_stats(src: FeatureStatistics, feat: ProtoFeatureNameStatistics):
    feat_num_stats = feat.num_stats
    feat_num_stats.std_dev = src.num_stats.std_dev
    feat_num_stats.mean = src.num_stats.mean
    feat_num_stats.min = src.num_stats.min
    feat_num_stats.max = src.num_stats.max
    feat_num_stats.median = src.num_stats.median
    feat_num_stats.num_zeros = src.num_stats.num_zeros
    _copy_common_stats(src.num_stats.common_stats, feat_num_stats.common_stats)
    for hp in src.num_stats.histograms:
        hist: ProtoHistogram = feat_num_stats.histograms.add()
        _copy_proto_histogram(hp, hist)


def _copy_str_stats(src: FeatureStatistics, feat: ProtoFeatureNameStatistics):
    feat_str_stats = feat.string_stats
    feat_str_stats.avg_length = src.string_stats.avg_length
    feat_str_stats.unique = src.string_stats.unique_vals
    rank_hist = feat_str_stats.rank_histogram
    rh = src.string_stats.rank_histogram
    for r_bk in rh.buckets:
        rank_hist.buckets.add(
            low_rank=r_bk.low_rank,
            high_rank=r_bk.high_rank,
            sample_count=r_bk.sample_count,
            label=r_bk.label)
    _copy_common_stats(src.string_stats.common_stats, feat_str_stats.common_stats)
