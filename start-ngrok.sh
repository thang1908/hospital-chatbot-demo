#!/bin/bash

# Script để chạy ngrok cho frontend và backend
# Yêu cầu: cài ngrok và đã chạy `docker compose up`

set -e

echo "==================================="
echo "Starting ngrok tunnels..."
echo "==================================="

# Kiểm tra ngrok đã cài chưa
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok chưa được cài đặt."
    echo "Cài đặt ngrok tại: https://ngrok.com/download"
    exit 1
fi

# Kiểm tra Docker services đang chạy
if ! curl -s http://localhost:8000/health &> /dev/null; then
    echo "❌ Backend chưa chạy. Vui lòng chạy 'docker compose up' trước."
    exit 1
fi

if ! curl -s http://localhost:5173 &> /dev/null; then
    echo "❌ Frontend chưa chạy. Vui lòng chạy 'docker compose up' trước."
    exit 1
fi

echo ""
echo "✅ Services đã sẵn sàng."
echo ""

# Tạo file ngrok config
cat > ngrok.yml <<EOF
version: "2"
authtoken: YOUR_NGROK_AUTHTOKEN
tunnels:
  backend:
    proto: http
    addr: 8000
  frontend:
    proto: http
    addr: 5173
EOF

echo "📝 Đã tạo file ngrok.yml"
echo ""
echo "⚠️  QUAN TRỌNG:"
echo "1. Mở file ngrok.yml và thay YOUR_NGROK_AUTHTOKEN bằng authtoken của bạn"
echo "   Lấy authtoken tại: https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
echo "2. Sau khi điền authtoken, chạy lệnh:"
echo "   ngrok start --all --config ngrok.yml"
echo ""
echo "3. Copy 2 URL ngrok hiển thị (backend và frontend)"
echo ""
echo "4. Cập nhật CORS trong backend/.env:"
echo "   FRONTEND_URL=https://YOUR-FRONTEND-URL.ngrok-free.app"
echo ""
echo "5. Restart backend: docker compose restart backend"
echo ""
echo "6. Truy cập frontend URL từ điện thoại/máy khác để test"
echo "==================================="
