"""
XAPK Player - Self-contained Android Emulator
All files (QEMU, Android-x86, ADB) are bundled in the same folder.
No internet download needed - just run the EXE.
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


def get_app_dir():
    """Get the directory where the EXE is located"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# --- All paths relative to EXE location ---
APP_DIR = get_app_dir()
QEMU_EXE = os.path.join(APP_DIR, "qemu", "qemu-system-x86_64.exe")
if not os.path.isfile(QEMU_EXE):
    QEMU_EXE = os.path.join(APP_DIR, "qemu", "qemu-system-i386.exe")
QEMU_IMG_EXE = os.path.join(APP_DIR, "qemu", "qemu-img.exe")
QEMU_BIOS = os.path.join(APP_DIR, "qemu", "share")
ADB_EXE = os.path.join(APP_DIR, "platform-tools", "adb.exe")
ANDROID_ISO = os.path.join(APP_DIR, "android", "android-x86.iso")
ANDROID_KERNEL = os.path.join(APP_DIR, "android", "kernel")
ANDROID_INITRD = os.path.join(APP_DIR, "android", "initrd.img")
ANDROID_SYSTEM = os.path.join(APP_DIR, "android", "system.sfs")
DATA_DIR = os.path.join(APP_DIR, "data")
DATA_DISK = os.path.join(DATA_DIR, "userdata.qcow2")
EXTRACT_DIR = os.path.join(tempfile.gettempdir(), "xapk_extract")

# QEMU settings
QEMU_RAM = "2048"
QEMU_CORES = "2"
ADB_FWD_PORT = "5556"


class XAPKPlayer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XAPK Player")
        self.root.geometry("700x500")
        self.root.configure(bg="#0d1117")
        self.root.resizable(False, False)

        self.xapk_path = None
        self.manifest = None
        self.qemu_proc = None

        self._build_ui()
        self.root.after(300, self._check_files)

    def _build_ui(self):
        # Title
        tk.Label(
            self.root, text="▶ XAPK Player", font=("Segoe UI", 26, "bold"),
            fg="#58a6ff", bg="#0d1117"
        ).pack(pady=(20, 0))

        tk.Label(
            self.root, text="مشغل تطبيقات أندرويد - كل شيء مدمج",
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
        btn_frame.pack(pady=15)

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

        # Log
        self.log = tk.Label(
            self.root, text="", font=("Segoe UI", 10),
            fg="#3fb950", bg="#0d1117", wraplength=640, justify="center"
        )
        self.log.pack(pady=10)

        # Progress
        self.progress = ttk.Progressbar(self.root, mode='indeterminate', length=500)
        self.progress.pack(pady=5)

    def _check_files(self):
        """Check if all required files exist in the app folder"""
        has_android = os.path.isfile(ANDROID_ISO) or (os.path.isfile(ANDROID_KERNEL) and os.path.isfile(ANDROID_INITRD))
        checks = {
            "QEMU": os.path.isfile(QEMU_EXE),
            "ADB": os.path.isfile(ADB_EXE),
            "Android": has_android,
        }

        parts = []
        for name, ok in checks.items():
            parts.append(f"{'✅' if ok else '❌'} {name}")

        self.files_status.config(text="  |  ".join(parts))

        all_ok = all(checks.values())
        if not all_ok:
            if not has_android and os.path.isfile(QEMU_EXE):
                self._msg("📥 نظام أندرويد غير موجود - اضغط تحميل", "#e3b341")
                self.run_btn.config(text="📥 تحميل أندرويد", state="normal", command=self._download_android)
            else:
                self._msg("⚠️ ملفات ناقصة! تأكد من وجود مجلدات qemu و platform-tools و android", "#f85149")

        return all_ok

    def _download_android(self):
        """Download Android-x86 ISO on first run"""
        self.run_btn.config(state="disabled", text="⏳ جاري التحميل...")
        self.progress.start(10)

        def download():
            import urllib.request
            url = "https://downloads.sourceforge.net/project/android-x86/Release%209.0/android-x86_64-9.0-r2.iso"
            os.makedirs(os.path.dirname(ANDROID_ISO), exist_ok=True)
            
            try:
                self._msg("📥 جاري تحميل نظام أندرويد (~900 MB)...")
                
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                response = urllib.request.urlopen(req, timeout=600)
                total = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(ANDROID_ISO, 'wb') as f:
                    while True:
                        chunk = response.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = int(downloaded * 100 / total) if total else 0
                        mb = downloaded / (1024 * 1024)
                        self._msg(f"📥 تحميل: {mb:.0f} MB / {total/1024/1024:.0f} MB ({pct}%)")
                
                self._msg("✅ تم تحميل أندرويد بنجاح!")
                self.root.after(0, self._after_download)
                
            except Exception as e:
                self._msg(f"❌ فشل التحميل: {e}", "#f85149")
                if os.path.exists(ANDROID_ISO):
                    os.remove(ANDROID_ISO)
            finally:
                self.progress.stop()

        threading.Thread(target=download, daemon=True).start()

    def _after_download(self):
        """Called after Android download completes"""
        self.run_btn.config(text="🚀 تشغيل", command=self._start)
        self._check_files()
        if os.path.isfile(ANDROID_ISO):
            self.run_btn.config(state="normal")

    def _msg(self, text, color="#3fb950"):
        self.log.config(text=text, fg=color)
        self.root.update_idletasks()

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
            "-machine", "q35",
        ]

        # Add BIOS path if trimmed QEMU
        if os.path.isdir(QEMU_BIOS):
            cmd.extend(["-L", QEMU_BIOS])

        # Boot from extracted files or ISO
        if os.path.isfile(ANDROID_KERNEL) and os.path.isfile(ANDROID_INITRD):
            cmd.extend(["-kernel", ANDROID_KERNEL, "-initrd", ANDROID_INITRD])
            cmd.extend(["-append", "root=/dev/ram0 androidboot.selinux=permissive console=ttyS0 UVESA_MODE=1280x720"])
            if os.path.isfile(ANDROID_SYSTEM):
                cmd.extend(["-hdb", ANDROID_SYSTEM])
        elif os.path.isfile(ANDROID_ISO):
            cmd.extend(["-cdrom", ANDROID_ISO, "-boot", "d"])

        if os.path.isfile(DATA_DISK):
            cmd.extend(["-hda", DATA_DISK])

        # Check acceleration
        try:
            r = subprocess.run([QEMU_EXE, "-accel", "help"], capture_output=True, text=True, timeout=5)
            out = r.stdout.lower()
            if "whpx" in out:
                cmd.extend(["-accel", "whpx"])
            elif "hax" in out:
                cmd.extend(["-accel", "hax"])
            else:
                cmd.extend(["-accel", "tcg"])
        except:
            cmd.extend(["-accel", "tcg"])

        self.qemu_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

            # Copy OBB
            if self.manifest:
                pkg = self.manifest.get('package_name', '')
                if pkg and os.path.exists(EXTRACT_DIR):
                    for root, _, files in os.walk(EXTRACT_DIR):
                        for f in files:
                            if f.endswith('.obb'):
                                rem = f"/sdcard/Android/obb/{pkg}/"
                                subprocess.run([ADB_EXE, "-s", target, "shell", "mkdir", "-p", rem], capture_output=True, timeout=5)
                                subprocess.run([ADB_EXE, "-s", target, "push", os.path.join(root, f), rem + f], capture_output=True, timeout=300)

            # Launch
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
