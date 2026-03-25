import tkinter as tk
from tkinter import messagebox, filedialog
import os

class GUIInstallerBuilder:
    def __init__(self, root):
        self.root = root
        self.root.title('Windows Installer Builder')
        self.root.geometry('400x300')

        # Language support
        self.language = 'Arabic'

        # Buttons
        self.create_buttons()

    def create_buttons(self):
        tk.Label(self.root, text='اختيار خطوة', font=('Arial', 14)).pack(pady=10)

        tk.Button(self.root, text='اختر مجلد المشروع', command=self.select_project_folder).pack(pady=10)
        tk.Button(self.root, text='إضافة ملفات', command=self.add_files).pack(pady=10)
        tk.Button(self.root, text='إعدادات التثبيت', command=self.setup_installation).pack(pady=10)
        tk.Button(self.root, text='بناء المثبت', command=self.build_installer).pack(pady=10)
        tk.Button(self.root, text='بناء تلقائي', command=self.auto_build).pack(pady=10)

    def select_project_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            messagebox.showinfo('معلومات', f'تم اختيار المجلد: {folder_path}')  

    def add_files(self):
        files = filedialog.askopenfilenames()
        if files:
            messagebox.showinfo('معلومات', f'تم إضافة الملفات: {files}') 

    def setup_installation(self):
        messagebox.showinfo('معلومات', 'إعدادات التثبيت المكتملة.') 

    def build_installer(self):
        messagebox.showinfo('معلومات', 'بدء عملية بناء المثبت...') 
        # Here you would integrate the build process

    def auto_build(self):
        messagebox.showinfo('معلومات', 'بدء البناء التلقائي...') 
        # Here you would implement the automatic build process

if __name__ == '__main__':
    root = tk.Tk()
    gui = GUIInstallerBuilder(root)
    root.mainloop()