"""Unit tests for training_validation_io.py."""

import copy
import unittest
import numpy
from gewittergefahr.deep_learning import training_validation_io as trainval_io

TOLERANCE = 1e-6

# The following constants are used to test _get_num_examples_per_batch_by_class.
NUM_EXAMPLES_PER_BATCH = 100
TORNADO_TARGET_NAME = 'tornado_lead-time=0000-3600sec_distance=00001-05000m'

SAMPLING_FRACTION_BY_TOR_CLASS_DICT = {0: 0.8, 1: 0.2}
NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT = {0: 80, 1: 20}
MANY_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT = {
    0: NUM_EXAMPLES_PER_BATCH, 1: NUM_EXAMPLES_PER_BATCH
}

WIND_TARGET_NAME = (
    'wind-speed_percentile=100.0_lead-time=1800-3600sec_distance=00001-05000m'
    '_cutoffs=30-50kt')
SAMPLING_FRACTION_BY_WIND_CLASS_DICT = {-2: 0.3, 0: 0.4, 1: 0.2, 2: 0.1}
NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT = {-2: 30, 0: 40, 1: 20, 2: 10}

# The following constants are used to test _get_num_examples_left_by_class and
# _need_negative_target_values.
NUM_FILE_TIMES_PER_BATCH = 20
NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT = {0: 1000, 1: 10}
NUM_EXAMPLES_LEFT_BY_TOR_CLASS_DICT = {0: 0, 1: 10}
NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT = {-2: 500, 0: 1000, 1: 18, 2: 5}
NUM_EXAMPLES_LEFT_BY_WIND_CLASS_DICT = {-2: 0, 0: 0, 1: 2, 2: 5}

# The following constants are used to test _determine_stopping_criterion.
TARGET_VALUES_50ZEROS = numpy.full(50, 0, dtype=int)
TARGET_VALUES_200ZEROS = numpy.full(200, 0, dtype=int)

THESE_INDICES = numpy.linspace(0, 199, num=200, dtype=int)
THESE_INDICES = numpy.random.choice(THESE_INDICES, size=30, replace=False)
TORNADO_TARGET_VALUES_ENOUGH_ONES = copy.deepcopy(TARGET_VALUES_200ZEROS)
TORNADO_TARGET_VALUES_ENOUGH_ONES[THESE_INDICES] = 1

THESE_INDICES = numpy.linspace(0, 199, num=200, dtype=int)
THESE_INDICES = numpy.random.choice(THESE_INDICES, size=120, replace=False)
WIND_TARGET_VALUES_ENOUGH = copy.deepcopy(TARGET_VALUES_200ZEROS)
WIND_TARGET_VALUES_ENOUGH[THESE_INDICES[:30]] = 2
WIND_TARGET_VALUES_ENOUGH[THESE_INDICES[30:70]] = 1
WIND_TARGET_VALUES_ENOUGH[THESE_INDICES[70:]] = -2

NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_50ZEROS = {0: 50, 1: 0}
NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_200ZEROS = {0: 200, 1: 0}
NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_ENOUGH_ONES = {0: 170, 1: 30}

NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_50ZEROS = {-2: 0, 0: 50, 1: 0, 2: 0}
NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_200ZEROS = {-2: 0, 0: 200, 1: 0, 2: 0}
NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_ENOUGH = {-2: 50, 0: 80, 1: 40, 2: 30}

# The following constants are used to test separate_radar_files_2d3d.
RADAR_FILE_NAME_MATRIX = numpy.array([
    ['storm_images/myrorss/2018/mesh_mm/00250_metres_agl/'
     'storm_images_20180728.nc',
     'storm_images/myrorss/2018/reflectivity_dbz/05000_metres_agl/'
     'storm_images_20180728.nc',
     'storm_images/myrorss/2018/reflectivity_dbz/01000_metres_agl/'
     'storm_images_20180728.nc',
     'storm_images/myrorss/2018/mid_level_shear_s01/00250_metres_agl/'
     'storm_images_20180728.nc',
     'storm_images/myrorss/2018/low_level_shear_s01/00250_metres_agl/'
     'storm_images_20180728.nc'],
    ['storm_images/myrorss/2018/mesh_mm/00250_metres_agl/'
     'storm_images_20180729.nc',
     'storm_images/myrorss/2018/reflectivity_dbz/05000_metres_agl/'
     'storm_images_20180729.nc',
     'storm_images/myrorss/2018/reflectivity_dbz/01000_metres_agl/'
     'storm_images_20180729.nc',
     'storm_images/myrorss/2018/mid_level_shear_s01/00250_metres_agl/'
     'storm_images_20180729.nc',
     'storm_images/myrorss/2018/low_level_shear_s01/00250_metres_agl/'
     'storm_images_20180729.nc']
], dtype=object)

REFLECTIVITY_INDICES = numpy.array([1, 2], dtype=int)
AZIMUTHAL_SHEAR_INDICES = numpy.array([3, 4], dtype=int)
MESH_INDICES = numpy.array([0], dtype=int)
NON_REFLECTIVITY_INDICES = numpy.array([0, 3, 4], dtype=int)
NON_AZIMUTHAL_SHEAR_INDICES = numpy.array([0, 1, 2], dtype=int)
NON_MESH_INDICES = numpy.array([1, 2, 3, 4], dtype=int)

REFLECTIVITY_FILE_NAME_MATRIX = RADAR_FILE_NAME_MATRIX[..., [2, 1]]
AZ_SHEAR_FILE_NAME_MATRIX = RADAR_FILE_NAME_MATRIX[..., [4, 3]]


class TrainingValidationIoTests(unittest.TestCase):
    """Each method is a unit test for training_validation_io.py."""

    def test_get_num_examples_per_batch_by_class_tornado(self):
        """Ensures correct output from _get_num_examples_per_batch_by_class.

        In this case, the target variable is tornado occurrence.
        """

        this_dict = trainval_io._get_num_examples_per_batch_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            target_name=TORNADO_TARGET_NAME,
            sampling_fraction_by_class_dict=SAMPLING_FRACTION_BY_TOR_CLASS_DICT)

        self.assertTrue(this_dict == NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT)

    def test_get_num_examples_per_batch_by_class_wind(self):
        """Ensures correct output from _get_num_examples_per_batch_by_class.

        In this case, the target variable is wind-speed category.
        """

        this_dict = trainval_io._get_num_examples_per_batch_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            target_name=WIND_TARGET_NAME,
            sampling_fraction_by_class_dict=
            SAMPLING_FRACTION_BY_WIND_CLASS_DICT)

        self.assertTrue(this_dict == NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT)

    def test_get_num_examples_per_batch_by_class_no_fractions(self):
        """Ensures correct output from _get_num_examples_per_batch_by_class.

        In this case, `sampling_fraction_by_class_dict` is empty, which means
        that there will be no downsampling.
        """

        this_dict = trainval_io._get_num_examples_per_batch_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            target_name=TORNADO_TARGET_NAME,
            sampling_fraction_by_class_dict=None)

        self.assertTrue(this_dict == MANY_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT)

    def test_get_num_examples_left_by_tor_need_times_and_examples(self):
        """Ensures correct output from _get_num_examples_left_by_class.

        Target variable = tornado occurrence.  No downsampling, because there
        are not yet enough file times or examples in memory.
        """

        this_dict = trainval_io._get_num_examples_left_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_examples_in_memory=NUM_EXAMPLES_PER_BATCH - 1,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH - 1,
            num_examples_in_memory_by_class_dict=
            NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT)

        self.assertTrue(this_dict == NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT)

    def test_get_num_examples_left_by_tor_need_times(self):
        """Ensures correct output from _get_num_examples_left_by_class.

        Target variable = tornado occurrence.  No downsampling, because there
        are not yet enough file times in memory.
        """

        this_dict = trainval_io._get_num_examples_left_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_examples_in_memory=NUM_EXAMPLES_PER_BATCH + 1,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH - 1,
            num_examples_in_memory_by_class_dict=
            NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT)

        self.assertTrue(this_dict == NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT)

    def test_get_num_examples_left_by_tor_need_examples(self):
        """Ensures correct output from _get_num_examples_left_by_class.

        Target variable = tornado occurrence.  No downsampling, because there
        are not yet enough examples in memory.
        """

        this_dict = trainval_io._get_num_examples_left_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_examples_in_memory=NUM_EXAMPLES_PER_BATCH - 1,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            num_examples_in_memory_by_class_dict=
            NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT)

        self.assertTrue(this_dict == NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT)

    def test_get_num_examples_left_by_tor_downsampling(self):
        """Ensures correct output from _get_num_examples_left_by_class.

        Target variable = tornado occurrence.  Will downsample, because there
        are already enough file times and examples in memory.
        """

        this_dict = trainval_io._get_num_examples_left_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_examples_in_memory=NUM_EXAMPLES_PER_BATCH + 1,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            num_examples_in_memory_by_class_dict=
            NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT)

        self.assertTrue(this_dict == NUM_EXAMPLES_LEFT_BY_TOR_CLASS_DICT)

    def test_get_num_examples_left_by_wind_downsampling(self):
        """Ensures correct output from _get_num_examples_left_by_class.

        Target variable = wind class.  Will downsample, because there are
        already enough file times and examples in memory.
        """

        this_dict = trainval_io._get_num_examples_left_by_class(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT,
            num_examples_in_memory=NUM_EXAMPLES_PER_BATCH + 1,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            num_examples_in_memory_by_class_dict=
            NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT)

        self.assertTrue(this_dict == NUM_EXAMPLES_LEFT_BY_WIND_CLASS_DICT)

    def test_need_negative_target_values_wind_yes(self):
        """Ensures correct output from _need_negative_target_values.

        In this case, target variable = wind-speed category and answer = yes.
        """

        self.assertTrue(trainval_io._need_negative_target_values(
            NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT))

    def test_need_negative_target_values_tornado_no(self):
        """Ensures correct output from _need_negative_target_values.

        In this case, target variable = tornado occurrence and answer = no.
        """

        self.assertFalse(trainval_io._need_negative_target_values(
            NUM_EXAMPLES_LEFT_BY_TOR_CLASS_DICT))

    def test_need_negative_target_values_wind_no(self):
        """Ensures correct output from _need_negative_target_values.

        In this case, target variable = tornado occurrence and answer = no.
        """

        self.assertFalse(trainval_io._need_negative_target_values(
            NUM_EXAMPLES_LEFT_BY_WIND_CLASS_DICT))

    def test_determine_stopping_tor_need_times_and_examples(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = tornado occurrence.  Stopping criterion should be
        False, as there are not yet enough file times or examples in memory.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH - 1,
            sampling_fraction_by_class_dict=SAMPLING_FRACTION_BY_TOR_CLASS_DICT,
            target_values_in_memory=TARGET_VALUES_50ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_50ZEROS)
        self.assertFalse(this_flag)

    def test_determine_stopping_wind_need_times_and_examples(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = wind class.  Stopping criterion should be False, as
        there are not yet enough file times or examples in memory.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH - 1,
            sampling_fraction_by_class_dict=
            SAMPLING_FRACTION_BY_WIND_CLASS_DICT,
            target_values_in_memory=TARGET_VALUES_50ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_50ZEROS)
        self.assertFalse(this_flag)

    def test_determine_stopping_tor_need_times(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = tornado occurrence.  Stopping criterion should be
        False, as there are not yet enough file times in memory.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH - 1,
            sampling_fraction_by_class_dict=SAMPLING_FRACTION_BY_TOR_CLASS_DICT,
            target_values_in_memory=TORNADO_TARGET_VALUES_ENOUGH_ONES)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_ENOUGH_ONES)
        self.assertFalse(this_flag)

    def test_determine_stopping_wind_need_times(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = wind class.  Stopping criterion should be False, as
        there are not yet enough file times in memory.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH - 1,
            sampling_fraction_by_class_dict=
            SAMPLING_FRACTION_BY_WIND_CLASS_DICT,
            target_values_in_memory=WIND_TARGET_VALUES_ENOUGH)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_ENOUGH)
        self.assertFalse(this_flag)

    def test_determine_stopping_tor_need_examples(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = tornado occurrence.  Stopping criterion should be
        False, as there are not yet enough examples in memory.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=SAMPLING_FRACTION_BY_TOR_CLASS_DICT,
            target_values_in_memory=TARGET_VALUES_50ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_50ZEROS)
        self.assertFalse(this_flag)

    def test_determine_stopping_wind_need_examples(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = wind class.  Stopping criterion should be False, as
        there are not yet enough examples in memory.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=
            SAMPLING_FRACTION_BY_WIND_CLASS_DICT,
            target_values_in_memory=TARGET_VALUES_50ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_50ZEROS)
        self.assertFalse(this_flag)

    def test_determine_stopping_tor_no_downsampling(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = tornado occurrence.  There are enough file times
        and examples in memory.  All examples have target = 0, but this doesn't
        matter, because no oversampling is desired.  Thus, stopping criterion
        should be True.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=None,
            target_values_in_memory=TARGET_VALUES_200ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_200ZEROS)
        self.assertTrue(this_flag)

    def test_determine_stopping_wind_no_downsampling(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = wind class.  There are enough file times and
        examples in memory.  All examples have target = 0, but this doesn't
        matter, because no oversampling is desired.  Thus, stopping criterion
        should be True.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=None,
            target_values_in_memory=TARGET_VALUES_200ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_200ZEROS)
        self.assertTrue(this_flag)

    def test_determine_stopping_tor_need_ones(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = tornado occurrence.  There are enough file times
        and examples in memory.  However, all examples have target = 0, which
        matters because oversampling is desired.  Thus, stopping criterion
        should be False.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=SAMPLING_FRACTION_BY_TOR_CLASS_DICT,
            target_values_in_memory=TARGET_VALUES_200ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_200ZEROS)
        self.assertFalse(this_flag)

    def test_determine_stopping_wind_need_nonzero(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = wind class.  There are enough file times and
        examples in memory.  However, all examples have target = 0, which
        matters because oversampling is desired.  Thus, stopping criterion
        should be False.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=
            SAMPLING_FRACTION_BY_WIND_CLASS_DICT,
            target_values_in_memory=TARGET_VALUES_200ZEROS)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_200ZEROS)
        self.assertFalse(this_flag)

    def test_determine_stopping_tor_enough_ones(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = tornado occurrence.  There are enough file times,
        negative examples, and positive examples in memory.  Thus, stopping
        criterion should be True.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_TOR_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=SAMPLING_FRACTION_BY_TOR_CLASS_DICT,
            target_values_in_memory=TORNADO_TARGET_VALUES_ENOUGH_ONES)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_TOR_CLASS_DICT_ENOUGH_ONES)
        self.assertTrue(this_flag)

    def test_determine_stopping_wind_enough_per_class(self):
        """Ensures correct output from _determine_stopping_criterion.

        Target variable = wind class.  There are enough file times, and
        enough examples of each class, in memory.  Thus, stopping criterion
        should be True.
        """

        this_dict, this_flag = trainval_io._determine_stopping_criterion(
            num_examples_per_batch=NUM_EXAMPLES_PER_BATCH,
            num_file_times_per_batch=NUM_FILE_TIMES_PER_BATCH,
            num_examples_per_batch_by_class_dict=
            NUM_EXAMPLES_PER_BATCH_BY_WIND_CLASS_DICT,
            num_file_times_in_memory=NUM_FILE_TIMES_PER_BATCH + 1,
            sampling_fraction_by_class_dict=
            SAMPLING_FRACTION_BY_WIND_CLASS_DICT,
            target_values_in_memory=WIND_TARGET_VALUES_ENOUGH)

        self.assertTrue(
            this_dict == NUM_EXAMPLES_IN_MEMORY_BY_WIND_CLASS_DICT_ENOUGH)
        self.assertTrue(this_flag)

    def test_separate_radar_files_2d3d_no_refl(self):
        """Ensures correctness of separate_radar_files_2d3d.

        In this case, there are no reflectivity files.
        """

        with self.assertRaises(ValueError):
            trainval_io.separate_radar_files_2d3d(
                radar_file_name_matrix=RADAR_FILE_NAME_MATRIX[
                    ..., NON_REFLECTIVITY_INDICES])

    def test_separate_radar_files_2d3d_no_az_shear(self):
        """Ensures correctness of separate_radar_files_2d3d.

        In this case, there are no azimuthal-shear files.
        """

        with self.assertRaises(ValueError):
            trainval_io.separate_radar_files_2d3d(
                radar_file_name_matrix=RADAR_FILE_NAME_MATRIX[
                    ..., NON_AZIMUTHAL_SHEAR_INDICES])

    def test_separate_radar_files_2d3d_bad_fields(self):
        """Ensures correctness of separate_radar_files_2d3d.

        In this case, one of the radar fields is neither reflectivity nor
        azimuthal shear.
        """

        with self.assertRaises(ValueError):
            trainval_io.separate_radar_files_2d3d(
                radar_file_name_matrix=RADAR_FILE_NAME_MATRIX[
                    ..., MESH_INDICES])

    def test_separate_radar_files_2d3d_all_good(self):
        """Ensures correctness of separate_radar_files_2d3d.

        In this case, all input files are valid.
        """

        (this_refl_file_name_matrix, this_az_shear_file_name_matrix
        ) = trainval_io.separate_radar_files_2d3d(
            radar_file_name_matrix=RADAR_FILE_NAME_MATRIX[
                ..., NON_MESH_INDICES])

        self.assertTrue(numpy.array_equal(
            this_refl_file_name_matrix, REFLECTIVITY_FILE_NAME_MATRIX))
        self.assertTrue(numpy.array_equal(
            this_az_shear_file_name_matrix, AZ_SHEAR_FILE_NAME_MATRIX))


if __name__ == '__main__':
    unittest.main()
