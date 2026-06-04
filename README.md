# Hospital Appointment Chatbot Demo

Prototype hackathon cho de tai chatbot ho tro dat lich kham benh vien.

## Muc tieu demo

Flow truyen thong hien tai:

```text
Nhap thong tin nguoi kham
-> Chon kham theo chuyen khoa hoac theo bac si
-> Chon ngay kham
-> Xem lich con trong
-> Dat lich va xac nhan
```

Diem gay:

```text
Nguoi benh thuong khong biet nen chon chuyen khoa hay bac si nao khi chi co trieu chung ban dau.
```

Prototype nay them mot lop AI truoc flow dat lich:

```text
Nhap thong tin nguoi kham
-> Chatbot hoi dap trieu chung
-> AI goi y chuyen khoa hoac phat hien red flag
-> Chon ngay, xem slot con trong
-> Xac nhan lich kham
```

## Kien truc

```text
hospital-chatbot-demo
├── docker-compose.yml
├── backend
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app
│       ├── data
│       │   └── chuyenkhoa.json
│       ├── main.py
│       ├── db
│       │   ├── models.py
│       │   └── session.py
│       ├── routers
│       │   ├── bookings.py
│       │   ├── catalog.py
│       │   └── chat.py
│       └── services
│           ├── mock_catalog.py
│           ├── specialty_knowledge.py
│           ├── specialty_tools.py
│           └── triage_graph.py
└── frontend
    ├── Dockerfile
    ├── package.json
    └── src
        ├── main.jsx
        └── styles.css
```

## Tech stack

- Frontend: React + Vite
- Backend: FastAPI
- AI workflow: LangGraph
- AI agent layer: LangChain `create_agent` + `ChatOpenAI`
- AI tool: `search_hospital_specialties` tra cuu DB chuyen khoa seed tu `chuyenkhoa.json`
- Database: Postgres
- Container: Docker Compose

## Chay demo bang Docker

```bash
cp backend/.env.example backend/.env
# Dien OPENAI_API_KEY trong backend/.env de dung ChatOpenAI agent.
# Neu bo trong key, backend tu fallback ve rule + specialty DB.
docker compose up --build
```

Docker Compose tu nap `backend/.env` cho backend, nen khong can truyen `--env-file`.

Mo:

- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## API chinh

### Triage chat

```http
POST /api/chat/triage
```

Input gom thong tin nguoi kham va danh sach message. Backend chay qua LangGraph:

```text
collect_context -> analyze_symptoms(agent + specialty-search tool + safety rules) -> route
  -> happy
  -> low-confidence
  -> failure / red flag
```

Danh muc chuyen khoa duoc seed vao bang `specialties` khi backend khoi dong.
Agent phai goi tool tim chuyen khoa truoc khi tra structured output.

### Lay slot con trong

```http
GET /api/catalog/slots?specialty=Tieu%20hoa&date=2026-06-05
```

### Tao booking

```http
POST /api/bookings
```

Booking duoc luu vao Postgres de demo sau khi user xac nhan.

## Test case demo

Happy path:

```text
Toi dau bung am i 3 ngay nay, hay buon non sau khi an
```

Ket qua mong doi:

```text
Goi y chuyen khoa Tieu hoa -> hien slot -> xac nhan dat lich.
```

Low-confidence path:

```text
Toi thay met
```

Ket qua mong doi:

```text
Bot hoi them thong tin, khong tu ket luan chuyen khoa.
```

Failure path:

```text
Toi dau nguc du doi va kho tho
```

Ket qua mong doi:

```text
Bot dung flow dat lich thuong va khuyen nghi lien he cap cuu/nhan vien benh vien.
```

Correction path:

```text
Chon slot -> vao man xac nhan -> bam Sua lich -> chon slot khac.
```

## Khong build trong demo 3 tieng

- Dang nhap va OTP.
- Tich hop lich that cua benh vien.
- Thanh toan.
- Ho so benh an.
- Chan doan benh hoac ke don.
- Admin dashboard.

## Cau noi khi demo

```text
Prototype khong thay the toan bo flow dat lich truyen thong. No chi giai quyet diem gay truoc khi dat lich: nguoi benh khong biet nen chon chuyen khoa hay bac si nao. AI hoi them trieu chung, goi y chuyen khoa hoac dung flow khi co red flag, sau do user van xac nhan lich kham bang form ro rang.
```
