import os.path
import tkinter as tk
from tkinter import ttk

from thonnycontrib.micropython import MicroPythonProxy, MicroPythonConfigPage,\
    add_micropython_backend
from thonny import get_workbench
from thonny.ui_utils import center_window
from tkinter.filedialog import askopenfile, askopenfilename
from urllib.request import urlretrieve, urlopen
import threading
import json
import subprocess
import time
from tkinter.messagebox import showerror, showinfo, askyesno
from thonny.misc_utils import list_volumes

_asset_names_by_models = {
    "CPlay Express" : "circuitplayground_express",
    "Feather M0" : "feather_m0_express",
    "Gemma M0" : "gemma_m0",
    "Itsy Bitsy M0" : "itsybitsy_m0",
    "Metro M0" : "metro_m0_express",
    "Trinket M0" : "trinket_m0",
}

class CircuitPythonProxy(MicroPythonProxy):
    def __init__(self, clean):
        MicroPythonProxy.__init__(self, clean)
        
    def _supports_directories(self):
        return True
    
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

class CircuitPythonConfigPage(MicroPythonConfigPage):
    pass

class FlashingDialog(tk.Toplevel):
    def __init__(self):
        master = get_workbench()
        tk.Toplevel.__init__(self, master)
        
        self._latest_release_data = None
        self._device_info = None
        self._firmware_path = None
        self._latest_firmware_assets = None
        self._download_progess = None
        self._copy_progess = None
        self._start_fetching_latest_release_data()
        
        
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        main_frame = tk.Frame(self)
        main_frame.grid(row=0, column=0, sticky=tk.NSEW, ipadx=15, ipady=15)
        
        self.title("Install CircuitPython firmware to your device")
        #self.resizable(height=tk.FALSE, width=tk.FALSE)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)
        
        
        ttk.Label(main_frame, text="Device:").grid(row=1, column=0, sticky="nw", pady=(15,10), padx=15)
        self.device_label = ttk.Label(main_frame, text="<not found>")
        self.device_label.grid(row=1, column=1, columnspan=2, sticky="nw", pady=(15,10), padx=15)
        
        ttk.Label(main_frame, text="Firmware:").grid(row=2, column=0, sticky="nw", pady=0, padx=15)
        self._firmware_label = ttk.Label(main_frame, text="", wraplength="10cm")
        self._firmware_label.grid(row=2, column=1, columnspan=2, sticky="nw", pady=0, padx=15)
        
        file_button = ttk.Button(main_frame, text="Select file ...", width=15, command=self._select_file)
        file_button.grid(row=3, column=1, sticky="ne", pady=10, padx=15)
        
        self._download_button = ttk.Button(main_frame, text="Download latest", width=25, command=self._start_download_latest)
        self._download_button.grid(row=3, column=2, sticky="new", pady=10, padx=(0,15))
        
        main_frame.rowconfigure(3, weight=1)
        main_frame.columnconfigure(2, weight=1)
        
        command_bar = tk.Frame(main_frame)
        command_bar.grid(row=4, column=0, columnspan=3, sticky="nsew")
        command_bar.columnconfigure(0, weight=1)
        
        self._install_button = ttk.Button(command_bar, text="Install", command=self._start_install, width=20)
        self._install_button.grid(row=0, column=1, pady=15, padx=15, sticky="ne")
        self._install_button.focus_set()
        
        close_button = ttk.Button(command_bar, text="Close", command=self._close)
        close_button.grid(row=0, column=2, pady=15, padx=(0,15), sticky="ne")
        
        self.bind('<Escape>', self._close, True)
        
        center_window(self, master)
        
        self._update_state()
                
        self.wait_window()
    
    def _select_file(self):
        result = askopenfilename (
            filetypes = [('UF2 files', '.uf2')], 
            initialdir = get_workbench().get_option("run.working_directory")
        )
        
        if result:
            self._firmware_path = os.path.normpath(result)
            self._download_progess = None
            self._update_firmware_label()
    
    def _update_state(self):
        self._update_device_info()
        
        if self._latest_release_data:
            self._download_button.configure(text="Download latest (%s)" % self._latest_release_data["tag_name"])
        else:
            self._download_button.configure(text="Download latest")
        
        self._latest_firmware_assets = None
        if (self._device_info and self._latest_release_data 
            and self._device_info["model"] in _asset_names_by_models):
            asset_name_sub = _asset_names_by_models[self._device_info["model"]]
            self._latest_firmware_assets = []
            for asset in self._latest_release_data["assets"]:
                if asset_name_sub in asset["name"]:
                    self._latest_firmware_assets.append(asset)
        
        if self._latest_firmware_assets is not None and self._download_progess is None:
            self._download_button.state(["!disabled"])
        else:
            self._download_button.state(["disabled"])
        
        self._update_firmware_label()
        
        if isinstance(self._copy_progess, int):
            self._install_button.configure(text="Installing (%d %%)" % self._copy_progess)
        elif self._copy_progess == "done":
            self._install_button.configure(text="Installing (100%)")
            showinfo("Done", "Firmware installation is complete.\nDevice will be back in normal mode.")
            self._copy_progess = None
        else:
            self._install_button.configure(text="Install")
            
        if self._firmware_path and self._copy_progess is None:
            self._install_button.state(["!disabled"])
        else:
            self._install_button.state(["disabled"])
        
        self.after(300, self._update_state)
    
    def _update_device_info(self):
        info_file_name = "INFO_UF2.TXT"
        suitable_volumes = {vol for vol in list_volumes() 
                            if os.path.exists(os.path.join(vol, info_file_name))}
        
        if len(suitable_volumes) == 0:
            self._device_info = None
            device_text = (
                  "Device not connected or not in bootloader mode.\n"
                + "\n"
                + "After connecting the device to a USB port, double-press its reset button\n"
                + "and wait for a second.\n"
                + "\n"
                + "If nothing happens, then try again with longer or shorter pauses between\n"
                + "the presses (or just a single press) until this message disappears."
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
            with open(os.path.join(vol,  info_file_name), encoding="utf-8") as fp:
                for line in fp:
                    if line.startswith("Model:"):
                        model = line[len("Model:"):].strip()
                        self._device_info = {"volume" : vol, "model" : model}
                        device_text = "%s    (%s)" % (vol, model)
                        break
                else:
                    self._device_info = None
                    device_text = "Could not determine device model"
        
        self.device_label.configure(text=device_text)
        
    def _update_firmware_label(self):
        if self._firmware_path:
            p = self._firmware_path
            assert os.path.isabs(p)
            last_sep = p.rfind(os.path.sep)
            self._firmware_label.configure(text=p[:last_sep+1] + "\n" + p[last_sep+1:])
        elif self._download_progess is not None:
            self._firmware_label.configure(text="Downloading (%d %%)" % self._download_progess)
        else:
            self._firmware_label.configure(text="")
    
    def _start_download_latest(self):
        if len(self._latest_firmware_assets) == 0:
            showerror("Can't download", "Didn't find suitable download for this model")
            return
        
        elif len(self._latest_firmware_assets) > 1:
            showerror("Can't download",
                      "Found several suitable downloads for this model:\n  "
                      + "\  ".join([asset["name"] for asset in self._latest_firmware_assets]))
            return
        
        name = self._latest_firmware_assets[0]["name"]
        url = self._latest_firmware_assets[0]["browser_download_url"]
        
        def on_progress(blocknum, bs, size):
            if self._firmware_path:
                self._download_progess = None
            elif size > 0:
                self._download_progess = int((blocknum * bs) / size * 100)
            else:
                self._download_progess = 1 
        
        def work():
            self._download_progess = 0
            self._firmware_path = None
            
            download_path = os.path.expanduser("~/Downloads/" + name)
            urlretrieve(url, download_path, on_progress)
            self._firmware_path = os.path.normpath(download_path)
            self._download_progess = None
        
        threading.Thread(target=work).start()
    
    
    
    def _start_install(self):
        assert self._firmware_path
        assert self._device_info
        
        asset_name_sub = _asset_names_by_models[self._device_info["model"]] 
        if asset_name_sub.lower() not in self._firmware_path.lower():
            if not askyesno("Confusion",
                            "For this device it is expected that firmware file name contains\n\n"
                              + "    %s\n\n" % asset_name_sub
                              + "Are you sure you want to continue?"):
                return
            
        
        
        dest_path = os.path.join(self._device_info["volume"], 
                                   os.path.basename(self._firmware_path))
        size = os.path.getsize(self._firmware_path)
        
        def work():
            self._copy_progess = 0
            
            with open(self._firmware_path, "rb") as fsrc:
                with open(dest_path, 'wb') as fdst:
                    copied = 0
                    while True:
                        buf = fsrc.read(8*1024)
                        if not buf:
                            break
                        
                        fdst.write(buf)
                        copied += len(buf)
                        
                        self._copy_progess = int(copied / size * 100)                    
            
            
            self._copy_progess = "done"
        
        threading.Thread(target=work).start()
    
    
    def _close(self, event=None):
        self.destroy()
    
    
    def _start_fetching_latest_release_data(self):
        def work():
            with urlopen("https://api.github.com/repos/adafruit/circuitpython/releases/latest") as fp:
                self._latest_release_data = json.loads(fp.read().decode("UTF-8"))
        
        threading.Thread(target=work).start()



def load_plugin():
    add_micropython_backend("CircuitPython", CircuitPythonProxy, 
                            "CircuitPython", CircuitPythonConfigPage)
    
    get_workbench().add_command("uploadcp", "tools", "Upload CircuitPython firmware ...",
                                FlashingDialog,
                                group=120)

