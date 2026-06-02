from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from backend.storage import MongoStorage  # Nạp module lưu trữ sạch

app = FastAPI(title="Smart Farm Mê Linh API v1")

# Khởi tạo duy nhất 1 Instance Storage dùng chung cho toàn bộ vòng đời API
storage = MongoStorage()

class SensorDataInput(BaseModel):
    sensor_id: str
    temperature: float
    soil_moisture: float
    timestamp: int
    data_hash: str

@app.post("/api/v1/sensor", status_code=status.HTTP_201_CREATED)
def receive_sensor_data(data: SensorDataInput):
    packet = data.model_dump()
    
    # 1. [Logic Check Hash]: Chỗ này hôm sau ông cắm logic giải mã chuỗi data_hash vào
    is_hash_valid = True # Tạm thời giả định qua chốt bảo mật DePIN
    
    if not is_hash_valid:
        raise HTTPException(status_code=403, detail="Mã băm DePIN không hợp lệ. Từ chối gói tin!")
        
    # 2. [Lệnh Giao Diện Phẳng]: Gọi duy nhất một dòng để đẩy vào DB
    db_saved = storage.save_sensor_data(packet)
    
    if not db_saved:
        # Nếu DB sập, vẫn trả về 202 (Accepted) hoặc thông báo lưu tạm để tránh block trạm IoT
        return {"message": "Dữ liệu được tiếp nhận nhưng lưu trữ tạm thời gặp sự cố", "status": "fallback"}
        
    return {"message": "Dữ liệu Mê Linh đã ghi nhận thành công vào MongoDB Atlas!", "status": "success"}