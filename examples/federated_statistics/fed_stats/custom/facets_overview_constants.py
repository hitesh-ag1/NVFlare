class FOConstants(object):

    # TASKS
    CLIENT_STATS_TASK = "client_stats"
    AGGR_VAR_TASK = "aggregate_var"
    AGGR_HISTOGRAM_TASK = "aggregate_histogram"
    AGGR_MEDIAN_TASK = "aggregate_median"
    AGGR_MEDIAN_RANDOM_TASK = "aggregate_median:random_select"
    AGGR_MEDIAN_SIZE_COLL_TASK = "aggregate_median:size_collection"
    AGGR_MEDIAN_DATA_PURGE_TASK = "aggregate_median:data_purge"

    # Stats variables
    STD_HISTOGRAMS = "std_histograms"
    QUAN_HISTOGRAMS = "quantile_histograms"
    AGGR_VARS = "aggr_vars"
    AGGR_STDDEV = "aggr_std_dev"
    AGGR_MEANS = "aggr_means"
    AGGR_COUNTS = "aggr_counts"
    AGGR_MINS = "aggr_mins"
    AGGR_MAXES = "aggr_maxs"
    AGGR_ZEROS = "aggr_zeros"
    AGGR_MISSINGs = "aggr_missings"
    TOTAL_COUNT = "total_counts"
    CLIENT_MEDIANS = "client_medians"
    BINS = "number_of_bins"

    K_VALUES = "k_values"
    PIVOTS = "pivots"
    PIVOT_SIZES = "pivot_sizes"

    # ACTIONS
    MEDIAN_ACTION = "MEDIAN_ACTION"
    DISCARD_GREATER_SET_ACTION = 1
    DISCARD_LESS_SET_ACTION = 2
    STOP_ACTION = 4
    INIT_ACTION = 8
    CONTINUE_ACTION = 16

    # KEY WARDS
    TASK_FLOW_ROUND = "task_flow_round"
