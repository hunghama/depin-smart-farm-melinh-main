import os
import sys
import requests
from dotenv import load_dotenv

# 🔥 Đóng đinh đường dẫn tuyệt đối từ gốc lên quyền ưu tiên CAO NHẤT để diệt tận gốc lỗi ModuleNotFoundError
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 1. Nạp file .env lên hệ thống trước khi các module khác khởi chạy
load_dotenv()

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai  # SDK Gemini chính hãng mới nhất
from backend.storage import MongoStorage

# 2. Khởi tạo ứng dụng và lớp lưu trữ dữ liệu
app = FastAPI(title="Smart Farm Mê Linh API v1 - Zalo MVP Edition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = MongoStorage()

# Khởi tạo Client Gemini
try:
    ai_client = genai.Client()
except Exception as e:
    print(f"⚠️ Cảnh báo: Chưa cấu hình được Gemini Client (Thiếu API Key): {e}")
    ai_client = None


# =====================================================================
# 🌤️ XÁC THỰC DỮ LIỆU ĐẦU VÀO KHÍ TƯỢNG VĨ MÔ
# =====================================================================
class WeatherDataInput(BaseModel):
    station_name: str = Field(..., example="Trạm khí tượng vĩ mô Mê Linh")
    temperature: float = Field(..., ge=-10.0, le=60.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    rain: float = Field(..., ge=0.0)
    weather_code: int = Field(..., description="Mã trạng thái thời tiết")


@app.post("/api/v1/weather", status_code=status.HTTP_201_CREATED)
def receive_weather_data(data: WeatherDataInput):
    """Cổng kết nối tiếp nhận dữ liệu thời tiết từ Sky Bot bắn về"""
    packet = data.model_dump()
    db_saved = storage.save_weather_data(packet)
    if not db_saved:
        raise HTTPException(status_code=500, detail="Lưu trữ dữ liệu thời tiết gặp sự cố")
    return {"message": "Dữ liệu thời tiết Mê Linh đã đồng bộ thành công!", "status": "success"}


# =====================================================================
# 📡 PHÂN HỆ KẾT NỐI VÀ BẮN TIN NHẮN TRỰC TIẾP SANG ZALO API
# =====================================================================
def send_zalo_message(user_zalo_id: str, text: str) -> bool:
    """Gọi API chính thức của Zalo Official Account để gửi tin nhắn cho người dùng"""
    url = "https://openapi.zalo.me/v2.0/oa/message"
    access_token = os.getenv("ZALO_ACCESS_TOKEN")
    
    if not access_token:
        print("⚠️ [Zalo Error] Thiếu cấu hình ZALO_ACCESS_TOKEN trong file .env")
        return False
        
    headers = {
        "Content-Type": "application/json",
        "access_token": access_token
    }
    
    payload = {
        "recipient": {"user_id": user_zalo_id},
        "message": {"text": text}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        res_json = response.json()
        if res_json.get("error") == 0:
            print(f"🟩 [Zalo] Đã gửi tin nhắn thành công tới User: {user_zalo_id}")
            return True
        else:
            print(f"❌ [Zalo API Thất bại] Mã lỗi {res_json.get('error')}: {res_json.get('message')}")
            return False
    except Exception as e:
        print(f"🚨 [Zalo Transport Error] Không thể kết nối tới máy chủ Zalo: {e}")
        return False


# =====================================================================
# 🚀 ĐÃ THÊM: ENDPOINT CHỦ ĐỘNG KÍCH HOẠT PHÁT TIN TƯ VẤN ZALO hàng ngày
# =====================================================================
@app.get("/api/v1/zalo/broadcast")
def trigger_zalo_broadcast():
    """
    🔥 ĐỘT PHÁ LỖI MVP: Endpoint chủ động gọi dữ liệu, xin lệnh Gemini 
    rồi nã thẳng tin nhắn nông nghiệp thực chiến vào Zalo của bà con Mê Linh.
    """
    # 1. Bốc dữ liệu thời tiết mới nhất từ MongoDB
    weather_data = storage.get_latest_weather_data()
    if not weather_data:
        raise HTTPException(status_code=404, detail="Hệ thống trống dữ liệu thời tiết, hoãn phát tin Zalo!")

    temp = weather_data.get("temperature", 25.0)
    humidity = weather_data.get("humidity", 70.0)
    rain = weather_data.get("rain", 0.0)

    # 2. Ép Gemini tạo nội dung thông báo thuần sạch sẽ
    recommendation_text = ""
    if ai_client and os.getenv("GEMINI_API_KEY"):
        prompt = f"""
        Bạn là chuyên gia cố vấn nông nghiệp số cho vùng trồng hoa hồng, hoa cúc, đào Tết tại Mê Linh, Hà Nội.
        Hãy phân tích chỉ số hiện tại: Nhiệt độ {temp}°C, Độ ẩm {humidity}%, Lượng mưa {rain}mm.
        Viết 1 bản tin ngắn gọn (3-4 câu), dùng ngôn từ bình dị, mộc mạc của nhà nông hướng dẫn bà con cần làm gì ngay hôm nay để bảo vệ vườn hoa (ví dụ: tưới nước, che lưới, khơi rãnh hay phun thuốc phòng bệnh).
        ⚠️ Quy định nghiêm ngặt: Tuyệt đối không dùng bất kỳ ký tự bôi đậm **, dấu gạch đầu dòng, hay ký hiệu dạng Markdown. Chỉ trả về một đoạn văn thuần duy nhất để gửi qua SMS/Zalo không bị lỗi phông chữ.
        """
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            recommendation_text = response.text.strip()
        except Exception as e:
            print(f"⚠️ Sự cố gọi Gemini API: {e}")

    # Fallback nếu mất API Key Gemini
    if not recommendation_text:
        recommendation_text = f"🌤️ Bản tin Smart Farm Mê Linh: Hiện tại nhiệt độ khoảng {temp}°C, độ ẩm {humidity}%. Thời tiết ổn định, bà con tranh thủ chăm sóc vườn hoa và theo dõi sát sao tình hình sâu bệnh định kỳ."

    # 3. Đóng gói lời nhắn hoàn chỉnh
    final_message = f"📢 BẢN TIN SÁNG SMART FARM MÊ LINH\n\n{recommendation_text}"

    # 4. Lấy danh sách ID Zalo người nhận (Giai đoạn MVP test, cấu hình ID của sếp trong file .env trước nhé)
    target_user = os.getenv("ZALO_TEST_USER_ID")
    
    if not target_user:
        return {
            "status": "dry_run_success",
            "message": "Đã tạo bản tin thành công nhưng chưa cấu hình ZALO_TEST_USER_ID để bắn tin đi.",
            "preview_content": final_message
        }

    # Tiến hành nã đạn qua Zalo
    is_sent = send_zalo_message(user_zalo_id=target_user, text=final_message)
    
    if is_sent:
        return {"status": "success", "message": "Bản tin AI đã được gửi trực tiếp tới Zalo người dùng thành công!"}
    else:
        raise HTTPException(status_code=500, detail="Lưu bản tin thành công nhưng cổng API Zalo từ chối gửi")


# =====================================================================
# 🔍 CÁC ENDPOINT ĐỌC DATA TRUYỀN THỐNG PHỤC VỤ WEB APP
# =====================================================================
@app.get("/api/v1/weather/latest")
def get_latest_weather():
    weather_data = storage.get_latest_weather_data()
    if not weather_data:
        raise HTTPException(status_code=404, detail="Kho dữ liệu trống!")
    return {"status": "success", "data": weather_data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
