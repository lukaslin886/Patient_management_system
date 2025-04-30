import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ExifTags
import os
import re
import csv
from database import Database
import datetime

class PatientManagementSystem:
    def __init__(self, root, db):
        self.root = root
        self.root.title("病患資料管理系統")
        self.root.geometry("1200x800")
        self.db = db
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, fill="both", expand=True)
        
        # 啟動自動備份
        self.schedule_backup()

        self.frame1 = tk.Frame(self.notebook)
        self.frame3 = tk.Frame(self.notebook)

        self.notebook.add(self.frame1, text='新增病患資料')
        self.notebook.add(self.frame3, text='病患資料總覽')

        self.patient_info_frame()
        self.patient_overview_frame()

        # 初始載入資料
        self.refresh_overview()

    def patient_info_frame(self):
        # 病患資料輸入介面
        labels = ["姓名", "身分證字號", "性別", "聯絡方式", "出生日期", "地址", "部位＆尺寸", "負責人員"]
        self.vars = [tk.StringVar() for _ in range(8)]
        
        for i, text in enumerate(labels):
            tk.Label(self.frame1, text=text).grid(row=i, column=0)
            tk.Entry(self.frame1, textvariable=self.vars[i]).grid(row=i, column=1)

        tk.Button(self.frame1, text="新增病患", command=self.add_patient).grid(row=8, column=0)
        tk.Button(self.frame1, text="新增照片", command=self.add_photo_from_patient_info).grid(row=8, column=1)

    def add_patient(self):
        name = self.vars[0].get().strip()
        id_number = self.vars[1].get().strip()
        gender = self.vars[2].get().strip()
        contact_info = self.vars[3].get().strip()
        date_of_birth = self.vars[4].get().strip()
        address = self.vars[5].get().strip()
        medical_history = self.vars[6].get().strip()
        responsible_personnel = self.vars[7].get().strip()
        
        if not name or not id_number or not gender:
            messagebox.showerror("錯誤", "姓名、身分證字號和性別為必填欄位")
            return
            
        if not re.match(r'^[A-Z][12]\d{8}$', id_number):
            messagebox.showerror("錯誤", "身分證字號格式不正確")
            return
        
        # 聯絡方式驗證
        if contact_info and not re.match(r'^09\d{8}$', contact_info):
            messagebox.showerror("錯誤", "聯絡方式格式不正確，應為有效的手機號碼 (09開頭的10位數字)")
            return
        
        # 出生日期驗證
        if date_of_birth:
            try:
                datetime.datetime.strptime(date_of_birth, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("錯誤", "出生日期格式不正確，應為YYYY-MM-DD格式")
                return
        
        # 地址驗證
        if address and len(address) > 100:
            messagebox.showerror("錯誤", "地址過長，請輸入100字元以內的地址")
            return

        patient_id = self.db.add_patient(name, id_number, gender, contact_info, date_of_birth, address, medical_history, responsible_personnel)

        # 清除輸入欄位
        for var in self.vars:
            var.set("")
        self.vars[0].set(f"新增成功，病患ID: {patient_id}")
        # 刷新總覽頁面
        self.refresh_overview()

    def add_photo_from_patient_info(self):
        photo_path = filedialog.askopenfilename()
        if photo_path and self.vars[0].get().startswith("新增成功"):
            patient_id = self.vars[0].get().split(": ")[1]
            # 提取照片的 EXIF 日期
            capture_date = None
            try:
                img = Image.open(photo_path)
                exif_data = img._getexif()
                if exif_data:
                    for tag, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        if tag_name in ('DateTimeOriginal', 'DateTimeDigitized'):
                            try:
                                # 嘗試解析 EXIF 日期格式
                                dt_obj = datetime.datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                                capture_date = dt_obj.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                # 如果解析失敗，直接使用原始值
                                capture_date = value
                                break
            except Exception as e:
                print(f"無法提取 EXIF 日期: {e}")
            if os.path.exists(photo_path):
                self.db.add_photo(patient_id, photo_path, capture_date, 'clinical_photo')
                # 刷新總覽頁面
                self.refresh_overview()
            else:
                print(f"Invalid photo path: {photo_path}")

    def patient_overview_frame(self):
        """病患資料總覽頁面，顯示所有病患基本資料與最近照片"""
        # 創建可滾動容器
        self.canvas = tk.Canvas(self.frame3)
        self.scrollbar = ttk.Scrollbar(self.frame3, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # 設定滾動區域
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 搜尋區域
        top_frame = tk.Frame(self.frame3)
        top_frame.pack(fill="x", pady=10)

        # 搜尋區域
        search_frame = tk.Frame(top_frame)
        search_frame.pack(side="left", fill="y")

        tk.Button(search_frame, text="搜尋", command=self.search_overview).grid(row=2, column=0, columnspan=9, padx=5, pady=5)

        search_labels = ["病患ID", "姓名", "身分證字號", "性別", "聯絡方式", "出生日期", "地址", "部位＆尺寸", "負責人員"]
        self.overview_search_vars = [tk.StringVar() for _ in range(9)]

        search_frame_inner = tk.Frame(search_frame)
        search_frame_inner.grid(row=0, column=0, sticky="nsew")
        search_frame.grid_rowconfigure(0, weight=1)
        search_frame.grid_columnconfigure(0, weight=1)

        # 創建搜尋標籤和輸入框，使用網格佈局
        for i, text in enumerate(search_labels):
            tk.Label(search_frame_inner, text=text).grid(row=i, column=0, padx=2, pady=2)
            if i == 0:
                # 病患ID使用整數輸入
                entry = tk.Entry(search_frame_inner, textvariable=self.overview_search_vars[i], width=10)
            else:
                entry = tk.Entry(search_frame_inner, textvariable=self.overview_search_vars[i], width=15)
            entry.grid(row=i, column=1, padx=2, pady=2)

        button_frame = tk.Frame(top_frame)
        button_frame.pack(side="left", padx=5)

        def add_photo_overview():
            patient_id = self.overview_search_vars[0].get().strip()
            if not patient_id:
                messagebox.showerror("錯誤", "請輸入病患ID")
                return
            photo_path = filedialog.askopenfilename()
            capture_date = self.overview_search_vars[5].get() or None
            if photo_path and os.path.exists(photo_path):
                self.db.add_photo(patient_id, photo_path, capture_date, 'clinical_photo')
                self.refresh_overview()
            else:
                print(f"Invalid photo path: {photo_path}")

        tk.Button(button_frame, text="新增照片", command=add_photo_overview).pack(pady=5)
        tk.Button(button_frame, text="匯出資料", command=self.export_patient_data_overview).pack(pady=5)

        # 初始載入資料
        self.refresh_overview()

    def refresh_overview(self, search_params=None):
        """刷新總覽頁面資料"""
        # 清除現有內容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # 根據搜尋條件載入資料
        if search_params:
            patients = self.db.search_patients(**search_params)
        else:
            patients = self.db.get_all_patients()

        for idx, patient in enumerate(patients):
            patient_frame = ttk.Frame(self.scrollable_frame, padding=10)
            patient_frame.grid(row=idx, column=0, sticky="ew", pady=5)

            # 顯示基本資料
            headers = ["病患ID", "姓名", "身分證字號", "性別", "聯絡方式", "出生日期", "地址", "部位＆尺寸", "負責人員", "臨床照片"]
            for i, (header, value) in enumerate(zip(headers, patient)):
                ttk.Label(patient_frame, text=f"{header}: {value}").grid(row=0, column=i, padx=5)

            patient_id = patient[0]

            # 修改按鈕
            def view_and_update_patient(pid):
                patient = self.db.get_patient(pid)
                if not patient:
                    messagebox.showerror("錯誤", f"無法獲取病患ID {pid} 的資料")
                    return

                detail_win = tk.Toplevel(self.root)
                detail_win.title(f"病患 {patient[1]} 的詳情")

                print(f"Patient data: {patient}")

                # 顯示完整的病患數據結構，用於調試
                print(f"Patient data structure: {[type(item) for item in patient]}")
                print(f"Patient data length: {len(patient)}")

                # 修改欄位
                edit_frame = tk.Frame(detail_win)
                edit_frame.pack(fill="both", expand=True, padx=10, pady=10)

                edit_fields = ["姓名", "身分證字號", "性別", "聯絡方式", "出生日期", "地址", "部位＆尺寸", "負責人員"]

                # 確保病患數據結構正確
                if len(patient) < 9:
                    messagebox.showerror("錯誤", f"病患資料不完整，預期9個欄位，實際只有{len(patient)}個")
                    return

                # 正確初始化edit_vars
                edit_vars = []
                for i, field in enumerate(edit_fields):
                    # 索引從1開始，因為patient[0]是PatientID
                    value = patient[i + 1] if i + 1 < len(patient) and patient[i + 1] is not None else ""
                    edit_vars.append(tk.StringVar(value=value))

                # 顯示調試信息
                print(f"Edit vars values: {[var.get() for var in edit_vars]}")

                for i, text in enumerate(edit_fields):
                    tk.Label(edit_frame, text=text, font=('Arial', 10)).grid(row=i, column=0, padx=5, pady=5)
                    tk.Entry(edit_frame, textvariable=edit_vars[i], font=('Arial', 10), width=30).grid(row=i, column=1, padx=5, pady=5)

                def save_changes():
                    self.db.update_patient(
                        pid,
                        name=edit_vars[0].get(),
                        id_number=edit_vars[1].get(),
                        gender=edit_vars[2].get(),
                        contact_info=edit_vars[3].get(),
                        date_of_birth=edit_vars[4].get(),
                        address=edit_vars[5].get(),
                        medical_history=edit_vars[6].get(),
                        responsible_personnel=edit_vars[7].get()
                    )
                    self.refresh_overview()
                    detail_win.destroy()

                button_frame = tk.Frame(detail_win)
                button_frame.pack(fill="x", padx=10, pady=10)

                def add_photo_detail():
                    photo_path = filedialog.askopenfilename()
                    capture_date = edit_vars[4].get() or None
                    if photo_path and os.path.exists(photo_path):
                        self.db.add_photo(pid, photo_path, capture_date, 'clinical_photo')
                        # 刷新總覽頁面和詳情頁面照片
                        self.refresh_overview()
                        detail_win.destroy()
                        view_and_update_patient(pid)
                    else:
                        print(f"Invalid photo path: {photo_path}")

                tk.Button(button_frame, text="儲存變更", command=save_changes, font=('Arial', 10)).pack(side="left", fill="x", expand=True)
                tk.Button(button_frame, text="新增相片", command=add_photo_detail, font=('Arial', 10)).pack(side="left", fill="x", expand=True)

                # 顯示所有照片
                photos_frame = tk.Frame(detail_win)
                photos_frame.pack(fill="both", expand=True)

                photos = self.db.get_photos(pid)
                print(f"Photos: {photos}")

                if not photos:
                    tk.Label(photos_frame, text="此病患沒有照片記錄", font=('Arial', 10)).pack(pady=10)
                else:
                    row = 0
                    col = 0
                    for p_idx, photo in enumerate(photos):
                        try:
                            if not photo[2] or not os.path.exists(photo[2]):
                                print(f"照片路徑不存在: {photo[2]}")
                                continue

                            img = Image.open(photo[2])
                            img.thumbnail((100, 100))
                            photo_img = ImageTk.PhotoImage(img)
                            lbl = tk.Label(photos_frame, image=photo_img)
                            lbl.image = photo_img
                            lbl.grid(row=row, column=col, padx=5, pady=5)

                            # 正確顯示照片資訊
                            capture_date = photo[3] or '未知'
                            photo_type = photo[4] or '未知'
                            photo_info = f"日期: {capture_date}\n部位＆尺寸: {photo_type}"
                            tk.Label(photos_frame, text=photo_info, font=('Arial', 7)).grid(row=row + 1, column=col)

                            col += 1
                            if col > 2:
                                col = 0
                                row += 2
                        except Exception as e:
                            print(f"無法載入照片: {str(e)}")

            ttk.Button(patient_frame, text="查看/修改", command=lambda pid=patient_id: view_and_update_patient(pid)).grid(row=0, column=9)

            # 刪除按鈕
            def delete_patient(pid):
                self.db.delete_patient(pid)
                self.refresh_overview()

            ttk.Button(patient_frame, text="刪除", command=lambda pid=patient_id: delete_patient(pid)).grid(row=0, column=10)

            # 顯示最近三張照片
            photos = self.db.get_recent_photos(patient_id, 3)

            # 創建照片框架
            photo_frame = ttk.Frame(patient_frame)
            photo_frame.grid(row=1, column=0, columnspan=11, sticky="w")

            if not photos:
                ttk.Label(photo_frame, text="無照片記錄", font=('Arial', 8)).grid(row=0, column=0)
            else:
                valid_photos = False
                row = 0
                col = 0
                for p_idx, photo in enumerate(photos):
                    try:
                        if not photo[2] or not os.path.exists(photo[2]):
                            print(f"照片路徑不存在: {photo[2]}")
                            continue

                        valid_photos = True
                        img = Image.open(photo[2])
                        img.thumbnail((100, 100))
                        photo_img = ImageTk.PhotoImage(img)
                        lbl = tk.Label(photo_frame, image=photo_img)
                        lbl.image = photo_img
                        lbl.grid(row=row, column=col, padx=5, pady=5)

                        # 獲取 "部位＆尺寸" (來自 patient 資料)
                        part_and_size = patient[7] or '未知'  # patient[7] 是 medical_history

                        # 更新顯示的資訊
                        photo_info = f"日期: {photo[3] or '未知'}\n部位＆尺寸: {part_and_size}"
                        ttk.Label(photo_frame, text=photo_info, font=('Arial', 7)).grid(row=row + 1, column=col)

                        col += 1
                        if col > 2:
                            col = 0
                            row += 2
                    except Exception as e:
                        print(f"無法載入照片: {str(e)}")

                # 如果所有照片都無效，顯示提示
                if not valid_photos:
                    ttk.Label(photo_frame, text="照片路徑無效", font=('Arial', 8)).grid(row=0, column=0)

    def search_overview(self):
        search_params = {
            'patient_id': self.overview_search_vars[0].get() or None,
            'name': self.overview_search_vars[1].get() or None,
            'id_number': self.overview_search_vars[2].get() or None,
            'gender': self.overview_search_vars[3].get() or None,
            'contact_info': self.overview_search_vars[4].get() or None,
            'date_of_birth': self.overview_search_vars[5].get() or None,
            'address': self.overview_search_vars[6].get() or None,
            'medical_history': self.overview_search_vars[7].get() or None,
            'responsible_personnel': self.overview_search_vars[8].get() or None
        }
        self.refresh_overview(search_params)

    def export_patient_data_overview(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        try:
            search_params = {
                'patient_id': self.overview_search_vars[0].get().strip() or None,
                'name': self.overview_search_vars[1].get().strip() or None,
                'id_number': self.overview_search_vars[2].get().strip() or None,
                'gender': self.overview_search_vars[3].get().strip() or None,
                'contact_info': self.overview_search_vars[4].get().strip() or None,
                'date_of_birth': self.overview_search_vars[5].get().strip() or None,
                'address': self.overview_search_vars[6].get().strip() or None,
                'medical_history': self.overview_search_vars[7].get().strip() or None,
                'responsible_personnel': self.overview_search_vars[8].get().strip() or None
            }

            if search_params['id_number'] and not re.match(r'^[A-Z][12]\d{8}$', search_params['id_number']):
                messagebox.showerror("錯誤", "身分證字號格式不正確")
                return

            patients = self.db.search_patients(**search_params) if any(search_params.values()) else self.db.get_all_patients()

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                headers = ["病患ID", "姓名", "身分證字號", "性別", "聯絡方式", "出生日期", "地址", "部位＆尺寸", "負責人員", "照片"]
                writer.writerow(headers)

                for patient in patients:
                    try:
                        patient_id = patient[0]
                        photos = self.db.get_photos(patient_id)

                        # 確保只包含有效的照片路径
                        valid_photos = []
                        for photo in photos:
                            if photo[2] and os.path.exists(photo[2]):
                                valid_photos.append(photo[2])
                            else:
                                print(f"匯出時跳過無效照片路径: {photo[2]}")

                        # 写入病患资料，确保处理NULL值
                        row = []
                        for item in patient:
                            row.append(item if item is not None else "")

                        # 扩充照片栏位
                        max_photos = 3  # 最多显示3张照片
                        for i in range(max_photos):
                            if i < len(valid_photos):
                                row.append(valid_photos[i])
                            else:
                                row.append("")  # 空白栏位

                        writer.writerow(row)
                    except Exception as e:
                        print(f"匯出病患 {patient_id} 資料時出錯: {str(e)}")

            messagebox.showinfo("成功", "病患資料已成功匯出")
        except Exception as e:
            messagebox.showerror("錯誤", f"匯出失敗: {str(e)}")

    def schedule_backup(self):
        """排程資料庫備份"""
        try:
            backup_path = f"backup/patient_database_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            os.makedirs("backup", exist_ok=True)
            self.db.backup_database(backup_path)
        except Exception as e:
            print(f"備份失敗: {str(e)}")
        finally:
            # 每天凌晨1點備份一次
            self.root.after(24 * 60 * 60 * 1000, self.schedule_backup)

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
            db = Database('./patient_database.db')
            username = username_var.get()
            password = password_var.get()

            if db.login_user(username, password):
                root.destroy()
                main_root = tk.Tk()
                # Pass db instance to PatientManagementSystem
                app = PatientManagementSystem(main_root, db)
                main_root.mainloop()
            else:
                messagebox.showerror("錯誤", "使用者名稱或密碼錯誤")
                db.close()  # Close db connection if login fails
        except Exception as e:
            messagebox.showerror("錯誤", f"登入過程中發生錯誤: {str(e)}")
            # Ensure db is closed in case of exception during login
            if 'db' in locals() and db:
                db.close()

    tk.Button(root, text="登入", command=login).grid(row=2, columnspan=2)
    root.mainloop()

