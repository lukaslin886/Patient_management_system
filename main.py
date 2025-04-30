import os
import sys
import tkinter as tk
from tkinter import messagebox

# Add the parent directory (TREST_PY) to sys.path
# This allows absolute imports from patient_management_system
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Use absolute imports relative to the parent directory (TREST_PY)
from patient_management_system.patient_app import PatientManagementSystem # Corrected class name
from patient_management_system.database import Database

if __name__ == "__main__":
    root = tk.Tk()
    root.title("登入")

    tk.Label(root, text="使用者名稱").grid(row=0, column=0)
    username_var = tk.StringVar()
    tk.Entry(root, textvariable=username_var).grid(row=0, column=1)

    tk.Label(root, text="密碼").grid(row=1, column=0)
    password_var = tk.StringVar()
    tk.Entry(root, textvariable=password_var, show="*").grid(row=1, column=1)

    def login():
        try:
            db = Database('patient_management_system/patient_database.db')
            username = username_var.get()
            password = password_var.get()

            if db.login_user(username, password):
                root.destroy()
                main_root = tk.Tk()
                # Correct class name and pass db instance
                app = PatientManagementSystem(main_root, db) # Pass both root and db
                main_root.mainloop()
            else:
                messagebox.showerror("錯誤", "使用者名稱或密碼錯誤")
                db.close()
        except Exception as e:
            messagebox.showerror("錯誤", f"登入過程中發生錯誤: {str(e)}")
            if 'db' in locals() and db:
                db.close()

    tk.Button(root, text="登入", command=login).grid(row=2, columnspan=2)
    root.mainloop()
