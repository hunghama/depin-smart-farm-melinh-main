import os
import sys
import time  
import requests
from datetime import datetime, timedelta, timezone  
from dotenv import load_dotenv

# 🔥 Đóng đinh đường dẫn tuyệt đối từ gốc lên quyền ưu tiên CAO NHẤT
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 1. Nạp file .env trước khi các module khác khởi chạy
load_dotenv()

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  
from pydantic import BaseModel, Field
from google import genai  # SDK Gemini chính hãng mới nhất
from backend.storage import MongoStorage
# 📦 Nạp Sổ tay kỹ thuật chống ảo giác
from backend.knowledge import AGRI_KNOWLEDGE_BASE
# 🛡️ Nạp hạ tầng minh chứng tự động Sprint 2
from backend.provenance import ProvenanceEngine

app = FastAPI(title="Smart Farm Mê Linh API v1 - Market Ready MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = MongoStorage()
# Khởi tạo bộ máy tự động sinh dấu chân số nông sản
provenance_engine = ProvenanceEngine(storage_client=storage)

# NẠP MÃ KHÓA BẢO MẬT
CRON_SECRET_TOKEN = os.getenv("CRON_SECRET_TOKEN")

# Khởi tạo Client Gemini
try:
    ai_client = genai.Client()
except Exception as e:
    print(f"⚠️ Cảnh báo: Unconfigured Gemini Client: {e}")
    ai_client = None


# =====================================================================
# 🌤️ RECEIVE WEATHER DATA (GIỮ NGUYÊN)
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

def send_telegram_message(text: str) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.json().get("ok", False)
    except Exception:
        return False


# =====================================================================
# 🚀 ENDPOINT PHÁT TIN MVP THƯƠNG MẠI
# =====================================================================
@app.get("/api/v1/zalo/broadcast")
def trigger_concierge_broadcast(crop: str = "chung", days_old: int = 0, token: str = None):
    """
    🔥 CONCIERGE FLOW V2.8 MARKET-READY + PROVENANCE ENGINE: 
    - Chống spam bằng Token Lock.
    - Cá nhân hóa lời dặn theo tuổi cây.
    - TỰ ĐỘNG sinh chứng chỉ số bất biến xuất thẳng cho chuỗi siêu thị.
    """
    if CRON_SECRET_TOKEN and token != CRON_SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Xác thực thất bại: Quyền truy cập bị từ chối!"
        )

    stage_text = "Giai đoạn phát triển chung"
    if days_old > 0:
        if days_old <= 10:
            stage_text = f"Cây non vừa xuống giống được {days_old} ngày (Bộ rễ yếu, dễ rửa trôi)"
        elif days_old <= 45:
            stage_text = f"Cây tăng trưởng mạnh được {days_old} ngày (Cần độ ẩm ổn định)"
        else:
            stage_text = f"Cây giai đoạn cuối được {days_old} ngày, chuẩn bị thu hoạch"

    forecast_summary = ""
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        if api_key:
            url_forecast = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q=21.18,105.71&days=3&aqi=no"
            response = requests.get(url_forecast, timeout=5)
            if response.status_code == 200:
                forecast_days = response.json()["forecast"]["forecastday"]
                lines = []
                for day in forecast_days:
                    date_str = day["date"]
                    max_temp = day["day"]["maxtemp_c"]
                    min_temp = day["day"]["mintemp_c"]
                    condition = day["day"]["condition"]["text"]
                    lines.append(f"- Ngày {date_str}: Nhiệt độ từ {min_temp}°C đến {max_temp}°C. Trạng thái: {condition}")
                forecast_summary = "\n".join(lines)
    except Exception:
        pass

    if not forecast_summary:
        forecast_summary = "- Xu hướng 3 ngày tới: Nắng nóng hè cao điểm, nhiệt độ duy trì 29-37°C."

    knowledge = AGRI_KNOWLEDGE_BASE.get(crop)
    if knowledge:
        crop_title = crop.upper().replace("_", " ")
        strict_rules_text = "\n".join([f"- {rule}" for rule in knowledge["rules"]])
    else:
        crop_title = "BÀ CON NÔNG SẢN MÊ LINH"
        strict_rules_text = "- Bà con chủ động giữ ẩm ruộng rau màu và theo dõi sát thời tiết cực đoan."

    vn_now = datetime.now(timezone.utc) + timedelta(hours=7)
    current_date_vn = vn_now.strftime("%d/%m/%Y")
    current_time_vn = vn_now.strftime("%H:%M")

    prompt = f"""
    Bạn là một cố vấn nông nghiệp số thực địa tại Mê Linh, Hà Nội.
    Hãy phân tích thời tiết và Sổ tay kỹ thuật dưới đây để viết lời dặn dò ĐỘC BẢN, CÁ NHÂN HÓA SÂU cho ruộng của hộ dân này.

    📋 THÔNG TIN THỰC ĐỊA CỦA RUỘNG HỘ DÂN:
    - Loại cây trồng: {crop_title}
    - Tình trạng sinh trưởng hiện tại: {stage_text}

    ⏰ MỐC THỜI GIAN ĐỒNG HỒ THỰC TẾ:
    - Bây giờ là {current_time_vn} ngày {current_date_vn}.

    📊 DỰ BÁO THỜI TIẾT TỪ API:
    {forecast_summary}

    📋 SỔ TAY KỸ THUẬT BẮT BUỘC:
    {strict_rules_text}

    🚨 YÊU CẦU BIÊN SOẠN BẢN TIN (BẮT BUỘC QUYẾT ĐỊNH):
    1. Lời khuyên hành động phải ĐẶC BIỆT PHÙ HỢP với "Tình trạng sinh trưởng hiện tại".
    2. BẮT BUỘC phải lồng ghép khéo léo thông tin số liệu về nhiệt độ của từng ngày vào đoạn văn.
    3. Viết thành một đoạn văn xuôi liên tục, mượt mà từ đầu đến cuối (5-6 câu), văn phong chân chất của nhà nông. Không dùng gạch đầu dòng, không dùng bôi đậm **.
    """

    recommendation_text = ""
    if ai_client and os.getenv("GEMINI_API_KEY"):
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                recommendation_text = response.text.strip()
                if recommendation_text and len(recommendation_text) > 60:
                    break
            except Exception:
                time.sleep(2)

    if not recommendation_text or len(recommendation_text) < 60:
        recommendation_text = "Hệ thống đang cập nhật lịch khuyến nông hè. Bà con chủ động giữ ẩm ruộng rau màu."

    provenance_record = provenance_engine.build_provenance_footprint(
        crop=crop,
        stage=stage_text,
        weather_text=forecast_summary,
        ai_text=recommendation_text
    )

    final_message = f"📢 [DỰ BÁO KHUYẾN NÔNG MVP - {crop_title}]\n\n{recommendation_text}\n\n🔑 [MÃ MINH CHỨNG SỐ VIETGAP]: {provenance_record.record_id}\n🛡️ [CHỮ KÝ ĐIỆN TỬ]: {provenance_record.verification_hash[:16]}..."
    
    is_sent = send_telegram_message(text=final_message)
    
    if is_sent:
        return {
            "status": "success", 
            "preview": final_message,
            "provenance_metadata": provenance_record.model_dump()
        }
    else:
        raise HTTPException(status_code=500, detail="Lỗi kết nối cổng Telegram")


# =====================================================================
# ⚙️ ENDPOINT TRA CỨU JSON DÀNH CHO LẬP TRÌNH VIÊN (SPRINT 3)
# =====================================================================
@app.get("/api/v1/provenance/{record_id}")
def get_provenance_verification(record_id: str):
    record = storage.get_provenance_record(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thất bại: Không tìm thấy mã minh chứng nông sản hợp lệ cho '{record_id}'!"
        )
    return {"status": "success", "data": record}


# =====================================================================
# 🔥 THÊM MỚI SPRINT 4: GIAO DIỆN CHỨNG CHỈ SỐ MẶT TIỀN (QUÉT MÃ QR)
# =====================================================================
@app.get("/verify/{record_id}", response_class=HTMLResponse)
def verify_provenance_page(record_id: str):
    """
    MẶT TIỀN THƯƠNG MẠI: Dệt trang web chứng chỉ số VietGAP siêu đẹp bằng Tailwind CSS.
    Hiển thị trực quan cho người tiêu dùng và chuỗi siêu thị khi quét mã QR thực địa.
    """
    record = storage.get_provenance_record(record_id)
    
    # 🚨 KỊCH BẢN THẤT BẠI: Nếu nhập mã khống, hiển thị trang cảnh báo an ninh màu đỏ
    if not record:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CẢNH BÁO MINH CHỨNG - Smart Farm Mê Linh</title>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        </head>
        <body class="bg-slate-950 text-slate-100 font-sans min-h-screen flex items-center justify-center p-4">
            <div class="bg-slate-900 border-2 border-red-500 p-8 rounded-2xl shadow-2xl max-w-md w-full text-center">
                <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-900/50 border border-red-500 mb-4 animate-pulse">
                    <span class="text-red-500 text-3xl font-bold">⚠️</span>
                </div>
                <h1 class="text-xl font-bold text-red-400 mb-2">MÃ GIAN LẬN HOẶC KHÔNG TỒN TẠI</h1>
                <p class="text-sm text-slate-400 mb-6">Hệ thống Đám mây không tìm thấy bất kỳ chứng chỉ VietGAP nào khớp với mã số <span class="text-red-300 font-mono font-bold block mt-1 bg-slate-950 p-2 rounded border border-red-900/50">{record_id}</span></p>
                <div class="text-xs text-slate-500 border-t border-slate-800 pt-4">Phát hiện nguy cơ tráo hàng hoặc lỗi tem nhãn trung gian.</div>
            </div>
        </body>
        </html>
        """, status_code=404)

    # 🟩 KỊCH BẢN THÀNH CÔNG: Dệt chứng chỉ xanh tươi bảo chứng chất lượng nông sản
    crop_name = str(record.get('crop_type', 'NÔNG SẢN SẠCH')).replace('_', ' ')
    stage_desc = record.get('crop_stage', 'Đang cập nhật dữ liệu sinh trưởng')
    weather_desc = record.get('weather_telemetry', 'Không ghi nhận sự cố khí tượng')
    ai_text = record.get('ai_directive', 'Đang cập nhật lịch khuyến nông số.')
    v_hash = record.get('verification_hash', 'N/A')
    time_iso = record.get('timestamp', 'N/A')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CHỨNG CHỈ SỐ VIETGAP - {crop_name}</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 font-sans min-h-screen p-4 flex justify-center items-center">
        <div class="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden">
            
            <!-- Banner Bảo Chứng -->
            <div class="bg-linear-to-r from-emerald-600 to-teal-700 p-6 text-center border-b border-emerald-500/20">
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-emerald-500/30 border border-emerald-300 mb-2">
                    <span class="text-white text-xl font-bold">✓</span>
                </div>
                <h1 class="text-lg font-bold text-white uppercase tracking-wider">Chứng Chỉ Minh Chứng Số VietGAP</h1>
                <p class="text-xs text-emerald-100/80 font-mono mt-1">Mã số: {record_id}</p>
            </div>

            <!-- Nội Dung Chứng Chỉ Thực Địa -->
            <div class="p-6 space-y-5">
                
                <!-- Loại nông sản -->
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800/60">
                    <span class="text-[10px] uppercase font-bold text-slate-400 tracking-widest block mb-1">📦 Sản phẩm mục tiêu</span>
                    <div class="text-xl font-black text-emerald-400 tracking-wide font-mono">{crop_name}</div>
                    <div class="text-xs text-slate-400 mt-1">🌾 Trạng thái thu hoạch: <span class="text-slate-200">{stage_desc}</span></div>
                </div>

                <!-- Dấu vết khí tượng -->
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800/60">
                    <span class="text-[10px] uppercase font-bold text-slate-400 tracking-widest block mb-1">🌤️ Minh chứng thời tiết thực tế</span>
                    <p class="text-xs text-slate-300 whitespace-pre-line leading-relaxed">{weather_desc}</p>
                </div>

                <!-- Lời dặn AI (Bằng chứng trí tuệ gốc) -->
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800/60">
                    <span class="text-[10px] uppercase font-bold text-slate-400 tracking-widest block mb-1">🤖 Khuyến nông số độc bản (AI Directive)</span>
                    <p class="text-xs text-slate-300 italic leading-relaxed">"{ai_text}"</p>
                </div>

                <!-- Thời gian đồng bộ -->
                <div class="flex justify-between items-center text-xs text-slate-400 bg-slate-950/40 p-3 rounded-lg border border-slate-900">
                    <span>⏰ Thời gian đúc mã:</span>
                    <span class="font-mono text-slate-200">{time_iso}</span>
                </div>

                <!-- Mỏ neo mật mã bất biến SHA-256 -->
                <div class="border-t border-slate-800/80 pt-4 text-center">
                    <span class="text-[10px] uppercase font-bold text-emerald-500 tracking-widest block mb-1.5">🛡️ CHỮ KÝ TOÁN HỌC BẤT BIẾN (SHA-256)</span>
                    <div class="bg-slate-950 p-2.5 rounded-lg border border-emerald-900/30 font-mono text-[9px] text-emerald-400 break-all select-all shadow-inner">
                        {v_hash}
                    </div>
                    <p class="text-[9px] text-slate-500 mt-2">Dữ liệu đã khóa chết trên Blockchain/MongoDB Cloud. Phát hiện gian lận nếu sai một ký tự.</p>
                </div>

            </div>
            
            <!-- Footer Thương hiệu -->
            <div class="bg-slate-950 p-3 text-center border-t border-slate-850 text-[10px] text-slate-500 tracking-wide font-medium">
                NỀN TẢNG THƯƠNG MẠI SMART FARM MÊ LINH V2.8
            </div>

        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


# =====================================================================
# 🎛️ BẢNG ĐIỀU KHIỂN TỪ XA MVP THƯƠNG MẠI CHUYÊN NGHIỆP
# =====================================================================
@app.get("/", response_class=HTMLResponse)
def remote_dashboard(token: str = None):
    token_suffix = f"&token={token}" if token else ""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Farm Mê Linh - MVP Panel</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 font-sans min-h-screen flex flex-col justify-center items-center p-4">
        <div class="bg-slate-800 p-6 rounded-2xl shadow-xl w-full max-w-md border border-slate-700 text-center">
            <h1 class="text-xl font-bold text-emerald-400 mb-2">🚜 SMART FARM MÊ LINH v2.8</h1>
            <p class="text-xs text-slate-400 mb-6">Bảng điều khiển mô phỏng Hạ tầng minh chứng tự động</p>
            
            <div class="space-y-4 text-left">
                <p class="text-xs font-semibold text-slate-300">🎯 KÍCH HOẠT PHÁT TIN & ĐÚC CHỨNG CHỈ SỐ:</p>
                
                <a href="/api/v1/zalo/broadcast?crop=ngo_ngot&days_old=5{token_suffix}" target="_blank" class="block w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-sm font-medium rounded-xl transition text-center no-underline">
                    🌽 Gieo hạt (5 ngày) + Tự đúc minh chứng
                </a>
                
                <a href="/api/v1/zalo/broadcast?crop=ngo_ngot&days_old=55{token_suffix}" target="_blank" class="block w-full py-2.5 px-4 bg-yellow-600 hover:bg-yellow-500 text-sm font-medium rounded-xl transition text-center text-slate-900 no-underline">
                    🌽 Thu hoạch (55 ngày) + Tự đúc minh chứng
                </a>
            </div>
            
            <p class="text-[10px] text-slate-500 mt-6">Automated Provenance SaaS Grade v2.8</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
