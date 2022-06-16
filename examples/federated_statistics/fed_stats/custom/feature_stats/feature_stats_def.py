# feature stats data structure that mimic
# https://github.com/PAIR-code/facets/blob/master/facets_overview/proto/feature_statistics.proto
# Definitions for aggregated feature statistics for datasets,
# this definition mirror the feature_statistics.proto definition
# with some classname changed. This allows us to restructure the dataset list when we ready to leverage
# Facets to generate the visualization

from enum import Enum
from typing import Dict, List, NamedTuple, Optional


class DataType(Enum):
    INT = 0
    FLOAT = 1
    STRING = 2
    BYTES = 3
    STRUCT = 4
    DATETIME = 5


class BasicNumStats(NamedTuple):
    name: str
    num_count: int
    num_nan: int
    num_zeros: int
    num_posinf: int
    num_neginf: int
    std_dev: float
    mean: float
    min: float
    median: float
    max: float


class FreqAndValue(NamedTuple):
    value: str
    frequency: float


class Bucket(NamedTuple):
    # The low value of the bucket, inclusive.
    low_value: float

    # The high value of the bucket, exclusive (unless the highValue is positive infinity).
    high_value: float

    # quantile sample count could be fractional
    sample_count: float


class RankBucket(NamedTuple):
    # Each bucket defines its start and end ranks along with its count.
    # The low rank of the bucket, inclusive.
    low_rank: int

    # The high rank of the bucket, exclusive.
    high_rank: int

    # The label for the bucket. Can be used to list or summarize the values in
    # this rank bucket.
    label: str

    # The number of items in the bucket.
    sample_count: float


class HistogramType(Enum):
    STANDARD = 0
    QUANTILES = 1


class Histogram(NamedTuple):
    # Each bucket defines its low and high values along with its count. The
    # low and high values must be a real number or positive or negative
    # infinity. They cannot be NaN or undefined. Counts of those special values
    # can be found in the numNaN and numUndefined fields.
    # The number of NaN values in the dataset.
    num_nan: int

    # The number of undefined values in the dataset.
    num_undefined: int

    # A list of buckets in the histogram, sorted from lowest bucket to highest bucket.
    buckets: List[Bucket]

    # The type of the histogram. A standard histogram has equal-width buckets.
    # The quantiles type is used for when the histogram message is used to store
    # quantile information (by using equal-count buckets with variable widths).

    # The type of the histogram.
    hist_type: HistogramType

    # An optional descriptive name of the histogram, to be used for labeling.
    hist_name: Optional[str] = None


class RankHistogram(NamedTuple):
    """
    The data used to create a rank histogram of a non-numeric feature of a
    dataset. The rank of a value in a feature can be used as a measure of how
    commonly the value is found in the entire dataset. With bucket sizes of one,
    this becomes a distribution function of all feature values.
    """

    # A list of buckets in the histogram, sorted from lowest-ranked bucket to
    # highest-ranked bucket.
    buckets: List[RankBucket]

    # An optional descriptive name of the histogram, to be used for labeling.
    name: Optional[str] = None


class CommonStatistics(NamedTuple):
    """
    The histogram for the number of features in the feature list (only set if
    this feature is a non-context feature from a tf.SequenceExample).
    This is different from num_values_histogram, as num_values_histogram tracks
    the count of all values for a feature in an example, whereas this tracks
    the length of the feature list for this feature in an example (where each
    feature list can contain multiple values).
    """

    num_non_missing: int

    num_missing: int

    min_num_values: int

    max_num_values: int

    avg_num_values: float

    # tot_num_values = avg_num_values * num_non_missing.
    tot_num_values: int

    # The quantiles histogram for the number of values in this feature.
    num_values_histogram: Optional[Histogram] = None

    #  The histogram for the number of features in the feature list (only set if
    #  this feature is a non-context feature from a tf.SequenceExample).
    #  This is different from num_values_histogram, as num_values_histogram tracks
    #  the count of all values for a feature in an example, whereas this tracks
    #  the length of the feature list for this feature in an example (where each
    #  feature list can contain multiple values).
    feature_list_length_histogram: Optional[Histogram] = None


class NumericStatistics(NamedTuple):
    common_stats: CommonStatistics
    mean: float
    std_dev: float
    num_zeros: float
    min: float
    median: float
    max: float
    histograms: List[Histogram]
    extra: Dict[str, float] = dict()


class StringStatistics(NamedTuple):
    """
    The rank histogram for the values of the feature.
    The rank is used to measure of how commonly the value is found in the
    dataset. The most common value would have a rank of 1, with the second-most
    common value having a rank of 2, and so on.
    """

    common_stats: CommonStatistics
    unique_vals: int
    top_values: List[FreqAndValue]
    avg_length: float
    rank_histogram: RankHistogram


class CustomStatistic(NamedTuple):
    name: str
    num_val: float
    str_val: str
    histogram: Histogram
    rank_histogram: RankHistogram


class BytesStatistics(NamedTuple):
    common_stats: CommonStatistics
    unique_vals: int
    avg_num_bytes: float
    min_num_bytes: float
    max_num_bytes: float


class StructStatistics(NamedTuple):
    common_stats: CommonStatistics


class FeatureStatistics(NamedTuple):
    name: str
    data_type: DataType
    num_stats: Optional[NumericStatistics] = None
    string_stats: Optional[StringStatistics] = None
    bytes_stats: Optional[BytesStatistics] = None
    struct_stats: Optional[StructStatistics] = None
    custom_stats: Optional[CustomStatistic] = None


class DatasetStatistics(NamedTuple):
    name: str
    num_examples: int
    features: List[FeatureStatistics]


class DatasetStatisticsList(NamedTuple):
    datasets: List[DatasetStatistics]
