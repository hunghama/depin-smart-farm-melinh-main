import os
import sys
import requests
from dotenv import load_dotenv

# 🔥 Đóng đinh đường dẫn tuyệt đối từ gốc lên quyền ưu tiên CAO NHẤT
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 1. Nạp file .env trước khi các module khác khởi chạy
load_dotenv()

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai  # SDK Gemini chính hãng mới nhất
from backend.storage import MongoStorage

app = FastAPI(title="Smart Farm Mê Linh API v1 - Telegram Concierge MVP")

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
    print(f"⚠️ Cảnh báo: Chưa cấu hình được Gemini Client: {e}")
    ai_client = None


# =====================================================================
# 🌤️ RECEIVE WEATHER DATA FROM SKY BOT
# =====================================================================
class WeatherDataInput(BaseModel):
    station_name: str = Field(..., example="Trạm khí tượng vĩ mô Mê Linh")
    temperature: float = Field(..., ge=-10.0, le=60.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    rain: float = Field(..., ge=0.0)
    weather_code: int = Field(..., description="Mã trạng thái thời tiết")


@app.post("/api/v1/weather", status_code=status.HTTP_201_CREATED)
def receive_weather_data(data: WeatherDataInput):
    packet = data.model_dump()
    db_saved = storage.save_weather_data(packet)
    if not db_saved:
        raise HTTPException(status_code=500, detail="Lưu dữ liệu thời tiết thất bại")
    return {"message": "Dữ liệu thời tiết Mê Linh đã đồng bộ thành công!", "status": "success"}


# =====================================================================
# 📡 PHÂN HỆ BẮN TIN NHẮN VỀ TELEGRAM ADMIN (CONCIERGE FLOW)
# =====================================================================
def send_telegram_message(text: str) -> bool:
    """Gọi API Telegram để nã bản tin tư vấn về máy của Hùng để chuẩn bị copy sang Zalo"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ [Telegram Error] Thiếu cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        res_json = response.json()
        if res_json.get("ok"):
            print("🟩 [Telegram] Đã bắn bản tin về máy Admin thành công!")
            return True
        else:
            print(f"❌ [Telegram API Thất bại]: {res_json}")
            return False
    except Exception as e:
        print(f"🚨 [Telegram Transport Error]: {e}")
        return False


# =====================================================================
# 🚀 ENDPOINT KÍCH HOẠT PHÁT TIN TƯ VẤN HÀNG NGÀY
# =====================================================================
@app.get("/api/v1/zalo/broadcast")
def trigger_concierge_broadcast():
    """
    🔥 CONCIERGE MVP: Bốc dữ liệu, hỏi Gemini, bắn bản tin thuần sạch sẽ 
    về Telegram của sếp để sếp copy nã thẳng vào các nhóm Zalo Mê Linh.
    """
    # 1. Bốc dữ liệu thời tiết mới nhất từ MongoDB
    weather_data = storage.get_latest_weather_data()
    if not weather_data:
        raise HTTPException(status_code=404, detail="Hệ thống trống dữ liệu thời tiết!")

    temp = weather_data.get("temperature", 25.0)
    humidity = weather_data.get("humidity", 70.0)
    rain = weather_data.get("rain", 0.0)

    # 2. Ép Gemini tạo nội dung tư vấn thuần mộc mạc
    recommendation_text = ""
    if ai_client and os.getenv("GEMINI_API_KEY"):
        prompt = f"""
        Bạn là chuyên gia cố vấn nông nghiệp số cho vùng trồng hoa hồng, hoa cúc, đào Tết tại Mê Linh, Hà Nội.
        Hãy phân tích chỉ số hiện tại: Nhiệt độ {temp}°C, Độ ẩm {humidity}%, Lượng mưa {rain}mm.
        Viết 1 bản tin ngắn gọn (3-4 câu), dùng ngôn từ bình dị, mộc mạc của nhà nông hướng dẫn bà con cần làm gì ngay hôm nay để bảo vệ vườn hoa (ví dụ: tưới nước, che lưới, khơi rãnh hay phun thuốc phòng bệnh).
        ⚠️ Quy định nghiêm ngặt: Tuyệt đối không dùng bất kỳ ký tự bôi đậm **, dấu gạch đầu dòng, hay ký hiệu dạng Markdown. Chỉ trả về một đoạn văn thuần duy nhất để khi copy sang Zalo không bị lỗi phông chữ.
        """
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            recommendation_text = response.text.strip()
        except Exception as e:
            print(f"⚠️ Sự cố gọi Gemini API: {e}")

    if not recommendation_text:
        recommendation_text = f"🌤️ Bản tin Smart Farm Mê Linh: Hiện tại nhiệt độ khoảng {temp}°C, độ ẩm {humidity}%. Thời tiết ổn định, bà con tranh thủ chăm sóc vườn hoa và theo dõi sát sao tình hình sâu bệnh định kỳ."

    # 3. Đóng gói lời nhắn hoàn chỉnh
    final_message = f"📢 BẢN TIN SÁNG SMART FARM MÊ LINH\n\n{recommendation_text}"

    # 4. Tiến hành nã đạn qua Telegram
    is_sent = send_telegram_message(text=final_message)
    
    if is_sent:
        return {
            "status": "success", 
            "message": "Bản tin AI đã được gửi về Telegram của sếp! Hãy copy và paste sang nhóm Zalo của bà con.",
            "preview": final_message
        }
    else:
        raise HTTPException(status_code=500, detail="Cổng gọi API Telegram gặp sự cố kỹ thuật")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
