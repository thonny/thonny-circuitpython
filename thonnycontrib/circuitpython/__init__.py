import os.path
import tkinter as tk
from tkinter import ttk

from thonny.plugins.micropython import MicroPythonProxy, MicroPythonConfigPage,\
    add_micropython_backend
from thonny import get_workbench
from thonny.ui_utils import create_url_label, show_dialog, askopenfilename
import threading
from tkinter.messagebox import showinfo
from thonny.misc_utils import list_volumes

class CircuitPythonProxy(MicroPythonProxy):
    def __init__(self, clean):
        MicroPythonProxy.__init__(self, clean)
        
    def _clean_environment_during_startup(self, timeout):
        # In CP Ctrl+C already cleaned the environment
        pass
    
    def _get_boot_script_path(self):
        files = self._list_files()
        if "settings.txt" in files:
            return "/settings.txt"
        elif "settings.py" in files:
            return "/settings.py"
        elif "boot.txt" in files:
            return "/boot.txt"
        elif "boot.py" in files:
            return "/boot.py"
        else:
            return "/boot.py"
    
    def _get_main_script_path(self):
        # https://learn.adafruit.com/welcome-to-circuitpython/creating-and-editing-code#naming-your-program-file
        files = self._list_files()
        if "code.txt" in files:
            return "/code.txt"
        elif "code.py" in files:
            return "/code.py"
        elif "main.txt" in files:
            return "/main.txt"
        elif "main.py" in files:
            return "/main.py"
        else:
            return "/code.py"
    
    def _get_fs_mount_name(self):
        # TODO: in 3.0 file system label (CIRCUITPY by default) can be changed using storage.getmount("/").label.
        return "CIRCUITPY"
    
    @property
    def known_usb_vids_pids(self):
        """Copied from https://github.com/mu-editor/mu/blob/master/mu/modes/adafruit.py"""
        return {
            (0x239A, 0x8015),  # Adafruit Feather M0 CircuitPython
            (0x239A, 0x8023),  # Adafruit Feather M0 Express CircuitPython
            (0x239A, 0x801B),  # Adafruit Feather M0 Express CircuitPython
            (0x239A, 0x8014),  # Adafruit Metro M0 CircuitPython
            (0x239A, 0x8019),  # Adafruit CircuitPlayground Express CircuitPython
            (0x239A, 0x801D),  # Adafruit Gemma M0
            (0x239A, 0x801F),  # Adafruit Trinket M0
            (0x239A, 0x8012),  # Adafruit ItsyBitsy M0
            (0x239A, 0x8021),  # Adafruit Metro M4
            (0x239A, 0x8025),  # Adafruit Feather RadioFruit
            (0x239A, 0x8026),  # Adafruit Feather M4
            (0x239A, 0x8028),  # Adafruit pIRKey M0
            (0x239A, 0x802A),  # Adafruit Feather 52840
            (0x239A, 0x802C),  # Adafruit Itsy M4
            (0x239A, 0x802E),  # Adafruit CRICKit M0
        }

    def _report_upload_via_mount_error(self, source, target, error):
        self._send_error_to_shell(("Couldn't write to %s\n"
                                   + "Original error: %s\n"
                                   + "\n"
                                   + "If the target directory does exist then device's filesystem may be corrupted.\n"
                                   + "You can repair it with following code (NB! Deletes all files on the device!):\n"
                                   + "\n"
                                   + "import storage\n"
                                   + "storage.erase_filesystem()\n")
                                   % (target, error))
    
class CircuitPythonConfigPage(MicroPythonConfigPage):
    def _get_usb_driver_url(self):
        return "https://learn.adafruit.com/welcome-to-circuitpython/installing-circuitpython"
    
class FlashingDialog(tk.Toplevel):
    def __init__(self):
        master = get_workbench()
        tk.Toplevel.__init__(self, master)
        
        self._copy_progess = None
        self._device_info = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky=tk.NSEW, ipadx=15, ipady=15)
        
        self.title("Install CircuitPython firmware to your device")
        #self.resizable(height=tk.FALSE, width=tk.FALSE)
        self.protocol("WM_DELETE_WINDOW", self._close)
        
        ttk.Label(main_frame, text="Download .uf2 file:").grid(row=1, column=0, sticky="nw", pady=(15,0), padx=15)
        url_label = create_url_label(main_frame, url="https://circuitpython.org/downloads")
        url_label.grid(row=1, column=1, columnspan=2, sticky="nw", pady=(15,0), padx=15)
        
        ttk.Label(main_frame, text="Select the file:").grid(row=2, column=0, sticky="nw", pady=(10,0), padx=15)
        self._path_var = tk.StringVar(value="")
        self._path_entry = ttk.Entry(main_frame, textvariable=self._path_var, width=60)
        self._path_entry.grid(row=2, column=1, columnspan=1, sticky="nsew", pady=(10,0), padx=(15, 10))
        file_button = ttk.Button(main_frame, text=" ... ", command=self._select_file)
        file_button.grid(row=2, column=2, sticky="nsew", pady=(10,0), padx=(0,15))
        
        ttk.Label(main_frame, text="Prepare device:").grid(row=3, column=0, sticky="nw", pady=(10,0), padx=15)
        self.device_label = ttk.Label(main_frame, text="<not found>")
        self.device_label.grid(row=3, column=1, columnspan=2, sticky="nw", pady=(10,0), padx=15)
        
        
        main_frame.rowconfigure(3, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        command_bar = ttk.Frame(main_frame)
        command_bar.grid(row=4, column=0, columnspan=3, sticky="nsew")
        command_bar.columnconfigure(0, weight=1)
        
        self._install_button = ttk.Button(command_bar, text="Install", command=self._start_install, width=20)
        self._install_button.grid(row=0, column=1, pady=15, padx=15, sticky="ne")
        self._install_button.focus_set()
        
        close_button = ttk.Button(command_bar, text="Cancel", command=self._close)
        close_button.grid(row=0, column=2, pady=15, padx=(0,15), sticky="ne")
        
        self.bind('<Escape>', self._close, True)
        
        self._update_state()
        
    def _select_file(self):
        result = askopenfilename (
            filetypes = [('UF2 files', '.uf2')], 
            initialdir = get_workbench().get_option("run.working_directory")
        )
        
        if result:
            self._path_var.set(os.path.normpath(result))
    

    def _update_state(self):
        self._update_device_info()
        
        if isinstance(self._copy_progess, int):
            self._install_button.configure(text="Installing (%d %%)" % self._copy_progess)
        elif self._copy_progess == "done":
            self._install_button.configure(text="Installing (100%)")
            self.update_idletasks()
            showinfo("Done", "Firmware installation is complete.\nDevice will be back in normal mode.")
            self._copy_progess = None
            self._close()
            return
        else:
            self._install_button.configure(text="Install")
            
        if os.path.isfile(self._get_file_path()) and self._copy_progess is None and self._device_info:
            self._install_button.state(["!disabled"])
        else:
            self._install_button.state(["disabled"])
        
        self.after(200, self._update_state)
    
    def _get_file_path(self):
        return self._path_var.get()
    
    def _update_device_info(self):
        info_file_name = "INFO_UF2.TXT"
        suitable_volumes = {vol for vol in list_volumes(skip_letters=["A"]) 
                            if os.path.exists(os.path.join(vol, info_file_name))}
        
        if len(suitable_volumes) == 0:
            self._device_info = None
            device_text = (
                  "Device not connected or not in bootloader mode.\n"
                + "\n"
                + "After connecting the device to a USB port, double-press its reset button\n"
                + "and wait for couple of seconds until OS mounts it in bootloader mode.\n"
                + "\n"
                + "If nothing happens, then try again with longer or shorter pauses between the\n"
                + "presses (or just a single press) or wait longer until this message disappears.\n"
            )
        elif len(suitable_volumes) > 1:
            self._device_info = None
            device_text = (
                  "Found more than one device:\n  "
                  + "\n  ".join(sorted(suitable_volumes))
                  + "\n\n"
                  + "Please keep only one in bootloader mode!"
            )
        else:
            vol = suitable_volumes.pop()
            model = "Unknown device"
            with open(os.path.join(vol,  info_file_name), encoding="utf-8") as fp:
                for line in fp:
                    if line.startswith("Model:"):
                        model = line[len("Model:"):].strip()
                        break
                    
            self._device_info = {"volume" : vol, "model" : model}
            device_text = "%s at %s is ready" % (model, vol)
        
        self.device_label.configure(text=device_text)
    
    
    def _start_install(self):
        assert os.path.isfile(self._get_file_path())
        assert self._device_info
        
        dest_path = os.path.join(self._device_info["volume"], 
                                   os.path.basename(self._get_file_path()))
        size = os.path.getsize(self._get_file_path())
        
        def work():
            self._copy_progess = 0
            
            with open(self._get_file_path(), "rb") as fsrc:
                with open(dest_path, 'wb') as fdst:
                    copied = 0
                    while True:
                        buf = fsrc.read(16*1024)
                        if not buf:
                            break
                        
                        fdst.write(buf)
                        fdst.flush()
                        os.fsync(fdst)
                        copied += len(buf)
                        
                        self._copy_progess = int(copied / size * 100)                    
            
            
            self._copy_progess = "done"
        
        threading.Thread(target=work).start()
    
    
    def _close(self, event=None):
        self.destroy()
    

def load_plugin():
    add_micropython_backend("CircuitPython", CircuitPythonProxy, 
                            "CircuitPython (generic)", CircuitPythonConfigPage)
    
    get_workbench().add_command("installcp", "device", "Install CircuitPython firmware ...",
                                lambda: show_dialog(FlashingDialog()),
                                group=40)

