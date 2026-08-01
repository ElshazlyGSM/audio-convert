import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk


APP_DIR = Path(__file__).resolve().parent
os.chdir(APP_DIR)

import convert  # noqa: E402


class QueueWriter:
    def __init__(self, messages):
        self.messages = messages

    def write(self, text):
        if text:
            self.messages.put(text)

    def flush(self):
        pass


class SongCoverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Song Cover Tool")
        self.geometry("900x560")
        self.minsize(760, 460)

        self.messages = queue.Queue()
        self.worker = None
        self.input_path = None
        self.output_dir = None
        self.audio_files = []

        self.status_var = tk.StringVar(value="Choose a file or folder to start")
        self.source_var = tk.StringVar(value="No file or folder selected")
        self.output_var = tk.StringVar(value="Output folder will be created after selecting a source")
        self.count_var = tk.StringVar(value="0 audio files")
        self.progress_var = tk.StringVar(value="0 / 0 files processed")
        self.manual_search_var = tk.StringVar(value="")
        self.quality_var = tk.StringVar(value="192k")
        self.preview_var = tk.BooleanVar(value=True)
        self.skip_existing_var = tk.BooleanVar(value=True)
        self.keep_original_var = tk.BooleanVar(value=False)
        self.open_output_var = tk.BooleanVar(value=True)
        self.custom_cover_var = tk.BooleanVar(value=False)
        self.custom_cover_path = None
        self.custom_cover_text_var = tk.StringVar(value="No custom cover selected")
        self.format_options = [
            f"{ext} - {info['label']}" for ext, info in convert.OUTPUT_FORMATS.items()
        ]
        self.output_format_var = tk.StringVar(value=".mp3 - MP3")
        self.busy_widgets = []

        self._build_ui()
        self._update_run_state()
        self.after(100, self._drain_messages)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="Song Cover Tool", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            header,
            text="Choose one audio file or a folder, pick the output format, then run conversion with cover art.",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        source_panel = ttk.Frame(self, padding=(16, 6, 16, 6))
        source_panel.grid(row=1, column=0, sticky="ew")
        source_panel.columnconfigure(2, weight=1)

        ttk.Button(source_panel, text="Choose File", command=self.choose_input_file).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(source_panel, text="Choose Folder", command=self.choose_input_folder).grid(
            row=0, column=1, padx=(8, 0), sticky="w"
        )
        ttk.Label(source_panel, textvariable=self.source_var).grid(
            row=0, column=2, padx=(10, 0), sticky="ew"
        )

        ttk.Label(source_panel, text="Output").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(source_panel, textvariable=self.output_var).grid(
            row=1, column=2, padx=(10, 0), pady=(8, 0), sticky="ew"
        )

        options = ttk.Frame(self, padding=(16, 6, 16, 6))
        options.grid(row=2, column=0, sticky="ew")
        options.columnconfigure(7, weight=1)

        ttk.Label(options, text="Format").grid(row=0, column=0, sticky="w")

        self.format_combo = ttk.Combobox(
            options,
            textvariable=self.output_format_var,
            values=self.format_options,
            state="readonly",
            width=14,
        )
        self.format_combo.grid(row=0, column=1, padx=(8, 12), sticky="w")

        ttk.Label(options, text="Quality").grid(row=0, column=2, sticky="w")

        self.quality_combo = ttk.Combobox(
            options,
            textvariable=self.quality_var,
            values=convert.QUALITY_OPTIONS,
            state="readonly",
            width=8,
        )
        self.quality_combo.grid(row=0, column=3, padx=(8, 12), sticky="w")

        self.keep_original_check = ttk.Checkbutton(
            options,
            text="Keep original format",
            variable=self.keep_original_var,
            command=self._sync_option_state,
        )
        self.keep_original_check.grid(row=0, column=4, padx=(0, 12), sticky="w")

        self.skip_existing_check = ttk.Checkbutton(
            options,
            text="Skip if output exists",
            variable=self.skip_existing_var,
        )
        self.skip_existing_check.grid(row=0, column=5, padx=(0, 12), sticky="w")

        self.preview_check = ttk.Checkbutton(
            options,
            text="Preview cover",
            variable=self.preview_var,
        )
        self.preview_check.grid(row=0, column=6, padx=(0, 12), sticky="w")

        self.open_output_check = ttk.Checkbutton(
            options,
            text="Open output when done",
            variable=self.open_output_var,
        )
        self.open_output_check.grid(row=0, column=7, sticky="w")

        search_panel = ttk.Frame(self, padding=(16, 0, 16, 8))
        search_panel.grid(row=3, column=0, sticky="ew")
        search_panel.columnconfigure(1, weight=1)

        ttk.Label(search_panel, text="Manual search").grid(row=0, column=0, sticky="w")
        self.manual_search_entry = ttk.Entry(search_panel, textvariable=self.manual_search_var)
        self.manual_search_entry.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self.custom_cover_check = ttk.Checkbutton(
            search_panel,
            text="Use custom cover",
            variable=self.custom_cover_var,
            command=self._sync_option_state,
        )
        self.custom_cover_check.grid(row=1, column=0, pady=(8, 0), sticky="w")

        custom_cover_row = ttk.Frame(search_panel)
        custom_cover_row.grid(row=1, column=1, padx=(8, 0), pady=(8, 0), sticky="ew")
        custom_cover_row.columnconfigure(1, weight=1)

        self.choose_cover_button = ttk.Button(
            custom_cover_row,
            text="Choose Image",
            command=self.choose_custom_cover,
        )
        self.choose_cover_button.grid(row=0, column=0, sticky="w")
        ttk.Label(custom_cover_row, textvariable=self.custom_cover_text_var).grid(
            row=0, column=1, padx=(8, 0), sticky="ew"
        )

        controls = ttk.Frame(self, padding=(16, 6, 16, 10))
        controls.grid(row=4, column=0, sticky="ew")
        controls.columnconfigure(6, weight=1)

        ttk.Label(controls, textvariable=self.count_var).grid(row=0, column=0, sticky="w")
        ttk.Label(controls, textvariable=self.progress_var).grid(row=0, column=1, padx=(12, 0), sticky="w")

        self.run_button = ttk.Button(controls, text="Run", command=self.start_conversion)
        self.run_button.grid(row=0, column=2, padx=(12, 0), sticky="w")

        self.open_input_button = ttk.Button(
            controls,
            text="Open Source",
            command=self.open_source,
        )
        self.open_input_button.grid(row=0, column=3, padx=(8, 0), sticky="w")

        self.open_output_button = ttk.Button(
            controls,
            text="Open Output",
            command=lambda: self.open_folder(self.output_dir),
        )
        self.open_output_button.grid(row=0, column=4, padx=(8, 0), sticky="w")

        self.progress = ttk.Progressbar(controls, mode="indeterminate")
        self.progress.grid(row=0, column=6, padx=(14, 0), sticky="ew")

        log_frame = ttk.Frame(self, padding=(16, 0, 16, 10))
        log_frame.grid(row=5, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(log_frame, wrap="word", height=18, state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self, padding=(16, 0, 16, 14))
        footer.grid(row=6, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

        self.busy_widgets = [
            self.format_combo,
            self.quality_combo,
            self.keep_original_check,
            self.skip_existing_check,
            self.preview_check,
            self.open_output_check,
            self.manual_search_entry,
            self.custom_cover_check,
            self.choose_cover_button,
        ]
        self._sync_option_state()

    def choose_input_folder(self):
        selected = filedialog.askdirectory(
            title="Choose folder with audio files",
            initialdir=str(APP_DIR),
        )
        if not selected:
            return

        self.set_source(Path(selected))

    def choose_input_file(self):
        filetypes = [
            ("Audio files", " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
            ("All files", "*.*"),
        ]
        selected = filedialog.askopenfilename(
            title="Choose one audio file",
            initialdir=str(APP_DIR),
            filetypes=filetypes,
        )
        if not selected:
            return

        self.set_source(Path(selected))

    def choose_custom_cover(self):
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"),
            ("All files", "*.*"),
        ]
        selected = filedialog.askopenfilename(
            title="Choose cover image",
            initialdir=str(APP_DIR),
            filetypes=filetypes,
        )
        if not selected:
            return

        self.custom_cover_path = Path(selected)
        self.custom_cover_text_var.set(str(self.custom_cover_path))
        self.status_var.set("Custom cover selected")
        self._update_run_state()

    def set_source(self, source_path):
        self.input_path = source_path
        output_base = source_path.parent if source_path.is_file() else source_path
        self.output_dir = output_base / "output"
        self.audio_files = convert.collect_audio_files(self.input_path, self.output_dir)

        self.source_var.set(str(self.input_path))
        self.output_var.set(str(self.output_dir))
        self.count_var.set(f"{len(self.audio_files)} audio files")
        self.progress_var.set(f"0 / {len(self.audio_files)} files processed")

        if self.audio_files:
            self.status_var.set("Ready")
        else:
            self.status_var.set("No supported audio files found in this source")

        self._update_run_state()

    def open_source(self):
        if not self.input_path:
            return
        if self.input_path.is_file():
            self.open_folder(self.input_path.parent)
        else:
            self.open_folder(self.input_path)

    def open_folder(self, path):
        if not path:
            return

        path.mkdir(exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def start_conversion(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.input_path or not self.audio_files:
            return
        if self.custom_cover_var.get() and not self.custom_cover_path:
            messagebox.showwarning("Song Cover Tool", "Choose a cover image first.")
            return

        output_ext = self.selected_output_ext()
        quality = self.quality_var.get()
        skip_if_exists = self.skip_existing_var.get()
        keep_original_format = self.keep_original_var.get()
        search_text = self.manual_search_var.get().strip() or None
        custom_cover_path = self.custom_cover_path if self.custom_cover_var.get() else None
        self._clear_log()
        mode = "original format" if keep_original_format else output_ext
        self._append_log(f"Starting conversion as {mode}...\n")
        self.status_var.set("Running...")
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=max(len(self.audio_files), 1), value=0)
        self.progress_var.set(f"0 / {len(self.audio_files)} files processed")

        self.worker = threading.Thread(
            target=self._run_conversion,
            args=(
                output_ext,
                quality,
                skip_if_exists,
                keep_original_format,
                search_text,
                custom_cover_path,
            ),
            daemon=True,
        )
        self.worker.start()

    def selected_output_ext(self):
        return self.output_format_var.get().split(" ", 1)[0]

    def _run_conversion(
        self,
        output_ext,
        quality,
        skip_if_exists,
        keep_original_format,
        search_text,
        custom_cover_path,
    ):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        writer = QueueWriter(self.messages)
        sys.stdout = writer
        sys.stderr = writer

        try:
            convert.main(
                output_ext=output_ext,
                input_dir=self.input_path,
                output_dir=self.output_dir,
                skip_if_exists=skip_if_exists,
                keep_original_format=keep_original_format,
                quality=quality,
                search_text=search_text,
                preview_callback=self._preview_cover_request if self.preview_var.get() else None,
                progress_callback=self._progress_request,
                custom_cover_path=custom_cover_path,
            )
            self.messages.put("\n__DONE__")
        except Exception as exc:
            self.messages.put(f"\nError: {exc}\n")
            self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _drain_messages(self):
        try:
            while True:
                message = self.messages.get_nowait()
                if message == "\n__DONE__":
                    self._finish("Done")
                elif message == "\n__FAILED__":
                    self._finish("Failed", failed=True)
                elif isinstance(message, tuple) and message[0] == "progress":
                    _, current, total = message
                    self.progress.configure(maximum=max(total, 1), value=current)
                    self.progress_var.set(f"{current} / {total} files processed")
                elif isinstance(message, tuple) and message[0] == "preview":
                    _, payload = message
                    self._show_preview_dialog(payload)
                else:
                    self._append_log(message)
        except queue.Empty:
            pass

        self.after(100, self._drain_messages)

    def _finish(self, status, failed=False):
        self._set_busy(False)
        self.status_var.set(status)
        if self.open_output_var.get() and not failed:
            self.open_folder(self.output_dir)
        if failed:
            messagebox.showerror("Song Cover Tool", "Something went wrong. Check the log.")
        else:
            messagebox.showinfo("Song Cover Tool", "Files are ready in the output folder.")

    def _set_busy(self, busy):
        widget_state = "disabled" if busy else "normal"
        combo_state = "disabled" if busy else "readonly"
        for widget in self.busy_widgets:
            widget.configure(state=combo_state if isinstance(widget, ttk.Combobox) else widget_state)
        if not busy:
            self._sync_option_state()
        self.open_input_button.configure(state=widget_state if self.input_path else "disabled")
        self.open_output_button.configure(state=widget_state if self.output_dir else "disabled")
        self.run_button.configure(state="disabled" if busy else self._run_button_state())

    def _sync_option_state(self):
        if self.worker and self.worker.is_alive():
            return
        self.format_combo.configure(state="disabled" if self.keep_original_var.get() else "readonly")
        self.quality_combo.configure(state="readonly")
        self.manual_search_entry.configure(state="disabled" if self.custom_cover_var.get() else "normal")
        self.choose_cover_button.configure(state="normal" if self.custom_cover_var.get() else "disabled")
        self._update_run_state()

    def _progress_request(self, current, total, source_path):
        self.messages.put(("progress", current, total))

    def _preview_cover_request(self, audio_path, cover_data, cover_ext, search_name):
        done = threading.Event()
        payload = {
            "audio_path": audio_path,
            "cover_data": cover_data,
            "cover_ext": cover_ext,
            "search_name": search_name,
            "accepted": False,
            "done": done,
        }
        self.messages.put(("preview", payload))
        done.wait()
        return payload["accepted"]

    def _show_preview_dialog(self, payload):
        dialog = tk.Toplevel(self)
        dialog.title("Preview Cover")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text=payload["audio_path"].name, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(frame, text=f"Search: {payload['search_name']}").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(2, 10)
        )

        try:
            image = Image.open(BytesIO(payload["cover_data"]))
            image.thumbnail((420, 420))
            photo = ImageTk.PhotoImage(image)
            image_label = ttk.Label(frame, image=photo)
            image_label.image = photo
            image_label.grid(row=2, column=0, columnspan=2, pady=(0, 12))
        except Exception as exc:
            ttk.Label(frame, text=f"Could not preview image: {exc}").grid(
                row=2, column=0, columnspan=2, pady=(0, 12)
            )

        def choose(accepted):
            payload["accepted"] = accepted
            payload["done"].set()
            dialog.destroy()

        ttk.Button(frame, text="Use Cover", command=lambda: choose(True)).grid(
            row=3, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(frame, text="Skip Cover", command=lambda: choose(False)).grid(
            row=3, column=1, sticky="ew", padx=(6, 0)
        )

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose(False))
        dialog.wait_window()

    def _run_button_state(self):
        if not self.input_path or not self.audio_files:
            return "disabled"
        if self.custom_cover_var.get() and not self.custom_cover_path:
            return "disabled"
        return "normal"

    def _update_run_state(self):
        self.run_button.configure(state=self._run_button_state())
        self.open_input_button.configure(state="normal" if self.input_path else "disabled")
        self.open_output_button.configure(state="normal" if self.output_dir else "disabled")

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")


if __name__ == "__main__":
    SongCoverApp().mainloop()
