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
# 🛡️ TẦNG BẢO MẬT: KHUNG XÁC THỰC DỮ LIỆU ĐẦU VÀO (PYDANTIC SCHEMAS)
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
# 🌤️ CỔNG NHẬN DATA KHÍ TƯỢNG VĨ MÔ (DỮ LIỆU TRỜI)
# =====================================================================
@app.post("/api/v1/weather", status_code=status.HTTP_201_CREATED)
def receive_weather_data(data: WeatherDataInput):
    """Cổng kết nối tiếp nhận dữ liệu thời tiết trên trời do Sky Bot bắn về"""
    packet = data.model_dump()
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
    """
    🔥 NÃO HYBRID HOÀN CHỈNH: Hợp nhất dữ liệu Trời (Open-Meteo) + Đất (ESP32)
    để ép Gemini đưa ra quyết định nông nghiệp chuẩn xác độc bản.
    """
    # 1. Bốc đồng thời 2 nguồn dữ liệu mới nhất từ MongoDB Atlas
    weather_data = storage.get_latest_weather_data()
    sensor_data = storage.get_latest_sensor_data() # (Đảm bảo file storage.py có hàm bốc data sensor này nhé sếp)

    # Nếu cả 2 kho đều trống, không thể chạy AI
    if not weather_data and not sensor_data:
        raise HTTPException(status_code=404, detail="Hệ thống trống dữ liệu! Không thể phân tích.")

    # Trích xuất dữ liệu Trời (Dự phòng nếu thiếu)
    temp_air = weather_data.get("temperature", 25.0) if weather_data else 25.0
    humidity_air = weather_data.get("humidity", 70.0) if weather_data else 70.0
    rain = weather_data.get("rain", 0.0) if weather_data else 0.0

    # Trích xuất dữ liệu Đất (Dự phòng nếu thiếu)
    temp_soil = sensor_data.get("temperature", 24.0) if sensor_data else 24.0
    soil_moisture = sensor_data.get("soil_moisture", 75.0) if sensor_data else 75.0

    # 🤖 BIẾN THỂ 1: SỬ DỤNG NÃO THẬT GEMINI HYBRID PROMPT
    if ai_client and os.getenv("GEMINI_API_KEY"):
        prompt = f"""
        Bạn là một chuyên gia cố vấn nông nghiệp số độc quyền cho vùng hoa hồng, hoa cúc, đào Tết tại Mê Linh, Hà Nội.
        Hãy thực hiện phân tích tương quan giữa Thời tiết vĩ mô (Trời) và Cảm biến tại luống (Đất) sau đây:
        
        [DỮ LIỆU TỪ TRỜI (Khí tượng vĩ mô - Open-Meteo)]:
        - Nhiệt độ không khí: {temp_air}°C
        - Độ ẩm không khí: {humidity_air}%
        - Lượng mưa dự báo: {rain}mm
        
        [DỮ LIỆU DƯỚI ĐẤT (Cảm biến vi khí hậu - ESP32)]:
        - Nhiệt độ lòng đất: {temp_soil}°C
        - Độ ẩm thực tế của đất luống hoa: {soil_moisture}%
        
        Yêu cầu logic: 
        1. Hãy đối chiếu xem có sự mâu thuẫn nào giữa Trời và Đất không (Ví dụ: Đất đang rất khô nhưng Trời chuẩn bị mưa lớn, hoặc Trời nắng gắt nhưng đất vẫn quá đẫm nước).
        2. Đưa ra 1 khuyến nghị hành động tối ưu nhất (khoảng 3-4 câu), dùng ngôn từ bình dị của nhà nông để giúp bà con tiết kiệm chi phí tưới tiêu hoặc chủ động phòng bệnh đặc thù (mốc sương, thối rễ, cháy lá).
        3. Tuyệt đối không dùng định dạng ký tự Markdown (như bôi đậm **, dấu gạch đầu dòng), hãy trả về một đoạn văn thuần sạch sẽ.
        """
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return {
                "status": "success",
                "ai_engine": "Gemini 2.5 Flash (Hybrid AI Brain)",
                "metrics_analyzed": {
                    "air_temperature_celsius": temp_air,
                    "air_humidity_percent": humidity_air,
                    "rain_mm": rain,
                    "soil_temperature_celsius": temp_soil,
                    "soil_moisture_percent": soil_moisture
                },
                "ai_decision": {
                    "recommendation": response.text.strip(),
                    "action_code": "GEMINI_HYBRID_SUCCESS"
                }
            }
        except Exception as e:
            print(f"⚠️ Sự cố gọi Gemini API: {e}")

    # 🪵 BIẾN THỂ 2: HỆ CHUYÊN GIA DỰ PHÒNG HYBRID RULE-BASED (Khi mất mạng/Hết hạn mức API)
    recommendation = "🌤️ Các chỉ số ổn định. Bà con theo dõi vườn hoa và chăm sóc theo lịch định kỳ."
    action_code = "HYBRID_STATUS_OK"
    
    # Logic If/Else lai giữa Đất và Trời cơ bản
    if rain > 15.0 and soil_moisture > 85.0:
        recommendation = "🚨 Cảnh báo khẩn cấp! Trời đang mưa lớn kèm theo độ ẩm đất luống hoa đã quá đẫm (trên 85%). Nguy cơ thối rễ bùng phát cực cao. Bà con Mê Linh khẩn trương ra đồng khơi rãnh, bật máy bơm xả nước ngay lập tức!"
        action_code = "CRITICAL_DRAINAGE"
    elif rain > 10.0 and soil_moisture < 50.0:
        recommendation = "🌧️ Thời tiết chuẩn bị có mưa, kết hợp đất ruộng hiện tại đang khá khô. Khuyến nghị bà con HOÃN việc bật hệ thống tưới tự động để tận dụng nước mưa, giúp tiết kiệm chi phí điện nước."
        action_code = "DELAY_IRRIGATION"
    elif temp_air > 35.0 and soil_moisture < 60.0:
        recommendation = "🔥 Trời nắng gắt trên 35°C và đất luống hoa đang thiếu nước nghiêm trọng. Nông dân cần kéo ngay lưới đen che nắng và bật hệ thống tưới nhỏ giọt vào lúc chiều mát để hồi sức cho hoa."
        action_code = "HEAT_STRESS_WATER"

    return {
        "status": "success",
        "ai_engine": "Rule-based Expert System (Fallback Mode)",
        "metrics_analyzed": {
            "air_temperature_celsius": temp_air,
            "air_humidity_percent": humidity_air,
            "rain_mm": rain,
            "soil_temperature_celsius": temp_soil,
            "soil_moisture_percent": soil_moisture
        },
        "ai_decision": {
            "recommendation": recommendation,
            "action_code": action_code
        }
    }


# 3. Bộ kích hoạt chạy Server trực tiếp
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
