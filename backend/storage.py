import os
import sys
from pymongo import MongoClient
from pymongo.errors import PyMongoError

class MongoStorage:
    def __init__(self):
        """Khởi tạo kết nối đám mây. Giấu kín URI kết nối trong Environment Variable."""
        self.mongo_uri = os.getenv("MONGO_ATLAS_URI")
        
        if not self.mongo_uri:
            print("❌ LỖI KIẾN TRÚC: Chưa cấu hình biến môi trường MONGO_ATLAS_URI!")
            self.client = None
            return

        try:
            # Thiết lập Connection Pool chuẩn, giới hạn thời gian chờ kết nối (Timeout) là 5 giây
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client["SmartFarmMeLinh"]
            
            # 1. Collection chứa dữ liệu cảm biến mặt đất (ESP32 hoặc Phần cứng giả lập)
            self.collection = self.db["sensor_logs"]
            
            # 2. Collection chứa dữ liệu khí tượng vĩ mô trên trời do Sky Bot cào về
            self.weather_collection = self.db["weather_logs"]
            
        except Exception as e:
            print(f"❌ Không thể khởi tạo kết nối MongoDB Client: {e}")
            self.client = None

    # =====================================================================
    # 💾 CÁC INTERFACE LƯU TRỮ DỮ LIỆU (WRITE PATH)
    # =====================================================================

    def save_sensor_data(self, packet: dict) -> bool:
        """Lưu trữ dữ liệu vi khí hậu thô từ luống đất (ESP32) vào collection sensor_logs"""
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database. Không thể lưu dữ liệu cảm biến đất.")
            return False
        try:
            self.collection.insert_one(packet)
            return True
        except PyMongoError as e:
            print(f"❌ Sự cố lưu trữ dữ liệu đất trên MongoDB Atlas: {e}")
            return False

    def save_weather_data(self, packet: dict) -> bool:
        """
        🔥 THÊM MỚI: Cổng lưu trữ dữ liệu khí tượng vĩ mô từ Sky Bot vào collection weather_logs
        Giúp Backend xử lý được request POST từ con bot cào thời tiết app.py.
        """
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database. Không thể lưu dữ liệu thời tiết trời.")
            return False
        try:
            self.weather_collection.insert_one(packet)
            return True
        except PyMongoError as e:
            print(f"❌ Sự cố lưu trữ dữ liệu trời trên MongoDB Atlas: {e}")
            return False

    # =====================================================================
    # 🔍 CÁC INTERFACE ĐỌC DỮ LIỆU MỚI NHẤT (READ PATH FOR GEMINI)
    # =====================================================================

    def get_latest_weather_data(self) -> dict | None:
        """Bốc bản ghi thời tiết vĩ mô (Trời) mới nhất từ collection weather_logs"""
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi lấy dữ liệu thời tiết trời.")
            return None
            
        try:
            latest = list(self.weather_collection.find().sort("timestamp", -1).limit(1))
            if latest:
                doc = latest[0]
                doc["_id"] = str(doc["_id"])  # Ép kiểu ObjectId thành string để né lỗi JSON
                return doc
            return None
        except PyMongoError as e:
            print(f"❌ Sự cố truy vấn dữ liệu thời tiết trên MongoDB Atlas: {e}")
            return None

    def get_latest_sensor_data(self) -> dict | None:
        """
        🔥 THÊM MỚI: Bốc bản ghi cảm biến vi khí hậu (Đất) mới nhất từ collection sensor_logs
        Cung cấp dữ liệu mặt đất thời gian thực cho bộ não Gemini Hybrid xử lý.
        """
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi lấy dữ liệu cảm biến đất.")
            return None
            
        try:
            # Sắp xếp theo trường 'timestamp' giảm dần để lấy bản ghi ESP32 mới nhất vừa bắn lên
            latest = list(self.collection.find().sort("timestamp", -1).limit(1))
            if latest:
                doc = latest[0]
                doc["_id"] = str(doc["_id"])  # Ép kiểu ObjectId thành string để né lỗi JSON
                return doc
            return None
        except PyMongoError as e:
            print(f"❌ Sự cố truy vấn dữ liệu cảm biến đất trên MongoDB Atlas: {e}")
            return None
