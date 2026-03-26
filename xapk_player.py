"""
XAPK Player - Self-contained Android Emulator + XAPK Launcher
Uses portable QEMU + Android-x86 to run Android apps on Windows.
Everything downloads automatically on first run.
"""
import os
import sys
import json
import zipfile
import shutil
import subprocess
import threading
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.request
import socket

# --- Paths ---
APP_DIR = os.path.join(os.path.expanduser("~"), ".xapk_player")
QEMU_DIR = os.path.join(APP_DIR, "qemu")
QEMU_EXE = os.path.join(QEMU_DIR, "qemu-system-x86_64.exe")
QEMU_IMG = os.path.join(QEMU_DIR, "qemu-img.exe")
ADB_DIR = os.path.join(APP_DIR, "platform-tools")
ADB_EXE = os.path.join(ADB_DIR, "adb.exe")
ANDROID_DIR = os.path.join(APP_DIR, "android")
ANDROID_ISO = os.path.join(ANDROID_DIR, "android-x86.iso")
DATA_DISK = os.path.join(ANDROID_DIR, "data.qcow2")
EXTRACT_DIR = os.path.join(tempfile.gettempdir(), "xapk_player_temp")

# --- Download URLs ---
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
# QEMU portable for Windows (from qemu.weilnetz.de - official Windows builds)
QEMU_URL = "https://qemu.weilnetz.de/w64/2024/qemu-w64-setup-20240903.exe"
# Android-x86 9.0-r2 (stable, lightweight)
ANDROID_URL = "https://sourceforge.net/projects/android-x86/files/Release%209.0/android-x86_64-9.0-r2.iso/download"

# QEMU settings
QEMU_RAM = "2048"  # MB
QEMU_CORES = "2"
ADB_PORT = "5555"
QEMU_ADB_FWD = "5556"


class DownloadProgress:
    """Track download progress"""
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, (downloaded / total_size) * 100)
            mb_done = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            self.callback(f"{mb_done:.0f}/{mb_total:.0f} MB ({percent:.0f}%)")
        else:
            mb_done = downloaded / (1024 * 1024)
            self.callback(f"{mb_done:.0f} MB...")


class XAPKPlayer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XAPK Player - مشغل تطبيقات أندرويد")
        self.root.geometry("750x600")
        self.root.configure(bg="#0d1117")
        self.root.resizable(False, False)

        self.xapk_path = None
        self.manifest = None
        self.qemu_process = None
        self.is_running = False

        self._build_ui()
        # Check setup status on start
        self.root.after(500, self._check_setup_status)

    def _build_ui(self):
        # --- Title ---
        header = tk.Frame(self.root, bg="#0d1117")
        header.pack(fill="x", padx=30, pady=(20, 5))

        tk.Label(
            header, text="▶ XAPK Player", font=("Segoe UI", 26, "bold"),
            fg="#58a6ff", bg="#0d1117"
        ).pack(side="left")

        # --- Status indicator ---
        self.status_dot = tk.Label(
            header, text="●", font=("Segoe UI", 14),
            fg="#f85149", bg="#0d1117"
        )
        self.status_dot.pack(side="right", padx=5)

        self.status_text = tk.Label(
            header, text="غير جاهز", font=("Segoe UI", 10),
            fg="#8b949e", bg="#0d1117"
        )
        self.status_text.pack(side="right")

        # --- Setup section ---
        setup_frame = tk.LabelFrame(
            self.root, text=" ⚙️ إعداد المحاكي ",
            font=("Segoe UI", 11, "bold"), fg="#c9d1d9", bg="#161b22",
            labelanchor="n"
        )
        setup_frame.pack(padx=30, pady=10, fill="x", ipady=10)

        self.setup_status = tk.Label(
            setup_frame, text="", font=("Segoe UI", 10),
            fg="#8b949e", bg="#161b22", wraplength=650, justify="right"
        )
        self.setup_status.pack(pady=5)

        self.progress = ttk.Progressbar(
            setup_frame, mode='indeterminate', length=600
        )
        self.progress.pack(pady=5, padx=20)

        self.setup_btn = tk.Button(
            setup_frame, text="⬇️ تحميل وتثبيت المحاكي", font=("Segoe UI", 12, "bold"),
            fg="white", bg="#238636", activebackground="#2ea043",
            border=0, padx=20, pady=8, cursor="hand2",
            command=self._run_setup
        )
        self.setup_btn.pack(pady=8)

        # --- File selection ---
        file_frame = tk.LabelFrame(
            self.root, text=" 📁 ملف التطبيق ",
            font=("Segoe UI", 11, "bold"), fg="#c9d1d9", bg="#161b22",
            labelanchor="n"
        )
        file_frame.pack(padx=30, pady=10, fill="x", ipady=10)

        self.file_label = tk.Label(
            file_frame, text="📂 اضغط لاختيار ملف XAPK أو APK",
            font=("Segoe UI", 13), fg="#58a6ff", bg="#161b22", cursor="hand2"
        )
        self.file_label.pack(pady=10)
        self.file_label.bind("<Button-1>", self._pick_file)

        self.info_label = tk.Label(
            file_frame, text="", font=("Segoe UI", 10),
            fg="#8b949e", bg="#161b22"
        )
        self.info_label.pack(pady=3)

        # --- Action buttons ---
        btn_frame = tk.Frame(self.root, bg="#0d1117")
        btn_frame.pack(pady=15)

        self.run_btn = tk.Button(
            btn_frame, text="🚀 تشغيل التطبيق", font=("Segoe UI", 14, "bold"),
            fg="white", bg="#1f6feb", activebackground="#388bfd",
            border=0, padx=35, pady=12, cursor="hand2",
            command=self._run_app, state="disabled"
        )
        self.run_btn.pack(side="left", padx=10)

        self.stop_btn = tk.Button(
            btn_frame, text="⏹ إيقاف المحاكي", font=("Segoe UI", 14, "bold"),
            fg="white", bg="#f85149", activebackground="#da3633",
            border=0, padx=35, pady=12, cursor="hand2",
            command=self._stop_emulator, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)

        # --- Log ---
        self.log_label = tk.Label(
            self.root, text="", font=("Segoe UI", 10),
            fg="#3fb950", bg="#0d1117", wraplength=680, justify="right"
        )
        self.log_label.pack(pady=5)

        # Footer
        tk.Label(
            self.root,
            text="XAPK Player v1.0 - محاكي أندرويد مدمج خفيف",
            font=("Segoe UI", 9), fg="#484f58", bg="#0d1117"
        ).pack(side="bottom", pady=8)

    # ===== Setup Check =====
    def _check_setup_status(self):
        has_qemu = os.path.isfile(QEMU_EXE)
        has_adb = os.path.isfile(ADB_EXE)
        has_android = os.path.isfile(ANDROID_ISO)

        parts = []
        if has_qemu:
            parts.append("✅ QEMU")
        else:
            parts.append("❌ QEMU")
        if has_adb:
            parts.append("✅ ADB")
        else:
            parts.append("❌ ADB")
        if has_android:
            parts.append("✅ Android")
        else:
            parts.append("❌ Android")

        self.setup_status.config(text="  |  ".join(parts))

        if has_qemu and has_adb and has_android:
            self.status_dot.config(fg="#3fb950")
            self.status_text.config(text="جاهز ✓")
            self.setup_btn.config(text="✅ المحاكي جاهز", state="disabled", bg="#21262d")
            if self.xapk_path:
                self.run_btn.config(state="normal")
        else:
            self.status_dot.config(fg="#f85149")
            self.status_text.config(text="يحتاج إعداد")

    # ===== Downloads =====
    def _log(self, text, color="#3fb950"):
        self.log_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def _download_file(self, url, dest, name):
        """Download file with progress"""
        self._log(f"⬇️ جاري تحميل {name}...")

        def progress(info):
            self._log(f"⬇️ {name}: {info}")

        urllib.request.urlretrieve(url, dest, reporthook=DownloadProgress(progress))
        self._log(f"✅ تم تحميل {name}")

    def _setup_adb(self):
        """Download ADB platform-tools"""
        if os.path.isfile(ADB_EXE):
            return True
        self._log("⬇️ تحميل ADB...")
        os.makedirs(APP_DIR, exist_ok=True)
        zip_path = os.path.join(tempfile.gettempdir(), "platform-tools.zip")
        self._download_file(ADB_URL, zip_path, "ADB")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(APP_DIR)
        os.remove(zip_path)
        return os.path.isfile(ADB_EXE)

    def _setup_qemu(self):
        """Download portable QEMU"""
        if os.path.isfile(QEMU_EXE):
            return True

        self._log("⬇️ تحميل QEMU (محاكي)...")
        os.makedirs(QEMU_DIR, exist_ok=True)

        # Download QEMU installer
        installer_path = os.path.join(tempfile.gettempdir(), "qemu-setup.exe")
        self._download_file(QEMU_URL, installer_path, "QEMU")

        # Extract QEMU silently to our directory
        self._log("📦 جاري تثبيت QEMU...")
        subprocess.run(
            [installer_path, "/S", f"/D={QEMU_DIR}"],
            capture_output=True, timeout=120
        )

        # If silent install didn't work, try 7z extraction
        if not os.path.isfile(QEMU_EXE):
            # Try running installer normally
            self._log("⚡ جاري تثبيت QEMU (قد تظهر نافذة التثبيت)...")
            proc = subprocess.Popen([installer_path])
            proc.wait()

        os.remove(installer_path) if os.path.isfile(installer_path) else None
        return os.path.isfile(QEMU_EXE)

    def _setup_android(self):
        """Download Android-x86 ISO"""
        if os.path.isfile(ANDROID_ISO):
            return True

        self._log("⬇️ تحميل Android-x86 (نظام أندرويد)... ~900 MB")
        os.makedirs(ANDROID_DIR, exist_ok=True)
        self._download_file(ANDROID_URL, ANDROID_ISO, "Android-x86")

        # Create data disk for app installation persistence
        if os.path.isfile(QEMU_IMG) and not os.path.isfile(DATA_DISK):
            self._log("📀 إنشاء قرص البيانات...")
            subprocess.run(
                [QEMU_IMG, "create", "-f", "qcow2", DATA_DISK, "8G"],
                capture_output=True
            )

        return os.path.isfile(ANDROID_ISO)

    def _run_setup(self):
        """Download and setup everything"""
        self.setup_btn.config(state="disabled")
        self.progress.start(10)

        def worker():
            try:
                # Step 1: ADB
                if not self._setup_adb():
                    self._log("❌ فشل تثبيت ADB", "#f85149")
                    return

                # Step 2: QEMU
                if not self._setup_qemu():
                    self._log("❌ فشل تثبيت QEMU", "#f85149")
                    return

                # Step 3: Android image
                if not self._setup_android():
                    self._log("❌ فشل تحميل Android", "#f85149")
                    return

                self._log("✅ تم إعداد كل شيء بنجاح! يمكنك الآن تشغيل التطبيقات")
                self.root.after(0, self._check_setup_status)

            except Exception as e:
                self._log(f"❌ خطأ: {e}", "#f85149")
            finally:
                self.progress.stop()
                self.root.after(0, lambda: self.setup_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    # ===== File Selection =====
    def _pick_file(self, event=None):
        path = filedialog.askopenfilename(
            title="اختر ملف XAPK أو APK",
            filetypes=[
                ("XAPK Files", "*.xapk"),
                ("APK Files", "*.apk"),
                ("All Files", "*.*")
            ]
        )
        if not path:
            return

        self.xapk_path = path
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        self.file_label.config(text=f"📄 {filename}")

        # Read manifest
        try:
            if path.endswith(".xapk"):
                with zipfile.ZipFile(path, 'r') as z:
                    if 'manifest.json' in z.namelist():
                        with z.open('manifest.json') as mf:
                            self.manifest = json.loads(mf.read().decode('utf-8'))
                            name = self.manifest.get('name', '')
                            pkg = self.manifest.get('package_name', '')
                            ver = self.manifest.get('version_name', '')
                            self.info_label.config(
                                text=f"📱 {name} | 📦 {pkg} | v{ver} | {size_mb:.0f} MB"
                            )
            elif path.endswith(".apk"):
                self.manifest = {"package_name": "unknown"}
                self.info_label.config(text=f"📱 APK | {size_mb:.0f} MB")
        except Exception as e:
            self.info_label.config(text=f"⚠️ {e}")

        # Enable run if setup is complete
        if os.path.isfile(QEMU_EXE) and os.path.isfile(ANDROID_ISO):
            self.run_btn.config(state="normal")

    # ===== Emulator Control =====
    def _start_emulator(self):
        """Boot Android-x86 in QEMU"""
        if self.qemu_process and self.qemu_process.poll() is None:
            self._log("⚡ المحاكي يعمل بالفعل")
            return True

        self._log("🚀 جاري تشغيل المحاكي...")

        cmd = [
            QEMU_EXE,
            "-m", QEMU_RAM,
            "-smp", QEMU_CORES,
            "-cdrom", ANDROID_ISO,
            "-boot", "d",
            "-net", "nic,model=virtio",
            "-net", f"user,hostfwd=tcp::{QEMU_ADB_FWD}-:{ADB_PORT}",
            "-display", "sdl",
            "-device", "virtio-vga",
            "-usb",
            "-device", "usb-tablet",
            "-machine", "q35",
        ]

        # Add data disk if exists
        if os.path.isfile(DATA_DISK):
            cmd.extend(["-hda", DATA_DISK])

        # Try hardware acceleration
        try:
            # Check if WHPX (Windows Hypervisor) is available
            result = subprocess.run(
                [QEMU_EXE, "-accel", "help"],
                capture_output=True, text=True, timeout=5
            )
            if "whpx" in result.stdout.lower():
                cmd.extend(["-accel", "whpx"])
                self._log("⚡ تسريع الأجهزة (WHPX) مفعّل")
            elif "hax" in result.stdout.lower():
                cmd.extend(["-accel", "hax"])
                self._log("⚡ تسريع الأجهزة (HAXM) مفعّل")
            else:
                cmd.extend(["-accel", "tcg"])
                self._log("⚠️ بدون تسريع - قد يكون بطيئاً", "#e3b341")
        except:
            cmd.extend(["-accel", "tcg"])

        self.qemu_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self.is_running = True
        self.stop_btn.config(state="normal")

        return True

    def _wait_for_boot(self, timeout=180):
        """Wait for Android to boot by trying ADB connection"""
        self._log("⏳ انتظار تشغيل أندرويد (قد يستغرق 1-3 دقائق)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.qemu_process and self.qemu_process.poll() is not None:
                self._log("❌ المحاكي توقف بشكل غير متوقع", "#f85149")
                return False

            try:
                # Try connecting ADB
                result = subprocess.run(
                    [ADB_EXE, "connect", f"127.0.0.1:{QEMU_ADB_FWD}"],
                    capture_output=True, text=True, timeout=5
                )
                if "connected" in result.stdout.lower():
                    # Check if boot completed
                    result = subprocess.run(
                        [ADB_EXE, "-s", f"127.0.0.1:{QEMU_ADB_FWD}",
                         "shell", "getprop", "sys.boot_completed"],
                        capture_output=True, text=True, timeout=5
                    )
                    if "1" in result.stdout.strip():
                        self._log("✅ أندرويد جاهز!")
                        return True
            except:
                pass

            elapsed = int(time.time() - start_time)
            self._log(f"⏳ انتظار التشغيل... {elapsed}/{timeout} ثانية")
            time.sleep(3)

        self._log("⚠️ انتهت مهلة الانتظار - جرّب يدوياً", "#e3b341")
        return False

    def _extract_and_install(self):
        """Extract XAPK and install via ADB"""
        adb_target = f"127.0.0.1:{QEMU_ADB_FWD}"

        if self.xapk_path.endswith(".apk"):
            apk_files = [self.xapk_path]
        else:
            # Extract XAPK
            self._log("📦 جاري استخراج XAPK...")
            if os.path.exists(EXTRACT_DIR):
                shutil.rmtree(EXTRACT_DIR)
            os.makedirs(EXTRACT_DIR, exist_ok=True)

            apk_files = []
            with zipfile.ZipFile(self.xapk_path, 'r') as z:
                for name in z.namelist():
                    if name.endswith('.apk'):
                        z.extract(name, EXTRACT_DIR)
                        apk_files.append(os.path.join(EXTRACT_DIR, name))
                    elif name.endswith('.obb'):
                        z.extract(name, EXTRACT_DIR)

        if not apk_files:
            self._log("❌ لم يتم العثور على ملفات APK", "#f85149")
            return False

        # Install APKs
        self._log(f"⚡ جاري تثبيت التطبيق ({len(apk_files)} ملف)...")

        if len(apk_files) > 1:
            cmd = [ADB_EXE, "-s", adb_target, "install-multiple", "-r"] + apk_files
        else:
            cmd = [ADB_EXE, "-s", adb_target, "install", "-r", apk_files[0]]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if "Success" in result.stdout:
            self._log("✅ تم تثبيت التطبيق بنجاح!")

            # Copy OBB files if present
            if self.manifest:
                pkg = self.manifest.get('package_name', '')
                if pkg:
                    for root_dir, dirs, files in os.walk(EXTRACT_DIR):
                        for f in files:
                            if f.endswith('.obb'):
                                obb_path = os.path.join(root_dir, f)
                                remote = f"/sdcard/Android/obb/{pkg}/"
                                subprocess.run(
                                    [ADB_EXE, "-s", adb_target, "shell", "mkdir", "-p", remote],
                                    capture_output=True, timeout=10
                                )
                                self._log(f"📥 نسخ OBB: {f}")
                                subprocess.run(
                                    [ADB_EXE, "-s", adb_target, "push", obb_path, remote + f],
                                    capture_output=True, timeout=300
                                )

            # Launch app
            if self.manifest:
                pkg = self.manifest.get('package_name', '')
                if pkg and pkg != "unknown":
                    self._log(f"🚀 جاري تشغيل {pkg}...")
                    subprocess.run(
                        [ADB_EXE, "-s", adb_target, "shell", "monkey",
                         "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
                        capture_output=True, timeout=10
                    )
                    self._log("✅ التطبيق يعمل الآن في نافذة المحاكي!", "#3fb950")

            return True
        else:
            error = (result.stderr or result.stdout)[:200]
            self._log(f"❌ فشل التثبيت: {error}", "#f85149")
            return False

    def _run_app(self):
        """Main flow: start emulator, wait for boot, install and run"""
        self.run_btn.config(state="disabled")

        def worker():
            try:
                if not self._start_emulator():
                    return

                if not self._wait_for_boot():
                    self._log("⚠️ اختر 'Run with internal data' من قائمة GRUB في نافذة المحاكي", "#e3b341")
                    # Give more time after user selects boot option
                    self._wait_for_boot(timeout=120)

                self._extract_and_install()

            except Exception as e:
                self._log(f"❌ خطأ: {e}", "#f85149")
            finally:
                self.root.after(0, lambda: self.run_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _stop_emulator(self):
        """Stop the QEMU emulator"""
        if self.qemu_process:
            self.qemu_process.terminate()
            self.qemu_process = None
            self.is_running = False
            self.stop_btn.config(state="disabled")
            self._log("⏹ تم إيقاف المحاكي")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._stop_emulator()
        try:
            subprocess.run([ADB_EXE, "kill-server"], capture_output=True, timeout=3)
        except:
            pass
        self.root.destroy()


def main():
    app = XAPKPlayer()

    # Auto-load file from argument
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.xapk_path = sys.argv[1]
        filename = os.path.basename(sys.argv[1])
        app.file_label.config(text=f"📄 {filename}")
        if os.path.isfile(QEMU_EXE) and os.path.isfile(ANDROID_ISO):
            app.run_btn.config(state="normal")

    app.run()


if __name__ == '__main__':
    main()
