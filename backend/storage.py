import os
import sys
from pymongo import MongoClient
from pymongo.errors import PyMongoError

class MongoStorage:
    def __init__(self):
        """Khởi tạo kết nối đám mây. Giấu kín URI kết nối trong Environment Variable."""
        # Lấy Connection String từ biến môi trường của hệ thống
        self.mongo_uri = os.getenv("MONGO_ATLAS_URI")
        
        if not self.mongo_uri:
            print("❌ LỖI KIẾN TRÚC: Chưa cấu hình biến môi trường MONGO_ATLAS_URI!")
            # Tránh làm sập Server bất thình lình, gán cờ None để xử lý Fallback
            self.client = None
            return

        try:
            # Thiết lập Connection Pool chuẩn, giới hạn thời gian chờ kết nối (Timeout) là 5 giây
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client["SmartFarmMeLinh"]
            self.collection = self.db["sensor_logs"]
        except Exception as e:
            print(f"❌ Không thể khởi tạo kết nối MongoDB Client: {e}")
            self.client = None

    def save_sensor_data(self, packet: dict) -> bool:
        """
        INTERFACE PHẲNG DUY NHẤT:
        Nhận vào một Dictionary, trả về True nếu lưu thành công, False nếu có sự cố.
        Bên ngoài không cần biết bên trong dùng thư viện gì hay xử lý lỗi ra sao.
        """
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database. Kích hoạt cơ chế chống sập (Fallback)...")
            return False
            
        try:
            # Thực hiện ghi dữ liệu vào Collection trên Cloud Atlas
            self.collection.insert_one(packet)
            return True
        except PyMongoError as e:
            # Đóng gói và cô lập hoàn toàn lỗi của thư viện PyMongo tại đây
            print(f"❌ Sự cố lưu trữ MongoDB Atlas: {e}")
            return False