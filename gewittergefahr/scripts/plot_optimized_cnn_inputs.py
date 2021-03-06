"""Plots optimized input examples (synthetic storm objects) for a CNN.

CNN = convolutional neural network
"""

import os.path
import argparse
import numpy
from gewittergefahr.gg_utils import radar_utils
from gewittergefahr.deep_learning import cnn
from gewittergefahr.deep_learning import deep_learning_utils as dl_utils
from gewittergefahr.deep_learning import model_interpretation
from gewittergefahr.deep_learning import feature_optimization
from gewittergefahr.deep_learning import training_validation_io as trainval_io
from gewittergefahr.plotting import \
    feature_optimization_plotting as fopt_plotting

SEPARATOR_STRING = '\n\n' + '*' * 50 + '\n\n'

INPUT_FILE_ARG_NAME = 'input_file_name'
ONE_FIG_PER_COMPONENT_ARG_NAME = 'one_figure_per_component'
NUM_PANEL_ROWS_ARG_NAME = 'num_panel_rows'
TEMP_DIRECTORY_ARG_NAME = 'temp_directory_name'
OUTPUT_DIR_ARG_NAME = 'output_dir_name'

INPUT_FILE_HELP_STRING = (
    'Path to input file.  Will be read by `feature_optimization.read_file`.')

ONE_FIG_PER_COMPONENT_HELP_STRING = (
    'Boolean flag.  If 1, this script will create one figure per model '
    'component, where each panel is a different radar field/height.  If 0, will'
    ' create one figure per radar field/height, where each panel is a different'
    ' model component.')

NUM_PANEL_ROWS_HELP_STRING = 'Number of panel rows in each figure.'

TEMP_DIRECTORY_HELP_STRING = (
    'Name of temporary directory.  Will be used only if `{0:s}` contains '
    'optimized soundings and `{1:s}` = 0.'
).format(INPUT_FILE_ARG_NAME, ONE_FIG_PER_COMPONENT_ARG_NAME)

OUTPUT_DIR_HELP_STRING = (
    'Name of output directory.  Figures will be saved here.')

DEFAULT_TEMP_DIRECTORY_NAME = '/condo/swatwork/ralager/temporary_soundings'

INPUT_ARG_PARSER = argparse.ArgumentParser()
INPUT_ARG_PARSER.add_argument(
    '--' + INPUT_FILE_ARG_NAME, type=str, required=True,
    help=INPUT_FILE_HELP_STRING)

INPUT_ARG_PARSER.add_argument(
    '--' + ONE_FIG_PER_COMPONENT_ARG_NAME, type=int, required=False, default=1,
    help=ONE_FIG_PER_COMPONENT_HELP_STRING)

INPUT_ARG_PARSER.add_argument(
    '--' + NUM_PANEL_ROWS_ARG_NAME, type=int, required=False, default=-1,
    help=NUM_PANEL_ROWS_HELP_STRING)

INPUT_ARG_PARSER.add_argument(
    '--' + TEMP_DIRECTORY_ARG_NAME, type=str, required=False,
    default=DEFAULT_TEMP_DIRECTORY_NAME, help=TEMP_DIRECTORY_HELP_STRING)

INPUT_ARG_PARSER.add_argument(
    '--' + OUTPUT_DIR_ARG_NAME, type=str, required=True,
    help=OUTPUT_DIR_HELP_STRING)


def _run(input_file_name, one_figure_per_component, num_panel_rows,
         temp_directory_name, output_dir_name):
    """Plots optimized input examples (synthetic storm objects) for a CNN.

    This is effectively the main method.

    :param input_file_name: See documentation at top of file.
    :param one_figure_per_component: Same.
    :param num_panel_rows: Same.
    :param temp_directory_name: Same.
    :param output_dir_name: Same.
    :raises: TypeError: if input examples were optimized for a model that does
        2-D and 3-D convolution.
    """

    print 'Reading data from: "{0:s}"...'.format(input_file_name)
    list_of_optimized_input_matrices, fopt_metadata_dict = (
        feature_optimization.read_file(input_file_name))

    model_file_name = fopt_metadata_dict[
        feature_optimization.MODEL_FILE_NAME_KEY]
    model_metafile_name = '{0:s}/model_metadata.p'.format(
        os.path.split(model_file_name)[0])

    print 'Reading data from: "{0:s}"...'.format(model_metafile_name)
    model_metadata_dict = cnn.read_model_metadata(model_metafile_name)
    training_option_dict = model_metadata_dict[cnn.TRAINING_OPTION_DICT_KEY]

    print 'Denormalizing optimized inputs...'
    list_of_optimized_input_matrices = model_interpretation.denormalize_data(
        list_of_input_matrices=list_of_optimized_input_matrices,
        model_metadata_dict=model_metadata_dict)
    print SEPARATOR_STRING

    if training_option_dict[trainval_io.SOUNDING_FIELDS_KEY] is None:
        list_of_metpy_dictionaries = None
    else:
        num_storm_objects = list_of_optimized_input_matrices[-1].shape[0]
        storm_elevations_m_asl = numpy.full(num_storm_objects, 0.)

        list_of_metpy_dictionaries = dl_utils.soundings_to_metpy_dictionaries(
            sounding_matrix=list_of_optimized_input_matrices[-1],
            field_names=training_option_dict[trainval_io.SOUNDING_FIELDS_KEY],
            height_levels_m_agl=training_option_dict[
                trainval_io.SOUNDING_HEIGHTS_KEY],
            storm_elevations_m_asl=storm_elevations_m_asl)

    if model_metadata_dict[cnn.USE_2D3D_CONVOLUTION_KEY]:
        fopt_plotting.plot_many_optimized_fields_3d(
            radar_image_matrix=list_of_optimized_input_matrices[0],
            radar_field_names=[radar_utils.REFL_NAME],
            radar_heights_m_agl=training_option_dict[
                trainval_io.RADAR_HEIGHTS_KEY],
            one_figure_per_component=one_figure_per_component,
            component_type_string=fopt_metadata_dict[
                feature_optimization.COMPONENT_TYPE_KEY],
            output_dir_name=output_dir_name,
            num_panel_rows=num_panel_rows,
            target_class=fopt_metadata_dict[
                feature_optimization.TARGET_CLASS_KEY],
            layer_name=fopt_metadata_dict[feature_optimization.LAYER_NAME_KEY],
            neuron_index_matrix=fopt_metadata_dict[
                feature_optimization.NEURON_INDICES_KEY],
            channel_indices=fopt_metadata_dict[
                feature_optimization.CHANNEL_INDICES_KEY],
            list_of_metpy_dictionaries=list_of_metpy_dictionaries,
            temp_directory_name=temp_directory_name)

        these_heights_m_agl = numpy.full(
            len(training_option_dict[trainval_io.RADAR_FIELDS_KEY]),
            radar_utils.SHEAR_HEIGHT_M_ASL)

        fopt_plotting.plot_many_optimized_fields_2d(
            radar_image_matrix=list_of_optimized_input_matrices[1],
            field_name_by_pair=training_option_dict[
                trainval_io.RADAR_FIELDS_KEY],
            height_by_pair_m_agl=these_heights_m_agl,
            one_figure_per_component=one_figure_per_component,
            num_panel_rows=1,
            component_type_string=fopt_metadata_dict[
                feature_optimization.COMPONENT_TYPE_KEY],
            output_dir_name=output_dir_name,
            target_class=fopt_metadata_dict[
                feature_optimization.TARGET_CLASS_KEY],
            layer_name=fopt_metadata_dict[feature_optimization.LAYER_NAME_KEY],
            neuron_index_matrix=fopt_metadata_dict[
                feature_optimization.NEURON_INDICES_KEY],
            channel_indices=fopt_metadata_dict[
                feature_optimization.CHANNEL_INDICES_KEY])

        return

    num_radar_dimensions = len(list_of_optimized_input_matrices[0].shape) - 2

    if num_radar_dimensions == 3:
        fopt_plotting.plot_many_optimized_fields_3d(
            radar_image_matrix=list_of_optimized_input_matrices[0],
            radar_field_names=training_option_dict[
                trainval_io.RADAR_FIELDS_KEY],
            radar_heights_m_agl=training_option_dict[
                trainval_io.RADAR_HEIGHTS_KEY],
            one_figure_per_component=one_figure_per_component,
            component_type_string=fopt_metadata_dict[
                feature_optimization.COMPONENT_TYPE_KEY],
            output_dir_name=output_dir_name,
            num_panel_rows=num_panel_rows,
            target_class=fopt_metadata_dict[
                feature_optimization.TARGET_CLASS_KEY],
            layer_name=fopt_metadata_dict[feature_optimization.LAYER_NAME_KEY],
            neuron_index_matrix=fopt_metadata_dict[
                feature_optimization.NEURON_INDICES_KEY],
            channel_indices=fopt_metadata_dict[
                feature_optimization.CHANNEL_INDICES_KEY],
            list_of_metpy_dictionaries=list_of_metpy_dictionaries,
            temp_directory_name=temp_directory_name)
    else:
        fopt_plotting.plot_many_optimized_fields_2d(
            radar_image_matrix=list_of_optimized_input_matrices[0],
            field_name_by_pair=training_option_dict[
                trainval_io.RADAR_FIELDS_KEY],
            height_by_pair_m_agl=training_option_dict[
                trainval_io.RADAR_HEIGHTS_KEY],
            one_figure_per_component=one_figure_per_component,
            num_panel_rows=num_panel_rows,
            component_type_string=fopt_metadata_dict[
                feature_optimization.COMPONENT_TYPE_KEY],
            output_dir_name=output_dir_name,
            target_class=fopt_metadata_dict[
                feature_optimization.TARGET_CLASS_KEY],
            layer_name=fopt_metadata_dict[feature_optimization.LAYER_NAME_KEY],
            neuron_index_matrix=fopt_metadata_dict[
                feature_optimization.NEURON_INDICES_KEY],
            channel_indices=fopt_metadata_dict[
                feature_optimization.CHANNEL_INDICES_KEY],
            list_of_metpy_dictionaries=list_of_metpy_dictionaries,
            temp_directory_name=temp_directory_name)


if __name__ == '__main__':
    INPUT_ARG_OBJECT = INPUT_ARG_PARSER.parse_args()

    _run(
        input_file_name=getattr(INPUT_ARG_OBJECT, INPUT_FILE_ARG_NAME),
        one_figure_per_component=bool(
            getattr(INPUT_ARG_OBJECT, ONE_FIG_PER_COMPONENT_ARG_NAME)),
        num_panel_rows=getattr(INPUT_ARG_OBJECT, NUM_PANEL_ROWS_ARG_NAME),
        temp_directory_name=getattr(INPUT_ARG_OBJECT, TEMP_DIRECTORY_ARG_NAME),
        output_dir_name=getattr(INPUT_ARG_OBJECT, OUTPUT_DIR_ARG_NAME)
    )
