"""Methods for creating, training, and applying a CNN*.

* convolutional neural network

--- NOTATION ---

The following letters will be used throughout this module.

E = number of examples (storm objects)
M = number of rows in each radar image
N = number of columns in each radar image
H_r = number of radar heights
F_r = number of radar fields (or "variables" or "channels")
H_s = number of sounding heights
F_s = number of sounding fields (or "variables" or "channels")
C = number of radar field/height pairs
"""

import copy
import pickle
import numpy
import netCDF4
import keras.losses
import keras.optimizers
import keras.models
import keras.callbacks
from gewittergefahr.deep_learning import deep_learning_utils as dl_utils
from gewittergefahr.deep_learning import keras_metrics
from gewittergefahr.deep_learning import training_validation_io as trainval_io
from gewittergefahr.deep_learning import input_examples
from gewittergefahr.gg_io import netcdf_io
from gewittergefahr.gg_utils import file_system_utils
from gewittergefahr.gg_utils import error_checking

NUM_EPOCHS_FOR_PLATEAU = 3
NUM_EPOCHS_FOR_EARLY_STOPPING = 6
MIN_XENTROPY_CHANGE_FOR_EARLY_STOPPING = 0.005

LOSS_FUNCTION_STRING = 'loss'
PEIRCE_SCORE_STRING = 'binary_peirce_score'
VALID_MONITOR_STRINGS = [LOSS_FUNCTION_STRING, PEIRCE_SCORE_STRING]

PERFORMANCE_METRIC_DICT = {
    'accuracy': keras_metrics.accuracy,
    'binary_accuracy': keras_metrics.binary_accuracy,
    'binary_csi': keras_metrics.binary_csi,
    'binary_frequency_bias': keras_metrics.binary_frequency_bias,
    'binary_pod': keras_metrics.binary_pod,
    'binary_pofd': keras_metrics.binary_pofd,
    'binary_peirce_score': keras_metrics.binary_peirce_score,
    'binary_success_ratio': keras_metrics.binary_success_ratio,
    'binary_focn': keras_metrics.binary_focn
}

TARGET_NAME_KEY = 'target_name'
NUM_EPOCHS_KEY = 'num_epochs'
NUM_TRAINING_BATCHES_KEY = 'num_training_batches_per_epoch'
NUM_VALIDATION_BATCHES_KEY = 'num_validation_batches_per_epoch'
MONITOR_STRING_KEY = 'monitor_string'
WEIGHT_LOSS_FUNCTION_KEY = 'weight_loss_function'
USE_2D3D_CONVOLUTION_KEY = 'use_2d3d_convolution'
VALIDATION_FILES_KEY = 'validation_file_names'
FIRST_VALIDN_TIME_KEY = 'first_validn_time_unix_sec'
LAST_VALIDN_TIME_KEY = 'last_validn_time_unix_sec'
TRAINING_OPTION_DICT_KEY = 'training_option_dict'

REQUIRED_METADATA_KEYS = [
    TARGET_NAME_KEY, NUM_EPOCHS_KEY, NUM_TRAINING_BATCHES_KEY,
    NUM_VALIDATION_BATCHES_KEY, MONITOR_STRING_KEY, WEIGHT_LOSS_FUNCTION_KEY,
    USE_2D3D_CONVOLUTION_KEY, VALIDATION_FILES_KEY, FIRST_VALIDN_TIME_KEY,
    LAST_VALIDN_TIME_KEY, TRAINING_OPTION_DICT_KEY
]

DEFAULT_TARGET_NAME = 'tornado_lead-time=0000-3600sec_distance=00000-10000m'

STORM_OBJECT_DIMENSION_KEY = 'storm_object'
FEATURE_DIMENSION_KEY = 'feature'
SPATIAL_DIMENSION_KEYS = [
    'spatial_dimension1', 'spatial_dimension2', 'spatial_dimension3'
]

FEATURE_MATRIX_KEY = 'feature_matrix'
TARGET_VALUES_KEY = 'target_values'
NUM_CLASSES_KEY = 'num_classes'


def _check_training_args(
        model_file_name, history_file_name, tensorboard_dir_name, num_epochs,
        num_training_batches_per_epoch, num_validation_batches_per_epoch,
        training_option_dict, weight_loss_function):
    """Error-checks input arguments for training.

    :param model_file_name: Path to output file (HDF5 format).  The model will
        be saved here after each epoch.
    :param history_file_name: Path to output file (CSV format).  Training
        history (performance metrics) will be saved here after each epoch.
    :param tensorboard_dir_name: Path to output directory for TensorBoard log
        files.
    :param num_epochs: Number of epochs.
    :param num_training_batches_per_epoch: Number of training batches in each
        epoch.
    :param num_validation_batches_per_epoch: Number of validation batches in
        each epoch.
    :param training_option_dict: See doc for
        `training_validation_io.example_generator_2d_or_3d`.
    :param weight_loss_function: Boolean flag.  If False, classes will be
        weighted equally in the loss function.  If True, classes will be
        weighted differently (inversely proportional to their sampling
        fractions).
    :return: class_to_weight_dict: Dictionary, where each key is the integer ID
        for a target class (-2 for "dead storm") and each value is the weight
        for the loss function.  If None, classes will be equally weighted in the
        loss function.
    """

    orig_option_dict = training_option_dict.copy()
    training_option_dict = trainval_io.DEFAULT_GENERATOR_OPTION_DICT.copy()
    training_option_dict.update(orig_option_dict)

    file_system_utils.mkdir_recursive_if_necessary(file_name=model_file_name)
    file_system_utils.mkdir_recursive_if_necessary(file_name=history_file_name)
    file_system_utils.mkdir_recursive_if_necessary(
        directory_name=tensorboard_dir_name)

    error_checking.assert_is_integer(num_epochs)
    error_checking.assert_is_geq(num_epochs, 1)
    error_checking.assert_is_integer(num_training_batches_per_epoch)
    error_checking.assert_is_geq(num_training_batches_per_epoch, 1)
    error_checking.assert_is_integer(num_validation_batches_per_epoch)
    error_checking.assert_is_geq(num_validation_batches_per_epoch, 0)

    error_checking.assert_is_boolean(weight_loss_function)
    if not weight_loss_function:
        return None

    class_to_sampling_fraction_dict = training_option_dict[
        trainval_io.SAMPLING_FRACTIONS_KEY]
    if class_to_sampling_fraction_dict is None:
        return None

    this_example_dict = input_examples.read_example_file(
        netcdf_file_name=training_option_dict[trainval_io.EXAMPLE_FILES_KEY][0],
        metadata_only=True)
    target_name = this_example_dict[input_examples.TARGET_NAME_KEY]

    return dl_utils.class_fractions_to_weights(
        sampling_fraction_by_class_dict=class_to_sampling_fraction_dict,
        target_name=target_name,
        binarize_target=training_option_dict[trainval_io.BINARIZE_TARGET_KEY])


def _get_checkpoint_object(
        output_model_file_name, monitor_string, use_validation):
    """Creates checkpoint object for Keras model.

    The checkpoint object determines, after each epoch, whether or not the new
    model will be saved.  If the model is saved, the checkpoint object also
    determines *where* the model will be saved.

    :param output_model_file_name: Path to output file (HDF5 format).
    :param monitor_string: Evaluation function reported after each epoch.  Valid
        options are in the list `VALID_MONITOR_STRINGS`.
    :param use_validation: Boolean flag.  If True, after each epoch
        `monitor_string` will be computed for the validation data and the new
        model will be saved only if `monitor_string` has improved.  If False,
        after each epoch `monitor_string` will be computed for the training
        data and the new model will be saved regardless of the value of
        `monitor_string`.
    :return: checkpoint_object: Instance of `keras.callbacks.ModelCheckpoint`.
    :raises: ValueError: if `monitor_string not in VALID_MONITOR_STRINGS`.
    """

    error_checking.assert_is_string(monitor_string)
    if monitor_string not in VALID_MONITOR_STRINGS:
        error_string = (
            '\n\n{0:s}\nValid monitors (listed above) do not include "{1:s}".'
        ).format(str(VALID_MONITOR_STRINGS), monitor_string)
        raise ValueError(error_string)

    if monitor_string == LOSS_FUNCTION_STRING:
        mode_string = 'min'
    else:
        mode_string = 'max'

    if use_validation:
        return keras.callbacks.ModelCheckpoint(
            filepath=output_model_file_name,
            monitor='val_{0:s}'.format(monitor_string), verbose=1,
            save_best_only=True, save_weights_only=False, mode=mode_string,
            period=1)

    return keras.callbacks.ModelCheckpoint(
        filepath=output_model_file_name, monitor=monitor_string, verbose=1,
        save_best_only=False, save_weights_only=False, mode=mode_string,
        period=1)


def model_to_feature_generator(model_object, output_layer_name):
    """Reduces Keras model from predictor to feature-generator.

    Specifically, this method turns an intermediate layer H into the output
    layer, removing all layers after H.  The output of the new ("intermediate")
    model will consist of activations from layer H, rather than predictions.

    :param model_object: Instance of `keras.models.Model`.
    :param output_layer_name: Name of new output layer.
    :return: intermediate_model_object: Same as input, except that all layers
        after H are removed.
    """

    error_checking.assert_is_string(output_layer_name)
    return keras.models.Model(
        inputs=model_object.input,
        outputs=model_object.get_layer(name=output_layer_name).output)


def read_model(hdf5_file_name):
    """Reads model from HDF5 file.

    :param hdf5_file_name: Path to input file.
    :return: model_object: Instance of `keras.models.Model`.
    """

    error_checking.assert_file_exists(hdf5_file_name)
    return keras.models.load_model(
        hdf5_file_name, custom_objects=PERFORMANCE_METRIC_DICT)


def write_model_metadata(
        pickle_file_name, metadata_dict, training_option_dict):
    """Writes metadata for CNN to Pickle file.

    :param pickle_file_name: Path to output file.
    :param metadata_dict: Dictionary with the following keys.
    metadata_dict['target_name']: Name of target variable (must be accepted by
        `labels.column_name_to_label_params`).
    metadata_dict['num_epochs']: Number of epochs.
    metadata_dict['num_training_batches_per_epoch']: Number of training batches
        in each epoch.
    metadata_dict['num_validation_batches_per_epoch']: Number of validation
        batches in each epoch.
    metadata_dict['monitor_string']: See doc for `_get_checkpoint_object`.
    metadata_dict['weight_loss_function']: See doc for `_check_training_args`.
    metadata_dict['use_2d3d_convolution']: Boolean flag.  If True, the net
        convolves over both 2-D and 3-D radar images, so was trained with
        `train_cnn_2d3d_myrorss`.  If False, the net convolves over only 2-D or
        only 3-D images, so was trained with `train_cnn_2d_or_3d`.
    metadata_dict['validation_file_names']: See doc for `train_cnn_2d_or_3d` or
        `train_cnn_2d3d_myrorss`.
    metadata_dict['first_validn_time_unix_sec']: Same.
    metadata_dict['last_validn_time_unix_sec']: Same.

    :param training_option_dict: See doc for
        `training_validation_io.example_generator_2d_or_3d` or
        `training_validation_io.example_generator_2d3d_myrorss`.
    :raises: ValueError: if any of the aforelisted keys are missing from
        `metadata_dict`.
    """

    orig_training_option_dict = training_option_dict.copy()
    training_option_dict = trainval_io.DEFAULT_GENERATOR_OPTION_DICT.copy()
    training_option_dict.update(orig_training_option_dict)
    metadata_dict.update({TRAINING_OPTION_DICT_KEY: training_option_dict})

    missing_keys = list(set(REQUIRED_METADATA_KEYS) - set(metadata_dict.keys()))
    if len(missing_keys):
        error_string = (
            'The following keys are missing from `metadata_dict`.\n{0:s}'
        ).format(str(missing_keys))
        raise ValueError(error_string)

    file_system_utils.mkdir_recursive_if_necessary(file_name=pickle_file_name)
    pickle_file_handle = open(pickle_file_name, 'wb')
    pickle.dump(metadata_dict, pickle_file_handle)
    pickle_file_handle.close()


def read_model_metadata(pickle_file_name):
    """Reads metadata from Pickle file.

    :param pickle_file_name: Path to input file.
    :return: metadata_dict: See doc for `write_model_metadata`.
    """

    pickle_file_handle = open(pickle_file_name, 'rb')
    metadata_dict = pickle.load(pickle_file_handle)
    pickle_file_handle.close()

    if TARGET_NAME_KEY not in metadata_dict:
        metadata_dict[TARGET_NAME_KEY] = DEFAULT_TARGET_NAME

    return metadata_dict


def train_cnn_2d_or_3d(
        model_object, model_file_name, history_file_name, tensorboard_dir_name,
        num_epochs, num_training_batches_per_epoch, training_option_dict,
        monitor_string=LOSS_FUNCTION_STRING, weight_loss_function=False,
        num_validation_batches_per_epoch=0, validation_file_names=None,
        first_validn_time_unix_sec=None, last_validn_time_unix_sec=None):
    """Trains CNN with radar images, which are either all 2-D or all 3-D.

    :param model_object: Instance of `keras.models.Model` or
        `keras.models.Sequential`, containing the architecture of the net to be
        trained.
    :param model_file_name: See doc for `_check_training_args`.
    :param history_file_name: Same.
    :param tensorboard_dir_name: Same.
    :param num_epochs: Same.
    :param num_training_batches_per_epoch: Same.
    :param training_option_dict: See doc for
        `training_validation_io.example_generator_2d_or_3d`.
    :param monitor_string: See doc for `_get_checkpoint_object`.
    :param weight_loss_function: See doc for `_check_training_args`.
    :param num_validation_batches_per_epoch: Same.
    :param validation_file_names:
        [used only if num_validation_batches_per_epoch > 0]
        1-D list of paths to files with validation examples.  These will be read
        by `input_examples.read_example_file`.

    :param first_validn_time_unix_sec:
        [used only if num_validation_batches_per_epoch > 0]
        Start of validation period.  Examples before this time will not be used.

    :param last_validn_time_unix_sec: Same.
        [used only if num_validation_batches_per_epoch > 0]
        End of validation period.  Examples after this time will not be used.
    """

    class_to_weight_dict = _check_training_args(
        model_file_name=model_file_name, history_file_name=history_file_name,
        tensorboard_dir_name=tensorboard_dir_name, num_epochs=num_epochs,
        num_training_batches_per_epoch=num_training_batches_per_epoch,
        num_validation_batches_per_epoch=num_validation_batches_per_epoch,
        training_option_dict=training_option_dict,
        weight_loss_function=weight_loss_function)

    history_object = keras.callbacks.CSVLogger(
        filename=history_file_name, separator=',', append=False)

    checkpoint_object = _get_checkpoint_object(
        output_model_file_name=model_file_name, monitor_string=monitor_string,
        use_validation=num_validation_batches_per_epoch is not None)

    early_stopping_object = keras.callbacks.EarlyStopping(
        monitor='val_loss', min_delta=MIN_XENTROPY_CHANGE_FOR_EARLY_STOPPING,
        patience=NUM_EPOCHS_FOR_EARLY_STOPPING, verbose=1, mode='min')

    plateau_object = keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.2, patience=NUM_EPOCHS_FOR_PLATEAU,
        verbose=1, mode='min')

    list_of_callback_objects = [
        checkpoint_object, history_object, early_stopping_object, plateau_object
    ]

    if num_validation_batches_per_epoch > 0:
        validation_option_dict = copy.deepcopy(training_option_dict)
        validation_option_dict[
            trainval_io.EXAMPLE_FILES_KEY] = validation_file_names
        validation_option_dict[
            trainval_io.FIRST_STORM_TIME_KEY] = first_validn_time_unix_sec
        validation_option_dict[
            trainval_io.LAST_STORM_TIME_KEY] = last_validn_time_unix_sec

        model_object.fit_generator(
            generator=trainval_io.example_generator_2d_or_3d(
                training_option_dict),
            steps_per_epoch=num_training_batches_per_epoch, epochs=num_epochs,
            verbose=1, class_weight=class_to_weight_dict,
            callbacks=list_of_callback_objects,
            validation_data=trainval_io.example_generator_2d_or_3d(
                validation_option_dict),
            validation_steps=num_validation_batches_per_epoch)
    else:
        model_object.fit_generator(
            generator=trainval_io.example_generator_2d_or_3d(
                training_option_dict),
            steps_per_epoch=num_training_batches_per_epoch, epochs=num_epochs,
            verbose=1, class_weight=class_to_weight_dict,
            callbacks=list_of_callback_objects)


def train_cnn_2d3d_myrorss(
        model_object, model_file_name, history_file_name, tensorboard_dir_name,
        num_epochs, num_training_batches_per_epoch, training_option_dict,
        monitor_string=LOSS_FUNCTION_STRING, weight_loss_function=False,
        num_validation_batches_per_epoch=0, validation_file_names=None,
        first_validn_time_unix_sec=None, last_validn_time_unix_sec=None):
    """Trains CNN with both 2-D and 3-D radar images.

    :param model_object: See doc for `train_cnn_2d_or_3d`.
    :param model_file_name: Same.
    :param history_file_name: Same.
    :param tensorboard_dir_name: Same.
    :param num_epochs: Same.
    :param num_training_batches_per_epoch: Same.
    :param training_option_dict: Same.
    :param monitor_string: Same.
    :param weight_loss_function: Same.
    :param num_validation_batches_per_epoch: Same.
    :param validation_file_names: Same.
    :param first_validn_time_unix_sec: Same.
    :param last_validn_time_unix_sec: Same.
    """

    class_to_weight_dict = _check_training_args(
        model_file_name=model_file_name, history_file_name=history_file_name,
        tensorboard_dir_name=tensorboard_dir_name, num_epochs=num_epochs,
        num_training_batches_per_epoch=num_training_batches_per_epoch,
        num_validation_batches_per_epoch=num_validation_batches_per_epoch,
        training_option_dict=training_option_dict,
        weight_loss_function=weight_loss_function)

    history_object = keras.callbacks.CSVLogger(
        filename=history_file_name, separator=',', append=False)

    checkpoint_object = _get_checkpoint_object(
        output_model_file_name=model_file_name, monitor_string=monitor_string,
        use_validation=num_validation_batches_per_epoch is not None)

    early_stopping_object = keras.callbacks.EarlyStopping(
        monitor='val_loss', min_delta=MIN_XENTROPY_CHANGE_FOR_EARLY_STOPPING,
        patience=NUM_EPOCHS_FOR_EARLY_STOPPING, verbose=1, mode='min')

    plateau_object = keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.2, patience=NUM_EPOCHS_FOR_PLATEAU,
        verbose=1, mode='min')

    list_of_callback_objects = [
        checkpoint_object, history_object, early_stopping_object, plateau_object
    ]

    if num_validation_batches_per_epoch > 0:
        validation_option_dict = copy.deepcopy(training_option_dict)
        validation_option_dict[
            trainval_io.EXAMPLE_FILES_KEY] = validation_file_names
        validation_option_dict[
            trainval_io.FIRST_STORM_TIME_KEY] = first_validn_time_unix_sec
        validation_option_dict[
            trainval_io.LAST_STORM_TIME_KEY] = last_validn_time_unix_sec

        model_object.fit_generator(
            generator=trainval_io.example_generator_2d3d_myrorss(
                training_option_dict),
            steps_per_epoch=num_training_batches_per_epoch, epochs=num_epochs,
            verbose=1, class_weight=class_to_weight_dict,
            callbacks=list_of_callback_objects,
            validation_data=trainval_io.example_generator_2d3d_myrorss(
                validation_option_dict),
            validation_steps=num_validation_batches_per_epoch)
    else:
        model_object.fit_generator(
            generator=trainval_io.example_generator_2d3d_myrorss(
                training_option_dict),
            steps_per_epoch=num_training_batches_per_epoch, epochs=num_epochs,
            verbose=1, class_weight=class_to_weight_dict,
            callbacks=list_of_callback_objects)


def apply_2d_cnn(
        model_object, radar_image_matrix, sounding_matrix=None,
        return_features=False, output_layer_name=None):
    """Applies CNN to 2-D radar images.

    :param model_object: Trained instance of `keras.models.Model` or
        `keras.models.Sequential`.
    :param radar_image_matrix: E-by-M-by-N-by-C numpy array of storm-centered
        radar images.
    :param sounding_matrix: [may be None]
        numpy array (E x H_s x F_s) of storm-centered sounding.
    :param return_features: Boolean flag.  If True, this method will return
        features (activations of an intermediate layer).  If False, this method
        will return probabilistic predictions.
    :param output_layer_name: [used only if return_features = True]
        Name of layer for which features will be returned.

    If return_features = True...

    :return: feature_matrix: E-by-Z numpy array of features, where Z = number of
        outputs from the given layer.

    If return_features = False...

    :return: class_probability_matrix: E-by-K numpy array of class
        probabilities.  class_probability_matrix[i, k] is the forecast
        probability that the [i]th storm object belongs to the [k]th class.
        Classes are mutually exclusive and collectively exhaustive, so the sum
        across each row is 1.
    """

    dl_utils.check_radar_images(
        radar_image_matrix=radar_image_matrix, min_num_dimensions=4,
        max_num_dimensions=4)

    error_checking.assert_is_boolean(return_features)
    num_examples = radar_image_matrix.shape[0]

    if sounding_matrix is not None:
        dl_utils.check_soundings(
            sounding_matrix=sounding_matrix, num_examples=num_examples)

    if return_features:
        intermediate_model_object = model_to_feature_generator(
            model_object=model_object, output_layer_name=output_layer_name)
        if sounding_matrix is None:
            return intermediate_model_object.predict(
                radar_image_matrix, batch_size=num_examples)

        return intermediate_model_object.predict(
            [radar_image_matrix, sounding_matrix], batch_size=num_examples)

    if sounding_matrix is None:
        these_probabilities = model_object.predict(
            radar_image_matrix, batch_size=num_examples)
    else:
        these_probabilities = model_object.predict(
            [radar_image_matrix, sounding_matrix], batch_size=num_examples)

    if these_probabilities.shape[-1] > 1:
        return these_probabilities

    these_probabilities = numpy.reshape(
        these_probabilities, (len(these_probabilities), 1))
    return numpy.hstack((1. - these_probabilities, these_probabilities))


def apply_3d_cnn(
        model_object, radar_image_matrix, sounding_matrix=None,
        return_features=False, output_layer_name=None):
    """Applies CNN to 3-D radar images.

    :param model_object: Trained instance of `keras.models.Model` or
        `keras.models.Sequential`.
    :param radar_image_matrix: numpy array (E x M x N x H_r x F_r) of
        storm-centered radar images.
    :param sounding_matrix: See doc for `apply_2d_cnn`.
    :param return_features: Same.
    :param output_layer_name: Same.

    If return_features = True...

    :return: feature_matrix: See doc for `apply_2d_cnn`.

    If return_features = False...

    :return: class_probability_matrix: See doc for `apply_2d_cnn`.
    """

    dl_utils.check_radar_images(
        radar_image_matrix=radar_image_matrix, min_num_dimensions=5,
        max_num_dimensions=5)

    error_checking.assert_is_boolean(return_features)
    num_examples = radar_image_matrix.shape[0]

    if sounding_matrix is not None:
        dl_utils.check_soundings(
            sounding_matrix=sounding_matrix, num_examples=num_examples)

    if return_features:
        intermediate_model_object = model_to_feature_generator(
            model_object=model_object, output_layer_name=output_layer_name)
        if sounding_matrix is None:
            return intermediate_model_object.predict(
                radar_image_matrix, batch_size=num_examples)

        return intermediate_model_object.predict(
            [radar_image_matrix, sounding_matrix], batch_size=num_examples)

    if sounding_matrix is None:
        these_probabilities = model_object.predict(
            radar_image_matrix, batch_size=num_examples)
    else:
        these_probabilities = model_object.predict(
            [radar_image_matrix, sounding_matrix], batch_size=num_examples)

    if these_probabilities.shape[-1] > 1:
        return these_probabilities

    these_probabilities = numpy.reshape(
        these_probabilities, (len(these_probabilities), 1))
    return numpy.hstack((1. - these_probabilities, these_probabilities))


def apply_2d3d_cnn(
        model_object, reflectivity_image_matrix_dbz, az_shear_image_matrix_s01,
        sounding_matrix=None, return_features=False, output_layer_name=None):
    """Applies CNN to both 2-D and 3-D radar images.

    M = number of rows in each reflectivity image
    N = number of columns in each reflectivity image

    :param model_object: Trained instance of `keras.models.Model` or
        `keras.models.Sequential`.
    :param reflectivity_image_matrix_dbz: numpy array (E x M x N x H_r x 1) of
        storm-centered reflectivity images.
    :param az_shear_image_matrix_s01: numpy array (E x 2M x 2N x C) of
        storm-centered azimuthal-shear images.
    :param sounding_matrix: See doc for `apply_2d_cnn`.
    :param return_features: Same.
    :param output_layer_name: Same.

    If return_features = True...

    :return: feature_matrix: See doc for `apply_2d_cnn`.

    If return_features = False...

    :return: class_probability_matrix: See doc for `apply_2d_cnn`.
    """

    dl_utils.check_radar_images(
        radar_image_matrix=reflectivity_image_matrix_dbz, min_num_dimensions=5,
        max_num_dimensions=5)
    dl_utils.check_radar_images(
        radar_image_matrix=az_shear_image_matrix_s01,
        min_num_dimensions=4, max_num_dimensions=4)

    num_examples = reflectivity_image_matrix_dbz.shape[0]
    error_checking.assert_is_boolean(return_features)

    expected_dimensions = numpy.array(
        reflectivity_image_matrix_dbz.shape[:-1] + (1,))
    error_checking.assert_is_numpy_array(
        reflectivity_image_matrix_dbz, exact_dimensions=expected_dimensions)

    expected_dimensions = numpy.array(
        (num_examples,) + az_shear_image_matrix_s01[1:])
    error_checking.assert_is_numpy_array(
        az_shear_image_matrix_s01, exact_dimensions=expected_dimensions)

    if sounding_matrix is not None:
        dl_utils.check_soundings(
            sounding_matrix=sounding_matrix, num_examples=num_examples)

    if return_features:
        intermediate_model_object = model_to_feature_generator(
            model_object=model_object, output_layer_name=output_layer_name)
        if sounding_matrix is None:
            return intermediate_model_object.predict(
                [reflectivity_image_matrix_dbz,
                 az_shear_image_matrix_s01],
                batch_size=num_examples)

        return intermediate_model_object.predict(
            [reflectivity_image_matrix_dbz, az_shear_image_matrix_s01,
             sounding_matrix],
            batch_size=num_examples)

    if sounding_matrix is None:
        these_probabilities = model_object.predict(
            [reflectivity_image_matrix_dbz, az_shear_image_matrix_s01],
            batch_size=num_examples)
    else:
        these_probabilities = model_object.predict(
            [reflectivity_image_matrix_dbz, az_shear_image_matrix_s01,
             sounding_matrix],
            batch_size=num_examples)

    if these_probabilities.shape[-1] > 1:
        return these_probabilities

    these_probabilities = numpy.reshape(
        these_probabilities, (len(these_probabilities), 1))
    return numpy.hstack((1. - these_probabilities, these_probabilities))


def write_features(
        netcdf_file_name, feature_matrix, target_values, num_classes,
        append_to_file=False):
    """Writes features (activations of intermediate layer) to NetCDF file.

    :param netcdf_file_name: Path to output file.
    :param feature_matrix: numpy array of features.  Must have >= 2 dimensions,
        where the first dimension (length E) represents examples and the last
        dimension represents channels (transformed input variables).
    :param target_values: length-E numpy array of target values.  Must all be
        integers in 0...(K - 1), where K = number of classes.
    :param num_classes: Number of classes.
    :param append_to_file: Boolean flag.  If True, will append to existing file.
        If False, will create new file.
    """

    error_checking.assert_is_boolean(append_to_file)
    error_checking.assert_is_numpy_array(feature_matrix)
    num_storm_objects = feature_matrix.shape[0]

    dl_utils.check_target_array(
        target_array=target_values, num_dimensions=1, num_classes=num_classes)
    error_checking.assert_is_numpy_array(
        target_values, exact_dimensions=numpy.array([num_storm_objects]))

    if append_to_file:
        error_checking.assert_is_string(netcdf_file_name)
        netcdf_dataset = netCDF4.Dataset(
            netcdf_file_name, 'a', format='NETCDF3_64BIT_OFFSET')

        prev_num_storm_objects = len(numpy.array(
            netcdf_dataset.variables[TARGET_VALUES_KEY][:]))
        netcdf_dataset.variables[FEATURE_MATRIX_KEY][
            prev_num_storm_objects:(prev_num_storm_objects + num_storm_objects),
            ...
        ] = feature_matrix
        netcdf_dataset.variables[TARGET_VALUES_KEY][
            prev_num_storm_objects:(prev_num_storm_objects + num_storm_objects)
        ] = target_values

    else:
        file_system_utils.mkdir_recursive_if_necessary(
            file_name=netcdf_file_name)
        netcdf_dataset = netCDF4.Dataset(
            netcdf_file_name, 'w', format='NETCDF3_64BIT_OFFSET')

        netcdf_dataset.setncattr(NUM_CLASSES_KEY, num_classes)
        netcdf_dataset.createDimension(STORM_OBJECT_DIMENSION_KEY, None)
        netcdf_dataset.createDimension(
            FEATURE_DIMENSION_KEY, feature_matrix.shape[1])

        num_spatial_dimensions = len(feature_matrix.shape) - 2
        tuple_of_dimension_keys = (STORM_OBJECT_DIMENSION_KEY,)

        for i in range(num_spatial_dimensions):
            netcdf_dataset.createDimension(
                SPATIAL_DIMENSION_KEYS[i], feature_matrix.shape[i + 1])
            tuple_of_dimension_keys += (SPATIAL_DIMENSION_KEYS[i],)

        tuple_of_dimension_keys += (FEATURE_DIMENSION_KEY,)
        netcdf_dataset.createVariable(
            FEATURE_MATRIX_KEY, datatype=numpy.float32,
            dimensions=tuple_of_dimension_keys)
        netcdf_dataset.variables[FEATURE_MATRIX_KEY][:] = feature_matrix

        netcdf_dataset.createVariable(
            TARGET_VALUES_KEY, datatype=numpy.int32,
            dimensions=STORM_OBJECT_DIMENSION_KEY)
        netcdf_dataset.variables[TARGET_VALUES_KEY][:] = target_values

    netcdf_dataset.close()


def read_features(netcdf_file_name):
    """Reads features (activations of intermediate layer) from NetCDF file.

    :param netcdf_file_name: Path to input file.
    :return: feature_matrix: E-by-Z numpy array of features.
    :return: target_values: length-E numpy array of target values.  All in
        0...(K - 1), where K = number of classes.
    :return: num_classes: Number of classes.
    """

    netcdf_dataset = netcdf_io.open_netcdf(
        netcdf_file_name=netcdf_file_name, raise_error_if_fails=True)

    feature_matrix = numpy.array(
        netcdf_dataset.variables[FEATURE_MATRIX_KEY][:])
    target_values = numpy.array(
        netcdf_dataset.variables[TARGET_VALUES_KEY][:], dtype=int)
    num_classes = getattr(netcdf_dataset, NUM_CLASSES_KEY)
    netcdf_dataset.close()

    return feature_matrix, target_values, num_classes
