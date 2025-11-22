#!/usr/bin/env python3
"""
MP4 to HLS Video Converter - GUI
Simple graphical interface for configuring and running the converter.
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import subprocess
import threading
import sys


class ConverterGUI:
    """GUI application for MP4 to HLS converter configuration and execution."""
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("MP4 to HLS Video Converter")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        self.config_file = Path("config.json")
        self.conversion_process = None
        
        self._create_widgets()
        self._load_config()
    
    def _create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="MP4 to HLS Video Converter", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input Directory
        ttk.Label(main_frame, text="Input Directory:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.input_dir_var = tk.StringVar()
        input_entry = ttk.Entry(
            main_frame, 
            textvariable=self.input_dir_var, 
            width=50
        )
        input_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(
            main_frame, 
            text="Browse...", 
            command=self._browse_input_dir
        ).grid(row=1, column=2, pady=5)
        
        # Output Directory
        ttk.Label(main_frame, text="Output Directory:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(
            main_frame, 
            textvariable=self.output_dir_var, 
            width=50
        )
        output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(
            main_frame, 
            text="Browse...", 
            command=self._browse_output_dir
        ).grid(row=2, column=2, pady=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(
            row=3, column=0, columnspan=3, 
            sticky=(tk.W, tk.E), pady=10
        )
        
        # Compress checkbox
        self.compress_var = tk.BooleanVar()
        compress_check = ttk.Checkbutton(
            options_frame,
            text="Compress output to ZIP files",
            variable=self.compress_var,
            command=self._save_config
        )
        compress_check.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Delete MP4 checkbox
        self.delete_mp4_var = tk.BooleanVar()
        delete_check = ttk.Checkbutton(
            options_frame,
            text="Delete original MP4 files after successful conversion",
            variable=self.delete_mp4_var,
            command=self._save_config
        )
        delete_check.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Warning label for delete option
        warning_label = ttk.Label(
            options_frame,
            text="⚠️  Warning: Deleted files cannot be recovered!",
            foreground="red",
            font=("Arial", 9)
        )
        warning_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 5), padx=20)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(
            buttons_frame,
            text="Start Conversion",
            command=self._start_conversion,
            width=20
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(
            buttons_frame,
            text="Stop",
            command=self._stop_conversion,
            width=20,
            state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="Save Settings",
            command=self._save_config,
            width=20
        ).grid(row=0, column=2, padx=5)
        
        # Log output frame
        log_frame = ttk.LabelFrame(main_frame, text="Conversion Log", padding="5")
        log_frame.grid(
            row=5, column=0, columnspan=3, 
            sticky=(tk.W, tk.E, tk.N, tk.S), pady=10
        )
        main_frame.rowconfigure(5, weight=1)
        
        # Scrolled text widget for log output
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=80,
            height=15,
            font=("Courier", 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def _browse_input_dir(self):
        """Open directory browser for input directory."""
        directory = filedialog.askdirectory(
            title="Select Input Directory",
            initialdir=self.input_dir_var.get() or "."
        )
        if directory:
            self.input_dir_var.set(directory)
            self._save_config()
    
    def _browse_output_dir(self):
        """Open directory browser for output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir_var.get() or "."
        )
        if directory:
            self.output_dir_var.set(directory)
            self._save_config()
    
    def _load_config(self):
        """Load configuration from config.json file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                self.input_dir_var.set(config.get("input_directory_path", ""))
                self.output_dir_var.set(config.get("output_directory_path", ""))
                self.compress_var.set(config.get("compress", False))
                self.delete_mp4_var.set(config.get("delete_mp4", False))
                
                self._log("Configuration loaded successfully")
                self.status_var.set("Configuration loaded")
            else:
                self._log("No configuration file found, using defaults")
                self.status_var.set("No configuration file found")
        except Exception as e:
            self._log(f"Error loading configuration: {e}")
            messagebox.showerror("Error", f"Failed to load configuration:\n{e}")
    
    def _save_config(self):
        """Save current settings to config.json file."""
        try:
            config = {
                "compress": self.compress_var.get(),
                "delete_mp4": self.delete_mp4_var.get(),
                "output_directory_path": self.output_dir_var.get(),
                "input_directory_path": self.input_dir_var.get()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self._log("Configuration saved successfully")
            self.status_var.set("Settings saved")
        except Exception as e:
            self._log(f"Error saving configuration: {e}")
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def _validate_settings(self):
        """Validate settings before starting conversion."""
        input_dir = self.input_dir_var.get()
        output_dir = self.output_dir_var.get()
        
        if not input_dir:
            messagebox.showerror("Error", "Please select an input directory")
            return False
        
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory")
            return False
        
        if not Path(input_dir).exists():
            messagebox.showerror("Error", f"Input directory does not exist:\n{input_dir}")
            return False
        
        if not Path(input_dir).is_dir():
            messagebox.showerror("Error", f"Input path is not a directory:\n{input_dir}")
            return False
        
        # Warn if delete option is enabled
        if self.delete_mp4_var.get():
            result = messagebox.askyesno(
                "Confirm Deletion",
                "You have enabled deletion of original MP4 files.\n\n"
                "This action cannot be undone!\n\n"
                "Are you sure you want to continue?",
                icon=messagebox.WARNING
            )
            if not result:
                return False
        
        return True
    
    def _log(self, message):
        """Add message to log output."""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def _start_conversion(self):
        """Start the conversion process."""
        # Save settings first
        self._save_config()
        
        # Validate settings
        if not self._validate_settings():
            return
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        self._log("Starting conversion process...")
        self._log("=" * 60)
        
        # Disable start button, enable stop button
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Converting...")
        
        # Run conversion in separate thread
        thread = threading.Thread(target=self._run_conversion, daemon=True)
        thread.start()
    
    def _run_conversion(self):
        """Run the main.py conversion script in a subprocess."""
        try:
            # Run main.py as subprocess
            self.conversion_process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output line by line
            for line in self.conversion_process.stdout:
                self.root.after(0, self._log, line.rstrip())
            
            # Wait for process to complete
            return_code = self.conversion_process.wait()
            
            if return_code == 0:
                self.root.after(0, self._log, "=" * 60)
                self.root.after(0, self._log, "Conversion completed successfully!")
                self.root.after(0, self.status_var.set, "Conversion completed")
                self.root.after(
                    0, 
                    messagebox.showinfo, 
                    "Success", 
                    "Conversion completed successfully!"
                )
            elif return_code == 130:
                self.root.after(0, self._log, "Conversion stopped by user")
                self.root.after(0, self.status_var.set, "Stopped")
            else:
                self.root.after(0, self._log, f"Conversion failed with exit code {return_code}")
                self.root.after(0, self.status_var.set, "Conversion failed")
                self.root.after(
                    0,
                    messagebox.showerror,
                    "Error",
                    f"Conversion failed with exit code {return_code}"
                )
        
        except Exception as e:
            self.root.after(0, self._log, f"Error running conversion: {e}")
            self.root.after(0, self.status_var.set, "Error")
            self.root.after(
                0,
                messagebox.showerror,
                "Error",
                f"Failed to run conversion:\n{e}"
            )
        
        finally:
            # Re-enable start button, disable stop button
            self.root.after(0, self.start_button.config, {"state": tk.NORMAL})
            self.root.after(0, self.stop_button.config, {"state": tk.DISABLED})
            self.conversion_process = None
    
    def _stop_conversion(self):
        """Stop the running conversion process."""
        if self.conversion_process:
            try:
                self.conversion_process.terminate()
                self._log("Stopping conversion...")
                self.status_var.set("Stopping...")
            except Exception as e:
                self._log(f"Error stopping conversion: {e}")
                messagebox.showerror("Error", f"Failed to stop conversion:\n{e}")


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = ConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
