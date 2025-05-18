import re
import threading
import time
import requests
import os
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import webbrowser
import pyperclip
from tkinter.font import Font

class OsuBeatmapDownloader:
    def __init__(self, root=None):
        self.beatmap_id_pattern = r'osu\.ppy\.sh/beatmapsets/(\d+)'
        self.direct_download_url = "https://catboy.best/d/{}"  # Using direct Catboy download URL format
        self.download_folder = self.get_download_folder()
        self.previous_clipboard = ""
        self.is_running = True
        self.status_var = None
        self.download_history = []
        self.theme = "light"  # Default theme
        self.load_history()
        self.load_settings()
        
        # If root is provided, create GUI
        if root:
            self.setup_gui(root)
        
    def get_download_folder(self):
        # Default download folder - modify as needed
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads", "osu_beatmaps")
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        return download_folder
    
    def setup_gui(self, root):
        # Center the window on startup
        self.center_window(root, 550, 450)
        
        root.title("osu! Beatmap Downloader")
        root.resizable(True, True)
        
        # Create theme colors
        self.theme_colors = {
            "light": {
                "bg": "#f0f0f0",
                "fg": "#000000",
                "highlight": "#e1e1e1",
                "accent": "#0078d7"
            },
            "dark": {
                "bg": "#2d2d2d",
                "fg": "#ffffff",
                "highlight": "#3d3d3d",
                "accent": "#0098ff"
            }
        }
        
        # Create custom styles for ttk widgets
        self.style = ttk.Style()
        
        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main tab
        main_frame = ttk.Frame(notebook, padding="10")
        notebook.add(main_frame, text="Main")
        
        # Create widgets for main tab
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(header_frame, text="osu! Beatmap Downloader", font=("Arial", 16)).pack(side=tk.LEFT, pady=10)
        
        # Theme toggle button
        self.theme_var = tk.StringVar(value=self.theme)
        theme_frame = ttk.Frame(header_frame)
        theme_frame.pack(side=tk.RIGHT)
        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT)
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=["light", "dark"], width=6, state="readonly")
        theme_combo.pack(side=tk.LEFT, padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Waiting for beatmap links...")
        ttk.Label(main_frame, textvariable=self.status_var).pack(pady=5)
        
        # Progress bar for downloads
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=5)
        self.progress = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        self.progress.pack(fill=tk.X)
        self.progress_frame.pack_forget()  # Hide initially
        
        # Download folder display and browse button
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(fill=tk.X, pady=10)
        ttk.Label(folder_frame, text="Download folder:").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar(value=self.download_folder)
        ttk.Label(folder_frame, textvariable=self.folder_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT)
        
        # URL input for manual download
        manual_frame = ttk.LabelFrame(main_frame, text="Manual Download")
        manual_frame.pack(fill=tk.X, pady=10)
        
        url_frame = ttk.Frame(manual_frame)
        url_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(url_frame, text="Beatmap URL:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=40)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Paste button
        ttk.Button(url_frame, text="Paste", command=self.paste_url).pack(side=tk.LEFT, padx=2)
        ttk.Button(url_frame, text="Download", command=self.manual_download).pack(side=tk.LEFT)
        
        # Monitoring controls
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        # Start monitoring button
        self.start_button = ttk.Button(control_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Open folder button
        ttk.Button(control_frame, text="Open Download Folder", 
                  command=lambda: os.startfile(self.download_folder)).pack(side=tk.LEFT, padx=5)
        
        # History tab
        history_frame = ttk.Frame(notebook, padding="10")
        notebook.add(history_frame, text="Download History")
        
        # Create history list
        self.history_listbox = tk.Listbox(history_frame, width=70, height=15)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for history list
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Buttons for history actions
        history_buttons = ttk.Frame(history_frame)
        history_buttons.pack(fill=tk.X, pady=5)
        
        ttk.Button(history_buttons, text="Open Selected", 
                  command=self.open_selected_beatmap).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_buttons, text="Clear History", 
                  command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_buttons, text="View in Browser", 
                  command=self.view_in_browser).pack(side=tk.LEFT, padx=5)
        
        # Add signature at the bottom
        signature_frame = ttk.Frame(root)
        signature_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Create a stylish font for the signature
        try:
            # Try to use a fancy font, fall back to something more common if unavailable
            signature_font = Font(family="Brush Script MT", size=10, slant="italic")
        except tk.TclError:
            try:
                signature_font = Font(family="Comic Sans MS", size=9, slant="italic")
            except tk.TclError:
                signature_font = Font(family="Courier", size=9, slant="italic")
            
        self.signature_label = tk.Label(signature_frame, 
                                      text="Made with ♥ by hamdan", 
                                      font=signature_font)
        self.signature_label.pack(side=tk.RIGHT, padx=10)
        
        # Update history list
        self.update_history_list()
        
        # Apply initial theme
        self.apply_theme()
    
    def center_window(self, window, width, height):
        """Center the window on the screen"""
        window.geometry(f"{width}x{height}")
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    def paste_url(self):
        """Paste clipboard content into URL entry"""
        clipboard_content = pyperclip.paste()
        self.url_var.set(clipboard_content)
    
    def change_theme(self, event=None):
        """Change the application theme"""
        self.theme = self.theme_var.get()
        self.apply_theme()
        self.save_settings()
    
    def apply_theme(self):
        """Apply the current theme to all widgets"""
        colors = self.theme_colors[self.theme]
        
        # Configure ttk styles
        self.style.configure('TFrame', background=colors["bg"])
        self.style.configure('TLabel', background=colors["bg"], foreground=colors["fg"])
        self.style.configure('TButton', background=colors["highlight"])
        self.style.configure('TLabelframe', background=colors["bg"], foreground=colors["fg"])
        self.style.configure('TLabelframe.Label', background=colors["bg"], foreground=colors["fg"])
        self.style.configure('TNotebook', background=colors["bg"])
        self.style.configure('TNotebook.Tab', background=colors["highlight"], foreground=colors["fg"])
        self.style.map('TNotebook.Tab', background=[('selected', colors["accent"])])
        self.style.configure('Horizontal.TProgressbar', background=colors["accent"])
        
        # Configure Tk widgets (that don't use ttk styles)
        if hasattr(self, 'history_listbox'):
            self.history_listbox.configure(bg=colors["bg"], fg=colors["fg"])
        
        if hasattr(self, 'signature_label'):
            self.signature_label.configure(bg=colors["bg"], fg=colors["accent"])
            
        # Configure root window bg
        if hasattr(self, 'root'):
            self.root.configure(bg=colors["bg"])
    
    def update_status(self, message):
        if self.status_var:
            self.status_var.set(message)
    
    def start_monitoring(self):
        if hasattr(self, 'start_button'):
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self.monitor_clipboard)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        self.is_running = False
        if hasattr(self, 'start_button'):
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        self.update_status("Monitoring stopped")
    
    def monitor_clipboard(self):
        self.update_status("Monitoring clipboard for beatmap links...")
        
        while self.is_running:
            try:
                current_clipboard = pyperclip.paste()
                
                if current_clipboard != self.previous_clipboard:
                    self.previous_clipboard = current_clipboard
                    
                    # Check if it's an osu beatmap URL
                    beatmap_match = re.search(self.beatmap_id_pattern, current_clipboard)
                    if beatmap_match:
                        beatmap_id = beatmap_match.group(1)
                        self.update_status(f"Found beatmap ID: {beatmap_id}. Downloading...")
                        self.download_beatmap(beatmap_id)
                        
            except Exception as e:
                self.update_status(f"Error: {str(e)}")
            
            time.sleep(0.5)  # Check every half second
    
    def show_progress(self):
        """Show progress bar"""
        if hasattr(self, 'progress_frame'):
            self.progress_frame.pack(fill=tk.X, pady=5)
            self.progress.start(10)
    
    def hide_progress(self):
        """Hide progress bar"""
        if hasattr(self, 'progress_frame'):
            self.progress.stop()
            self.progress_frame.pack_forget()
    
    def download_beatmap(self, beatmap_id):
        try:
            # Show progress bar
            self.show_progress()
            
            download_url = self.direct_download_url.format(beatmap_id)
            self.update_status(f"Downloading from: {download_url}")
            
            # Add User-Agent header to avoid potential API blocks
            headers = {
                'User-Agent': 'OsuBeatmapDownloader/1.0'
            }
            
            response = requests.get(download_url, stream=True, headers=headers)
            
            if response.status_code == 200:
                # Extract filename from header or use beatmap ID
                content_disposition = response.headers.get('Content-Disposition')
                if content_disposition and 'filename=' in content_disposition:
                    filename = re.findall('filename="(.+)"', content_disposition)[0]
                else:
                    filename = f"beatmap_{beatmap_id}.osz"
                
                filepath = os.path.join(self.download_folder, filename)
                
                # Ensure we have unique filenames
                counter = 1
                base_name, extension = os.path.splitext(filename)
                while os.path.exists(filepath):
                    filename = f"{base_name}_{counter}{extension}"
                    filepath = os.path.join(self.download_folder, filename)
                    counter += 1
                
                # Download the file
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                self.update_status(f"Downloaded to: {filepath}")
                
                # Add to history
                history_entry = {
                    "id": beatmap_id,
                    "filename": filename,
                    "path": filepath,
                    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "url": f"https://osu.ppy.sh/beatmapsets/{beatmap_id}"
                }
                self.download_history.append(history_entry)
                self.save_history()
                self.update_history_list()
                
                # Open the file
                self.open_file(filepath)
                
                # Hide progress bar
                self.hide_progress()
                return filepath
            else:
                self.update_status(f"Download failed: HTTP {response.status_code}")
                self.hide_progress()
                return None
                
        except Exception as e:
            self.update_status(f"Download error: {str(e)}")
            self.hide_progress()
            return None
    
    def open_file(self, filepath):
        try:
            if os.path.exists(filepath):
                # Windows-only implementation
                os.startfile(filepath)
                self.update_status(f"Opened: {os.path.basename(filepath)}")
            else:
                self.update_status("File not found after download")
        except Exception as e:
            self.update_status(f"Error opening file: {str(e)}")

    # Methods for additional features
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder)
        if folder:
            self.download_folder = folder
            self.folder_var.set(folder)
            self.save_settings()
    
    def manual_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a beatmap URL")
            return
            
        beatmap_match = re.search(self.beatmap_id_pattern, url)
        if beatmap_match:
            beatmap_id = beatmap_match.group(1)
            self.update_status(f"Manual download of beatmap ID: {beatmap_id}")
            self.download_beatmap(beatmap_id)
        else:
            messagebox.showwarning("Invalid URL", "The URL you entered is not a valid osu! beatmap URL")
    
    def load_history(self):
        history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.json")
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.download_history = json.load(f)
            else:
                self.download_history = []
        except Exception as e:
            print(f"Error loading history: {str(e)}")
            self.download_history = []
    
    def save_history(self):
        history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.json")
        try:
            with open(history_file, 'w') as f:
                json.dump(self.download_history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {str(e)}")
    
    def load_settings(self):
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    if 'theme' in settings:
                        self.theme = settings['theme']
                    if 'download_folder' in settings:
                        folder = settings['download_folder']
                        if os.path.exists(folder):
                            self.download_folder = folder
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
    
    def save_settings(self):
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        try:
            settings = {
                "theme": self.theme,
                "download_folder": self.download_folder
            }
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {str(e)}")
    
    def update_history_list(self):
        if hasattr(self, 'history_listbox'):
            self.history_listbox.delete(0, tk.END)
            for item in self.download_history:
                self.history_listbox.insert(tk.END, f"{item['date']} - {item['filename']} (ID: {item['id']})")
    
    def open_selected_beatmap(self):
        if not hasattr(self, 'history_listbox'):
            return
            
        selected = self.history_listbox.curselection()
        if not selected:
            messagebox.showinfo("Selection", "Please select a beatmap from the history list")
            return
            
        index = selected[0]
        if 0 <= index < len(self.download_history):
            filepath = self.download_history[index]['path']
            if os.path.exists(filepath):
                os.startfile(filepath)
                self.update_status(f"Opened: {os.path.basename(filepath)}")
            else:
                if messagebox.askyesno("File Not Found", 
                                     f"The file no longer exists at {filepath}. Would you like to re-download it?"):
                    beatmap_id = self.download_history[index]['id']
                    self.download_beatmap(beatmap_id)
    
    def clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all download history?"):
            self.download_history = []
            self.save_history()
            self.update_history_list()
    
    def view_in_browser(self):
        selected = self.history_listbox.curselection()
        if not selected:
            messagebox.showinfo("Selection", "Please select a beatmap from the history list")
            return
            
        index = selected[0]
        if 0 <= index < len(self.download_history):
            url = self.download_history[index]['url']
            webbrowser.open(url)

def main():
    root = tk.Tk()
    app = OsuBeatmapDownloader(root)
    app.root = root  # Store reference to root for theme changes
    app.start_monitoring()
    
    # Set up proper shutdown
    def on_closing():
        app.stop_monitoring()
        app.save_history()
        app.save_settings()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()