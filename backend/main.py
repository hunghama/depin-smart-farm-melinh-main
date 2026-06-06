from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from backend.storage import MongoStorage  # Nạp module lưu trữ sạch

# 1. Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Smart Farm Mê Linh API v1")

# 2. Khởi tạo duy nhất 1 Instance Storage dùng chung cho toàn bộ vòng đời API
storage = MongoStorage()

class SensorDataInput(BaseModel):
    sensor_id: str
    temperature: float
    soil_moisture: float
    timestamp: int
    data_hash: str

# =====================================================================
# 💾 CỔNG NHẬN DATA PHẦN CỨNG (Để dành làm gói VIP cắm ruộng sau này)
# =====================================================================
@app.post("/api/v1/sensor", status_code=status.HTTP_201_CREATED)
def receive_sensor_data(data: SensorDataInput):
    packet = data.model_dump()
    
    # [Logic Check Hash]: Chỗ này hôm sau ông cắm logic giải mã chuỗi data_hash vào
    is_hash_valid = True # Tạm thời giả định qua chốt bảo mật DePIN
    
    if not is_hash_valid:
        raise HTTPException(status_code=403, detail="Mã băm DePIN không hợp lệ. Từ chối gói tin!")
        
    # [Lệnh Giao Diện Phẳng]: Gọi duy nhất một dòng để đẩy vào DB
    db_saved = storage.save_sensor_data(packet)
    
    if not db_saved:
        return {"message": "Dữ liệu được tiếp nhận nhưng lưu trữ tạm thời gặp sự cố", "status": "fallback"}
        
    return {"message": "Dữ liệu Mê Linh đã ghi nhận thành công vào MongoDB Atlas!", "status": "success"}


# =====================================================================
# 🚀 CÁC ENDPOINT MVP CHÍNH: LẤY DATA KHÍ TƯỢNG & AI KHUYẾN NGHỊ MÊ LINH
# =====================================================================

@app.get("/api/v1/weather/latest")
def get_latest_weather():
    """
    Endpoint bốc dữ liệu thời tiết thô mới nhất do bot cào về 
    để phục vụ giao diện Web App (vẽ biểu đồ, hiển thị dashboard).
    """
    weather_data = storage.get_latest_weather_data()
    
    if not weather_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Kho dữ liệu thời tiết trống! Hãy kiểm tra lại con bot cào dữ liệu."
        )
        
    return {"status": "success", "data": weather_data}


@app.get("/api/v1/weather/recommendation")
def get_ai_recommendation():
    """
    Linh hồn hệ chuyên gia: Tự động phân tích dữ liệu khí tượng Mê Linh 
    thời gian thực từ MongoDB để nhả khuyến nghị hành động cho bà con.
    """
    weather_data = storage.get_latest_weather_data()
    
    if not weather_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Thiếu dữ liệu thời tiết thực tế để hệ chuyên gia AI chạy phân tích!"
        )
        
    # Bóc tách chuẩn các trường dữ liệu theo đúng Schema mà bot simulator/app.py đang cào lên mây
    temp = weather_data.get("temperature", 25.0)
    humidity = weather_data.get("humidity", 70.0)
    rain = weather_data.get("rain", 0.0)
    
    # Thiết lập thuật toán logic nông nghiệp tối ưu cho vùng hoa, rau màu đặc thù Mê Linh
    recommendation = "🌤️ Thời tiết đang rất lý tưởng. Bà con tranh thủ bón phân định kỳ và chăm sóc cây trồng bình thường."
    action_code = "STATUS_OK"
    
    if temp > 35.0:
        recommendation = "⚠️ Trời nắng gắt trên 35°C! Khuyến nghị kéo lưới đen che giảm nắng cho các ruộng hoa hồng, hoa cúc Mê Linh; tuyệt đối không bón phân hóa học vào giữa trưa."
        action_code = "SHADE_REQUIRED"
        
    elif rain > 20.0:
        recommendation = "🚨 Cảnh báo mưa lớn úng rễ! Bà con cần chủ động ra đồng khơi thông bờ thửa, chuẩn bị máy bơm thoát nước cho các luống rau màu và vườn đào tránh đọng nước."
        action_code = "DRAINAGE_NOW"
        
    elif humidity < 50.0 and temp > 30.0:
        recommendation = "🍂 Không khí hanh khô, độ ẩm xuống thấp. Tăng cường hệ thống tưới phun sương vào đầu giờ sáng và chiều mát để bảo vệ lá và búp hoa không bị héo tắp."
        action_code = "INCREASE_IRRIGATION"
        
    elif temp < 15.0:
        recommendation = "❄️ Trời rét đậm, nguy cơ sương muối gây thối búp hoa cực cao. Khuyến nghị bà con tưới lướt nước chân ruộng vào sáng sớm để phá sương bảo vệ hoa tết."
        action_code = "ANTI_FROST"

    return {
        "status": "success",
        "station_name": weather_data.get("station_name"),
        "local_time": weather_data.get("local_time"),
        "metrics_analyzed": {
            "temperature_celsius": temp,
            "humidity_percent": humidity,
            "rain_mm": rain
        },
        "ai_decision": {
            "recommendation": recommendation,
            "action_code": action_code
        }
    }


# 3. Bộ kích hoạt chạy Server trực tiếp khi gõ lệnh python
if __name__ == "__main__":
    import uvicorn
    # Chạy từ thư mục gốc nên đường dẫn module phải là backend.main:app
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)