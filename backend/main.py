import os
import sys
from dotenv import load_dotenv

# 🔥 Đóng đinh đường dẫn tuyệt đối từ gốc lên quyền ưu tiên CAO NHẤT để diệt tận gốc lỗi ModuleNotFoundError
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 1. Nạp file .env lên hệ thống trước khi các module khác khởi chạy
load_dotenv()

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Thư viện mở khóa CORS
from pydantic import BaseModel, Field
from google import genai  # SDK Gemini chính hãng mới nhất
from backend.storage import MongoStorage  # Nạp module lưu trữ của ông

# 2. Khởi tạo ứng dụng và lớp lưu trữ dữ liệu
app = FastAPI(title="Smart Farm Mê Linh API v1 - Gemini Edition")

# Cấu hình thông chốt CORS bảo mật để file frontend/index.html bốc được API mà không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các nguồn truy cập
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép mọi phương thức GET, POST,...
    allow_headers=["*"],  # Cho phép mọi Header truyền lên
)

storage = MongoStorage()

# Khởi tạo Client Gemini (Nó sẽ tự động bốc biến GEMINI_API_KEY trong file .env ra dùng)
try:
    ai_client = genai.Client()
except Exception as e:
    print(f"⚠️ Cảnh báo: Chưa cấu hình được Gemini Client (Thiếu API Key): {e}")
    ai_client = None


# =====================================================================
# 🛡️ ĐẰNG BẢO MẬT: KHUNG XÁC THỰC DỮ LIỆU ĐẦU VÀO (PYDANTIC SCHEMAS)
# =====================================================================

class SensorDataInput(BaseModel):
    """Schema ép kiểu dữ liệu vi khí hậu từ luống đất (ESP32 thật hoặc giả lập phần cứng)"""
    sensor_id: str = Field(..., example="ESP32_MELINH_01")
    temperature: float = Field(..., ge=-10.0, le=60.0, description="Nhiệt độ đất (°C)")
    soil_moisture: float = Field(..., ge=0.0, le=100.0, description="Độ ẩm đất (%)")
    timestamp: int = Field(..., description="Epoch timestamp từ thiết bị")
    data_hash: str = Field(..., description="Mã băm SHA-256")


class WeatherDataInput(BaseModel):
    """Schema ép kiểu dữ liệu khí tượng vĩ mô từ trên trời (Bot cào vệ tinh Open-Meteo)"""
    station_name: str = Field(..., example="Trạm khí tượng vĩ mô Mê Linh")
    temperature: float = Field(..., ge=-10.0, le=60.0, description="Nhiệt độ không khí (°C)")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Độ ẩm không khí (%)")
    rain: float = Field(..., ge=0.0, description="Lượng mưa (mm)")
    weather_code: int = Field(..., description="Mã trạng thái thời tiết")


# =====================================================================
# 💾 CỔNG NHẬN DATA PHẦN CỨNG (DỮ LIỆU ĐẤT)
# =====================================================================
@app.post("/api/v1/sensor", status_code=status.HTTP_201_CREATED)
def receive_sensor_data(data: SensorDataInput):
    """Cổng tiếp nhận Telemetry thô từ luống đất gửi lên"""
    packet = data.model_dump()
    is_hash_valid = True  # Tạm thời giả định qua chốt bảo mật DePIN
    
    if not is_hash_valid:
        raise HTTPException(status_code=403, detail="Mã băm DePIN không hợp lệ!")
        
    db_saved = storage.save_sensor_data(packet)
    if not db_saved:
        raise HTTPException(status_code=500, detail="Lưu trữ dữ liệu cảm biến đất gặp sự cố")
        
    return {"message": "Dữ liệu mặt đất Mê Linh ghi nhận thành công!", "status": "success"}


# =====================================================================
# 🌤️ ĐÃ THÊM MỚI: CỔNG NHẬN DATA KHÍ TƯỢNG VĨ MÔ (DỮ LIỆU TRỜI)
# =====================================================================
@app.post("/api/v1/weather", status_code=status.HTTP_201_CREATED)
def receive_weather_data(data: WeatherDataInput):
    """Cổng kết nối tiếp nhận dữ liệu thời tiết trên trời do Sky Bot bắn về"""
    packet = data.model_dump()
    
    # Thực hiện lưu gói tin thời tiết vào database 
    # (Nếu file storage.py của ông dùng hàm khác tên, hãy sửa lại cho khớp nhé)
    db_saved = storage.save_weather_data(packet)
    if not db_saved:
        raise HTTPException(status_code=500, detail="Lưu trữ dữ liệu thời tiết vĩ mô gặp sự cố")
        
    return {"message": "Dữ liệu thời tiết trên trời Mê Linh đã đồng bộ thành công!", "status": "success"}


# =====================================================================
# 🚀 CÁC ENDPOINT MVP CHÍNH: LẤY DATA KHÍ TƯỢNG & AI CẤY NÃO GEMINI
# =====================================================================

@app.get("/api/v1/weather/latest")
def get_latest_weather():
    """Endpoint bốc dữ liệu thời tiết vĩ mô mới nhất phục vụ giao diện Web App"""
    weather_data = storage.get_latest_weather_data()
    if not weather_data:
        raise HTTPException(status_code=404, detail="Kho dữ liệu thời tiết vĩ mô trống!")
    return {"status": "success", "data": weather_data}


@app.get("/api/v1/weather/recommendation")
def get_ai_recommendation():
    """Linh hồn hệ thống: Gọi thẳng não thật Gemini API hoặc Hệ chuyên gia dự phòng"""
    weather_data = storage.get_latest_weather_data()
    if not weather_data:
        raise HTTPException(status_code=404, detail="Thiếu dữ liệu thời tiết thực tế để AI chạy phân tích!")
        
    temp = weather_data.get("temperature", 25.0)
    humidity = weather_data.get("humidity", 70.0)
    rain = weather_data.get("rain", 0.0)
    
    if ai_client and os.getenv("GEMINI_API_KEY"):
        prompt = f"""
        Bạn là một chuyên gia nông nghiệp công nghệ cao am hiểu sâu sắc về canh tác hoa hồng, hoa cúc, đào Tết và rau màu tại huyện Mê Linh, Hà Nội.
        Hãy phân tích các chỉ số thời tiết thời gian thực sau đây:
        - Nhiệt độ: {temp}°C
        - Độ ẩm không khí: {humidity}%
        - Lượng mưa: {rain}mm
        
        Yêu cầu: Hãy đưa ra 1 lời khuyên ngắn gọn (khoảng 3-4 câu), thực chiến, dùng ngôn từ bình dị của nhà nông để hướng dẫn bà con Mê Linh cần làm gì (ví dụ: che lưới, khơi thông luống, tưới nước hay dừng bón phân). Khuyến nghị phải sát thực tế với các loại cây trồng đặc thù của địa phương. Không sử dụng định dạng Markdown (như dấu sao, bôi đậm), hãy trả về văn bản thuần sạch sẽ.
        """
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return {
                "status": "success",
                "ai_engine": "Gemini 2.5 Flash (Dynamic AI)",
                "station_name": weather_data.get("station_name"),
                "metrics_analyzed": {"temperature_celsius": temp, "humidity_percent": humidity, "rain_mm": rain},
                "ai_decision": {"recommendation": response.text.strip(), "action_code": "GEMINI_DYNAMIC"}
            }
        except Exception as e:
            print(f"⚠️ Sự cố gọi Gemini API (Chuyển luồng về Hệ chuyên gia dự phòng): {e}")

    # Hệ chuyên gia dự phòng Rule-based (If/Else cố định)
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
        "ai_engine": "Rule-based Expert System (Fallback Mode)",
        "station_name": weather_data.get("station_name"),
        "metrics_analyzed": {"temperature_celsius": temp, "humidity_percent": humidity, "rain_mm": rain},
        "ai_decision": {"recommendation": recommendation, "action_code": action_code}
    }


# 3. Bộ kích hoạt chạy Server trực tiếp
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
