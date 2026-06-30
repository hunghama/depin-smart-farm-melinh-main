# =====================================================================
# STAGE 1: BUILDER - TẬP KÍCH VÀ BIÊN DỊCH THƯ VIỆN LÕI
# =====================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài đặt các công cụ biên dịch để build các package đặc thù nếu cần
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy danh sách thư viện và tiến hành cài đặt vào phân vùng cô lập
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =====================================================================
# STAGE 2: RUNTIME - ĐÓNG GÓI SIÊU NHẸ CHUẨN PRODUCTION
# =====================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Chỉ bốc phần thư viện sạch đã được biên dịch từ Stage 1 sang, loại bỏ rác biên dịch
COPY --from=builder /root/.local /root/.local
COPY . .

# Cấu hình biến môi trường hệ thống và PATH cho Container
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Mở cổng 8000 đón tiếp request từ Cloud Router
EXPOSE 8000

# Khai hỏa Uvicorn Server phục vụ giao tiếp diện rộng
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

