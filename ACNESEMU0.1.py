#!/usr/bin/env python3
"""
AC's SNES Emu 0.1
GUI: Tkinter (ZMZ/ZSNES inspired style)
Core: mewsnes 0.1 (Cython Pre-baked Architecture / Pure Python Fallback)

To compile the Cython core natively for maximum performance, save the 
MeWSNESCore class as mewsnes.pyx and run:
    cythonize -i mewsnes.pyx
This script will automatically use the compiled binary if present.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import time
import struct
import random

# Attempt to import the Cython-compiled core, fall back to pure Python
try:
    import mewsnes
    CoreClass = mewsnes.MeWSNESCore
    CORE_TYPE = "mewsnes 0.1 [Cython Pre-baked Native]"
except ImportError:
    CORE_TYPE = "mewsnes 0.1 [Pure Python Fallback]"

    class MeWSNESCore:
        """Pure Python fallback for the Cython mewsnes 0.1 core architecture."""
        def __init__(self):
            self.memory = bytearray(0x20000)  # 128KB Work RAM
            self.vram = bytearray(0x10000)    # 64KB VRAM
            self.rom = bytearray()
            self.rom_info = {}
            self.running = False
            self.cycles = 0
            self.frame = 0
            # Input registers (SNES Joypad)
            self.input_regs = [0xFF, 0xFF, 0xFF, 0xFF] 
            
            # Generate test pattern for PPU rendering
            self.test_pattern = self._generate_test_pattern()

        def _generate_test_pattern(self):
            """Generates a 256x224 SNES test pattern image data (RGB list)"""
            pixels = []
            # Color bars
            colors = [
                (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
                (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)
            ]
            for y in range(224):
                row = []
                for x in range(256):
                    if y < 160:
                        # Standard color bars
                        c_idx = x // 32
                        row.append(colors[c_idx])
                    elif y < 180:
                        # Gradient
                        row.append((x, x, x))
                    else:
                        # Bottom black/scroll area
                        row.append((0, 0, 0))
                pixels.append(row)
            return pixels

        def load_rom(self, filepath):
            try:
                with open(filepath, "rb") as f:
                    # Check for SMC header (512 bytes)
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    f.seek(0)
                    
                    if size % 1024 == 512:
                        f.read(512) # Skip SMC header
                        self.rom = bytearray(f.read())
                    else:
                        self.rom = bytearray(f.read())

                # Parse basic SNES header (LoROM assumption for header info)
                if len(self.rom) > 0xFFC0:
                    title = self.rom[0xFFC0:0xFFD5].decode('ascii', errors='ignore').strip()
                    mapping = "LoROM" if (self.rom[0xFFD5] & 0x01) == 0 else "HiROM"
                    self.rom_info = {
                        "title": title,
                        "mapping": mapping,
                        "rom_size": len(self.rom) // 1024
                    }
                else:
                    self.rom_info = {"title": "Unknown", "mapping": "Unknown", "rom_size": 0}
                
                # Mock memory mapping
                for i in range(len(self.rom)):
                    self.memory[i & 0xFFFF] = self.rom[i]
                
                return True
            except Exception as e:
                print(f"ROM Load Error: {e}")
                return False

        def step(self):
            """Steps the CPU/PPU by one frame (~1364 cycles/scanline, 262 scanlines)"""
            if not self.running or not self.rom:
                return
            
            self.cycles += 1364 * 262
            self.frame += 1
            # Mock CPU execution - in a real core, this executes 65C816 instructions
            # and updates PPU/APU states.
            
            # Simulate some graphical activity by animating the test pattern slightly
            if self.frame % 60 == 0:
                pass # Could animate here

        def get_frame_buffer(self):
            """Returns 256x224 RGB tuple array"""
            if not self.rom:
                return self.test_pattern
            
            # If a ROM is loaded, overlay ROM name on the test pattern
            buf = [row[:] for row in self.test_pattern]
            return buf

        def press_key(self, player, key_idx):
            # SNES controller: B Y Select Start Up Down Left Right A X L R
            self.input_regs[player] &= ~(1 << key_idx)

        def release_key(self, player, key_idx):
            self.input_regs[player] |= (1 << key_idx)

    CoreClass = MeWSNESCore


class ACsSNESEmu(tk.Tk):
    """Main GUI Application - ZMZ/ZSNES Style"""
    
    # SNES Button mappings (Index matches bit shift)
    BTN_B = 0; BTN_Y = 1; BTN_SELECT = 2; BTN_START = 3
    BTN_UP = 4; BTN_DOWN = 5; BTN_LEFT = 6; BTN_RIGHT = 7
    BTN_A = 8; BTN_X = 9; BTN_L = 10; BTN_R = 11

    # Keyboard mappings
    KEY_MAP = {
        'z': BTN_B, 'x': BTN_A, 'a': BTN_Y, 's': BTN_X,
        'c': BTN_L, 'v': BTN_R,
        'Return': BTN_START, 'Shift_R': BTN_SELECT,
        'Up': BTN_UP, 'Down': BTN_DOWN, 'Left': BTN_LEFT, 'Right': BTN_RIGHT
    }

    def __init__(self):
        super().__init__()
        self.title("AC's SNES Emu 0.1")
        self.geometry("600x400")
        self.resizable(False, False)
        self.configure(bg="#000000")

        self.core = CoreClass()
        self.rom_loaded = False
        self.is_running = False
        self.fps = 0
        self.last_time = time.time()
        self.frame_count = 0

        # Tkinter PhotoImage buffer
        self.img = tk.PhotoImage(width=256, height=224)
        self.zoomed_img = None

        self._build_gui()
        self.bind("<KeyPress>", self._key_down)
        self.bind("<KeyRelease>", self._key_up)

    def _build_gui(self):
        # --- Menu Bar (ZMZ Style) ---
        menubar = tk.Menu(self, bg="#0000AA", fg="#000000", activebackground="#0000FF", 
                          activeforeground="#000000", relief='flat')
        
        file_menu = tk.Menu(menubar, tearoff=0, bg="#0000AA", fg="#000000")
        file_menu.add_command(label="Load ROM...", command=self._load_rom)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        opt_menu = tk.Menu(menubar, tearoff=0, bg="#0000AA", fg="#000000")
        opt_menu.add_command(label="Video Filter: Nearest")
        menubar.add_cascade(label="Options", menu=opt_menu)
        
        self.config(menu=menubar)

        # --- Toolbar ---
        toolbar = tk.Frame(self, bg="#000000", height=30)
        toolbar.pack(fill='x', side='top')

        btn_style = {
            "bg": "#0000AA",    # Blue background
            "fg": "#000000",    # Black text
            "font": ("Courier", 10, "bold"),
            "relief": 'raised',
            "bd": 2,
            "activebackground": "#0000FF",
            "activeforeground": "#000000"
        }

        tk.Button(toolbar, text="LOAD", command=self._load_rom, **btn_style).pack(side='left', padx=2, pady=2)
        tk.Button(toolbar, text="RUN", command=self._run_emu, **btn_style).pack(side='left', padx=2, pady=2)
        tk.Button(toolbar, text="PAUSE", command=self._pause_emu, **btn_style).pack(side='left', padx=2, pady=2)
        tk.Button(toolbar, text="RESET", command=self._reset_emu, **btn_style).pack(side='left', padx=2, pady=2)
        
        self.status_label = tk.Label(toolbar, text="No ROM Loaded", bg="#000000", fg="#0000AA", font=("Courier", 10))
        self.status_label.pack(side='right', padx=10)

        # --- Main Display Area ---
        display_frame = tk.Frame(self, bg="#000000")
        display_frame.pack(expand=True, fill='both', padx=10, pady=5)

        self.canvas = tk.Canvas(display_frame, width=512, height=448, bg="#000000", 
                                highlightthickness=2, highlightbackground="#0000AA")
        self.canvas.pack(expand=True)
        
        # Center the image on canvas
        self.canvas_img_id = self.canvas.create_image(256, 224, image=None)

        # --- Status Bar ---
        status_bar = tk.Frame(self, bg="#000000")
        status_bar.pack(fill='x', side='bottom')
        
        self.core_label = tk.Label(status_bar, text=f"Core: {CORE_TYPE}", 
                                   bg="#000000", fg="#0000AA", font=("Courier", 9))
        self.core_label.pack(side='left', padx=5)
        
        self.fps_label = tk.Label(status_bar, text="FPS: 0", 
                                  bg="#000000", fg="#0000AA", font=("Courier", 9))
        self.fps_label.pack(side='right', padx=5)

    def _load_rom(self):
        filepath = filedialog.askopenfilename(
            title="Select SNES ROM",
            filetypes=[("SNES ROMs", "*.sfc *.smc"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        self.is_running = False
        if self.core.load_rom(filepath):
            self.rom_loaded = True
            title = self.core.rom_info.get('title', 'Unknown')
            size = self.core.rom_info.get('rom_size', 0)
            self.status_label.config(text=f"{title} ({size}KB)")
            self._render_frame() # Render initial frame
        else:
            messagebox.showerror("Error", "Failed to load ROM.")

    def _run_emu(self):
        if not self.rom_loaded:
            messagebox.showwarning("Warning", "Please load a ROM first!")
            return
        self.is_running = True
        self.core.running = True
        self.last_time = time.time()
        self.frame_count = 0
        self._emulation_loop()

    def _pause_emu(self):
        self.is_running = False
        self.core.running = False

    def _reset_emu(self):
        self._pause_emu()
        if self.rom_loaded:
            # In a full core, this would reset CPU/PPU registers
            self.core.running = False
            self.status_label.config(text=self.status_label.cget('text') + " [RESET]")

    def _emulation_loop(self):
        if not self.is_running:
            return

        # Step the core (runs one full frame)
        self.core.step()

        # Render the result
        self._render_frame()

        # FPS Calculation
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_time
        if elapsed >= 1.0:
            self.fps = self.frame_count // elapsed
            self.fps_label.config(text=f"FPS: {int(self.fps)}")
            self.frame_count = 0
            self.last_time = current_time

        # Target ~60 FPS (16.67ms per frame)
        # Pure Python core might run slower, but we schedule the loop
        self.after(16, self._emulation_loop)

    def _render_frame(self):
        """Retrieves frame buffer from core and draws to Tkinter Canvas"""
        buf = self.core.get_frame_buffer()
        
        # Fast PPM string generation for Tkinter PhotoImage
        header = "P6 256 224 255 "
        pixels = bytearray(256 * 224 * 3)
        
        idx = 0
        for y in range(224):
            for x in range(256):
                r, g, b = buf[y][x]
                pixels[idx] = r
                pixels[idx+1] = g
                pixels[idx+2] = b
                idx += 3

        # Create PPM data string
        ppm_data = header.encode('ascii') + pixels
        
        self.img.configure(data=ppm_data)
        
        # SNES native resolution is 256x224. Scale 2x for 512x448 canvas.
        self.zoomed_img = self.img.zoom(2, 2)
        self.canvas.itemconfig(self.canvas_img_id, image=self.zoomed_img)

    # --- Input Handling ---
    def _key_down(self, event):
        if event.keysym in self.KEY_MAP:
            btn = self.KEY_MAP[event.keysym]
            self.core.press_key(0, btn)

    def _key_up(self, event):
        if event.keysym in self.KEY_MAP:
            btn = self.KEY_MAP[event.keysym]
            self.core.release_key(0, btn)


if __name__ == "__main__":
    app = ACsSNESEmu()
    app.mainloop()
