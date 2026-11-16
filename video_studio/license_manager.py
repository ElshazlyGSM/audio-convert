"""
ClipCraft Studio - Enterprise Node-Locked Licensing & 3-Day Trial Engine
Uses RSA-2048 Asymmetric Digital Signatures and Hardware-ID (HWID) binding.
Author: ahmed elshazly <Elshazly.gsm@gmail.com>
"""

import os
import sys
import time
import json
import base64
import ctypes
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import tkinter as tk
from tkinter import ttk, messagebox

# Cryptography for RSA Verification
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

# Embedded RSA-2048 Public Key (Used ONLY for verification, cannot forge keys)
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAul8pTfsHeuEQfYCyfak3
uVMv5m3FHJidZryZHGhsbCZqQUFKMAKVSZwf4IzBRWYJUjkJdaOE124jq7aC+P3s
x4brNxFGZaSyS/35Scaa/Yy/3mWcpkgYIo9y5KaTcSpq74zCrBNxmZMA0PVvRsT1
V145O/eKTHUqzA9dJF5mQWw/x6cBrND7RnH7rhtlUCMGsYp3cClw4nZowqFZEkuF
wtZIksLVr2o0sfyXfnTUADvJ8C6MXmEmNvE+12jeqVFynVxcP7RdYQT76b+hAH7a
yoSNSBcm1reCi/3hyWAq/iadlljbSKAm5msXadpricBKleohfO/F/Nl6qfYa0kpW
OwIDAQAB
-----END PUBLIC KEY-----"""

TRIAL_DURATION_SECONDS = 3 * 86400  # 3 days = 72 hours
LICENSE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ClipCraftStudio"
LICENSE_FILE = LICENSE_DIR / "license.key"
TRIAL_STATE_FILE = LICENSE_DIR / "sys_state.dat"

_CACHED_HWID: Optional[str] = None


def get_hardware_id() -> str:
    """
    Computes a deterministic, immutable Hardware ID unique to this physical computer
    combining Motherboard UUID and System Drive Volume Serial Number.
    Format: CC-XXXX-XXXX-XXXX-XXXX
    """
    global _CACHED_HWID
    if _CACHED_HWID:
        return _CACHED_HWID

    # 1. Volume Serial Number
    vol_serial = "VOL0000"
    try:
        vol = ctypes.c_ulong()
        ctypes.windll.kernel32.GetVolumeInformationW("C:\\", None, 0, ctypes.byref(vol), None, None, None, 0)
        vol_serial = f"{vol.value:08X}"
    except Exception:
        pass

    # 2. Motherboard UUID
    sys_uuid = "SYS0000"
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
            capture_output=True, text=True, timeout=4, creationflags=0x08000000 if sys.platform.startswith("win") else 0
        )
        val = res.stdout.strip()
        if val and len(val) > 8:
            sys_uuid = val
    except Exception:
        pass

    if sys_uuid == "SYS0000":
        try:
            out = subprocess.check_output("wmic csproduct get uuid", shell=True, text=True, stderr=subprocess.DEVNULL)
            lines = [l.strip() for l in out.splitlines() if l.strip() and "UUID" not in l.upper()]
            if lines:
                sys_uuid = lines[0]
        except Exception:
            pass

    raw_seed = f"{vol_serial}::{sys_uuid}::ClipCraftStudio".encode("utf-8")
    h = hashlib.sha256(raw_seed).hexdigest().upper()
    _CACHED_HWID = f"CC-{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"
    return _CACHED_HWID


def _derive_tamper_key(hwid: str) -> bytes:
    return hashlib.sha256(f"ClipCraft_{hwid}_SecretKey".encode("utf-8")).digest()


def _read_trial_record() -> Dict[str, Any]:
    hwid = get_hardware_id()
    if not TRIAL_STATE_FILE.exists():
        now = time.time()
        record = {
            "hwid": hwid,
            "first_seen": now,
            "last_seen": now,
            "version": 1,
        }
        _write_trial_record(record)
        return record

    try:
        raw = TRIAL_STATE_FILE.read_bytes()
        # Decode: first 32 bytes are sha256 checksum
        expected_chk = raw[:32]
        payload_bytes = raw[32:]
        key = _derive_tamper_key(hwid)
        calc_chk = hashlib.sha256(key + payload_bytes).digest()
        if calc_chk != expected_chk:
            return {"hwid": hwid, "tampered": True}

        data = json.loads(payload_bytes.decode("utf-8"))
        if data.get("hwid") != hwid:
            return {"hwid": hwid, "tampered": True}
        return data
    except Exception:
        return {"hwid": hwid, "tampered": True}


def _write_trial_record(record: Dict[str, Any]):
    try:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        hwid = get_hardware_id()
        key = _derive_tamper_key(hwid)
        payload_bytes = json.dumps(record, sort_keys=True).encode("utf-8")
        chk = hashlib.sha256(key + payload_bytes).digest()
        TRIAL_STATE_FILE.write_bytes(chk + payload_bytes)
    except Exception:
        pass


def check_license_status() -> Dict[str, Any]:
    """
    Evaluates current licensing state.
    Returns:
      {
        "state": "licensed" | "trial" | "expired" | "tampered",
        "hwid": str,
        "remaining_seconds": float,
        "remaining_hours": int,
        "remaining_days": int,
        "plan": str,
        "customer": str,
      }
    """
    hwid = get_hardware_id()

    # 1. Check Permanent / Active License Key
    if LICENSE_FILE.exists():
        try:
            token = LICENSE_FILE.read_text(encoding="utf-8").strip()
            ok, data_or_err = _verify_license_token(token, hwid)
            if ok and isinstance(data_or_err, dict):
                expires_at = float(data_or_err.get("expires_at", 0) or 0)
                if expires_at > 0:
                    rem_sec = max(0.0, expires_at - time.time())
                    rem_hrs = int(rem_sec // 3600)
                    rem_days = int(math_ceil_days(rem_sec))
                else:
                    rem_sec = 999999999.0
                    rem_hrs = 999999
                    rem_days = 9999
                return {
                    "state": "licensed",
                    "hwid": hwid,
                    "remaining_seconds": rem_sec,
                    "remaining_hours": rem_hrs,
                    "remaining_days": rem_days,
                    "plan": data_or_err.get("plan", "LIFETIME"),
                    "customer": data_or_err.get("issued_to", "Registered User"),
                    "expires_at": expires_at,
                }
            elif not ok and "انتهت فترة" in str(data_or_err):
                return {
                    "state": "expired",
                    "hwid": hwid,
                    "remaining_seconds": 0.0,
                    "remaining_hours": 0,
                    "remaining_days": 0,
                    "plan": "EXPIRED_LICENSE",
                    "customer": "",
                }
        except Exception:
            pass

    # 2. Check 3-Day Trial Record
    rec = _read_trial_record()
    if rec.get("tampered"):
        return {
            "state": "tampered",
            "hwid": hwid,
            "remaining_seconds": 0.0,
            "remaining_hours": 0,
            "remaining_days": 0,
            "plan": "EXPIRED_TRIAL",
            "customer": "",
        }

    now = time.time()
    first_seen = float(rec.get("first_seen", now))
    last_seen = float(rec.get("last_seen", now))

    # Anti-Clock Rollback: if current time is older than last recorded time by > 5 min
    if now < last_seen - 300:
        return {
            "state": "tampered",
            "hwid": hwid,
            "remaining_seconds": 0.0,
            "remaining_hours": 0,
            "remaining_days": 0,
            "plan": "EXPIRED_TRIAL",
            "customer": "",
        }

    # Update last_seen
    rec["last_seen"] = max(now, last_seen)
    _write_trial_record(rec)

    elapsed = now - first_seen
    remaining = max(0.0, TRIAL_DURATION_SECONDS - elapsed)

    if remaining > 0.0:
        rem_hrs = int(remaining // 3600)
        rem_days = int(math_ceil_days(remaining))
        return {
            "state": "trial",
            "hwid": hwid,
            "remaining_seconds": remaining,
            "remaining_hours": rem_hrs,
            "remaining_days": rem_days,
            "plan": "TRIAL",
            "customer": "Trial User",
        }
    else:
        return {
            "state": "expired",
            "hwid": hwid,
            "remaining_seconds": 0.0,
            "remaining_hours": 0,
            "remaining_days": 0,
            "plan": "EXPIRED_TRIAL",
            "customer": "",
        }


def math_ceil_days(seconds: float) -> int:
    return max(1, int((seconds + 86399) // 86400))


def _verify_license_token(token: str, expected_hwid: str) -> Tuple[bool, Any]:
    """
    Cryptographically verifies an RSA-signed license token string against PUBLIC_KEY_PEM.
    """
    try:
        clean_token = token.replace("\r", "").replace("\n", "").strip()
        if "." not in clean_token:
            return False, "تنسيق كود التفعيل غير صحيح."

        payload_b64, sig_b64 = clean_token.split(".", 1)
        payload_bytes = base64.b64decode(payload_b64)
        sig_bytes = base64.b64decode(sig_b64)

        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        public_key.verify(
            sig_bytes,
            payload_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )

        data = json.loads(payload_bytes.decode("utf-8"))
        token_hwid = str(data.get("hwid", "")).strip().upper()
        if token_hwid != expected_hwid.strip().upper():
            return False, f"كود التفعيل هذا مخصص لجهاز آخر ({token_hwid}) ولا يطابق جهازك الحالى."

        expires_at = float(data.get("expires_at", 0) or 0)
        if expires_at > 0 and time.time() > expires_at:
            return False, "انتهت فترة صلاحية هذا الترخيص."

        return True, data
    except Exception as e:
        return False, f"مفتاح التفعيل غير صالح: {e}"


def activate_license_key(key_str: str) -> Tuple[bool, str]:
    """
    Validates and persists a user-entered activation key on this machine.
    """
    hwid = get_hardware_id()
    ok, res = _verify_license_token(key_str, hwid)
    if not ok:
        return False, str(res)

    try:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        LICENSE_FILE.write_text(key_str.strip(), encoding="utf-8")
        plan = res.get("plan", "PRO") if isinstance(res, dict) else "PRO"
        if plan == "LIFETIME":
            return True, "تم تفعيل النسخة الكاملة لبرنامج ClipCraft Studio بنجاح مدى الحياة!"
        else:
            return True, f"تم تفعيل البرنامج بنجاح (نوع الترخيص: {plan})!"
    except Exception as e:
        return False, f"تعذر حفظ ملف الترخيص: {e}"


# -----------------------------------------------------------------------------
# Sleek Activation UI Dialog (Bilingual English / Arabic)
# -----------------------------------------------------------------------------
class ActivationDialog(tk.Toplevel):
    """
    Modern modal activation window with 1-click Hardware ID copy and direct activation.
    Supports complete English and Arabic bilingual localization and clean styling.
    """
    def __init__(self, parent=None, is_expired: bool = False, on_success=None, is_ar: bool = False):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.is_expired = is_expired
        self.is_ar = is_ar
        self.activated_ok = False

        # Singleton guard: if parent already has an active license dialog, destroy it cleanly
        if parent and hasattr(parent, "_license_dialog_instance"):
            old = getattr(parent, "_license_dialog_instance", None)
            if old and old is not self:
                try:
                    if old.winfo_exists():
                        old.destroy()
                except Exception:
                    pass
            parent._license_dialog_instance = self

        title_str = "ClipCraft Studio — تفعيل البرنامج والترخيص" if self.is_ar else "ClipCraft Studio — License & Activation"
        self.title(title_str)
        self.geometry("580x540")
        self.minsize(580, 520)
        self.maxsize(580, 560)
        self.configure(bg="#0d1117")

        # Set app icon if available
        try:
            ico_candidates = [
                Path(__file__).resolve().parent.parent / "app_icon.ico",
                Path(sys.executable).resolve().parent / "app_icon.ico" if getattr(sys, "frozen", False) else None,
                Path(getattr(sys, "_MEIPASS", "")) / "app_icon.ico" if getattr(sys, "frozen", False) else None,
            ]
            for ico in ico_candidates:
                if ico and ico.exists():
                    self.iconbitmap(str(ico))
                    break
        except Exception:
            pass

        # Center on screen
        self.update_idletasks()
        w, h = 580, 540
        x = max(10, (self.winfo_screenwidth() - w) // 2)
        y = max(10, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Win32 HWND resolution
        self._dlg_hwnd = None
        self._root_hwnd = None
        try:
            self._dlg_hwnd = ctypes.windll.user32.GetAncestor(self.winfo_id(), 2)
            if self.parent and self.parent.winfo_exists():
                self._root_hwnd = ctypes.windll.user32.GetAncestor(self.parent.winfo_id(), 2)
        except Exception:
            pass

        # Enable native titlebar minimize button on Windows
        self._enable_titlebar_minimize()

        # Build UI
        self._build_ui()

        # Setup native Win32 modal & minimize synchronization (WITHOUT grab_set)
        self._setup_win32_modal()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _enable_titlebar_minimize(self):
        """Enables the native minimize button on Windows titlebar."""
        if not self._dlg_hwnd:
            return
        try:
            GWL_STYLE = -16
            WS_MINIMIZEBOX = 0x00020000
            WS_MAXIMIZEBOX = 0x00010000
            cur_style = ctypes.windll.user32.GetWindowLongW(self._dlg_hwnd, GWL_STYLE)
            new_style = (cur_style | WS_MINIMIZEBOX) & ~WS_MAXIMIZEBOX
            ctypes.windll.user32.SetWindowLongW(self._dlg_hwnd, GWL_STYLE, new_style)
            ctypes.windll.user32.SetWindowPos(self._dlg_hwnd, 0, 0, 0, 0, 0, 0x0027)
        except Exception:
            pass

    def _setup_win32_modal(self):
        """
        Uses native Win32 modal mechanics:
        Disables parent window so it cannot receive clicks or input,
        WITHOUT using Tkinter's internal grab_set() which blocks minimizing.
        This allows the native Windows minimize button, in-dialog buttons, and Win+D to work 100% natively!
        """
        if self._root_hwnd:
            try:
                ctypes.windll.user32.EnableWindow(self._root_hwnd, False)
            except Exception:
                pass

        def _on_dlg_unmap(e):
            if e.widget == self and self.wm_state() == "iconic":
                if self.parent and self.parent.winfo_exists() and self.parent.wm_state() != "iconic":
                    try:
                        self.parent.iconify()
                    except Exception:
                        pass

        def _on_dlg_map(e):
            if e.widget == self and self.wm_state() != "iconic":
                if self.parent and self.parent.winfo_exists() and self.parent.wm_state() == "iconic":
                    try:
                        self.parent.deiconify()
                    except Exception:
                        pass
                self.after(60, self._ensure_focus)

        self.bind("<Unmap>", _on_dlg_unmap, add="+")
        self.bind("<Map>", _on_dlg_map, add="+")

    def _ensure_focus(self):
        try:
            if self.winfo_exists() and self.wm_state() != "iconic":
                self.lift()
                self.focus_force()
        except Exception:
            pass

    def minimize_app(self):
        """Allows direct one-click minimization of both the dialog and main window."""
        if self.parent and self.parent.winfo_exists():
            try:
                self.parent.iconify()
            except Exception:
                pass
        try:
            self.iconify()
        except Exception:
            pass

    def destroy(self):
        """Re-enables the parent window in Win32 and cleans up references."""
        if self._root_hwnd:
            try:
                ctypes.windll.user32.EnableWindow(self._root_hwnd, True)
            except Exception:
                pass
        if self.parent and hasattr(self.parent, "_license_dialog_instance"):
            if self.parent._license_dialog_instance is self:
                self.parent._license_dialog_instance = None
        super().destroy()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()
        status = check_license_status()
        if status.get("state") == "licensed" and not getattr(self, "_force_input_mode", False):
            self._build_licensed_ui(status)
        else:
            self._build_activation_input_ui(status)

    def _build_licensed_ui(self, status: Dict[str, Any]):
        is_ar = self.is_ar
        hwid = status.get("hwid") or get_hardware_id()
        plan = status.get("plan", "LIFETIME")
        customer = status.get("customer", "Registered User")
        expires_at = float(status.get("expires_at", 0) or 0)
        rem_days = status.get("remaining_days", 9999)

        # Header Frame
        hdr_frame = tk.Frame(self, bg="#161b22", padx=20, pady=12)
        hdr_frame.pack(fill="x")

        top_hdr_row = tk.Frame(hdr_frame, bg="#161b22")
        top_hdr_row.pack(fill="x")

        lbl_title = tk.Label(
            top_hdr_row,
            text="👑 ClipCraft Studio Pro",
            font=("Segoe UI", 14, "bold"),
            fg="#e3b341",
            bg="#161b22",
        )
        lbl_title.pack(side="left")

        btn_min = ttk.Button(
            top_hdr_row,
            text="⬇️ تصغير النافذة" if is_ar else "⬇️ Minimize Window",
            command=self.minimize_app,
            style="Player.TButton",
        )
        btn_min.pack(side="right")

        lbl_sub = tk.Label(
            hdr_frame,
            text="✅ النسخة مرخصة ومفعلة رسمياً — كافة الميزات الاحترافية مفتوحة بالكامل" if is_ar else
                 "✅ Officially Licensed & Activated — All Pro features are unlocked",
            font=("Segoe UI", 9),
            fg="#3fb950",
            bg="#161b22",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        content_box = tk.Frame(self, bg="#0d1117", padx=20, pady=16)
        content_box.pack(fill="both", expand=True)

        # Verified License Certificate Card
        card = tk.Frame(content_box, bg="#161b22", padx=16, pady=14, highlightbackground="#3fb950", highlightthickness=1)
        card.pack(fill="both", expand=True, pady=(0, 12))

        # Status Badge Row
        badge_row = tk.Frame(card, bg="#161b22")
        badge_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            badge_row,
            text="💎 حالة الترخيص:" if is_ar else "💎 License Status:",
            font=("Segoe UI", 10, "bold"),
            fg="#8b949e",
            bg="#161b22",
        ).pack(side="left")

        tk.Label(
            badge_row,
            text="  نشط وموثق برمجياً (Active & Verified)  ",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#238636",
            padx=6,
            pady=2,
        ).pack(side="left", padx=(8, 0))

        # Details Grid
        details_frame = tk.Frame(card, bg="#161b22")
        details_frame.pack(fill="x", pady=(4, 8))

        def add_info_row(label_text, val_text, val_fg="#f0f6fc", is_code=False):
            r = tk.Frame(details_frame, bg="#161b22")
            r.pack(fill="x", pady=2)
            tk.Label(
                r,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                fg="#8b949e",
                bg="#161b22",
                width=18 if not is_ar else 14,
                anchor="e" if is_ar else "w",
            ).pack(side="right" if is_ar else "left")
            font_spec = ("Consolas", 10, "bold") if is_code else ("Segoe UI", 9, "bold")
            tk.Label(
                r,
                text=val_text,
                font=font_spec,
                fg=val_fg,
                bg="#161b22",
                anchor="w",
            ).pack(side="left" if not is_ar else "right", padx=(6, 6))

        val_duration = "مدى الحياة (Lifetime Access) — دائم" if is_ar else "Lifetime Access (Permanent)"
        if 0 < expires_at and rem_days < 9999:
            val_duration = f"متبقي {rem_days} يوم" if is_ar else f"{rem_days} days remaining"

        add_info_row("خطة الترخيص:" if is_ar else "Plan:", f"👑 {plan} EDITION", "#e3b341")
        add_info_row("المرخص له:" if is_ar else "Licensed To:", customer, "#58a6ff")
        add_info_row("مدة الصلاحية:" if is_ar else "Validity:", val_duration, "#3fb950")
        add_info_row("كود الجهاز (HWID):" if is_ar else "Hardware ID:", hwid, "#f0f6fc", is_code=True)
        add_info_row("التوثيق الرقمي:" if is_ar else "Security:", "RSA-2048 Asymmetric Signature", "#8b949e")

        # Copy HWID Shortcut button inside card
        btn_c_hwid = ttk.Button(
            card,
            text="📋 نسخ كود الجهاز (Copy HWID)" if is_ar else "📋 Copy Hardware ID",
            command=self._copy_hwid,
            style="Player.TButton",
        )
        btn_c_hwid.pack(anchor="e", pady=(4, 0))

        # Status & Message Label
        self.lbl_msg = tk.Label(
            content_box,
            text="",
            font=("Segoe UI", 9, "bold"),
            fg="#3fb950",
            bg="#0d1117",
        )
        self.lbl_msg.pack(fill="x", pady=(0, 8))

        # Bottom Button Row
        btn_row = tk.Frame(content_box, bg="#0d1117")
        btn_row.pack(fill="x")

        def _switch_to_input():
            self._force_input_mode = True
            self._build_ui()

        btn_change_key = ttk.Button(
            btn_row,
            text="🔄 تغيير مفتاح الترخيص" if is_ar else "🔄 Change License Key",
            command=_switch_to_input,
            style="Player.TButton",
        )
        btn_change_key.pack(side="left")

        btn_close = ttk.Button(
            btn_row,
            text="✔️ تم (إغلاق)" if is_ar else "✔️ Done (Close)",
            command=self.destroy,
            style="Action.TButton",
            width=14,
        )
        btn_close.pack(side="right")

    def _build_activation_input_ui(self, status: Dict[str, Any]):
        hwid = get_hardware_id()
        is_ar = self.is_ar

        # Header Frame
        hdr_frame = tk.Frame(self, bg="#161b22", padx=20, pady=12)
        hdr_frame.pack(fill="x")

        top_hdr_row = tk.Frame(hdr_frame, bg="#161b22")
        top_hdr_row.pack(fill="x")

        lbl_title = tk.Label(
            top_hdr_row,
            text="🎬 ClipCraft Studio Pro",
            font=("Segoe UI", 14, "bold"),
            fg="#58a6ff",
            bg="#161b22",
        )
        lbl_title.pack(side="left")

        btn_min = ttk.Button(
            top_hdr_row,
            text="⬇️ تصغير النافذة" if is_ar else "⬇️ Minimize Window",
            command=self.minimize_app,
            style="Player.TButton",
        )
        btn_min.pack(side="right")

        if self.is_expired:
            sub_text = "انتهت فترة التجربة المجانية — يرجى إدخال مفتاح التفعيل للمتابعة" if is_ar else "Trial period expired — Please enter your activation key to continue"
            sub_fg = "#f85149"
        else:
            sub_text = "إدارة ترخيص وتفعيل البرنامج المرتبط بالجهاز" if is_ar else "Node-Locked Machine License & Activation"
            sub_fg = "#8b949e"

        lbl_sub = tk.Label(
            hdr_frame,
            text=sub_text,
            font=("Segoe UI", 9),
            fg=sub_fg,
            bg="#161b22",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        content_box = tk.Frame(self, bg="#0d1117", padx=22, pady=16)
        content_box.pack(fill="both", expand=True)

        # Step 1: Hardware ID Box
        lbl_step1 = tk.Label(
            content_box,
            text="الخطوة 1: كود جهازك الفريد (Hardware ID):" if is_ar else "Step 1: Your Unique Hardware ID (HWID):",
            font=("Segoe UI", 10, "bold"),
            fg="#f0f6fc",
            bg="#0d1117",
        )
        lbl_step1.pack(anchor="w", pady=(0, 6))

        hw_box = tk.Frame(content_box, bg="#21262d", padx=8, pady=8)
        hw_box.pack(fill="x", pady=(0, 8))

        self.ent_hwid = tk.Entry(
            hw_box,
            font=("Consolas", 12, "bold"),
            fg="#3fb950",
            bg="#161b22",
            relief="flat",
            justify="center",
        )
        self.ent_hwid.insert(0, hwid)
        self.ent_hwid.configure(state="readonly")
        self.ent_hwid.pack(side="left", fill="x", expand=True, padx=(4, 8))

        btn_copy = ttk.Button(
            hw_box,
            text="📋 نسخ الكود" if is_ar else "📋 Copy ID",
            command=self._copy_hwid,
            style="Player.TButton",
        )
        btn_copy.pack(side="right")

        # Developer Contact Box (Clean & Distinct)
        contact_frame = tk.Frame(content_box, bg="#161b22", padx=12, pady=8, highlightbackground="#30363d", highlightthickness=1)
        contact_frame.pack(fill="x", pady=(0, 14))

        lbl_contact_info = tk.Label(
            contact_frame,
            text="للحصول على مفتاح التفعيل، أرسل الكود إلى المطور:" if is_ar else "To receive your activation key, send your ID to the developer:",
            font=("Segoe UI", 9),
            fg="#8b949e",
            bg="#161b22",
        )
        lbl_contact_info.pack(anchor="w")

        email_row = tk.Frame(contact_frame, bg="#161b22")
        email_row.pack(fill="x", pady=(4, 0))

        lbl_email_val = tk.Label(
            email_row,
            text="📧 Elshazly.gsm@gmail.com",
            font=("Segoe UI", 9, "bold"),
            fg="#58a6ff",
            bg="#161b22",
        )
        lbl_email_val.pack(side="left")

        self.btn_copy_email = ttk.Button(
            email_row,
            text="نسخ الإيميل" if is_ar else "Copy Email",
            command=self._copy_email,
            style="Player.TButton",
        )
        self.btn_copy_email.pack(side="right")

        # Step 2: Key Input Box
        lbl_step2 = tk.Label(
            content_box,
            text="الخطوة 2: أدخل مفتاح التفعيل المستلم من المطور:" if is_ar else "Step 2: Enter Activation Key received from developer:",
            font=("Segoe UI", 10, "bold"),
            fg="#f0f6fc",
            bg="#0d1117",
        )
        lbl_step2.pack(anchor="w", pady=(0, 6))

        self.txt_key = tk.Text(
            content_box,
            height=4,
            font=("Consolas", 10),
            fg="#e6edf3",
            bg="#161b22",
            relief="solid",
            bd=1,
            highlightcolor="#58a6ff",
            wrap="char",
            padx=8,
            pady=6,
        )
        self.txt_key.pack(fill="x", pady=(0, 8))

        # Status & Message Label
        self.lbl_msg = tk.Label(
            content_box,
            text="",
            font=("Segoe UI", 9, "bold"),
            fg="#3fb950",
            bg="#0d1117",
        )
        self.lbl_msg.pack(fill="x", pady=(0, 8))

        # Action Buttons Row
        btn_row = tk.Frame(content_box, bg="#0d1117")
        btn_row.pack(fill="x")

        btn_act = ttk.Button(
            btn_row,
            text="🚀 تفعيل البرنامج الآن" if is_ar else "🚀 Activate ClipCraft Studio",
            command=self._do_activate,
            style="Action.TButton",
        )
        btn_act.pack(side="left", fill="x", expand=True, padx=(0, 8))

        if getattr(self, "_force_input_mode", False):
            def _back_to_card():
                self._force_input_mode = False
                self._build_ui()
            btn_back = ttk.Button(
                btn_row,
                text="⬅️ العودة للترخيص" if is_ar else "⬅️ Back",
                command=_back_to_card,
                style="Player.TButton",
            )
            btn_back.pack(side="right")
        elif not self.is_expired:
            btn_later = ttk.Button(
                btn_row,
                text="متابعة التجربة" if is_ar else "Continue Trial",
                command=self.destroy,
                style="Player.TButton",
            )
            btn_later.pack(side="right")
        else:
            btn_min_bot = ttk.Button(
                btn_row,
                text="⬇️ تصغير مؤقت" if is_ar else "⬇️ Minimize",
                command=self.minimize_app,
                style="Player.TButton",
            )
            btn_min_bot.pack(side="right")

    def _copy_hwid(self):
        hwid = get_hardware_id()
        self.clipboard_clear()
        self.clipboard_append(hwid)
        msg = "✅ تم نسخ كود الجهاز إلى الحافظة بنجاح!" if self.is_ar else "✅ Hardware ID copied to clipboard!"
        self.lbl_msg.configure(text=msg, fg="#3fb950")

    def _copy_email(self):
        self.clipboard_clear()
        self.clipboard_append("Elshazly.gsm@gmail.com")
        self.btn_copy_email.configure(text="تم النسخ!" if self.is_ar else "Copied!")
        self.after(2000, lambda: self.btn_copy_email.configure(text="نسخ الإيميل" if self.is_ar else "Copy Email"))

    def _do_activate(self):
        raw_key = self.txt_key.get("1.0", "end").strip()
        if not raw_key:
            msg = "⚠️ يرجى لصق كود التفعيل أولاً." if self.is_ar else "⚠️ Please paste activation key first."
            self.lbl_msg.configure(text=msg, fg="#d29922")
            return

        ok, msg = activate_license_key(raw_key)
        if ok:
            self.activated_ok = True
            succ_title = "ClipCraft Studio"
            succ_text = f"🎉 {msg}" if self.is_ar else f"🎉 ClipCraft Studio successfully activated!"
            messagebox.showinfo(succ_title, succ_text)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            err_text = f"❌ {msg}" if self.is_ar else f"❌ Invalid key: {msg}"
            self.lbl_msg.configure(text=err_text, fg="#f85149")

    def _on_close(self):
        try:
            if self.parent and hasattr(self.parent, "_license_dialog_instance"):
                if self.parent._license_dialog_instance is self:
                    self.parent._license_dialog_instance = None
        except Exception:
            pass

        if self.is_expired and not self.activated_ok:
            if self.master:
                try:
                    self.master.destroy()
                except Exception:
                    pass
            sys.exit(0)
        self.destroy()

