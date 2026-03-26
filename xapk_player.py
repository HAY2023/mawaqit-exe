"""
XAPK Player - Lightweight XAPK Launcher for Windows
Extracts XAPK files, auto-downloads emulator if needed, installs/launches APKs.
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
from tkinter import filedialog, messagebox
import urllib.request

# --- Config ---
APP_DIR = os.path.join(os.path.expanduser("~"), ".xapk_player")
ADB_DIR = os.path.join(APP_DIR, "platform-tools")
ADB_EXE = os.path.join(ADB_DIR, "adb.exe")
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
EXTRACT_DIR = os.path.join(tempfile.gettempdir(), "xapk_player_temp")
BLUESTACKS_URLS = [
    "https://cdn3.bluestacks.com/downloads/windows/nxt/installer/BlueStacksMicroInstaller_native.exe",
    "https://cdn3.bluestacks.com/downloads/windows/nxt/installer/BlueStacksFullInstaller_native.exe",
]
BLUESTACKS_INSTALLER = os.path.join(APP_DIR, "BlueStacks_installer.exe")

# Known emulator ADB ports
EMULATOR_PORTS = [
    ("WSA", "127.0.0.1:58526"),
    ("BlueStacks 5", "127.0.0.1:5555"),
    ("BlueStacks 4", "127.0.0.1:5565"),
    ("NoxPlayer", "127.0.0.1:62001"),
    ("MEmu", "127.0.0.1:21503"),
    ("LDPlayer", "127.0.0.1:5555"),
    ("LDPlayer 2", "127.0.0.1:5556"),
    ("Genymotion", "127.0.0.1:5557"),
]


class XAPKPlayer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XAPK Player")
        self.root.geometry("720x550")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        self.xapk_path = None
        self.manifest = None

        self._build_ui()

    def _build_ui(self):
        # Title
        title = tk.Label(
            self.root, text="⬡ XAPK Player", font=("Segoe UI", 28, "bold"),
            fg="#e94560", bg="#1a1a2e"
        )
        title.pack(pady=(25, 3))

        subtitle = tk.Label(
            self.root, text="مشغل تطبيقات XAPK خفيف لنظام ويندوز",
            font=("Segoe UI", 12), fg="#8888aa", bg="#1a1a2e"
        )
        subtitle.pack(pady=(0, 15))

        # Drop zone frame
        self.drop_frame = tk.Frame(
            self.root, bg="#16213e", highlightbackground="#e94560",
            highlightthickness=2, cursor="hand2"
        )
        self.drop_frame.pack(padx=40, pady=8, fill="x", ipady=25)

        self.file_label = tk.Label(
            self.drop_frame, text="📂  اضغط هنا لاختيار ملف XAPK",
            font=("Segoe UI", 14), fg="#ccccdd", bg="#16213e", cursor="hand2"
        )
        self.file_label.pack(pady=18)
        self.file_label.bind("<Button-1>", self._pick_file)
        self.drop_frame.bind("<Button-1>", self._pick_file)

        # App info
        self.info_label = tk.Label(
            self.root, text="", font=("Segoe UI", 11),
            fg="#8888aa", bg="#1a1a2e", justify="right"
        )
        self.info_label.pack(pady=8)

        # Progress bar (simple text-based)
        self.progress_label = tk.Label(
            self.root, text="", font=("Segoe UI", 10),
            fg="#ffaa00", bg="#1a1a2e", wraplength=620
        )
        self.progress_label.pack(pady=2)

        # Status
        self.status_label = tk.Label(
            self.root, text="", font=("Segoe UI", 10),
            fg="#44bb77", bg="#1a1a2e", wraplength=620
        )
        self.status_label.pack(pady=3)

        # Buttons frame
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=12)

        self.install_btn = tk.Button(
            btn_frame, text="⚡ تثبيت وتشغيل", font=("Segoe UI", 14, "bold"),
            fg="white", bg="#e94560", activebackground="#c73450",
            border=0, padx=30, pady=10, cursor="hand2",
            command=self._run_install, state="disabled"
        )
        self.install_btn.pack(side="left", padx=10)

        self.extract_btn = tk.Button(
            btn_frame, text="📦 استخراج فقط", font=("Segoe UI", 14, "bold"),
            fg="white", bg="#0f3460", activebackground="#0a2540",
            border=0, padx=30, pady=10, cursor="hand2",
            command=self._run_extract_only, state="disabled"
        )
        self.extract_btn.pack(side="left", padx=10)

        # Footer
        footer = tk.Label(
            self.root, text="سيتم تحميل المحاكي تلقائياً إذا لم يكن موجوداً",
            font=("Segoe UI", 9), fg="#555566", bg="#1a1a2e"
        )
        footer.pack(side="bottom", pady=8)

    def _pick_file(self, event=None):
        path = filedialog.askopenfilename(
            title="اختر ملف XAPK",
            filetypes=[("XAPK Files", "*.xapk"), ("APK Files", "*.apk"), ("All", "*.*")]
        )
        if not path:
            return

        self.xapk_path = path
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        self.file_label.config(text=f"📄 {filename}", fg="#e94560")
        self.status_label.config(text=f"حجم الملف: {size_mb:.1f} MB", fg="#44bb77")

        # Try to read manifest
        try:
            if path.endswith(".xapk"):
                with zipfile.ZipFile(path, 'r') as z:
                    if 'manifest.json' in z.namelist():
                        with z.open('manifest.json') as mf:
                            self.manifest = json.loads(mf.read().decode('utf-8'))
                            name = self.manifest.get('name', self.manifest.get('package_name', ''))
                            pkg = self.manifest.get('package_name', '')
                            ver = self.manifest.get('version_name', self.manifest.get('version_code', ''))
                            self.info_label.config(
                                text=f"📱 {name}\n📦 {pkg}\n🏷️ v{ver}"
                            )
            elif path.endswith(".apk"):
                self.info_label.config(text="📱 ملف APK مباشر")
                self.manifest = {"package_name": "direct_apk"}
        except Exception as e:
            self.info_label.config(text=f"⚠️ لا يمكن قراءة البيانات: {e}")

        self.install_btn.config(state="normal")
        self.extract_btn.config(state="normal")

    def _set_status(self, text, color="#44bb77"):
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def _set_progress(self, text, color="#ffaa00"):
        self.progress_label.config(text=text, fg=color)
        self.root.update_idletasks()

    # ---- ADB Management ----
    def _ensure_adb(self):
        """Download ADB if not present"""
        if os.path.isfile(ADB_EXE):
            return True

        self._set_status("⏳ جاري تحميل ADB...")
        try:
            os.makedirs(APP_DIR, exist_ok=True)
            zip_path = os.path.join(tempfile.gettempdir(), "platform-tools.zip")

            self._download_with_progress(ADB_URL, zip_path, "ADB")

            self._set_status("📦 جاري استخراج ADB...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(APP_DIR)
            os.remove(zip_path)

            self._set_status("✅ تم تحميل ADB بنجاح")
            self._set_progress("")
            return True
        except Exception as e:
            self._set_status(f"❌ فشل تحميل ADB: {e}", "#ff4444")
            return False

    # ---- Emulator Management ----
    def _check_emulator_running(self):
        """Check if any Android emulator is running and accessible via ADB"""
        if not os.path.isfile(ADB_EXE):
            return False

        for emu_name, addr in EMULATOR_PORTS:
            try:
                subprocess.run(
                    [ADB_EXE, "connect", addr],
                    capture_output=True, timeout=3
                )
            except:
                pass

        try:
            result = subprocess.run(
                [ADB_EXE, "devices"], capture_output=True, text=True, timeout=5
            )
            lines = [
                l.strip() for l in result.stdout.strip().split('\n')
                if l.strip() and 'List' not in l and 'offline' not in l
            ]
            return len(lines) > 0
        except:
            return False

    def _detect_installed_emulators(self):
        """Detect if BlueStacks or other emulators are installed"""
        paths_to_check = [
            (r"C:\Program Files\BlueStacks_nxt", "BlueStacks 5"),
            (r"C:\Program Files\BlueStacks", "BlueStacks 4"),
            (r"C:\Program Files (x86)\BlueStacks", "BlueStacks"),
            (r"C:\Program Files\Nox\bin", "NoxPlayer"),
            (r"C:\Program Files (x86)\Nox\bin", "NoxPlayer"),
            (r"C:\Program Files\Microvirt\MEmu", "MEmu"),
            (r"C:\LDPlayer\LDPlayer4.0", "LDPlayer"),
            (r"C:\LDPlayer\LDPlayer9", "LDPlayer 9"),
        ]
        found = []
        for path, name in paths_to_check:
            if os.path.isdir(path):
                found.append((name, path))
        return found

    def _try_start_bluestacks(self):
        """Try to start BlueStacks if installed"""
        bs_paths = [
            r"C:\Program Files\BlueStacks_nxt\HD-Player.exe",
            r"C:\Program Files\BlueStacks\HD-Player.exe",
            r"C:\Program Files (x86)\BlueStacks\HD-Player.exe",
        ]
        for p in bs_paths:
            if os.path.isfile(p):
                self._set_status("🚀 جاري تشغيل BlueStacks...", "#ffaa00")
                subprocess.Popen([p], shell=False)
                return True
        return False

    def _download_with_progress(self, url, dest, name=""):
        """Download a file with progress updates"""
        def report(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, (downloaded / total_size) * 100)
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                self._set_progress(
                    f"⬇️ تحميل {name}: {mb_done:.0f}/{mb_total:.0f} MB ({percent:.0f}%)"
                )
            else:
                mb_done = downloaded / (1024 * 1024)
                self._set_progress(f"⬇️ تحميل {name}: {mb_done:.0f} MB...")

        urllib.request.urlretrieve(url, dest, reporthook=report)
        self._set_progress("")

    def _download_and_install_bluestacks(self):
        """Download and install BlueStacks automatically"""
        self._set_status("⏳ جاري تحميل محاكي BlueStacks...", "#ffaa00")

        try:
            os.makedirs(APP_DIR, exist_ok=True)

            # Try each URL until one works
            downloaded = False
            for url in BLUESTACKS_URLS:
                try:
                    self._set_status(f"⬇️ جاري تحميل BlueStacks...", "#ffaa00")
                    self._download_with_progress(url, BLUESTACKS_INSTALLER, "BlueStacks")
                    downloaded = True
                    break
                except Exception:
                    continue

            if not downloaded:
                self._set_status("❌ فشل تحميل BlueStacks من جميع الروابط", "#ff4444")
                messagebox.showinfo(
                    "تحميل يدوي",
                    "لم نتمكن من تحميل BlueStacks تلقائياً.\n\n"
                    "يرجى تحميله يدوياً من:\nhttps://www.bluestacks.com/download.html\n\n"
                    "ثم أعد المحاولة."
                )
                return False

            self._set_status("⚡ جاري تثبيت BlueStacks (قد يستغرق بضع دقائق)...", "#ffaa00")
            self._set_progress("⏳ يرجى الانتظار حتى يكتمل التثبيت...")

            # Run installer
            proc = subprocess.Popen(
                [BLUESTACKS_INSTALLER],
                shell=False
            )
            proc.wait()

            self._set_progress("")
            self._set_status("✅ تم تثبيت BlueStacks! جاري التشغيل...")

            # Try to start BlueStacks
            self._try_start_bluestacks()

            # Wait for BlueStacks to boot
            self._set_status("⏳ جاري انتظار تشغيل BlueStacks...", "#ffaa00")
            for i in range(60):  # Wait up to 2 minutes
                time.sleep(2)
                self._set_progress(f"⏳ انتظار المحاكي... ({i*2}/120 ثانية)")
                if self._check_emulator_running():
                    self._set_progress("")
                    self._set_status("✅ BlueStacks جاهز!")
                    return True

            self._set_progress("")
            self._set_status("⚠️ يرجى تشغيل BlueStacks يدوياً ثم المحاولة مرة أخرى", "#ffaa00")
            return False

        except Exception as e:
            self._set_progress("")
            self._set_status(f"❌ فشل تحميل/تثبيت BlueStacks: {e}", "#ff4444")
            return False

    # ---- XAPK Operations ----
    def _extract_xapk(self):
        """Extract XAPK and return list of APK paths"""
        if os.path.exists(EXTRACT_DIR):
            shutil.rmtree(EXTRACT_DIR)
        os.makedirs(EXTRACT_DIR, exist_ok=True)

        if self.xapk_path.endswith(".apk"):
            return [self.xapk_path]

        self._set_status("📦 جاري استخراج XAPK...")

        apk_files = []
        with zipfile.ZipFile(self.xapk_path, 'r') as z:
            total = len(z.namelist())
            for i, name in enumerate(z.namelist()):
                if name.endswith('.apk'):
                    z.extract(name, EXTRACT_DIR)
                    apk_files.append(os.path.join(EXTRACT_DIR, name))
                elif name.endswith('.obb'):
                    z.extract(name, EXTRACT_DIR)
                self._set_progress(f"📦 استخراج: {i+1}/{total}")

        self._set_progress("")
        self._set_status(f"✅ تم استخراج {len(apk_files)} ملف APK")
        return apk_files

    def _install_apks(self, apk_files):
        """Install APKs via ADB (auto-downloads emulator if needed)"""
        if not self._ensure_adb():
            return False

        self._set_status("🔌 جاري البحث عن محاكي أندرويد...")

        # Try connecting to running emulators
        if not self._check_emulator_running():
            # No emulator running - check if one is installed
            installed = self._detect_installed_emulators()

            if installed:
                emu_name, emu_path = installed[0]
                self._set_status(f"🚀 تم العثور على {emu_name}، جاري التشغيل...", "#ffaa00")

                if "BlueStacks" in emu_name:
                    self._try_start_bluestacks()

                # Wait for emulator to boot
                self._set_status("⏳ جاري انتظار تشغيل المحاكي...", "#ffaa00")
                for i in range(60):
                    time.sleep(2)
                    self._set_progress(f"⏳ انتظار المحاكي... ({i*2}/120 ثانية)")
                    if self._check_emulator_running():
                        break
                self._set_progress("")

            if not self._check_emulator_running():
                # Still no emulator - ask to download
                result = messagebox.askyesno(
                    "لا يوجد محاكي أندرويد",
                    "لم يتم العثور على محاكي أندرويد.\n\n"
                    "هل تريد تحميل وتثبيت BlueStacks تلقائياً؟\n"
                    "(حجم التحميل ~10 MB مثبت صغير، سيحمّل الباقي تلقائياً)"
                )
                if result:
                    if not self._download_and_install_bluestacks():
                        return False
                else:
                    self._set_status("❌ تم الإلغاء - يحتاج محاكي أندرويد للعمل", "#ff4444")
                    return False

        # Final check
        if not self._check_emulator_running():
            self._set_status("❌ لا يوجد جهاز متصل!", "#ff4444")
            return False

        self._set_status("📱 متصل بالمحاكي ✓")

        # Install APKs
        if len(apk_files) > 1:
            self._set_status("⚡ جاري تثبيت التطبيق (split APKs)...")
            cmd = [ADB_EXE, "install-multiple", "-r"] + apk_files
        else:
            self._set_status("⚡ جاري تثبيت التطبيق...")
            cmd = [ADB_EXE, "install", "-r", apk_files[0]]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if "Success" in result.stdout:
            self._set_status("✅ تم تثبيت التطبيق بنجاح!")
            return True
        else:
            error = result.stderr or result.stdout
            self._set_status(f"❌ فشل التثبيت: {error[:200]}", "#ff4444")
            return False

    def _install_obb(self):
        """Copy OBB files to device"""
        if not self.manifest:
            return
        pkg = self.manifest.get('package_name', '')
        if not pkg:
            return

        for root_dir, dirs, files in os.walk(EXTRACT_DIR):
            for f in files:
                if f.endswith('.obb'):
                    obb_path = os.path.join(root_dir, f)
                    remote_path = f"/sdcard/Android/obb/{pkg}/"
                    self._set_status(f"📥 جاري نسخ OBB: {f}")
                    subprocess.run(
                        [ADB_EXE, "shell", "mkdir", "-p", remote_path],
                        capture_output=True, timeout=10
                    )
                    subprocess.run(
                        [ADB_EXE, "push", obb_path, remote_path + f],
                        capture_output=True, timeout=300
                    )

    def _launch_app(self):
        """Launch the installed app"""
        if not self.manifest:
            return
        pkg = self.manifest.get('package_name', '')
        if not pkg:
            return

        self._set_status(f"🚀 جاري تشغيل {pkg}...")
        subprocess.run(
            [ADB_EXE, "shell", "monkey", "-p", pkg, "-c",
             "android.intent.category.LAUNCHER", "1"],
            capture_output=True, timeout=10
        )
        self._set_status("✅ تم تشغيل التطبيق!", "#44bb77")

    # ---- Main Actions ----
    def _run_install(self):
        """Full install + launch flow in background thread"""
        self.install_btn.config(state="disabled")
        self.extract_btn.config(state="disabled")

        def worker():
            try:
                apk_files = self._extract_xapk()
                if not apk_files:
                    self._set_status("❌ لم يتم العثور على ملفات APK داخل XAPK", "#ff4444")
                    return
                if self._install_apks(apk_files):
                    self._install_obb()
                    self._launch_app()
            except Exception as e:
                self._set_status(f"❌ خطأ: {e}", "#ff4444")
            finally:
                self.install_btn.config(state="normal")
                self.extract_btn.config(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def _run_extract_only(self):
        """Extract XAPK to a chosen folder"""
        dest = filedialog.askdirectory(title="اختر مجلد الاستخراج")
        if not dest:
            return

        self._set_status("📦 جاري الاستخراج...")

        def worker():
            try:
                with zipfile.ZipFile(self.xapk_path, 'r') as z:
                    z.extractall(dest)
                self._set_status(f"✅ تم الاستخراج إلى: {dest}")
                os.startfile(dest)
            except Exception as e:
                self._set_status(f"❌ خطأ: {e}", "#ff4444")

        threading.Thread(target=worker, daemon=True).start()

    def run(self):
        self.root.mainloop()


def main():
    app = XAPKPlayer()

    # Auto-load XAPK if passed as argument
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.xapk_path = sys.argv[1]
        filename = os.path.basename(sys.argv[1])
        size_mb = os.path.getsize(sys.argv[1]) / (1024 * 1024)
        app.file_label.config(text=f"📄 {filename}", fg="#e94560")
        app.status_label.config(text=f"حجم الملف: {size_mb:.1f} MB", fg="#44bb77")
        app.install_btn.config(state="normal")
        app.extract_btn.config(state="normal")

    app.run()


if __name__ == '__main__':
    main()
