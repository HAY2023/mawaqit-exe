"""
XAPK Player - Smart Android Emulator
Online mode: works immediately with internet
Offline mode: downloads heavy files from MAWAQIT Files Server
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
from tkinter import filedialog, ttk


# === Server API URL ===
FILES_API = "https://25016447-75a3-4e29-91b0-333910529c51.lovableproject.com/api/files"


def get_app_dir():
    """Get the directory where the EXE is located"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# --- All paths relative to EXE location ---
APP_DIR = get_app_dir()
QEMU_DIR = os.path.join(APP_DIR, "qemu")
QEMU_EXE = os.path.join(QEMU_DIR, "qemu-system-x86_64.exe")
if not os.path.isfile(QEMU_EXE):
    QEMU_EXE = os.path.join(QEMU_DIR, "qemu-system-i386.exe")
QEMU_IMG_EXE = os.path.join(QEMU_DIR, "qemu-img.exe")
QEMU_BIOS = os.path.join(QEMU_DIR, "share")
ADB_DIR = os.path.join(APP_DIR, "platform-tools")
ADB_EXE = os.path.join(ADB_DIR, "adb.exe")
ANDROID_DIR = os.path.join(APP_DIR, "android")
ANDROID_ISO = os.path.join(ANDROID_DIR, "android-x86.iso")
ANDROID_KERNEL = os.path.join(ANDROID_DIR, "kernel")
ANDROID_INITRD = os.path.join(ANDROID_DIR, "initrd.img")
ANDROID_SYSTEM_IMG = os.path.join(ANDROID_DIR, "system.img")
ANDROID_SYSTEM_SFS = os.path.join(ANDROID_DIR, "system.sfs")

DATA_DIR = os.path.join(APP_DIR, "data")
DATA_DISK = os.path.join(DATA_DIR, "userdata.qcow2")
EXTRACT_DIR = os.path.join(tempfile.gettempdir(), "xapk_extract")

# QEMU settings
QEMU_RAM = "2048"
QEMU_CORES = "2"
ADB_FWD_PORT = "5556"

# Map server file names to local extraction directories
FILE_EXTRACT_MAP = {
    "qemu.zip": QEMU_DIR,
    "android-lite.zip": ANDROID_DIR,
    "adb.zip": ADB_DIR,
}


class XAPKPlayer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MAWAQIT Player")
        self.root.geometry("700x520")
        self.root.configure(bg="#0d1117")
        self.root.resizable(False, False)

        self.xapk_path = None
        self.manifest = None
        self.qemu_proc = None
        self.downloading = False

        self._build_ui()
        self.root.after(300, self._check_files)

    def _build_ui(self):
        # Title
        tk.Label(
            self.root, text="🕌 MAWAQIT Player", font=("Segoe UI", 26, "bold"),
            fg="#58a6ff", bg="#0d1117"
        ).pack(pady=(20, 0))

        tk.Label(
            self.root, text="مشغل أوقات الصلاة - يعمل أونلاين وأوفلاين",
            font=("Segoe UI", 11), fg="#8b949e", bg="#0d1117"
        ).pack(pady=(0, 10))

        # Status
        self.status_frame = tk.Frame(self.root, bg="#161b22")
        self.status_frame.pack(padx=30, fill="x", ipady=8)

        self.files_status = tk.Label(
            self.status_frame, text="", font=("Segoe UI", 10),
            fg="#8b949e", bg="#161b22"
        )
        self.files_status.pack(pady=5)

        # File picker
        file_frame = tk.Frame(self.root, bg="#161b22", highlightbackground="#30363d", highlightthickness=1)
        file_frame.pack(padx=30, pady=15, fill="x", ipady=15)

        self.file_label = tk.Label(
            file_frame, text="📂 اضغط لاختيار ملف XAPK أو APK",
            font=("Segoe UI", 14), fg="#58a6ff", bg="#161b22", cursor="hand2"
        )
        self.file_label.pack(pady=8)
        self.file_label.bind("<Button-1>", self._pick_file)
        file_frame.bind("<Button-1>", self._pick_file)

        self.info_label = tk.Label(
            file_frame, text="", font=("Segoe UI", 10),
            fg="#8b949e", bg="#161b22"
        )
        self.info_label.pack()

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#0d1117")
        btn_frame.pack(pady=10)

        self.run_btn = tk.Button(
            btn_frame, text="🚀 تشغيل", font=("Segoe UI", 15, "bold"),
            fg="white", bg="#238636", activebackground="#2ea043",
            border=0, padx=40, pady=12, cursor="hand2",
            command=self._start, state="disabled"
        )
        self.run_btn.pack(side="left", padx=8)

        self.stop_btn = tk.Button(
            btn_frame, text="⏹ إيقاف", font=("Segoe UI", 15, "bold"),
            fg="white", bg="#f85149", activebackground="#da3633",
            border=0, padx=40, pady=12, cursor="hand2",
            command=self._stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=8)

        # Download button (for offline files)
        self.dl_btn = tk.Button(
            self.root, text="📥 تحميل ملفات الأوفلاين من السيرفر",
            font=("Segoe UI", 12, "bold"),
            fg="white", bg="#5B2D8E", activebackground="#7B3DBE",
            border=0, padx=30, pady=10, cursor="hand2",
            command=self._download_from_server
        )

        # Log
        self.log = tk.Label(
            self.root, text="", font=("Segoe UI", 10),
            fg="#3fb950", bg="#0d1117", wraplength=640, justify="center"
        )
        self.log.pack(pady=8)

        # Progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("purple.Horizontal.TProgressbar",
                        troughcolor='#161b22', background='#5B2D8E')

        self.progress = ttk.Progressbar(
            self.root, mode='determinate', length=500,
            style="purple.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=5)

        self.progress_label = tk.Label(
            self.root, text="", font=("Segoe UI", 9),
            fg="#8b949e", bg="#0d1117"
        )
        self.progress_label.pack()

    def _check_files(self):
        """Check if all required files exist in the app folder"""
        has_qemu = os.path.isfile(QEMU_EXE)
        has_adb = os.path.isfile(ADB_EXE)
        has_android = os.path.isfile(ANDROID_ISO) or (
            os.path.isfile(ANDROID_KERNEL) and
            (os.path.isfile(ANDROID_SYSTEM_SFS) or os.path.isfile(ANDROID_SYSTEM_IMG))
        )

        checks = {
            "QEMU": has_qemu,
            "ADB": has_adb,
            "Android": has_android,
        }

        parts = []
        for name, ok in checks.items():
            parts.append(f"{'✅' if ok else '❌'} {name}")

        self.files_status.config(text="  |  ".join(parts))

        all_ok = all(checks.values())
        missing = [k for k, v in checks.items() if not v]

        if not all_ok:
            self._msg(f"📥 ملفات ناقصة: {', '.join(missing)} - اضغط تحميل", "#e3b341")
            self.dl_btn.pack(pady=5)
        else:
            self._msg("✅ كل الملفات جاهزة - اختر XAPK وشغّل!", "#3fb950")
            self.dl_btn.pack_forget()

        return all_ok

    def _download_from_server(self):
        """Download all missing files from MAWAQIT Files Server"""
        if self.downloading:
            return
        self.downloading = True
        self.dl_btn.config(state="disabled", text="⏳ جاري التحميل...")
        self.run_btn.config(state="disabled")

        def download_work():
            import urllib.request

            try:
                # Step 1: Get file list from API
                self._msg("📡 الاتصال بسيرفر MAWAQIT...")
                req = urllib.request.Request(FILES_API, headers={"User-Agent": "MAWAQIT-Player/3.5"})
                response = urllib.request.urlopen(req, timeout=30)
                data = json.loads(response.read().decode('utf-8'))

                files = data.get("files", [])
                if not files:
                    self._msg("❌ لا توجد ملفات على السيرفر!", "#f85149")
                    return

                self._msg(f"📋 وجدت {len(files)} ملفات على السيرفر")

                # Step 2: Download each missing file
                for i, file_info in enumerate(files):
                    fname = file_info.get("name", "")
                    furl = file_info.get("url") or file_info.get("file_url", "")
                    fsize = file_info.get("size") or file_info.get("file_size", 0)
                    extract_dir = FILE_EXTRACT_MAP.get(fname)

                    if not furl or not extract_dir:
                        continue

                    # Skip if already exists
                    if fname == "qemu.zip" and os.path.isfile(QEMU_EXE):
                        continue
                    if fname == "android-lite.zip" and (
                        os.path.isfile(ANDROID_KERNEL) or os.path.isfile(ANDROID_ISO)
                    ):
                        continue
                    if fname == "adb.zip" and os.path.isfile(ADB_EXE):
                        continue

                    size_mb = fsize / (1024 * 1024) if fsize else 0
                    self._msg(f"📥 [{i+1}/{len(files)}] تحميل {fname} ({size_mb:.0f} MB)...")

                    # Download file
                    zip_path = os.path.join(APP_DIR, fname)
                    req = urllib.request.Request(furl, headers={"User-Agent": "MAWAQIT-Player/3.5"})
                    resp = urllib.request.urlopen(req, timeout=600)
                    total = int(resp.headers.get('Content-Length', fsize or 0))
                    downloaded = 0

                    with open(zip_path, 'wb') as f:
                        while True:
                            chunk = resp.read(1024 * 512)  # 512KB chunks
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                pct = int(downloaded * 100 / total)
                                mb_done = downloaded / (1024 * 1024)
                                mb_total = total / (1024 * 1024)
                                self.root.after(0, lambda p=pct: self.progress.configure(value=p))
                                self.root.after(0, lambda m=mb_done, t=mb_total, p=pct:
                                    self.progress_label.configure(
                                        text=f"{m:.1f} / {t:.1f} MB ({p}%)"
                                    ))

                    # Extract zip
                    self._msg(f"📦 فك ضغط {fname}...")
                    os.makedirs(extract_dir, exist_ok=True)
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as z:
                            z.extractall(extract_dir)
                    except Exception as e:
                        self._msg(f"⚠️ خطأ فك ضغط {fname}: {e}", "#e3b341")

                    # Clean up zip
                    try:
                        os.remove(zip_path)
                    except:
                        pass

                    self.root.after(0, lambda: self.progress.configure(value=0))
                    self.root.after(0, lambda: self.progress_label.configure(text=""))

                # Re-check files
                self._msg("✅ تم تحميل جميع الملفات بنجاح!", "#3fb950")
                self.root.after(0, self._after_download_complete)

            except Exception as e:
                self._msg(f"❌ خطأ: {e}", "#f85149")
            finally:
                self.downloading = False
                self.root.after(0, lambda: self.dl_btn.config(
                    state="normal", text="📥 تحميل ملفات الأوفلاين من السيرفر"
                ))

        threading.Thread(target=download_work, daemon=True).start()

    def _after_download_complete(self):
        """Called after all downloads complete"""
        # Re-find QEMU exe
        global QEMU_EXE
        qemu64 = os.path.join(QEMU_DIR, "qemu-system-x86_64.exe")
        qemu32 = os.path.join(QEMU_DIR, "qemu-system-i386.exe")
        if os.path.isfile(qemu64):
            QEMU_EXE = qemu64
        elif os.path.isfile(qemu32):
            QEMU_EXE = qemu32

        self._check_files()

    def _msg(self, text, color="#3fb950"):
        self.root.after(0, lambda: self.log.config(text=text, fg=color))

    def _pick_file(self, event=None):
        path = filedialog.askopenfilename(
            title="اختر ملف XAPK أو APK",
            filetypes=[("Android Apps", "*.xapk *.apk"), ("All", "*.*")]
        )
        if not path:
            return

        self.xapk_path = path
        name = os.path.basename(path)
        size = os.path.getsize(path) / (1024 * 1024)
        self.file_label.config(text=f"📄 {name}")

        try:
            if path.endswith(".xapk"):
                with zipfile.ZipFile(path, 'r') as z:
                    if 'manifest.json' in z.namelist():
                        with z.open('manifest.json') as f:
                            self.manifest = json.loads(f.read().decode('utf-8'))
                            app_name = self.manifest.get('name', '')
                            pkg = self.manifest.get('package_name', '')
                            ver = self.manifest.get('version_name', '')
                            self.info_label.config(text=f"📱 {app_name} | {pkg} | v{ver} | {size:.0f} MB")
            else:
                self.manifest = {"package_name": "unknown"}
                self.info_label.config(text=f"📱 APK | {size:.0f} MB")
        except Exception as e:
            self.info_label.config(text=str(e))

        if self._check_files():
            self.run_btn.config(state="normal")

    def _create_data_disk(self):
        """Create persistent data disk on first run"""
        if os.path.isfile(DATA_DISK):
            return
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.isfile(QEMU_IMG_EXE):
            subprocess.run(
                [QEMU_IMG_EXE, "create", "-f", "qcow2", DATA_DISK, "8G"],
                capture_output=True
            )

    def _boot_android(self):
        """Start QEMU with Android-x86"""
        self._msg("🚀 جاري تشغيل المحاكي...")
        self._create_data_disk()

        cmd = [
            QEMU_EXE,
            "-m", QEMU_RAM,
            "-smp", QEMU_CORES,
            "-net", "nic,model=virtio",
            "-net", f"user,hostfwd=tcp::{ADB_FWD_PORT}-:5555",
            "-display", "sdl",
            "-device", "virtio-vga",
            "-usb", "-device", "usb-tablet",
        ]

        if os.path.isdir(QEMU_BIOS):
            cmd.extend(["-L", QEMU_BIOS])

        if os.path.isfile(ANDROID_KERNEL) and os.path.isfile(ANDROID_INITRD):
            cmd.extend(["-kernel", ANDROID_KERNEL, "-initrd", ANDROID_INITRD])
            cmd.extend(["-append", "root=/dev/ram0 androidboot.selinux=permissive SRC=/"])

            if os.path.isfile(ANDROID_SYSTEM_IMG):
                cmd.extend(["-drive", f"file={ANDROID_SYSTEM_IMG},format=raw,readonly=on"])
            elif os.path.isfile(ANDROID_SYSTEM_SFS):
                cmd.extend(["-drive", f"file={ANDROID_SYSTEM_SFS},format=raw,readonly=on"])
        elif os.path.isfile(ANDROID_ISO):
            cmd.extend(["-cdrom", ANDROID_ISO, "-boot", "d"])

        if os.path.isfile(DATA_DISK):
            cmd.extend(["-hdb", DATA_DISK])

        # Acceleration with fallback
        cmd.extend([
            "-machine", "q35",
            "-accel", "whpx,kernel-irqchip=off",
            "-accel", "tcg"
        ])

        try:
            self.qemu_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            self._msg(f"❌ خطأ QEMU: {e}", "#f85149")
            return

        self.stop_btn.config(state="normal")

    def _wait_boot(self, timeout=180):
        """Wait for Android to finish booting"""
        self._msg("⏳ انتظار تشغيل أندرويد...")
        t0 = time.time()
        target = f"127.0.0.1:{ADB_FWD_PORT}"

        while time.time() - t0 < timeout:
            if self.qemu_proc and self.qemu_proc.poll() is not None:
                self._msg("❌ المحاكي توقف", "#f85149")
                return False
            try:
                subprocess.run([ADB_EXE, "connect", target], capture_output=True, timeout=3)
                r = subprocess.run(
                    [ADB_EXE, "-s", target, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True, text=True, timeout=3
                )
                if "1" in r.stdout.strip():
                    self._msg("✅ أندرويد جاهز!")
                    return True
            except:
                pass
            sec = int(time.time() - t0)
            self._msg(f"⏳ انتظار... {sec}s")
            time.sleep(3)

        self._msg("⚠️ انتهت المهلة", "#e3b341")
        return False

    def _install_xapk(self):
        """Extract XAPK and install APKs"""
        target = f"127.0.0.1:{ADB_FWD_PORT}"

        if self.xapk_path.endswith(".apk"):
            apks = [self.xapk_path]
        else:
            self._msg("📦 استخراج XAPK...")
            if os.path.exists(EXTRACT_DIR):
                shutil.rmtree(EXTRACT_DIR)
            os.makedirs(EXTRACT_DIR)

            apks = []
            with zipfile.ZipFile(self.xapk_path, 'r') as z:
                for n in z.namelist():
                    if n.endswith('.apk'):
                        z.extract(n, EXTRACT_DIR)
                        apks.append(os.path.join(EXTRACT_DIR, n))
                    elif n.endswith('.obb'):
                        z.extract(n, EXTRACT_DIR)

        if not apks:
            self._msg("❌ لا يوجد APK", "#f85149")
            return False

        self._msg(f"⚡ تثبيت {len(apks)} ملف...")

        if len(apks) > 1:
            cmd = [ADB_EXE, "-s", target, "install-multiple", "-r"] + apks
        else:
            cmd = [ADB_EXE, "-s", target, "install", "-r", apks[0]]

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if "Success" in r.stdout:
            self._msg("✅ تم التثبيت!")

            if self.manifest:
                pkg = self.manifest.get('package_name', '')
                if pkg and os.path.exists(EXTRACT_DIR):
                    for root_dir, _, files_list in os.walk(EXTRACT_DIR):
                        for f in files_list:
                            if f.endswith('.obb'):
                                rem = f"/sdcard/Android/obb/{pkg}/"
                                subprocess.run([ADB_EXE, "-s", target, "shell", "mkdir", "-p", rem],
                                               capture_output=True, timeout=5)
                                subprocess.run([ADB_EXE, "-s", target, "push",
                                                os.path.join(root_dir, f), rem + f],
                                               capture_output=True, timeout=300)

            if self.manifest:
                pkg = self.manifest.get('package_name', '')
                if pkg and pkg != "unknown":
                    self._msg(f"🚀 تشغيل {pkg}...")
                    subprocess.run(
                        [ADB_EXE, "-s", target, "shell", "monkey", "-p", pkg,
                         "-c", "android.intent.category.LAUNCHER", "1"],
                        capture_output=True, timeout=10
                    )
                    self._msg("✅ التطبيق يعمل في نافذة المحاكي!")
            return True
        else:
            self._msg(f"❌ فشل: {(r.stderr or r.stdout)[:150]}", "#f85149")
            return False

    def _start(self):
        self.run_btn.config(state="disabled")
        self.progress.configure(mode='indeterminate')
        self.progress.start(10)

        def work():
            try:
                self._boot_android()
                if self._wait_boot():
                    self._install_xapk()
                else:
                    self._msg("⚠️ اختر 'Run without installation' من قائمة المحاكي", "#e3b341")
                    if self._wait_boot(120):
                        self._install_xapk()
            except Exception as e:
                self._msg(f"❌ {e}", "#f85149")
            finally:
                self.progress.stop()
                self.progress.configure(mode='determinate', value=0)
                self.root.after(0, lambda: self.run_btn.config(state="normal"))

        threading.Thread(target=work, daemon=True).start()

    def _stop(self):
        if self.qemu_proc:
            self.qemu_proc.terminate()
            self.qemu_proc = None
        self.stop_btn.config(state="disabled")
        self._msg("⏹ تم الإيقاف")
        try:
            subprocess.run([ADB_EXE, "kill-server"], capture_output=True, timeout=3)
        except:
            pass

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: (self._stop(), self.root.destroy()))
        self.root.mainloop()


if __name__ == '__main__':
    app = XAPKPlayer()

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.xapk_path = sys.argv[1]
        app.file_label.config(text=f"📄 {os.path.basename(sys.argv[1])}")
        if app._check_files():
            app.run_btn.config(state="normal")

    app.run()
