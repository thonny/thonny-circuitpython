import os.path

from thonnycontrib.micropython import MicroPythonProxy, MicroPythonConfigPage
from thonny.globals import get_workbench

class CircuitPythonProxy(MicroPythonProxy):
    def __init__(self, clean):
        MicroPythonProxy.__init__(self, clean)
        
    @property
    def firmware_filetypes(self):
        return [('*.bin files', '.bin'), ('*.uf2 files', '.uf2'), ('all files', '.*')]
    
    def _get_main_script_path(self):
        # https://learn.adafruit.com/welcome-to-circuitpython/creating-and-editing-code#naming-your-program-file
        files = self._list_files()
        if "code.txt" in files:
            return "code.txt"
        elif "code.py" in files:
            return "code.py"
        elif "main.txt" in files:
            return "main.txt"
        elif "main.py" in files:
            return "main.py"
        else:
            return "code.py"
    
    def _get_fs_mount_name(self):
        return "CIRCUITPY"
        
    def _get_bootloader_mount_name(self):
        boot_names = {
            "Adafruit CircuitPlayground Express with samd21g18" : "CPLAYBOOT",
            "" : "TRINKETBOOT",
        }
        return boot_names.get(self._uname["machine"], None) 
    

class CircuitPythonConfigPage(MicroPythonConfigPage):
    pass

def load_early_plugin():
    get_workbench().set_default("CircuitPython.port", "auto")
    get_workbench().add_backend("CircuitPython", CircuitPythonProxy, 
                                "CircuitPython", CircuitPythonConfigPage)
