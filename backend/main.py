import os
import sys
import time  
import requests
from datetime import datetime, timedelta, timezone  
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

load_dotenv()

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  
from pydantic import BaseModel, Field
from google import genai  
from backend.storage import MongoStorage
from backend.knowledge import AGRI_KNOWLEDGE_BASE
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
provenance_engine = ProvenanceEngine(storage_client=storage)

CRON_SECRET_TOKEN = os.getenv("CRON_SECRET_TOKEN")

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
# 🚀 ENDPOINT PHÁT TIN MVP THƯƠNG MẠI (TÍCH HỢP QR CODE)
# =====================================================================
@app.get("/api/v1/zalo/broadcast")
def trigger_concierge_broadcast(crop: str = "chung", days_old: int = 0, token: str = None):
    if CRON_SECRET_TOKEN and token != CRON_SECRET_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Xác thực thất bại!")

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
    Hãy phân tích thời tiết và Sổ tay kỹ thuật dưới đây để viết lời dặn dò ĐỘC BẢN, CÁ NHÂN HÓA SÂU cho ruộng của hộ dân này...
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
        crop=crop, stage=stage_text, weather_text=forecast_summary, ai_text=recommendation_text
    )

    final_message = (
        f"📢 [DỰ BÁO KHUYẾN NÔNG MVP - {crop_title}]\n\n"
        f"{recommendation_text}\n\n"
        f"🔑 [MÃ MINH CHỨNG SỐ VIETGAP]: {provenance_record.record_id}\n"
        f"🛡️ [CHỮ KÝ ĐIỆN TỬ]: {provenance_record.verification_hash[:16]}...\n"
        f"📷 [TEM QR CODE IN ẤN]: {provenance_record.qr_code_url}"
    )
    
    is_sent = send_telegram_message(text=final_message)
    if is_sent:
        return {"status": "success", "preview": final_message, "provenance_metadata": provenance_record.model_dump()}
    else:
        raise HTTPException(status_code=500, detail="Lỗi kết nối cổng Telegram")

# =====================================================================
# ⚙️ ENDPOINT TRA CỨU JSON DÀNH CHO LẬP TRÌNH VIÊN
# =====================================================================
@app.get("/api/v1/provenance/{record_id}")
def get_provenance_verification(record_id: str):
    record = storage.get_provenance_record(record_id, increment=False)
    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã minh chứng nông sản!")
    return {"status": "success", "data": record}

# =====================================================================
# 🎨 ENDPOINT MẶT TIỀN GIAO DIỆN (QUÉT MÃ QR THẬT CỦA KHÁCH MUA HÀNG)
# =====================================================================
@app.get("/verify/{record_id}", response_class=HTMLResponse)
def verify_provenance_page(record_id: str):
    record = storage.get_provenance_record(record_id, increment=True)
    html_content = provenance_engine.render_html_certificate(record_id, record)
    status_code = status.HTTP_200_OK if record else status.HTTP_404_NOT_FOUND
    return HTMLResponse(content=html_content, status_code=status_code)

# =====================================================================
# 📊 TRANG TRUNG TÂM SỔ CÁI B2B CÔNG KHAI (AUDIT LEDGER HUB)
# =====================================================================
@app.get("/ledger", response_class=HTMLResponse)
def view_provenance_ledger(limit: int = 20):
    records = storage.get_all_provenance_records(limit=limit)
    html_content = provenance_engine.render_html_ledger(records)
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)

# =====================================================================
# 🎛️ NÂNG CẤP MẠNH MẼ: BẢNG ĐIỀU KHIỂN BÌNH DÂN CHO BÀ CON NÔNG DÂN
# =====================================================================
@app.get("/", response_class=HTMLResponse)
def remote_dashboard(token: str = None):
    default_token = token if token else ""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trạm Đúc Tem QR - Smart Farm Mê Linh</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 font-sans min-h-screen p-4 flex flex-col justify-center items-center">
        
        <div class="w-full max-w-md bg-slate-900 border border-slate-800 p-6 rounded-3xl shadow-2xl space-y-6">
            <div class="text-center">
                <span class="text-xs font-bold text-emerald-400 tracking-widest uppercase block mb-1">Hạ Tầng Thực Địa</span>
                <h1 class="text-xl font-black text-white uppercase tracking-wide">🌾 TRẠM ĐÚC TEM QR MÊ LINH</h1>
                <p class="text-xs text-slate-400 mt-1">Bà con nhập số tuổi cây để đúc nhãn VietGAP dán bao bì</p>
            </div>

            <!-- FORM ĐIỀU KHIỂN BÌNH DÂN -->
            <div class="space-y-4">
                <div>
                    <label class="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">📦 Chọn Loại Nông Sản</label>
                    <select id="cropSelect" class="w-full bg-slate-950 border border-slate-800 text-slate-200 px-3 py-2.5 rounded-xl text-sm focus:outline-none focus:border-emerald-500">
                        <option value="ngo_ngot">🌽 Ngô ngọt Mê Linh</option>
                        <option value="rau_cai">🥬 Rau cải xanh bẹ</option>
                        <option value="ca_chua">🍅 Cà chua thực phẩm</option>
                    </select>
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">🌱 Số Ngày Tuổi Của Cây (Từ khi trồng)</label>
                    <input type="number" id="daysInput" value="5" min="1" max="120" class="w-full bg-slate-950 border border-slate-800 text-slate-200 px-3 py-2.5 rounded-xl text-sm font-mono focus:outline-none focus:border-emerald-500" />
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">🔑 Mã Bảo Mật Ruộng Nông Trại</label>
                    <input type="text" id="tokenInput" value="{default_token}" placeholder="Nhập mã bí mật được cấp" class="w-full bg-slate-950 border border-slate-800 text-slate-200 px-3 py-2.5 rounded-xl text-sm font-mono focus:outline-none focus:border-emerald-500" />
                </div>

                <button onclick="executeForgeQR()" id="btnSubmit" class="w-full py-3 bg-emerald-600 hover:bg-emerald-500 active:scale-[0.98] transition text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-900/20 cursor-pointer">
                    🚀 ĐÚC TEM & PHÁT TIN KHUYẾN NÔNG
                </button>
            </div>

            <!-- KẾT QUẢ ĐÚC TEM XUẤT HIỆN TẠI ĐÂY (XÓA BỎ GIAO DIỆN JSON RAW) -->
            <div id="resultWidget" class="hidden bg-slate-950 border border-emerald-900/40 p-4 rounded-2xl space-y-4 animate-fade-in">
                <div class="text-center border-b border-slate-800 pb-3">
                    <span class="inline-flex items-center gap-1 text-[11px] font-black uppercase tracking-widest text-emerald-400">
                        🎉 Đúc Mã Thành Công!
                    </span>
                    <div id="recordIdLabel" class="text-xs font-mono text-slate-400 mt-1">Mã: REC-XXXX</div>
                </div>

                <!-- 📷 Ảnh QR thật hiện ra ngay trên màn hình để bà con cất điện thoại đi in -->
                <div class="flex flex-col items-center justify-center bg-white p-3 rounded-xl border border-slate-800">
                    <img id="qrImage" src="" alt="QR Code" class="w-40 h-40 object-contain" />
                    <span class="text-[9px] text-slate-500 font-bold mt-1.5 uppercase">📷 Nhấn giữ ảnh để tải về máy in tem</span>
                </div>

                <div class="space-y-1">
                    <span class="text-[10px] uppercase font-bold text-slate-400 block">🤖 Khuyến nông số đã phát:</span>
                    <p id="aiDirectiveLabel" class="text-xs text-slate-300 italic bg-slate-900 p-2.5 rounded-lg border border-slate-800 leading-relaxed"></p>
                </div>
            </div>

            <div class="text-center border-t border-slate-800/60 pt-4">
                <a href="/ledger" class="text-xs text-slate-500 hover:text-emerald-400 font-medium no-underline">🛡️ Xem Sổ Cái Hành Trình Nông Trại →</a>
            </div>
        </div>

        <script>
            async function executeForgeQR() {{
                const btn = document.getElementById("btnSubmit");
                const widget = document.getElementById("resultWidget");
                const crop = document.getElementById("cropSelect").value;
                const days = document.getElementById("daysInput").value;
                const token = document.getElementById("tokenInput").value;

                btn.disabled = true;
                btn.innerText = "⏳ ĐANG XỬ LÝ & ĐÚC CHỮ KÝ SỐ...";
                widget.classList.add("hidden");

                try {{
                    const res = await fetch(`/api/v1/zalo/broadcast?crop=${{crop}}&days_old=${{days}}&token=${{token}}`);
                    if (!res.ok) {{
                        const errorData = await res.json();
                        alert("❌ Thất bại: " + (errorData.detail || "Lỗi hệ thống"));
                        return;
                    }}
                    
                    const data = await res.json();
                    const metadata = data.provenance_metadata;

                    // Bơm dữ liệu thật vào màn hình cho nông dân xem
                    document.getElementById("recordIdLabel").innerText = "Mã số lô: " + metadata.record_id;
                    document.getElementById("qrImage").src = metadata.qr_code_url;
                    document.getElementById("aiDirectiveLabel").innerText = '"' + metadata.ai_directive + '"';
                    
                    // Hiện hộp đồ họa
                    widget.classList.remove("hidden");
                }} catch (err) {{
                    alert("❌ Lỗi kết nối máy chủ đám mây!");
                }} finally {{
                    btn.disabled = false;
                    btn.innerText = "🚀 ĐÚC TEM & PHÁT TIN KHUYẾN NÔNG";
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
