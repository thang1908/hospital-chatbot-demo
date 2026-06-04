# Hospital Appointment Chatbot Demo

## Thông tin nhóm

- **Tên nhóm:** Hospital Appointment Chatbot Demo
- **Track:** Healthcare
- **Thành viên:**
  - `2A202600934` - Trần Trúc Quỳnh
  - `2A202600855` - Nguyễn Tiến Huân
  - `2A202600840` - Nguyễn Nam Thắng
  - `2A202600663` - Phạm Huy Cảnh
  - `2A202600810` - Nguyễn Xuân Tới
  - `2A202600575` - Phạm Thị Bích Ngọc

---

Prototype hackathon cho đề tài chatbot hỗ trợ đặt lịch khám bệnh viện.

## Mục tiêu demo

Flow truyền thống hiện tại:

```
Nhập thông tin người khám
→ Chọn khám theo chuyên khoa hoặc theo bác sĩ
→ Chọn ngày khám
→ Xem lịch còn trống
→ Đặt lịch và xác nhận
```

**Điểm gãy:** Người bệnh thường không biết nên chọn chuyên khoa hay bác sĩ nào khi chỉ có triệu chứng ban đầu.

Prototype này thêm một lớp AI trước flow đặt lịch:

```
Nhập thông tin người khám
→ Chatbot hỏi đáp triệu chứng
→ AI gợi ý chuyên khoa hoặc phát hiện red flag
→ Chọn ngày, xem slot còn trống
→ Xác nhận lịch khám
```

---

## Kiến trúc

```
hospital-chatbot-demo
├── docker-compose.yml
├── backend
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app
│       ├── data
│       │   └── chuyenkhoa.json        # Dữ liệu 30+ chuyên khoa
│       ├── main.py                    # FastAPI entry point
│       ├── core
│       │   └── config.py
│       ├── db
│       │   ├── models.py              # Booking, SpecialtyInfo, Doctor, AppointmentSlot
│       │   ├── session.py
│       │   └── init.py                # Seed DB khi khởi động
│       ├── routers
│       │   ├── bookings.py
│       │   ├── catalog.py
│       │   └── chat.py
│       └── services
│           ├── mock_catalog.py        # Dữ liệu mẫu bác sĩ + slot (seed + fallback)
│           ├── specialty_knowledge.py # Logic tìm kiếm & scoring chuyên khoa
│           ├── tools.py               # LangChain tools: search_hospital_specialties, query_available_slots
│           └── triage_graph.py        # LangGraph workflow
└── frontend
    ├── Dockerfile
    ├── package.json
    └── src
        ├── main.jsx                   # React app (single file)
        └── styles.css                 # Mobile-style UI
```

---

## Tech stack

| Layer | Công nghệ |
|---|---|
| Frontend | React + Vite, giao diện kiểu mobile app |
| Backend | FastAPI |
| AI workflow | LangGraph (`StateGraph`) |
| AI agent | LangChain `create_agent` + `ChatOpenAI` (gpt-4o-mini) |
| AI tools | `search_hospital_specialties`, `query_available_slots` |
| Database | PostgreSQL (Docker) |
| Container | Docker Compose |

---

## Luồng AI xử lý triệu chứng

Khi user gửi tin nhắn mô tả triệu chứng, backend chạy qua pipeline sau:

```
User nhập triệu chứng
        │
        ▼
POST /api/chat/triage
(gửi kèm: thông tin bệnh nhân + toàn bộ messages)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                   LangGraph                         │
│                                                     │
│  1. collect_context                                 │
│     → Tách latest_user_text (tin nhắn mới nhất)    │
│     → Tạo conversation_text (8 turns gần nhất)     │
│                                                     │
│  2. analyze_symptoms  ← node chính                 │
│     → Gọi LangChain Agent (ChatOpenAI)             │
│     → Agent bắt buộc gọi tool trước khi trả kết quả│
│                                                     │
│       Tool 1: search_hospital_specialties          │
│         Input : chuỗi triệu chứng                  │
│         Xử lý : normalize text → tokenize          │
│                 → score từng chuyên khoa trong DB  │
│                   (token overlap + hint keywords)  │
│         Output: top 6 chuyên khoa phù hợp nhất    │
│                                                     │
│       Tool 2: query_available_slots                │
│         Input : tên chuyên khoa đã chọn            │
│         Xử lý : query bảng appointment_slots       │
│                 → fuzzy match tên chuyên khoa      │
│         Output: danh sách slot còn trống           │
│                                                     │
│     → Agent trả TriageAnalysis (structured output)│
│       • specialty + specialty_id                   │
│       • confidence (0–1)                           │
│       • red_flags / warning_signs                  │
│       • needs_more_info                            │
│       • follow_up_questions                        │
│       • reasoning_summary                          │
│       • matched_specialties + slots                │
│                                                     │
│  3. route_case (conditional edge)                  │
│     ├── red_flags?      → handle_red_flag          │
│     │     Dừng flow, khuyến nghị cấp cứu           │
│     ├── needs_more_info → handle_low_confidence    │
│     │     Hỏi thêm 1–2 câu làm rõ                 │
│     └── đủ thông tin   → handle_happy_path        │
│           Gợi ý chuyên khoa + hiện slot đặt lịch  │
└─────────────────────────────────────────────────────┘
        │
        ▼
JSON response → Frontend hiển thị bubble chat
```

### Nguồn dữ liệu

| Bảng / File | Nội dung | Được dùng bởi |
|---|---|---|
| `chuyenkhoa.json` | 30+ chuyên khoa, tên + mô tả | Seed vào Postgres lúc khởi động |
| `mock_catalog.py` | 8 bác sĩ + 14 slot mẫu | Seed DB; fallback khi DB trống |
| Postgres `specialties` | Chuyên khoa + search_text đã index | Tool 1: tìm kiếm chuyên khoa |
| Postgres `appointment_slots` | Lịch trống theo ngày + giờ | Tool 2: truy vấn slot |
| Postgres `bookings` | Lịch hẹn đã xác nhận | Router `/api/bookings` |

### Fallback khi không có OpenAI key

Agent trả về `needs_more_info=true` với thông báo lỗi rõ ràng. Frontend hiển thị low-confidence path, không crash.

---

## Chạy demo bằng Docker

```bash
cp backend/.env.example backend/.env
# Điền OPENAI_API_KEY trong backend/.env
docker compose up --build
```

Mở:
- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## Deploy với ngrok (public URL)

Để truy cập từ điện thoại hoặc chia sẻ demo:

### Bước 1: Cài ngrok

```bash
# macOS
brew install ngrok

# hoặc tải từ https://ngrok.com/download
```

### Bước 2: Lấy authtoken

1. Đăng ký tài khoản miễn phí tại https://ngrok.com
2. Lấy authtoken tại https://dashboard.ngrok.com/get-started/your-authtoken
3. Chạy: `ngrok config add-authtoken YOUR_TOKEN`

### Bước 3: Chạy script setup

```bash
./start-ngrok.sh
```

Script sẽ tạo file `ngrok.yml` với cấu hình 2 tunnels (backend + frontend).

### Bước 4: Start tunnels

```bash
ngrok start --all --config ngrok.yml
```

Bạn sẽ thấy 2 URL:
- `https://xxxx-backend.ngrok-free.app` → Backend
- `https://yyyy-frontend.ngrok-free.app` → Frontend

### Bước 5: Cập nhật config

**Backend CORS** — sửa `backend/.env`:
```env
FRONTEND_URL=https://yyyy-frontend.ngrok-free.app
```

**Frontend API URL** — rebuild với env:
```bash
docker compose build frontend --build-arg VITE_API_BASE_URL=https://xxxx-backend.ngrok-free.app
```

Hoặc đơn giản hơn: sửa trực tiếp `frontend/src/main.jsx`:
```js
const API_BASE_URL = "https://xxxx-backend.ngrok-free.app";
```

### Bước 6: Restart

```bash
docker compose restart backend
docker compose restart frontend
```

Giờ mở `https://yyyy-frontend.ngrok-free.app` từ điện thoại để test.

---

## API chính

### Triage chat

```http
POST /api/chat/triage
Content-Type: application/json

{
  "patient": { "name": "...", "phone": "...", "birth_year": 1990 },
  "messages": [
    { "role": "user", "content": "Tôi đau bụng âm ỉ 3 ngày nay" }
  ]
}
```

Response:
```json
{
  "path": "happy",
  "reply": "Dựa trên mô tả, tôi gợi ý khám Nội - Tiêu Hóa.",
  "specialty": "Nội - Tiêu Hóa",
  "specialty_id": "...",
  "confidence": 0.9,
  "slots": [...],
  "booking_ready": true
}
```

### Lấy slot còn trống

```http
GET /api/catalog/slots?specialty=Nội - Tiêu Hóa&date=2026-06-05
```

### Tạo booking

```http
POST /api/bookings
```

---

## Test case demo

**Happy path** — triệu chứng rõ, đủ để chọn chuyên khoa:
```
Tôi đau bụng âm ỉ 3 ngày nay, hay buồn nôn sau khi ăn
```
→ Gợi ý Nội - Tiêu Hóa → hiện slot → xác nhận đặt lịch.

**Low-confidence path** — triệu chứng mơ hồ:
```
Tôi thấy mệt
```
→ Bot hỏi thêm, không tự kết luận chuyên khoa.

**Red flag path** — dấu hiệu khẩn cấp:
```
Tôi đau ngực dữ dội và khó thở
```
→ Bot dừng flow đặt lịch, khuyến nghị liên hệ cấp cứu.

**Correction path:**
```
Chọn slot → vào màn xác nhận → bấm Sửa lịch → chọn slot khác.
```

---

## Không build trong demo 3 tiếng

- Đăng nhập và OTP
- Tích hợp lịch thật của bệnh viện
- Thanh toán
- Hồ sơ bệnh án
- Chẩn đoán bệnh hoặc kê đơn
- Admin dashboard

---

## Câu nói khi demo

> Prototype không thay thế toàn bộ flow đặt lịch truyền thống. Nó chỉ giải quyết điểm gãy trước khi đặt lịch: người bệnh không biết nên chọn chuyên khoa hay bác sĩ nào. AI hỏi thêm triệu chứng, gợi ý chuyên khoa hoặc dừng flow khi có red flag, sau đó user vẫn xác nhận lịch khám bằng form rõ ràng.
