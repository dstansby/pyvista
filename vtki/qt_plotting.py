import logging

import vtk
import vtk.qt

from vtki.plotting import BasePlotter, plotParams

# for display bugs due to older intel integrated GPUs
vtk.qt.QVTKRWIBase = 'QGLWidget'

log = logging.getLogger(__name__)
log.setLevel('DEBUG')


# dummy reference for when PyQt5 is not installed
has_pyqt = False
class QVTKRenderWindowInteractor(object):
    pass

def pyqtSignal():
    return

try:
    from PyQt5.QtCore import pyqtSignal
    from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    has_pyqt = True
except:
    pass


class QtInteractor(QVTKRenderWindowInteractor, BasePlotter):
    """
    Extends QVTKRenderWindowInteractor class by adding the methods
    available to vtki.Plotter.

    """
    render_trigger = pyqtSignal()

    def __init__(self, parent=None):
        """ Initialize Qt interactor """
        assert has_pyqt, 'Requires PyQt5'
        QVTKRenderWindowInteractor.__init__(self, parent)

        # Create and start the interactive renderer
        self.ren_win = self.GetRenderWindow()
        self.ren_win.AddRenderer(self.renderer)
        self.iren = self.ren_win.GetInteractor()
        
        self.background_color = plotParams['background']

        self.iren.RemoveObservers('MouseMoveEvent')  # slows window update?
        self.iren.Initialize()

        # Enter trackball camera mode
        istyle = vtk.vtkInteractorStyleTrackballCamera()
        self.SetInteractorStyle(istyle)
        self.add_axes()
