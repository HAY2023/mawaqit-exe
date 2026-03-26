"""
XAPK Player - Lightweight XAPK Launcher for Windows
Extracts XAPK files and installs/launches APKs via ADB on WSA or emulator.
"""
import os
import sys
import json
import zipfile
import shutil
import subprocess
import threading
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
import urllib.request

# --- Config ---
ADB_DIR = os.path.join(os.path.expanduser("~"), ".xapk_player", "platform-tools")
ADB_EXE = os.path.join(ADB_DIR, "adb.exe")
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
EXTRACT_DIR = os.path.join(tempfile.gettempdir(), "xapk_player_temp")


def resource_path(relative_path):
    """Get absolute path to resource (works for PyInstaller)"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class XAPKPlayer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XAPK Player")
        self.root.geometry("700x500")
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
        title.pack(pady=(30, 5))

        subtitle = tk.Label(
            self.root, text="مشغل تطبيقات XAPK خفيف لنظام ويندوز",
            font=("Segoe UI", 12), fg="#8888aa", bg="#1a1a2e"
        )
        subtitle.pack(pady=(0, 20))

        # Drop zone frame
        self.drop_frame = tk.Frame(
            self.root, bg="#16213e", highlightbackground="#e94560",
            highlightthickness=2, cursor="hand2"
        )
        self.drop_frame.pack(padx=40, pady=10, fill="x", ipady=30)

        self.file_label = tk.Label(
            self.drop_frame, text="📂  اضغط هنا لاختيار ملف XAPK",
            font=("Segoe UI", 14), fg="#ccccdd", bg="#16213e", cursor="hand2"
        )
        self.file_label.pack(pady=20)
        self.file_label.bind("<Button-1>", self._pick_file)
        self.drop_frame.bind("<Button-1>", self._pick_file)

        # App info
        self.info_label = tk.Label(
            self.root, text="", font=("Segoe UI", 11),
            fg="#8888aa", bg="#1a1a2e", justify="right"
        )
        self.info_label.pack(pady=10)

        # Status
        self.status_label = tk.Label(
            self.root, text="", font=("Segoe UI", 10),
            fg="#44bb77", bg="#1a1a2e", wraplength=600
        )
        self.status_label.pack(pady=5)

        # Buttons frame
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=15)

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
            self.root, text="يتطلب WSA أو محاكي أندرويد متصل عبر ADB",
            font=("Segoe UI", 9), fg="#555566", bg="#1a1a2e"
        )
        footer.pack(side="bottom", pady=10)

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
                self.info_label.config(text=f"📱 ملف APK مباشر")
                self.manifest = {"package_name": "direct_apk"}
        except Exception as e:
            self.info_label.config(text=f"⚠️ لا يمكن قراءة البيانات: {e}")

        self.install_btn.config(state="normal")
        self.extract_btn.config(state="normal")

    def _set_status(self, text, color="#44bb77"):
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def _ensure_adb(self):
        """Download ADB if not present"""
        if os.path.isfile(ADB_EXE):
            return True

        self._set_status("⏳ جاري تحميل ADB...", "#ffaa00")
        try:
            os.makedirs(os.path.dirname(ADB_DIR), exist_ok=True)
            zip_path = os.path.join(tempfile.gettempdir(), "platform-tools.zip")
            urllib.request.urlretrieve(ADB_URL, zip_path)

            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(os.path.dirname(ADB_DIR))

            os.remove(zip_path)
            self._set_status("✅ تم تحميل ADB بنجاح")
            return True
        except Exception as e:
            self._set_status(f"❌ فشل تحميل ADB: {e}", "#ff4444")
            return False

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
            for name in z.namelist():
                if name.endswith('.apk'):
                    z.extract(name, EXTRACT_DIR)
                    apk_files.append(os.path.join(EXTRACT_DIR, name))
                elif name.endswith('.obb'):
                    z.extract(name, EXTRACT_DIR)

        self._set_status(f"✅ تم استخراج {len(apk_files)} ملف APK")
        return apk_files

    def _install_apks(self, apk_files):
        """Install APKs via ADB"""
        if not self._ensure_adb():
            return False

        self._set_status("🔌 جاري الاتصال بـ ADB...")

        # Try WSA first
        try:
            subprocess.run(
                [ADB_EXE, "connect", "127.0.0.1:58526"],
                capture_output=True, timeout=5
            )
        except:
            pass

        # Check device connection
        result = subprocess.run(
            [ADB_EXE, "devices"], capture_output=True, text=True, timeout=10
        )

        lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip() and 'List' not in l]
        if not lines:
            self._set_status(
                "❌ لا يوجد جهاز متصل! شغّل WSA أو محاكي أندرويد أولاً",
                "#ff4444"
            )
            messagebox.showerror(
                "لا يوجد جهاز",
                "لم يتم العثور على جهاز أندرويد متصل.\n\n"
                "الحلول:\n"
                "1. شغّل Windows Subsystem for Android (WSA)\n"
                "2. أو شغّل محاكي أندرويد (BlueStacks, NoxPlayer...)\n"
                "3. أو اوصل هاتف أندرويد عبر USB مع تفعيل USB Debugging"
            )
            return False

        self._set_status(f"📱 جهاز متصل: {lines[0]}")

        # Install using install-multiple for split APKs
        if len(apk_files) > 1:
            self._set_status("⚡ جاري تثبيت التطبيق (split APKs)...")
            cmd = [ADB_EXE, "install-multiple", "-r"] + apk_files
        else:
            self._set_status("⚡ جاري تثبيت التطبيق...")
            cmd = [ADB_EXE, "install", "-r", apk_files[0]]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if "Success" in result.stdout:
            self._set_status("✅ تم تثبيت التطبيق بنجاح!")
            return True
        else:
            error = result.stderr or result.stdout
            self._set_status(f"❌ فشل التثبيت: {error}", "#ff4444")
            return False

    def _install_obb(self):
        """Copy OBB files to device"""
        if not self.manifest:
            return
        pkg = self.manifest.get('package_name', '')
        if not pkg:
            return

        obb_dir = os.path.join(EXTRACT_DIR)
        for root_dir, dirs, files in os.walk(obb_dir):
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
        self._set_status(f"✅ تم تشغيل التطبيق!", "#44bb77")

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
    # Auto-load XAPK if passed as argument
    app = XAPKPlayer()

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.xapk_path = sys.argv[1]
        app._pick_file.__func__(app)  # trigger UI update
        app.xapk_path = sys.argv[1]
        filename = os.path.basename(sys.argv[1])
        app.file_label.config(text=f"📄 {filename}", fg="#e94560")

    app.run()


if __name__ == '__main__':
    main()
