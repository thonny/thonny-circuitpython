from thonnycontrib.micropython import MicroPythonProxy, MicroPythonConfigPage
from thonny.globals import get_workbench

class CircuitPythonProxy(MicroPythonProxy):
    @property
    def firmware_filetypes(self):
        return [('*.bin files', '.bin'), ('*.uf2 files', '.uf2'), ('all files', '.*')]

class CircuitPythonConfigPage(MicroPythonConfigPage):
    pass

def load_early_plugin():
    get_workbench().set_default("CircuitPython.port", "auto")
    get_workbench().add_backend("CircuitPython", CircuitPythonProxy, 
                                "CircuitPython", CircuitPythonConfigPage)
