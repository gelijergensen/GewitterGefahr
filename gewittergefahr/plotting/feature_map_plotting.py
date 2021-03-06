"""Plotting methods for CNN feature maps."""

import numpy
import matplotlib
from gewittergefahr.gg_utils import error_checking
from gewittergefahr.plotting import plotting_utils

matplotlib.use('agg')

DEFAULT_FIG_WIDTH_INCHES = 15
DEFAULT_FIG_HEIGHT_INCHES = 15


def plot_2d_feature_map(
        feature_matrix, axes_object, colour_map_object, colour_norm_object=None,
        min_colour_value=None, max_colour_value=None, annotation_string=None):
    """Plots 2-D feature map.

    M = number of rows in grid
    N = number of columns in grid

    :param feature_matrix: M-by-N numpy array of feature values (either before
        or after activation function -- this method doesn't care).
    :param axes_object: Instance of `matplotlib.axes._subplots.AxesSubplot`.
    :param colour_map_object: Instance of `matplotlib.pyplot.cm`.
    :param colour_norm_object: Instance of `matplotlib.colors.BoundaryNorm`.
    :param min_colour_value: [used only if `colour_norm_object is None`]
        Minimum value in colour scheme.
    :param max_colour_value: [used only if `colour_norm_object is None`]
        Max value in colour scheme.
    :param annotation_string: Annotation (printed in the bottom-center of the
        map).  For no annotation, leave this alone.
    """

    error_checking.assert_is_numpy_array_without_nan(feature_matrix)
    error_checking.assert_is_numpy_array(feature_matrix, num_dimensions=2)

    if colour_norm_object is None:
        error_checking.assert_is_greater(max_colour_value, min_colour_value)
        colour_norm_object = None
    else:
        min_colour_value = colour_norm_object.boundaries[0]
        max_colour_value = colour_norm_object.boundaries[-1]

    axes_object.pcolormesh(
        feature_matrix, cmap=colour_map_object, norm=colour_norm_object,
        vmin=min_colour_value, vmax=max_colour_value, shading='flat',
        edgecolors='None')

    if annotation_string is not None:
        error_checking.assert_is_string(annotation_string)
        axes_object.text(
            0.5, 0.01, annotation_string, fontsize=20, color='k',
            horizontalalignment='center', verticalalignment='bottom',
            transform=axes_object.transAxes)

    axes_object.set_xticks([])
    axes_object.set_yticks([])


def plot_many_2d_feature_maps(
        feature_matrix, annotation_string_by_panel, num_panel_rows,
        colour_map_object, colour_norm_object=None, min_colour_value=None,
        max_colour_value=None, figure_width_inches=DEFAULT_FIG_WIDTH_INCHES,
        figure_height_inches=DEFAULT_FIG_HEIGHT_INCHES):
    """Plots many 2-D feature maps in the same figure (one per panel).

    M = number of rows in spatial grid
    N = number of columns in spatial grid
    P = number of panels

    :param feature_matrix: M-by-N-by-P numpy array of feature values (either
        before or after activation function -- this method doesn't care).
    :param annotation_string_by_panel: length-P list of annotations.
        annotation_string_by_panel[k] will be printed in the bottom-center of
        the [k]th panel.
    :param num_panel_rows: Number of panel rows.
    :param colour_map_object: See doc for `plot_2d_feature_map`.
    :param colour_norm_object: Same.
    :param min_colour_value: Same.
    :param max_colour_value: Same.
    :param figure_width_inches: Figure width.
    :param figure_height_inches: Figure height.
    :return: figure_object: Instance of `matplotlib.figure.Figure`.
    :return: axes_objects_2d_list: 2-D list, where each item is an instance of
        `matplotlib.axes._subplots.AxesSubplot`.
    """

    error_checking.assert_is_numpy_array(feature_matrix, num_dimensions=3)

    num_panels = feature_matrix.shape[-1]
    error_checking.assert_is_numpy_array(
        numpy.array(annotation_string_by_panel),
        exact_dimensions=numpy.array([num_panels])
    )

    error_checking.assert_is_integer(num_panel_rows)
    error_checking.assert_is_geq(num_panel_rows, 1)
    error_checking.assert_is_leq(num_panel_rows, num_panels)

    num_panel_columns = int(numpy.ceil(float(num_panels) / num_panel_rows))
    figure_object, axes_objects_2d_list = plotting_utils.init_panels(
        num_panel_rows=num_panel_rows, num_panel_columns=num_panel_columns,
        figure_width_inches=figure_width_inches,
        figure_height_inches=figure_height_inches)

    for i in range(num_panel_rows):
        for j in range(num_panel_columns):
            this_linear_index = i * num_panel_columns + j
            if this_linear_index >= num_panels:
                break

            plot_2d_feature_map(
                feature_matrix=feature_matrix[..., this_linear_index],
                axes_object=axes_objects_2d_list[i][j],
                colour_map_object=colour_map_object,
                colour_norm_object=colour_norm_object,
                min_colour_value=min_colour_value,
                max_colour_value=max_colour_value,
                annotation_string=annotation_string_by_panel[this_linear_index])

    return figure_object, axes_objects_2d_list
