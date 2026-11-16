"""
ClipCraft Studio - Smart Update Manager
Checks for new versions, parses release manifests, and provides bilingual update notifications.
Author: ahmed elshazly <Elshazly.gsm@gmail.com>
"""

import os
import json
import re
import sys
import time
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import tkinter as tk
from tkinter import ttk, messagebox

APP_VERSION = "1.0.0"
DEFAULT_MANIFEST_URL = "https://raw.githubusercontent.com/Elshazly-gsm/ClipCraft-Studio/main/version.json"


def parse_version_tuple(v_str: str) -> Tuple[int, ...]:
    """Converts a version string like '1.2.3' or 'v1.0.0' into a comparable integer tuple (1, 2, 3)."""
    clean = re.sub(r"[^\d.]", "", str(v_str).strip())
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def check_for_updates(manifest_url: str = DEFAULT_MANIFEST_URL, timeout: int = 5) -> Dict[str, Any]:
    """
    Connects to the remote manifest JSON to inspect latest version.
    Returns:
      {
        "success": bool,
        "has_update": bool,
        "current_version": str,
        "latest_version": str,
        "release_date": str,
        "title": str,
        "changelog": str,
        "download_url": str,
        "error": str,
      }
    """
    result: Dict[str, Any] = {
        "success": False,
        "has_update": False,
        "current_version": APP_VERSION,
        "latest_version": APP_VERSION,
        "release_date": "",
        "title": "",
        "changelog": "",
        "download_url": "",
        "error": "",
    }

    try:
        req = urllib.request.Request(
            manifest_url,
            headers={
                "User-Agent": f"ClipCraftStudio/{APP_VERSION} (Windows NT)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                result["error"] = f"HTTP {response.status}"
                return result
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)

            latest_v = str(data.get("version", APP_VERSION)).strip()
            cur_tuple = parse_version_tuple(APP_VERSION)
            lat_tuple = parse_version_tuple(latest_v)

            result["success"] = True
            result["latest_version"] = latest_v
            result["release_date"] = data.get("release_date", "")
            result["title"] = data.get("title", "")
            result["changelog"] = data.get("changelog", "")
            result["changelog_ar"] = data.get("changelog_ar", "")
            result["download_url"] = data.get("download_url", "https://github.com/Elshazly-gsm/ClipCraft-Studio/releases")
            result["has_update"] = (lat_tuple > cur_tuple)
            return result
    except urllib.error.URLError as e:
        result["error"] = f"Network connection unavailable ({e.reason})"
    except urllib.error.HTTPError as e:
        result["error"] = f"Server returned error {e.code}"
    except Exception as e:
        result["error"] = str(e)

    return result


class UpdateDialog(tk.Toplevel):
    """
    Modern modal dialog presenting update check results.
    Bilingual Arabic / English with clean Dark Theme UI styling.
    """
    def __init__(self, parent=None, result: Optional[Dict[str, Any]] = None, is_manual: bool = True, is_ar: bool = True):
        super().__init__(parent)
        self.result = result or {}
        self.is_manual = is_manual
        self.is_ar = is_ar

        title_text = "ClipCraft Studio — تحديث البرنامج" if self.is_ar else "ClipCraft Studio — Check for Updates"
        self.title(title_text)
        self.geometry("520x420")
        self.minsize(480, 360)
        self.configure(bg="#0d1117")
        self.resizable(False, False)

        # Center on parent or screen
        self.update_idletasks()
        w, h = 520, 420
        x = max(10, (self.winfo_screenwidth() - w) // 2)
        y = max(10, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        if parent:
            self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        is_ar = self.is_ar
        has_update = self.result.get("has_update", False)
        success = self.result.get("success", False)
        error = self.result.get("error", "")
        cur_v = self.result.get("current_version", APP_VERSION)
        lat_v = self.result.get("latest_version", APP_VERSION)
        rel_date = self.result.get("release_date", "")

        # Header Frame
        hdr_frame = tk.Frame(self, bg="#161b22", padx=20, pady=14)
        hdr_frame.pack(fill="x")

        if has_update:
            hdr_icon = "🚀"
            hdr_title = f"يتوفر إصدار جديد: v{lat_v}" if is_ar else f"New Update Available: v{lat_v}"
            hdr_fg = "#58a6ff"
            sub_text = f"الإصدار الحالي: v{cur_v}  |  تاريخ الإصدار: {rel_date or 'الأحدث'}" if is_ar else f"Current: v{cur_v}  |  Release Date: {rel_date or 'Latest'}"
        elif not success and error:
            hdr_icon = "⚠️"
            hdr_title = "تعذر الاتصال بخادم التحديثات" if is_ar else "Could Not Check for Updates"
            hdr_fg = "#d29922"
            sub_text = "تأكد من اتصالك بالإنترنت وحاول مرة أخرى" if is_ar else "Please verify your internet connection and try again"
        else:
            hdr_icon = "✅"
            hdr_title = "برنامجك محدث إلى أحدث إصدار!" if is_ar else "You are up to date!"
            hdr_fg = "#3fb950"
            sub_text = f"أنت تستخدم بالفعل الإصدار الأحدث v{cur_v}" if is_ar else f"You are currently running the latest version v{cur_v}"

        lbl_hdr = tk.Label(
            hdr_frame,
            text=f"{hdr_icon} {hdr_title}",
            font=("Segoe UI", 13, "bold"),
            fg=hdr_fg,
            bg="#161b22",
        )
        lbl_hdr.pack(anchor="w")

        lbl_sub = tk.Label(
            hdr_frame,
            text=sub_text,
            font=("Segoe UI", 9),
            fg="#8b949e",
            bg="#161b22",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Main Body
        body = tk.Frame(self, bg="#0d1117", padx=20, pady=16)
        body.pack(fill="both", expand=True)

        if has_update:
            lbl_cl_title = tk.Label(
                body,
                text="✨ ما الجديد في هذا التحديث (Changelog):" if is_ar else "✨ What's New in this Release:",
                font=("Segoe UI", 10, "bold"),
                fg="#f0f6fc",
                bg="#0d1117",
            )
            lbl_cl_title.pack(anchor="w", pady=(0, 6))

            cl_box = tk.Frame(body, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
            cl_box.pack(fill="both", expand=True, pady=(0, 14))

            txt_cl = tk.Text(
                cl_box,
                bg="#161b22",
                fg="#e6edf3",
                font=("Segoe UI", 9),
                wrap="word",
                bd=0,
                padx=10,
                pady=10,
                relief="flat",
            )
            txt_cl.pack(side="left", fill="both", expand=True)

            scb = ttk.Scrollbar(cl_box, orient="vertical", command=txt_cl.yview)
            scb.pack(side="right", fill="y")
            txt_cl.configure(yscrollcommand=scb.set)

            cl_content = self.result.get("changelog_ar" if is_ar else "changelog") or self.result.get("changelog") or (
                "• تحسينات شاملة في استقرار تشغيل ومعاينة الفيديو على كافة الأجهزة.\n• تسريع وتيرة تصدير ومونتاج الفيديو.\n• إصلاحات وتحسينات عامة في الواجهة." if is_ar else
                "• Standalone video playback and preview improvements on all PCs.\n• Accelerated video editing and export workflow.\n• General stability fixes and UI enhancements."
            )
            txt_cl.insert("1.0", cl_content)
            txt_cl.configure(state="disabled")

        elif not success and error:
            card = tk.Frame(body, bg="#161b22", padx=16, pady=20, highlightbackground="#30363d", highlightthickness=1)
            card.pack(fill="both", expand=True, pady=(10, 16))

            tk.Label(
                card,
                text="📡 تفاصيل الاتصال:" if is_ar else "📡 Connection Details:",
                font=("Segoe UI", 10, "bold"),
                fg="#d29922",
                bg="#161b22",
            ).pack(anchor="w", pady=(0, 6))

            tk.Label(
                card,
                text=str(error),
                font=("Consolas", 9),
                fg="#8b949e",
                bg="#161b22",
                wraplength=440,
                justify="left" if not is_ar else "right",
            ).pack(anchor="w")

        else:
            # All Up to Date Card
            card = tk.Frame(body, bg="#161b22", padx=16, pady=24, highlightbackground="#30363d", highlightthickness=1)
            card.pack(fill="both", expand=True, pady=(10, 16))

            tk.Label(
                card,
                text="🎉 برنامجك يعمل بأحدث التقنيات المستقرة" if is_ar else "🎉 You are on the cutting-edge version",
                font=("Segoe UI", 11, "bold"),
                fg="#3fb950",
                bg="#161b22",
            ).pack(pady=(0, 6))

            tk.Label(
                card,
                text=f"الإصدار المثبت: v{cur_v}\nكافة ميزات الذكاء الاصطناعي والمونتاج تعمل بأحدث كود متاح." if is_ar else
                     f"Installed Version: v{cur_v}\nAll AI features, video engines, and modules are current.",
                font=("Segoe UI", 9),
                fg="#8b949e",
                bg="#161b22",
                justify="center",
            ).pack()

        # Bottom Button Row
        btn_row = tk.Frame(body, bg="#0d1117")
        btn_row.pack(fill="x")

        if has_update:
            self.body = body
            btn_dl = ttk.Button(
                btn_row,
                text="🚀 تحميل وتثبيت التحديث الآن" if is_ar else "🚀 Download & Install Update",
                command=self._start_download,
                style="Action.TButton",
            )
            btn_dl.pack(side="left", fill="x", expand=True, padx=(0, 8))

            btn_close = ttk.Button(
                btn_row,
                text="لاحقاً" if is_ar else "Later",
                command=self.destroy,
                style="Player.TButton",
            )
            btn_close.pack(side="right")
        else:
            self.body = body
            btn_ok = ttk.Button(
                btn_row,
                text="حسناً" if is_ar else "OK",
                command=self.destroy,
                style="Action.TButton",
                width=14,
            )
            btn_ok.pack(side="right")

    def _start_download(self):
        is_ar = self.is_ar
        url = self.result.get("download_url") or ""
        if not url or not url.startswith("http"):
            self._open_download_url()
            return

        # Clear body and render downloading progress state
        for w in self.body.winfo_children():
            w.destroy()

        self._is_cancelled = False
        lat_v = self.result.get("latest_version", "latest")

        dl_card = tk.Frame(self.body, bg="#161b22", padx=20, pady=24, highlightbackground="#30363d", highlightthickness=1)
        dl_card.pack(fill="both", expand=True, pady=(10, 16))

        tk.Label(
            dl_card,
            text=f"🚀 جاري تحميل الإصدار الجديد v{lat_v}..." if is_ar else f"🚀 Downloading update v{lat_v}...",
            font=("Segoe UI", 11, "bold"),
            fg="#58a6ff",
            bg="#161b22",
        ).pack(anchor="w", pady=(0, 10))

        self.progress_bar = ttk.Progressbar(dl_card, orient="horizontal", mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x", pady=(0, 10))

        self.lbl_progress_txt = tk.Label(
            dl_card,
            text="جاري الاتصال بالسيرفر وبدء التحميل..." if is_ar else "Connecting and preparing download...",
            font=("Segoe UI", 9),
            fg="#e6edf3",
            bg="#161b22",
        )
        self.lbl_progress_txt.pack(anchor="w", pady=(0, 4))

        self.lbl_speed_txt = tk.Label(
            dl_card,
            text="",
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#161b22",
        )
        self.lbl_speed_txt.pack(anchor="w", pady=(0, 8))

        btn_row = tk.Frame(self.body, bg="#0d1117")
        btn_row.pack(fill="x")

        self.btn_cancel_dl = ttk.Button(
            btn_row,
            text="إلغاء التحميل" if is_ar else "Cancel Download",
            command=self._cancel_download,
            style="Player.TButton",
        )
        self.btn_cancel_dl.pack(side="right")

        threading.Thread(target=self._run_download_thread, args=(url, lat_v), daemon=True).start()

    def _cancel_download(self):
        self._is_cancelled = True
        self.destroy()

    def _run_download_thread(self, url: str, lat_v: str):
        is_ar = self.is_ar
        temp_dir = Path(tempfile.gettempdir()) / "ClipCraftUpdate"
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            target_exe = temp_dir / f"ClipCraft_Studio_Setup_v{lat_v}.exe"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"ClipCraftStudio/{APP_VERSION} (Windows NT)"}
            )

            start_time = time.time()
            with urllib.request.urlopen(req, timeout=15) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0) or 0)
                downloaded = 0
                chunk_size = 128 * 1024  # 128 KB
                last_ui_update = 0

                with open(target_exe, "wb") as f_out:
                    while True:
                        if self._is_cancelled:
                            f_out.close()
                            try:
                                target_exe.unlink(missing_ok=True)
                            except Exception:
                                pass
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_ui_update > 0.15:
                            last_ui_update = now
                            elapsed = max(0.1, now - start_time)
                            speed_bps = downloaded / elapsed
                            speed_mb = speed_bps / (1024 * 1024)

                            if total_bytes > 0:
                                pct = min(100.0, (downloaded / total_bytes) * 100)
                                cur_mb = downloaded / (1024 * 1024)
                                tot_mb = total_bytes / (1024 * 1024)
                                rem_sec = int((total_bytes - downloaded) / max(1, speed_bps))
                                prog_text = f"{cur_mb:.1f} MB / {tot_mb:.1f} MB ({pct:.1f}%)"
                                speed_text = f"السرعة: {speed_mb:.1f} MB/s  |  متبقي: {rem_sec} ثانية" if is_ar else f"Speed: {speed_mb:.1f} MB/s  |  Remaining: {rem_sec}s"
                            else:
                                pct = 0
                                cur_mb = downloaded / (1024 * 1024)
                                prog_text = f"تم تحميل: {cur_mb:.1f} MB" if is_ar else f"Downloaded: {cur_mb:.1f} MB"
                                speed_text = f"السرعة: {speed_mb:.1f} MB/s" if is_ar else f"Speed: {speed_mb:.1f} MB/s"

                            def _update_ui(p=pct, pt=prog_text, st=speed_text):
                                try:
                                    self.progress_bar["value"] = p
                                    self.lbl_progress_txt.configure(text=pt)
                                    self.lbl_speed_txt.configure(text=st)
                                except Exception:
                                    pass

                            self.after(0, _update_ui)

            # Download Complete
            def _on_success():
                try:
                    self.progress_bar["value"] = 100
                    done_msg = "✅ تم تحميل التحديث بنجاح! جاري تشغيل المثبت وإغلاق البرنامج..." if is_ar else "✅ Download completed! Launching installer and closing app..."
                    self.lbl_progress_txt.configure(text=done_msg, fg="#3fb950")
                    self.lbl_speed_txt.configure(text="")
                    if hasattr(self, "btn_cancel_dl"):
                        self.btn_cancel_dl.configure(state="disabled")
                    self.after(1400, lambda: self._launch_installer_and_exit(target_exe))
                except Exception:
                    pass

            self.after(0, _on_success)

        except Exception as e:
            def _on_err(err=str(e)):
                try:
                    err_msg = f"تعذر إكمال التحميل التلقائي: {err}" if is_ar else f"Download failed: {err}"
                    self.lbl_progress_txt.configure(text=err_msg, fg="#f85149")
                    if hasattr(self, "btn_cancel_dl"):
                        self.btn_cancel_dl.pack_forget()

                    btn_browser = ttk.Button(
                        self.body,
                        text="🌐 التحميل يدوياً من المتصفح" if is_ar else "🌐 Download via Browser",
                        command=self._open_download_url,
                        style="Action.TButton",
                    )
                    btn_browser.pack(side="left", pady=(10, 0))

                    btn_close = ttk.Button(
                        self.body,
                        text="إغلاق" if is_ar else "Close",
                        command=self.destroy,
                        style="Player.TButton",
                    )
                    btn_close.pack(side="right", pady=(10, 0))
                except Exception:
                    pass

            self.after(0, _on_err)

    def _launch_installer_and_exit(self, installer_path: Path):
        try:
            if installer_path.exists():
                subprocess.Popen([str(installer_path)], shell=True)
        except Exception:
            pass

        # Close main application
        try:
            if self.master:
                self.master.destroy()
        except Exception:
            pass
        sys.exit(0)

    def _open_download_url(self):
        url = self.result.get("download_url") or "https://github.com/Elshazly-gsm/ClipCraft-Studio/releases"
        try:
            webbrowser.open(url)
        except Exception:
            pass
        self.destroy()
