import gc
import pathlib
import os
import sys
from weakref import proxy
from pathlib import Path

import imageio
import numpy as np
import pytest
import vtk

import pyvista
from pyvista import examples
from pyvista.plotting import system_supports_plotting
from pyvista.plotting.plotting import SUPPORTED_FORMATS

NO_PLOTTING = not system_supports_plotting()

ffmpeg_failed = False
try:
    try:
        import imageio_ffmpeg
        imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        imageio.plugins.ffmpeg.download()
except:
    ffmpeg_failed = True

if __name__ != '__main__':
    OFF_SCREEN = 'pytest' in sys.modules
else:
    OFF_SCREEN = False

pyvista.OFF_SCREEN = OFF_SCREEN
VTK9 = vtk.vtkVersion().GetVTKMajorVersion() >= 9

sphere = pyvista.Sphere()
sphere_b = pyvista.Sphere(1.0)
sphere_c = pyvista.Sphere(2.0)


def _is_vtk(obj):
    try:
        return obj.__class__.__name__.startswith('vtk')
    except Exception:  # old Python sometimes no __class__.__name__
        return False


@pytest.fixture(autouse=True)
def check_gc():
    """Ensure that all VTK objects are garbage-collected by Python."""
    before = set(id(o) for o in gc.get_objects() if _is_vtk(o))
    yield
    pyvista.close_all()
    gc.collect()
    after = [o for o in gc.get_objects() if _is_vtk(o) and id(o) not in before]
    assert len(after) == 0, \
        'Not all objects GCed:\n' + \
        '\n'.join(sorted(o.__class__.__name__ for o in after))


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot(tmpdir):
    tmp_dir = tmpdir.mkdir("tmpdir2")
    filename = str(tmp_dir.join('tmp.png'))
    scalars = np.arange(sphere.n_points)
    cpos, img = pyvista.plot(sphere,
                             off_screen=OFF_SCREEN,
                             full_screen=True,
                             text='this is a sphere',
                             show_bounds=True,
                             color='r',
                             style='wireframe',
                             line_width=10,
                             scalars=scalars,
                             flip_scalars=True,
                             cmap='bwr',
                             interpolate_before_map=True,
                             screenshot=filename,
                             return_img=True)
    assert isinstance(cpos, pyvista.CameraPosition)
    assert isinstance(img, np.ndarray)
    assert os.path.isfile(filename)

    filename = pathlib.Path(str(tmp_dir.join('tmp2.png')))
    cpos = pyvista.plot(sphere, off_screen=OFF_SCREEN, screenshot=filename)

    # Ensure it added a PNG extension by default
    assert filename.with_suffix(".png").is_file()

    # test invalid extension
    with pytest.raises(ValueError):
        filename = pathlib.Path(str(tmp_dir.join('tmp3.foo')))
        pyvista.plot(sphere, off_screen=OFF_SCREEN, screenshot=filename)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_invalid_style():
    with pytest.raises(ValueError):
        pyvista.plot(sphere, style='not a style')


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_interactor_style():
    plotter = pyvista.Plotter()
    plotter.add_mesh(sphere)
    interactions = (
        'trackball',
        'trackball_actor',
        'image',
        'joystick',
        'zoom',
        'terrain',
        'rubber_band',
        'rubber_band_2d',
    )
    for interaction in interactions:
        getattr(plotter, f'enable_{interaction}_style')()
        assert plotter._style_class is not None
    plotter.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_lighting():
    plotter = pyvista.Plotter()

    # test default disable_3_lights()
    lights = list(plotter.renderer.GetLights())
    assert all([light.GetSwitch() for light in lights])

    plotter.enable_3_lights()
    lights = list(plotter.renderer.GetLights())
    headlight = lights.pop(0)
    assert not headlight.GetSwitch()
    for i in range(len(lights)):
        if i < 3:
            assert lights[i].GetSwitch()
        else:
            assert not lights[i].GetSwitch()
    assert lights[0].GetIntensity() == 1.0
    assert lights[1].GetIntensity() == 0.6
    assert lights[2].GetIntensity() == 0.5
    plotter.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plotter_shape_invalid():
    # wrong size
    with pytest.raises(ValueError):
        pyvista.Plotter(shape=(1,))
    # not positive
    with pytest.raises(ValueError):
        pyvista.Plotter(shape=(1, 0))
    with pytest.raises(ValueError):
        pyvista.Plotter(shape=(0, 2))
    # not a sequence
    with pytest.raises(TypeError):
        pyvista.Plotter(shape={1, 2})


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_bounds_axes_with_no_data():
    plotter = pyvista.Plotter()
    plotter.show_bounds()
    plotter.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_show_grid():
    plotter = pyvista.Plotter()
    plotter.show_grid()
    plotter.add_mesh(sphere)
    plotter.close()



cpos_param = [[(2.0, 5.0, 13.0),
              (0.0, 0.0, 0.0),
              (-0.7, -0.5, 0.3)],
             [-1, 2, -5],  # trigger view vector
             [1.0, 2.0, 3.0],
]
cpos_param.extend(pyvista.plotting.Renderer.CAMERA_STR_ATTR_MAP)
@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
@pytest.mark.parametrize('cpos', cpos_param)
def test_set_camera_position(cpos, sphere):
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.camera_position = cpos
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
@pytest.mark.parametrize('cpos', [[(2.0, 5.0),
                                   (0.0, 0.0, 0.0),
                                   (-0.7, -0.5, 0.3)],
                                  [-1, 2],
                                  [(1,2,3)],
                                  'notvalid'])
def test_set_camera_position_invalid(cpos, sphere):
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    with pytest.raises(pyvista.core.errors.InvalidCameraError):
        plotter.camera_position = cpos



@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_no_active_scalars():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    with pytest.raises(ValueError):
        plotter.update_scalars(np.arange(5))
    with pytest.raises(ValueError):
        plotter.update_scalars(np.arange(sphere.n_faces))


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_show_bounds():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.show_bounds(show_xaxis=False,
                        show_yaxis=False,
                        show_zaxis=False,
                        show_xlabels=False,
                        show_ylabels=False,
                        show_zlabels=False,
                        use_2d=True)
    # And test backwards compatibility
    plotter.add_bounds_axes(show_xaxis=False,
                            show_yaxis=False,
                            show_zaxis=False,
                            show_xlabels=False,
                            show_ylabels=False,
                            show_zlabels=False,
                            use_2d=True)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_label_fmt():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.show_bounds(xlabel='My X', fmt=r'%.3f')
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
@pytest.mark.parametrize('grid', [True, 'both', 'front', 'back'])
@pytest.mark.parametrize('location', ['all', 'origin', 'outer', 'front', 'back'])
def test_plot_show_bounds_params(grid, location):
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(pyvista.Cube())
    plotter.show_bounds(grid=grid, ticks='inside', location=location)
    plotter.show_bounds(grid=grid, ticks='outside', location=location)
    plotter.show_bounds(grid=grid, ticks='both', location=location)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plotter_scale():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.set_scale(10, 10, 10)
    assert plotter.scale == [10, 10, 10]
    plotter.set_scale(5.0)
    plotter.set_scale(yscale=6.0)
    plotter.set_scale(zscale=9.0)
    assert plotter.scale == [5.0, 6.0, 9.0]
    plotter.scale = [1.0, 4.0, 2.0]
    assert plotter.scale == [1.0, 4.0, 2.0]
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_add_scalar_bar():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.add_scalar_bar(label_font_size=10, title_font_size=20, title='woa',
                           interactive=True, vertical=True)
    plotter.add_scalar_bar(background_color='white', n_colors=256)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_invalid_add_scalar_bar():
    with pytest.raises(AttributeError):
        plotter = pyvista.Plotter()
        plotter.add_scalar_bar()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_list():
    pyvista.plot([sphere, sphere_b],
                 off_screen=OFF_SCREEN,
                 style='points')

    pyvista.plot([sphere, sphere_b, sphere_c],
                 off_screen=OFF_SCREEN,
                 style='wireframe')


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_add_lines_invalid():
    plotter = pyvista.Plotter()
    with pytest.raises(TypeError):
        plotter.add_lines(range(10))


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_open_gif_invalid():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    with pytest.raises(ValueError):
        plotter.open_gif('file.abs')


@pytest.mark.skipif(ffmpeg_failed, reason="Requires imageio-ffmpeg")
@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_make_movie():
    # Make temporary file
    filename = os.path.join(pyvista.USER_DATA_PATH, 'tmp.mp4')

    movie_sphere = sphere.copy()
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.open_movie(filename)
    actor = plotter.add_axes_at_origin()
    plotter.remove_actor(actor, reset_camera=False, render=True)
    plotter.add_mesh(movie_sphere,
                     scalars=np.random.random(movie_sphere.n_faces))
    plotter.show(auto_close=False, window_size=[304, 304])
    plotter.set_focus([0, 0, 0])
    for i in range(3):  # limiting number of frames to write for speed
        plotter.write_frame()
        random_points = np.random.random(movie_sphere.points.shape)
        movie_sphere.points[:] = random_points*0.01 + movie_sphere.points*0.99
        movie_sphere.points[:] -= movie_sphere.points.mean(0)
        scalars = np.random.random(movie_sphere.n_faces)
        plotter.update_scalars(scalars)

    # checking if plotter closes
    ref = proxy(plotter)
    plotter.close()

    # remove file
    os.remove(filename)

    try:
        ref
    except:
        raise RuntimeError('Plotter did not close')


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_add_legend():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    with pytest.raises(ValueError):
        plotter.add_legend()
    legend_labels = [['sphere', 'r']]
    plotter.add_legend(labels=legend_labels, border=True, bcolor=None,
                       size=[0.1, 0.1])
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_add_axes_twice():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_axes()
    plotter.add_axes(interactive=True)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_add_point_labels():
    n = 10
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    points = np.random.random((n, 3))

    with pytest.raises(ValueError):
        plotter.add_point_labels(points, range(n - 1))

    plotter.add_point_labels(points, range(n), show_points=True, point_color='r')
    plotter.add_point_labels(points - 1, range(n), show_points=False, point_color='r')
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
@pytest.mark.parametrize('always_visible', [False, True])
def test_add_point_labels_always_visible(always_visible):
    # just make sure it runs without exception
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_point_labels(
        np.array([[0, 0, 0]]), ['hello world'], always_visible=always_visible)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_set_background():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.set_background('k')
    plotter.background_color = "yellow"
    plotter.set_background([0, 0, 0], top=[1,1,1]) # Gradient
    _ = plotter.background_color
    plotter.show()

    plotter = pyvista.Plotter(off_screen=OFF_SCREEN, shape=(1,2))
    plotter.set_background('orange')
    for renderer in plotter.renderers:
        assert renderer.GetBackground() == pyvista.parse_color('orange')
    plotter.show()

    plotter = pyvista.Plotter(off_screen=OFF_SCREEN, shape=(1,2))
    plotter.subplot(0,1)
    plotter.set_background('orange', all_renderers=False)
    assert plotter.renderers[0].GetBackground() != pyvista.parse_color('orange')
    assert plotter.renderers[1].GetBackground() == pyvista.parse_color('orange')
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_add_points():
    n = 10
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    points = np.random.random((n, 3))
    plotter.add_points(points, scalars=np.arange(10), cmap=None, flip_scalars=True)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_key_press_event():
    plotter = pyvista.Plotter(off_screen=False)
    plotter.key_press_event(None, None)
    plotter.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_enable_picking_gc():
    plotter = pyvista.Plotter(off_screen=False)
    sphere = pyvista.Sphere()
    plotter.add_mesh(sphere)
    plotter.enable_cell_picking()
    plotter.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_left_button_down():
    plotter = pyvista.Plotter(off_screen=False)
    if VTK9:
        with pytest.raises(ValueError):
            plotter.left_button_down(None, None)
    else:
        plotter.left_button_down(None, None)
    plotter.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_show_axes():
    # if not closed correctly, a seg fault occurs when exitting
    plotter = pyvista.Plotter(off_screen=False)
    plotter.show_axes()
    plotter.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_update():
    plotter = pyvista.Plotter(off_screen=True)
    plotter.update()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_cell_arrays():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    scalars = np.arange(sphere.n_faces)
    plotter.add_mesh(sphere, interpolate_before_map=True, scalars=scalars,
                     n_colors=5, rng=10)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_clim():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    scalars = np.arange(sphere.n_faces)
    plotter.add_mesh(sphere, interpolate_before_map=True, scalars=scalars,
                     n_colors=5, clim=10)
    plotter.show()
    assert plotter.mapper.GetScalarRange() == (-10, 10)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_invalid_n_arrays():
    with pytest.raises(ValueError):
        plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
        plotter.add_mesh(sphere, scalars=np.arange(10))
        plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_arrow():
    cent = np.random.random(3)
    direction = np.random.random(3)
    pyvista.plot_arrows(cent, direction, off_screen=OFF_SCREEN)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_arrows():
    cent = np.random.random((100, 3))
    direction = np.random.random((100, 3))
    pyvista.plot_arrows(cent, direction, off_screen=OFF_SCREEN)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_axes():
    plotter = pyvista.Plotter(off_screen=True)
    plotter.add_axes()
    plotter.add_mesh(pyvista.Sphere())
    plotter.show()
    plotter = pyvista.Plotter(off_screen=True)
    plotter.add_orientation_widget(pyvista.Cube())
    plotter.add_mesh(pyvista.Cube())
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_box_axes():
    plotter = pyvista.Plotter(off_screen=True)
    plotter.add_axes(box=True, box_args={'color_box':True})
    plotter.add_mesh(pyvista.Sphere())
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_screenshot(tmpdir):
    plotter = pyvista.Plotter(off_screen=True)
    plotter.add_mesh(pyvista.Sphere())
    img = plotter.screenshot(transparent_background=True)
    assert np.any(img)
    img_again = plotter.screenshot()
    assert np.any(img_again)
    filename = str(tmpdir.mkdir("tmpdir").join('export-graphic.svg'))
    plotter.save_graphic(filename)

    # checking if plotter closes
    ref = proxy(plotter)
    plotter.close()

    try:
        ref
    except:
        raise RuntimeError('Plotter did not close')


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
@pytest.mark.parametrize('ext', SUPPORTED_FORMATS)
def test_save_screenshot(tmpdir, sphere, ext):
    filename = str(tmpdir.mkdir("tmpdir").join('tmp' + ext))
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.screenshot(filename)
    assert os.path.isfile(filename)
    assert Path(filename).stat().st_size


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_scalars_by_name():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    data = examples.load_uniform()
    plotter.add_mesh(data, scalars='Spatial Cell Data')
    plotter.show()


def test_themes():
    pyvista.set_plot_theme('paraview')
    pyvista.set_plot_theme('document')
    pyvista.set_plot_theme('night')
    pyvista.set_plot_theme('default')


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_multi_block_plot():
    multi = pyvista.MultiBlock()
    multi.append(examples.load_rectilinear())
    uni = examples.load_uniform()
    arr = np.random.rand(uni.n_cells)
    uni.cell_arrays.append(arr, 'Random Data')
    multi.append(uni)
    # And now add a data set without the desired array and a NULL component
    multi[3] = examples.load_airplane()
    with pytest.raises(ValueError):
        # The scalars are not available in all datasets so raises ValueError
        multi.plot(scalars='Random Data', off_screen=OFF_SCREEN, multi_colors=True)
    multi.plot(off_screen=OFF_SCREEN, multi_colors=True)



@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_clear():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.clear()
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_texture():
    """"Test adding a texture to a plot"""
    globe = examples.load_globe()
    texture = examples.load_globe_texture()
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(globe, texture=texture)
    plotter.show()
    texture.plot(off_screen=OFF_SCREEN)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_texture_associated():
    """"Test adding a texture to a plot"""
    globe = examples.load_globe()
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(globe, texture=True)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_read_texture_from_numpy():
    """"Test adding a texture to a plot"""
    globe = examples.load_globe()
    texture = pyvista.numpy_to_texture(imageio.imread(examples.mapfile))
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(globe, texture=texture)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_rgb():
    """"Test adding a texture to a plot"""
    cube = pyvista.Cube()
    cube.clear_arrays()
    x_face_color = (255, 0, 0)
    y_face_color = (0, 255, 0)
    z_face_color = (0, 0, 255)
    face_colors = np.array([x_face_color,
                            x_face_color,
                            y_face_color,
                            y_face_color,
                            z_face_color,
                            z_face_color,
                            ], dtype=np.uint8)
    cube.cell_arrays['face_colors'] = face_colors
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(cube, scalars='face_colors', rgb=True)
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_multi_component_array():
    """"Test adding a texture to a plot"""
    image = pyvista.UniformGrid((3,3,3))
    image['array'] = np.random.randn(*image.dimensions).ravel(order='f')
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(image, scalars='array')
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_camera():
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(sphere)
    plotter.view_isometric()
    plotter.reset_camera()
    plotter.view_xy()
    plotter.view_xz()
    plotter.view_yz()
    plotter.add_mesh(examples.load_uniform(), reset_camera=True, culling=True)
    plotter.view_xy(True)
    plotter.view_xz(True)
    plotter.view_yz(True)
    plotter.show()
    plotter.camera_position = None


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_multi_renderers():
    plotter = pyvista.Plotter(shape=(2, 2), off_screen=OFF_SCREEN)

    plotter.subplot(0, 0)
    plotter.add_text('Render Window 0', font_size=30)
    sphere = pyvista.Sphere()
    plotter.add_mesh(sphere, scalars=sphere.points[:, 2])
    plotter.add_scalar_bar('Z', vertical=True)

    plotter.subplot(0, 1)
    plotter.add_text('Render Window 1', font_size=30)
    plotter.add_mesh(pyvista.Cube(), show_edges=True)

    plotter.subplot(1, 0)
    plotter.add_text('Render Window 2', font_size=30)
    plotter.add_mesh(pyvista.Arrow(), color='y', show_edges=True)

    plotter.subplot(1, 1)
    plotter.add_text('Render Window 3', position=(0., 0.),
                     font_size=30, viewport=True)
    plotter.add_mesh(pyvista.Cone(), color='g', show_edges=True,
                     culling=True)
    plotter.add_bounding_box(render_lines_as_tubes=True, line_width=5)
    plotter.show_bounds(all_edges=True)

    plotter.update_bounds_axes()
    plotter.show()

    # Test subplot indices (2 rows by 1 column)
    plotter = pyvista.Plotter(shape=(2, 1), off_screen=OFF_SCREEN)
    # First row
    plotter.subplot(0,0)
    plotter.add_mesh(pyvista.Sphere())
    # Second row
    plotter.subplot(1,0)
    plotter.add_mesh(pyvista.Cube())
    plotter.show()

    # Test subplot indices (1 row by 2 columns)
    plotter = pyvista.Plotter(shape=(1, 2), off_screen=OFF_SCREEN)
    # First column
    plotter.subplot(0,0)
    plotter.add_mesh(pyvista.Sphere())
    # Second column
    plotter.subplot(0,1)
    plotter.add_mesh(pyvista.Cube())
    plotter.show()

    with pytest.raises(IndexError):
        # Test bad indices
        plotter = pyvista.Plotter(shape=(1, 2), off_screen=OFF_SCREEN)
        plotter.subplot(0,0)
        plotter.add_mesh(pyvista.Sphere())
        plotter.subplot(1,0)
        plotter.add_mesh(pyvista.Cube())
        plotter.show()

    # Test subplot 3 on left, 1 on right
    plotter = pyvista.Plotter(shape='3|1', off_screen=OFF_SCREEN)
    # First column
    plotter.subplot(0)
    plotter.add_mesh(pyvista.Sphere())
    plotter.subplot(1)
    plotter.add_mesh(pyvista.Cube())
    plotter.subplot(2)
    plotter.add_mesh(pyvista.Cylinder())
    plotter.subplot(3)
    plotter.add_mesh(pyvista.Cone())
    plotter.show()

    # Test subplot 3 on bottom, 1 on top
    plotter = pyvista.Plotter(shape='1|3', off_screen=OFF_SCREEN)
    # First column
    plotter.subplot(0)
    plotter.add_mesh(pyvista.Sphere())
    plotter.subplot(1)
    plotter.add_mesh(pyvista.Cube())
    plotter.subplot(2)
    plotter.add_mesh(pyvista.Cylinder())
    plotter.subplot(3)
    plotter.add_mesh(pyvista.Cone())
    plotter.show()


def test_subplot_groups():
    plotter = pyvista.Plotter(shape=(3,3), groups=[(1,[1,2]),(np.s_[:],0)])
    plotter.subplot(0,0)
    plotter.add_mesh(pyvista.Sphere())
    plotter.subplot(0,1)
    plotter.add_mesh(pyvista.Cube())
    plotter.subplot(0,2)
    plotter.add_mesh(pyvista.Arrow())
    plotter.subplot(1,1)
    plotter.add_mesh(pyvista.Cylinder())
    plotter.subplot(2,1)
    plotter.add_mesh(pyvista.Cone())
    plotter.subplot(2,2)
    plotter.add_mesh(pyvista.Box())
    # Test group overlap
    with pytest.raises(AssertionError):
        # Partial overlap
        pyvista.Plotter(shape=(3,3),groups=[([1,2],[0,1]),([0,1],[1,2])])
    with pytest.raises(AssertionError):
        # Full overlap (inner)
        pyvista.Plotter(shape=(4,4),groups=[(np.s_[:],np.s_[:]),([1,2],[1,2])])
    with pytest.raises(AssertionError):
        # Full overlap (outer)
        pyvista.Plotter(shape=(4,4),groups=[(1,[1,2]),([0,3],np.s_[:])])


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_link_views():
    plotter = pyvista.Plotter(shape=(1, 4), off_screen=OFF_SCREEN)
    sphere = pyvista.Sphere()
    plotter.subplot(0, 0)
    plotter.add_mesh(sphere, smooth_shading=False, show_edges=False)
    plotter.subplot(0, 1)
    plotter.add_mesh(sphere, smooth_shading=True, show_edges=False)
    plotter.subplot(0, 2)
    plotter.add_mesh(sphere, smooth_shading=False, show_edges=True)
    plotter.subplot(0, 3)
    plotter.add_mesh(sphere, smooth_shading=True, show_edges=True)
    with pytest.raises(TypeError):
        plotter.link_views(views='foo')
    plotter.link_views([0, 1])
    plotter.link_views()
    with pytest.raises(TypeError):
        plotter.unlink_views(views='foo')
    plotter.unlink_views([0, 1])
    plotter.unlink_views(2)
    plotter.unlink_views()
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_orthographic_slicer():
    data = examples.load_uniform()
    data.set_active_scalars('Spatial Cell Data')

    slices = data.slice_orthogonal()

    # Orthographic Slicer
    p = pyvista.Plotter(shape=(2,2), off_screen=OFF_SCREEN)

    p.subplot(1,1)
    p.add_mesh(slices, clim=data.get_data_range())
    p.add_axes()
    p.enable()

    p.subplot(0,0)
    p.add_mesh(slices['XY'])
    p.view_xy()
    p.disable()

    p.subplot(0,1)
    p.add_mesh(slices['XZ'])
    p.view_xz(negative=True)
    p.disable()

    p.subplot(1,0)
    p.add_mesh(slices['YZ'])
    p.view_yz()
    p.disable()

    p.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_remove_actor():
    data = examples.load_uniform()
    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_mesh(data, name='data')
    plotter.add_mesh(data, name='data')
    plotter.add_mesh(data, name='data')
    plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_image_properties():
    mesh = examples.load_uniform()
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh)
    p.show(auto_close=False) # DO NOT close plotter
    # Get RGB image
    _ = p.image
    # Get the depth image
    _ = p.get_image_depth()
    p.close()
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh)
    p.store_image = True
    assert p.store_image is True
    p.show() # close plotter
    # Get RGB image
    _ = p.image
    # Get the depth image
    _ = p.get_image_depth()
    p.close()

    # gh-920
    rr = np.array(
        [[-0.5, -0.5, 0], [-0.5, 0.5, 1], [0.5, 0.5, 0], [0.5, -0.5, 1]])
    tris = np.array([[3, 0, 2, 1], [3, 2, 0, 3]])
    mesh = pyvista.PolyData(rr, tris)
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh, color=True)
    p.renderer.camera_position = (0., 0., 1.)
    p.renderer.ResetCamera()
    p.enable_parallel_projection()
    assert p.renderer.camera_set
    p.show(interactive=False, auto_close=False)
    img = p.get_image_depth(fill_value=0.)
    rng = np.ptp(img)
    assert 0.3 < rng < 0.4, rng  # 0.3313504 in testing
    p.close()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_volume_rendering():
    # Really just making sure no errors are thrown
    vol = examples.load_uniform()
    vol.plot(off_screen=OFF_SCREEN, volume=True, opacity='linear')

    plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
    plotter.add_volume(vol, opacity='sigmoid', cmap='jet', n_colors=15)
    plotter.show()

    # Now test MultiBlock rendering
    data = pyvista.MultiBlock(dict(a=examples.load_uniform(),
                                   b=examples.load_uniform(),
                                   c=examples.load_uniform(),
                                   d=examples.load_uniform(),))
    data['a'].rename_array('Spatial Point Data', 'a')
    data['b'].rename_array('Spatial Point Data', 'b')
    data['c'].rename_array('Spatial Point Data', 'c')
    data['d'].rename_array('Spatial Point Data', 'd')
    data.plot(off_screen=OFF_SCREEN, volume=True, multi_colors=True, )

    # Check that NumPy arrays work
    arr = vol["Spatial Point Data"].reshape(vol.dimensions)
    pyvista.plot(arr, off_screen=OFF_SCREEN, volume=True, opacity='linear')


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_compar_four():
    # Really just making sure no errors are thrown
    mesh = examples.load_uniform()
    data_a = mesh.contour()
    data_b = mesh.threshold_percent(0.5)
    data_c = mesh.decimate_boundary(0.5)
    data_d = mesh.glyph()
    pyvista.plot_compare_four(data_a, data_b, data_c, data_d,
                              disply_kwargs={'color':'w'},
                              plotter_kwargs={'off_screen':OFF_SCREEN},)
    return


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_depth_peeling():
    mesh = examples.load_airplane()
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh)
    p.enable_depth_peeling()
    p.disable_depth_peeling()
    p.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
@pytest.mark.skipif(os.name == 'nt', reason="No testing on windows for EDL")
def test_plot_eye_dome_lighting():
    mesh = examples.load_airplane()
    mesh.plot(off_screen=OFF_SCREEN, eye_dome_lighting=True)
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh)
    p.enable_eye_dome_lighting()
    p.show()

    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh)
    p.enable_eye_dome_lighting()
    p.disable_eye_dome_lighting()
    p.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_opacity_by_array():
    mesh = examples.load_uniform()
    opac = mesh['Spatial Point Data'] / mesh['Spatial Point Data'].max()
    # Test with opacity array
    mesh['opac'] = opac
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh, scalars='Spatial Point Data', opacity='opac',)
    p.show()
    # Test with uncertainty array (transparency)
    mesh['unc'] = opac
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh, scalars='Spatial Point Data', opacity='unc',
               use_transparency=True)
    p.show()
    # Test using mismatched arrays
    with pytest.raises(ValueError):
        p = pyvista.Plotter(off_screen=OFF_SCREEN)
        p.add_mesh(mesh, scalars='Spatial Cell Data', opacity='unc',)
        p.show()
    # Test with user defined transfer function
    opacities = [0,0.2,0.9,0.2,0.1]
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh, scalars='Spatial Point Data', opacity=opacities,)
    p.show()


def test_opacity_transfer_functions():
    n = 256
    mapping = pyvista.opacity_transfer_function('linear', n)
    assert len(mapping) == n
    mapping = pyvista.opacity_transfer_function('sigmoid_10', n)
    assert len(mapping) == n
    with pytest.raises(KeyError):
        mapping = pyvista.opacity_transfer_function('foo', n)
    with pytest.raises(RuntimeError):
        mapping = pyvista.opacity_transfer_function(np.linspace(0, 1, 2*n), n)
    foo = np.linspace(0, n, n)
    mapping = pyvista.opacity_transfer_function(foo, n)
    assert np.allclose(foo, mapping)
    foo = [0,0.2,0.9,0.2,0.1]
    mapping = pyvista.opacity_transfer_function(foo, n, interpolate=False)
    assert len(mapping) == n
    foo = [3, 5, 6, 10]
    mapping = pyvista.opacity_transfer_function(foo, n)
    assert len(mapping) == n


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_closing_and_mem_cleanup():
    n = 5
    for _ in range(n):
        for _ in range(n):
            p = pyvista.Plotter(off_screen=OFF_SCREEN)
            for k in range(n):
                p.add_mesh(pyvista.Sphere(radius=k))
            p.show()
        pyvista.close_all()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_above_below_scalar_range_annotations():
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(examples.load_uniform(), clim=[100, 500], cmap='viridis',
               below_color='blue', above_color='red')
    p.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_user_annotations_scalar_bar():
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(examples.load_uniform(), annotations={100.:'yum'})
    p.show()
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_volume(examples.load_uniform(), annotations={100.:'yum'})
    p.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_plot_string_array():
    mesh = examples.load_uniform()
    labels = np.empty(mesh.n_cells, dtype='<U10')
    labels[:] = 'High'
    labels[mesh['Spatial Cell Data'] < 300] = 'Medium'
    labels[mesh['Spatial Cell Data'] < 100] = 'Low'
    mesh['labels'] = labels
    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    p.add_mesh(mesh, scalars='labels')
    p.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_fail_plot_table():
    """Make sure tables cannot be plotted"""
    table = pyvista.Table(np.random.rand(50, 3))
    with pytest.raises(TypeError):
        pyvista.plot(table)
    with pytest.raises(TypeError):
        plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
        plotter.add_mesh(table)


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_bad_keyword_arguments():
    """Make sure bad keyword arguments raise an error"""
    mesh = examples.load_uniform()
    with pytest.raises(TypeError):
        pyvista.plot(mesh, foo=5, off_screen=OFF_SCREEN)
    with pytest.raises(TypeError):
        pyvista.plot(mesh, scalar=mesh.active_scalars_name, off_screen=OFF_SCREEN)
    with pytest.raises(TypeError):
        plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
        plotter.add_mesh(mesh, scalar=mesh.active_scalars_name)
        plotter.show()
    with pytest.raises(TypeError):
        plotter = pyvista.Plotter(off_screen=OFF_SCREEN)
        plotter.add_mesh(mesh, foo="bad")
        plotter.show()


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_cmap_list():
    mesh = sphere.copy()

    n = mesh.n_points
    scalars = np.empty(n)
    scalars[:n//3] = 0
    scalars[n//3:2*n//3] = 1
    scalars[2*n//3:] = 2

    with pytest.raises(TypeError):
        mesh.plot(off_screen=OFF_SCREEN,
                  scalars=scalars, cmap=['red', None, 'blue'])

    mesh.plot(off_screen=OFF_SCREEN,
              scalars=scalars, cmap=['red', 'green', 'blue'])


@pytest.mark.skipif(NO_PLOTTING, reason="Requires system to support plotting")
def test_default_name_tracking():
    N = 10
    color = "tan"

    p = pyvista.Plotter(off_screen=OFF_SCREEN)
    for i in range(N):
        for j in range(N):
            center = (i, j, 0)
            mesh = pyvista.Sphere(center=center)
            p.add_mesh(mesh, color=color)
    n_made_it = len(p.renderer._actors)
    p.show()
    assert n_made_it == N**2

    # release attached scalars
    mesh.ReleaseData()
    del mesh

@pytest.mark.parametrize("as_global", [True, False])
def test_add_background_image(as_global):
    plotter = pyvista.Plotter()
    plotter.add_mesh(sphere)
    plotter.add_background_image(examples.mapfile, as_global=as_global)
    plotter.show()


def test_add_background_image_subplots():
    pl = pyvista.Plotter(shape=(2, 2))
    pl.add_background_image(examples.mapfile, scale=1, as_global=False)
    pl.add_mesh(examples.load_airplane())
    pl.subplot(1, 1)
    pl.add_background_image(examples.mapfile, scale=1, as_global=False)
    pl.add_mesh(examples.load_airplane())
    pl.remove_background_image()

    # should error out as there's no background
    with pytest.raises(RuntimeError):
        pl.remove_background_image()

    pl.add_background_image(examples.mapfile, scale=1, as_global=False)
    pl.show()


def test_add_remove_floor():
    pl = pyvista.Plotter()
    pl.add_mesh(sphere)
    pl.add_floor(color='b', line_width=2, lighting=True)
    pl.add_bounding_box()  # needed for update_bounds_axes
    assert len(pl.renderer._floors) == 1
    pl.add_mesh(sphere_b)
    pl.update_bounds_axes()
    assert len(pl.renderer._floors) == 1
    pl.show()

    pl = pyvista.Plotter()
    pl.add_mesh(sphere)
    pl.add_floor(color='b', line_width=2, lighting=True)
    pl.remove_floors()
    assert not pl.renderer._floors
    pl.show()


def test_reset_camera_clipping_range():
    pl = pyvista.Plotter()
    pl.add_mesh(sphere)

    default_clipping_range = pl.camera.GetClippingRange() # get default clipping range
    assert default_clipping_range != (10,100) # make sure we assign something different than default

    pl.camera.SetClippingRange(10,100) # set clipping range to some random numbers
    assert pl.camera.GetClippingRange() == (10,100) # make sure assignment is successful

    pl.reset_camera_clipping_range()
    assert pl.camera.GetClippingRange() ==  default_clipping_range
    assert pl.camera.GetClippingRange() != (10,100)


def test_index_vs_loc():
    # first: 2d grid
    pl = pyvista.Plotter(shape=(2, 3))
    # index_to_loc valid cases
    vals = [0, 2, 4]
    expecteds = [(0, 0), (0, 2), (1, 1)]
    for val,expected in zip(vals, expecteds):
        assert tuple(pl.index_to_loc(val)) == expected
    # loc_to_index valid cases
    vals = [(0, 0), (0, 2), (1, 1)]
    expecteds = [0, 2, 4]
    for val,expected in zip(vals, expecteds):
        assert pl.loc_to_index(val) == expected
        assert pl.loc_to_index(expected) == expected
    # failing cases
    with pytest.raises(TypeError):
        pl.loc_to_index({1, 2})
    with pytest.raises(TypeError):
        pl.index_to_loc(1.5)
    with pytest.raises(TypeError):
        pl.index_to_loc((1, 2))

    # then: "1d" grid
    pl = pyvista.Plotter(shape='2|3')
    # valid cases
    for val in range(5):
        assert pl.index_to_loc(val) == val
        assert pl.index_to_loc(np.int_(val)) == val
        assert pl.loc_to_index(val) == val
        assert pl.loc_to_index(np.int_(val)) == val
