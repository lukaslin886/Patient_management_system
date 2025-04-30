import sqlite3
import os
from cryptography.fernet import Fernet
import bcrypt

class Database:
    def __init__(self, db_name):
        self.key = b'ENdOpMAmi_y_joVb-HT53R0fpEGFq0hWI3zzOWa3G1A='
        self.cipher = Fernet(self.key)
        self.db_name = db_name
        # Allow connection to be used across threads
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        
    def encrypt_data(self, data):
        """加密資料"""
        if data is None:
            return None
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data):
        """解密資料"""
        if encrypted_data is None:
            return None
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            print(f"解密失敗: {str(e)}")
            return None

    def create_tables(self):
        """建立所有必要的資料表"""
        # 建立 patients 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                PatientID INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                id_number TEXT UNIQUE,
                gender TEXT,
                contact_info TEXT,
                date_of_birth TEXT,
                address TEXT,
                medical_history TEXT,
                responsible_personnel TEXT
            )
        ''')
        
        # 建立 photos 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                PhotoID INTEGER PRIMARY KEY AUTOINCREMENT,
                PatientID INTEGER,
                photo_path TEXT,
                capture_date DATE,
                part_and_size TEXT,
                photo_type TEXT,
                FOREIGN KEY (PatientID) REFERENCES patients(PatientID)
            )
        ''')

        # 建立 treatments 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS treatments (
                TreatmentID INTEGER PRIMARY KEY AUTOINCREMENT,
                PatientID INTEGER,
                treatment_date DATE,
                description TEXT,
                FOREIGN KEY (PatientID) REFERENCES patients(PatientID)
            )
        ''')

        # 建立 users 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user' NOT NULL 
            )
        ''')
        
        # 檢查並更新現有 patients 表格結構 (如果需要從舊結構遷移)
        # 這部分保留是為了兼容可能存在的舊數據庫結構
        self.cursor.execute("PRAGMA table_info(patients)")
        columns = [column[1] for column in self.cursor.fetchall()]
        if 'date_of_birth' not in columns:
            self.cursor.execute("ALTER TABLE patients ADD COLUMN date_of_birth TEXT")
        if 'address' not in columns:
            self.cursor.execute("ALTER TABLE patients ADD COLUMN address TEXT")
        if 'medical_history' not in columns:
            self.cursor.execute("ALTER TABLE patients ADD COLUMN medical_history TEXT")
        if 'responsible_personnel' not in columns:
            self.cursor.execute("ALTER TABLE patients ADD COLUMN responsible_personnel TEXT")

        # 檢查並更新現有 photos 表格結構 (如果需要從舊結構遷移)
        self.cursor.execute("PRAGMA table_info(photos)")
        photo_columns = [col[1] for col in self.cursor.fetchall()]
        if 'part_and_size' not in photo_columns:
             try:
                 self.cursor.execute("ALTER TABLE photos ADD COLUMN part_and_size TEXT")
             except sqlite3.OperationalError as e:
                 # 如果欄位已存在或其他錯誤，打印信息但繼續
                 print(f"無法新增 part_and_size 欄位 (可能已存在): {e}")
        if 'photo_type' not in photo_columns:
             try:
                 self.cursor.execute("ALTER TABLE photos ADD COLUMN photo_type TEXT")
             except sqlite3.OperationalError as e:
                 print(f"無法新增 photo_type 欄位 (可能已存在): {e}")


        # 初始化預設管理員帳號
        default_username = 'admin'
        default_password = 'admin123' # 實際應用中應使用更安全的方式處理預設密碼

        self.cursor.execute("SELECT * FROM users WHERE username = ?", (default_username,))
        if not self.cursor.fetchone():
             # 確保 register_user 方法存在且可用
             if hasattr(self, 'register_user') and callable(self.register_user):
                 self.register_user(default_username, default_password, role='admin') # 指定角色為 admin
                 print(f"已創建預設管理員帳號: {default_username}")
             else:
                 # 如果 register_user 不可用，直接插入 (需要先 hash 密碼)
                 hashed_password = self.hash_password(default_password)
                 self.cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                                     (default_username, hashed_password, 'admin'))
                 print(f"已直接插入預設管理員帳號: {default_username}")
        else:
            print("管理員帳號已存在")

        self.conn.commit()


    def add_patient(self, name, id_number, gender, contact_info, date_of_birth=None, address=None, medical_history=None, responsible_personnel=None):
        encrypted_name = self.encrypt_data(name)
        encrypted_id_number = self.encrypt_data(id_number)
        encrypted_gender = self.encrypt_data(gender)
        encrypted_contact_info = self.encrypt_data(contact_info)
        encrypted_date_of_birth = self.encrypt_data(date_of_birth)
        encrypted_address = self.encrypt_data(address)
        encrypted_medical_history = self.encrypt_data(medical_history)
        encrypted_responsible_personnel = self.encrypt_data(responsible_personnel)
        
        self.cursor.execute('''
            INSERT INTO patients (name, id_number, gender, contact_info, date_of_birth, address, medical_history, responsible_personnel) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
            (encrypted_name, encrypted_id_number, encrypted_gender, encrypted_contact_info, 
             encrypted_date_of_birth, encrypted_address, encrypted_medical_history, encrypted_responsible_personnel))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_patient(self, patient_id):
        self.cursor.execute("SELECT * FROM patients WHERE PatientID = ?", (patient_id,))
        patient = self.cursor.fetchone()
        if patient:
            # 打印原始數據，用於調試
            print(f"Raw patient data from DB: {patient}")
            
            # 確保所有欄位都存在，即使是NULL
            if len(patient) < 9:
                print(f"警告: 病患資料不完整，只有 {len(patient)} 個欄位")
                # 擴展元組以確保有9個元素
                patient = patient + (None,) * (9 - len(patient))
            
            # 解密數據，確保處理NULL值
            try:
                return (
                    patient[0],  # PatientID
                    self.decrypt_data(patient[1]),  # name
                    self.decrypt_data(patient[2]),  # id_number
                    self.decrypt_data(patient[3]),  # gender
                    self.decrypt_data(patient[4]),  # contact_info
                    self.decrypt_data(patient[5]),  # date_of_birth
                    self.decrypt_data(patient[6]),  # address
                    self.decrypt_data(patient[7]),  # medical_history
                    self.decrypt_data(patient[8])   # responsible_personnel
                )
            except Exception as e:
                print(f"解密病患資料時出錯: {str(e)}")
                # 返回原始數據，不進行解密
                return patient
        return None

    def get_photos(self, patient_id):
        self.cursor.execute('''
            SELECT p.*, pt.medical_history 
            FROM photos p 
            LEFT JOIN patients pt ON p.PatientID = pt.PatientID 
            WHERE p.PatientID = ?
        ''', (patient_id,))
        return self.cursor.fetchall()
        
    def get_recent_photos(self, patient_id, limit=3):
        """取得指定病患的最新照片資料"""
        self.cursor.execute('''
            SELECT * FROM photos 
            WHERE PatientID = ? 
            ORDER BY capture_date DESC 
            LIMIT ?
        ''', (patient_id, limit))
        return self.cursor.fetchall()

    def get_treatments(self, patient_id):
        self.cursor.execute("SELECT * FROM treatments WHERE PatientID = ?", (patient_id,))
        return self.cursor.fetchall()
    
    def get_photo(self, photo_id):
        self.cursor.execute("SELECT * FROM photos WHERE PhotoID = ?", (photo_id,))
        return self.cursor.fetchone()

    def get_all_patients(self):
        self.cursor.execute("SELECT * FROM patients")
        patients = self.cursor.fetchall()
        return [
            (
                patient[0],
                self.decrypt_data(patient[1]),
                self.decrypt_data(patient[2]),
                self.decrypt_data(patient[3]),
                self.decrypt_data(patient[4]),
                self.decrypt_data(patient[5]),
                self.decrypt_data(patient[6]),
                self.decrypt_data(patient[7]),
                self.decrypt_data(patient[8])
            ) for patient in patients
        ]

    def search_patients(self, patient_id=None, name=None, id_number=None, gender=None, contact_info=None, date_of_birth=None, address=None, medical_history=None, responsible_personnel=None):
        query = "SELECT * FROM patients WHERE 1=1"
        params = []
        if patient_id:
            query += " AND PatientID = ?"
            params.append(patient_id)
        if name:
            query += " AND name LIKE ?"
            params.append(f"%{name}%")
        if id_number:
            query += " AND id_number LIKE ?"
            params.append(f"%{id_number}%")
        if gender:
            query += " AND gender = ?"
            params.append(gender)
        if contact_info:
            query += " AND contact_info LIKE ?"
            params.append(f"%{contact_info}%")
        if date_of_birth:
            query += " AND date_of_birth LIKE ?"
            params.append(f"%{date_of_birth}%")
        if address:
            query += " AND address LIKE ?"
            params.append(f"%{address}%")
        if medical_history:
            query += " AND medical_history LIKE ?"
            params.append(f"%{medical_history}%")
        if responsible_personnel:
            query += " AND responsible_personnel LIKE ?"
            params.append(f"%{responsible_personnel}%")

        self.cursor.execute(query, params)
        patients = self.cursor.fetchall()
        return [
            (
                patient[0],
                self.decrypt_data(patient[1]),
                self.decrypt_data(patient[2]),
                self.decrypt_data(patient[3]),
                self.decrypt_data(patient[4]),
                self.decrypt_data(patient[5]),
                self.decrypt_data(patient[6]),
                self.decrypt_data(patient[7]),
                self.decrypt_data(patient[8])
            ) for patient in patients
        ]

    def update_patient(self, patient_id, name, id_number, gender, contact_info, date_of_birth=None, address=None, medical_history=None, responsible_personnel=None):
        encrypted_name = self.encrypt_data(name)
        encrypted_id_number = self.encrypt_data(id_number)
        encrypted_gender = self.encrypt_data(gender)
        encrypted_contact_info = self.encrypt_data(contact_info)
        encrypted_date_of_birth = self.encrypt_data(date_of_birth)
        encrypted_address = self.encrypt_data(address)
        encrypted_medical_history = self.encrypt_data(medical_history)
        encrypted_responsible_personnel = self.encrypt_data(responsible_personnel)
        
        self.cursor.execute('''
            UPDATE patients 
            SET name = ?, id_number = ?, gender = ?, contact_info = ?, 
                date_of_birth = ?, address = ?, medical_history = ?, responsible_personnel = ? 
            WHERE PatientID = ?''', 
            (encrypted_name, encrypted_id_number, encrypted_gender, encrypted_contact_info,
             encrypted_date_of_birth, encrypted_address, encrypted_medical_history, encrypted_responsible_personnel, patient_id))
        self.conn.commit()
        return self.cursor.rowcount

    def update_patient_medical_history(self, patient_id, medical_history):
        """僅更新病患的 medical_history (部位＆尺寸) 欄位"""
        encrypted_medical_history = self.encrypt_data(medical_history)
        self.cursor.execute('''
            UPDATE patients
            SET medical_history = ?
            WHERE PatientID = ?''',
            (encrypted_medical_history, patient_id))
        self.conn.commit()
        return self.cursor.rowcount

    def delete_patient(self, patient_id):
        # 先刪除相關的照片和處置記錄
        self.cursor.execute("DELETE FROM photos WHERE PatientID = ?", (patient_id,))
        self.cursor.execute("DELETE FROM treatments WHERE PatientID = ?", (patient_id,))
        # 再刪除病患記錄
        self.cursor.execute("DELETE FROM patients WHERE PatientID = ?", (patient_id,))
        self.conn.commit()
        return self.cursor.rowcount

    def add_photo(self, patient_id, photo_path, capture_date, part_and_size, photo_type):
        self.cursor.execute('''
            INSERT INTO photos (PatientID, photo_path, capture_date, part_and_size, photo_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (patient_id, photo_path, capture_date, part_and_size, photo_type))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_photo(self, photo_id, capture_date=None, part_and_size=None, photo_type=None):
        query = """
            UPDATE photos
            SET capture_date = COALESCE(?, capture_date),
                part_and_size = COALESCE(?, part_and_size),
                photo_type = COALESCE(?, photo_type)
            WHERE PhotoID = ?
        """
        self.cursor.execute(query, (capture_date, part_and_size, photo_type, photo_id))
        self.conn.commit()

    # The second create_tables definition is removed by this replacement.

    def delete_photo(self, photo_id):
        """刪除指定的照片記錄"""
        try:
            # 先獲取照片路徑
            self.cursor.execute("SELECT photo_path FROM photos WHERE PhotoID = ?", (photo_id,))
            photo = self.cursor.fetchone()
            
            if photo and photo[0] and os.path.exists(photo[0]):
                # 刪除實際檔案
                os.remove(photo[0])
            
            # 刪除資料庫記錄
            self.cursor.execute("DELETE FROM photos WHERE PhotoID = ?", (photo_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"刪除照片失敗: {str(e)}")
            return False

    def close(self):
        self.conn.close()

    def backup_database(self, backup_path):
        """備份資料庫到指定路徑"""
        try:
            # 關閉當前連接
            self.conn.close()
            
            # 備份資料庫
            import shutil
            shutil.copy(self.db_name, backup_path)
            
            # 重新建立連接
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            
            print(f"資料庫已備份到: {backup_path}")
            return True
        except Exception as e:
            print(f"備份失敗: {str(e)}")
            # 重新建立連接
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            return False

    def hash_password(self, password):
        """哈希密碼"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    
    def register_user(self, username, password, role='user'):
        """註冊新用戶"""
        hashed_password = self.hash_password(password)
        try:
            self.cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                                (username, hashed_password, role))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print("用戶名已存在")
            return False
    
    def login_user(self, username, password):
        """用戶登入驗證"""
        self.cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        user = self.cursor.fetchone()
        
        if not user:
            return False
            
        stored_hash = user[0]
        return bcrypt.checkpw(password.encode(), stored_hash.encode())

    def get_user_role(self, username):
        """獲取用戶角色"""
        try:
            self.cursor.execute("SELECT role FROM users WHERE username = ?", (username,))
            user = self.cursor.fetchone()
            if user:
                return user[0]
            return None
        except Exception as e:
            print(f"獲取用戶角色失敗: {str(e)}")
            return None
    
    def user_exists(self, username):
        """檢查用戶是否存在"""
        try:
            self.cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"檢查用戶是否存在失敗: {str(e)}")
            return False
    
    def reset_user_password(self, username, new_password):
        """重置用戶密碼"""
        try:
            hashed_password = self.hash_password(new_password)
            self.cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", 
                                (hashed_password, username))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"重置密碼失敗: {str(e)}")
            return False
