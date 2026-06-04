import React from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Bot,
  CalendarCheck,
  CheckCircle2,
  RotateCcw,
  Send,
  Stethoscope,
  User,
} from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [messages, setMessages] = React.useState([
    {
      id: "intro",
      role: "assistant",
      type: "text",
      content:
        "Xin chào! Tôi là trợ lý đặt lịch khám của bệnh viện. Để bắt đầu, bạn vui lòng cung cấp thông tin cá nhân nhé.",
    },
    { id: "patient-form", role: "assistant", type: "patient-form" },
  ]);

  const [patient, setPatient] = React.useState({ name: "", phone: "", birth_year: "" });
  const [patientConfirmed, setPatientConfirmed] = React.useState(false);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [chatMessages, setChatMessages] = React.useState([]);
  const [booking, setBooking] = React.useState(null);
  const messagesEndRef = React.useRef(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function confirmPatient() {
    if (!patient.name.trim() || !patient.phone.trim()) return;
    setMessages((prev) =>
      prev
        .map((m) => (m.type === "patient-form" ? { ...m, confirmed: true } : m))
        .concat({
          id: `msg-${Date.now()}`,
          role: "assistant",
          type: "text",
          content: `Xin chào **${patient.name}**! Bây giờ hãy cho tôi biết bạn đang có triệu chứng hay vấn đề sức khoẻ gì?`,
        })
    );
    setPatientConfirmed(true);
  }

  // Khi user bấm "Đặt lịch ngay" trên ask-booking bubble
  async function startBooking(specialty, existingSlots) {
    // Lock ask-booking bubble
    setMessages((prev) =>
      prev.map((m) => (m.type === "ask-booking" ? { ...m, locked: true } : m))
    );
    setLoading(true);
    try {
      // Dùng slots từ agent nếu có, không thì fetch
      let slots = existingSlots?.length ? existingSlots : null;
      if (!slots) {
        const res = await fetch(
          `${API_BASE_URL}/api/catalog/slots?specialty=${encodeURIComponent(specialty)}`
        );
        slots = await res.json();
      }
      setMessages((prev) => [
        ...prev,
        {
          id: `dt-form-${Date.now()}`,
          role: "assistant",
          type: "datetime-form",
          specialty,
          slots,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          type: "alert",
          content: "Không lấy được lịch trống. Vui lòng thử lại.",
          alertType: "warning",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function declineBooking() {
    setMessages((prev) =>
      prev.map((m) => (m.type === "ask-booking" ? { ...m, locked: true } : m)).concat({
        id: `reply-${Date.now()}`,
        role: "assistant",
        type: "text",
        content: "Được rồi! Nếu bạn cần hỗ trợ thêm, hãy cho tôi biết nhé.",
      })
    );
  }

  async function sendMessage(text = input) {
    const content = text.trim();
    if (!content || loading || !patientConfirmed) return;

    setInput("");

    const userMsg = { id: `user-${Date.now()}`, role: "user", type: "text", content };
    const nextChatMessages = [...chatMessages, { role: "user", content }];
    setMessages((prev) => [...prev, userMsg]);
    setChatMessages(nextChatMessages);
    setLoading(true);

    const thinkingId = `thinking-${Date.now()}`;
    setMessages((prev) => [...prev, { id: thinkingId, role: "assistant", type: "thinking" }]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient: {
            name: patient.name,
            phone: patient.phone,
            birth_year: patient.birth_year ? Number(patient.birth_year) : null,
          },
          messages: nextChatMessages,
        }),
      });
      const data = await response.json();
      setChatMessages([...nextChatMessages, { role: "assistant", content: data.reply }]);
      setMessages((prev) => prev.filter((m) => m.id !== thinkingId));

      if (data.path === "happy" && data.specialty) {
        if (data.booking_ready !== false) {
          // Lần đầu gợi ý chuyên khoa → hiện nút đặt lịch
          setMessages((prev) => [
            ...prev,
            { id: `reply-${Date.now()}`, role: "assistant", type: "text", content: data.reply },
            {
              id: `ask-book-${Date.now()}`,
              role: "assistant",
              type: "ask-booking",
              specialty: data.specialty,
              slots: data.slots || [],
            },
          ]);
        } else {
          // User đang hỏi lịch → chỉ hiện text reply
          setMessages((prev) => [
            ...prev,
            { id: `reply-${Date.now()}`, role: "assistant", type: "text", content: data.reply },
          ]);
        }
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `reply-${Date.now()}`,
            role: "assistant",
            type: data.path === "failure" ? "alert" : "text",
            content: data.reply,
            alertType: data.path === "failure" ? "danger" : null,
          },
        ]);
      }
    } catch {
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== thinkingId)
          .concat({
            id: `err-${Date.now()}`,
            role: "assistant",
            type: "alert",
            content: "Không thể kết nối backend. Hãy kiểm tra Docker/FastAPI và thử lại.",
            alertType: "warning",
          })
      );
    } finally {
      setLoading(false);
    }
  }

  async function confirmBooking(slot) {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/bookings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient: {
            name: patient.name,
            phone: patient.phone,
            birth_year: patient.birth_year ? Number(patient.birth_year) : null,
          },
          symptom_summary:
            chatMessages
              .filter((m) => m.role === "user")
              .map((m) => m.content)
              .join(" | ") || "Không có",
          specialty: slot.specialty,
          doctor: slot.doctor || null,
          appointment_date: slot.date,
          appointment_time: slot.time,
        }),
      });
      const data = await response.json();
      setBooking(data);
      setMessages((prev) =>
        prev
          .map((m) => (m.type === "datetime-form" ? { ...m, locked: true } : m))
          .concat({
            id: `confirm-${Date.now()}`,
            role: "assistant",
            type: "confirmation",
            booking: data,
            slot,
          })
      );
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          type: "alert",
          content: "Đặt lịch thất bại. Vui lòng thử lại.",
          alertType: "warning",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function resetDemo() {
    setMessages([
      {
        id: "intro",
        role: "assistant",
        type: "text",
        content:
          "Xin chào! Tôi là trợ lý đặt lịch khám của bệnh viện. Để bắt đầu, bạn vui lòng cung cấp thông tin cá nhân nhé.",
      },
      { id: "patient-form", role: "assistant", type: "patient-form" },
    ]);
    setPatient({ name: "", phone: "", birth_year: "" });
    setPatientConfirmed(false);
    setInput("");
    setLoading(false);
    setChatMessages([]);
    setBooking(null);
  }

  const isDone = !!booking;

  return (
    <div className="chat-app">
      <header className="chat-header">
        <div className="chat-header-brand">
          <div className="header-icon">
            <Stethoscope size={20} />
          </div>
          <div>
            <h1>Trợ lý đặt lịch khám</h1>
            <p>Bệnh viện Demo · Tư vấn & đặt lịch tự động</p>
          </div>
        </div>
        <button className="reset-btn" onClick={resetDemo} title="Bắt đầu lại">
          <RotateCcw size={16} />
          <span>Đặt lại</span>
        </button>
      </header>

      <div className="chat-body">
        <div className="messages-container">
          {messages.map((msg) => (
            <MessageRow
              key={msg.id}
              msg={msg}
              patient={patient}
              setPatient={setPatient}
              onConfirmPatient={confirmPatient}
              onConfirmBooking={confirmBooking}
              onStartBooking={startBooking}
              onDeclineBooking={declineBooking}
              loading={loading}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {!isDone && (
        <div className="chat-input-bar">
          {patientConfirmed && !loading && (
            <div className="quick-replies">
              {[
                "Tôi đau bụng âm ỉ 3 ngày nay",
                "Tôi bị đau đầu và sốt nhẹ",
                "Tôi đau ngực dữ dội và khó thở",
                "Tôi thấy mệt mỏi",
              ].map((q) => (
                <button key={q} className="quick-chip" onClick={() => sendMessage(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}
          <div className="input-row">
            <input
              className="chat-input"
              placeholder={
                !patientConfirmed
                  ? "Điền thông tin bên trên trước..."
                  : "Mô tả triệu chứng của bạn..."
              }
              value={input}
              disabled={!patientConfirmed || loading}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={!patientConfirmed || loading || !input.trim()}
            >
              <Send size={18} />
            </button>
          </div>
          <p className="input-hint">AI chỉ gợi ý khoa — không thay thế chẩn đoán y khoa.</p>
        </div>
      )}
    </div>
  );
}

// ─── MessageRow ────────────────────────────────────────────────────────────
function MessageRow({ msg, patient, setPatient, onConfirmPatient, onConfirmBooking, onStartBooking, onDeclineBooking, loading }) {
  const isUser = msg.role === "user";

  if (msg.type === "thinking") {
    return (
      <div className="msg-row assistant">
        <BotAvatar />
        <div className="bubble assistant thinking-bubble">
          <span className="dot" /><span className="dot" /><span className="dot" />
        </div>
      </div>
    );
  }

  if (msg.type === "ask-booking") {
    return (
      <div className="msg-row assistant">
        <BotAvatar />
        <div className="bubble assistant">
          {msg.locked ? (
            <span style={{ color: "var(--gray-400)", fontSize: 13 }}>Đã xử lý.</span>
          ) : (
            <div className="ask-booking">
              <span>Bạn có muốn đặt lịch khám <strong>{msg.specialty}</strong> không? Tôi có thể hỗ trợ bạn ngay bây giờ.</span>
              <div className="ask-booking-actions">
                <button className="confirm-btn" onClick={() => onStartBooking(msg.specialty, msg.slots)}>
                  Đặt lịch ngay
                </button>
                <button className="decline-btn" onClick={onDeclineBooking}>
                  Không, cảm ơn
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (msg.type === "patient-form") {
    return (
      <div className="msg-row assistant">
        <BotAvatar />
        <div className="bubble assistant wide-bubble">
          {msg.confirmed ? (
            <div className="form-confirmed">
              <CheckCircle2 size={16} className="icon-green" />
              <span>Thông tin đã xác nhận: <strong>{patient.name}</strong> · {patient.phone}</span>
            </div>
          ) : (
            <PatientForm patient={patient} setPatient={setPatient} onConfirm={onConfirmPatient} />
          )}
        </div>
      </div>
    );
  }

  if (msg.type === "datetime-form") {
    return (
      <div className="msg-row assistant">
        <BotAvatar />
        <div className="bubble assistant wide-bubble">
          <DateTimeForm
            specialty={msg.specialty}
            slots={msg.slots}
            locked={msg.locked}
            onConfirm={onConfirmBooking}
            loading={loading}
          />
        </div>
      </div>
    );
  }

  if (msg.type === "confirmation") {
    return (
      <div className="msg-row assistant">
        <BotAvatar />
        <div className="bubble assistant wide-bubble">
          <ConfirmationCard booking={msg.booking} slot={msg.slot} />
        </div>
      </div>
    );
  }

  if (msg.type === "alert") {
    return (
      <div className="msg-row assistant">
        <BotAvatar />
        <div className={`bubble assistant alert-bubble ${msg.alertType || "warning"}`}>
          <AlertTriangle size={16} />
          <span>{msg.content}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`msg-row ${isUser ? "user" : "assistant"}`}>
      {!isUser && <BotAvatar />}
      <div className={`bubble ${isUser ? "user" : "assistant"}`}>
        <RichText text={msg.content} />
      </div>
      {isUser && <UserAvatar />}
    </div>
  );
}

// ─── PatientForm ───────────────────────────────────────────────────────────
function PatientForm({ patient, setPatient, onConfirm }) {
  const valid = patient.name.trim().length >= 2 && patient.phone.trim().length >= 8;
  return (
    <div className="inline-form">
      <p className="form-title">
        <User size={14} />
        Thông tin người khám
      </p>
      <div className="inline-form-fields">
        <label>
          Họ và tên *
          <input
            placeholder="Nguyễn Văn A"
            value={patient.name}
            onChange={(e) => setPatient((p) => ({ ...p, name: e.target.value }))}
          />
        </label>
        <label>
          Số điện thoại *
          <input
            placeholder="0901234567"
            value={patient.phone}
            onChange={(e) => setPatient((p) => ({ ...p, phone: e.target.value }))}
          />
        </label>
        <label>
          Năm sinh
          <input
            type="number"
            placeholder="1990"
            value={patient.birth_year}
            onChange={(e) => setPatient((p) => ({ ...p, birth_year: e.target.value }))}
          />
        </label>
      </div>
      <button className="confirm-btn" onClick={onConfirm} disabled={!valid}>
        Xác nhận & bắt đầu tư vấn
      </button>
    </div>
  );
}

// ─── DateTimeForm ──────────────────────────────────────────────────────────
function DateTimeForm({ specialty, slots, locked, onConfirm, loading }) {
  const [specialties, setSpecialties] = React.useState([]);
  const [selectedSpecialty, setSelectedSpecialty] = React.useState(specialty || "");
  const [availableSlots, setAvailableSlots] = React.useState(slots || []);
  const [loadingSlots, setLoadingSlots] = React.useState(false);

  const [selectedDate, setSelectedDate] = React.useState("");
  const [selectedTime, setSelectedTime] = React.useState("");
  const [confirmed, setConfirmed] = React.useState(false);

  // Load danh sách chuyên khoa từ API
  React.useEffect(() => {
    fetch(`${API_BASE_URL}/api/catalog/specialties`)
      .then((res) => res.json())
      .then((data) => setSpecialties(data))
      .catch(() => {});
  }, []);

  // Khi chọn chuyên khoa khác → fetch lại slots
  React.useEffect(() => {
    if (!selectedSpecialty) return;
    setLoadingSlots(true);
    fetch(`${API_BASE_URL}/api/catalog/slots?specialty=${encodeURIComponent(selectedSpecialty)}`)
      .then((res) => res.json())
      .then((data) => {
        setAvailableSlots(data);
        setSelectedDate("");
        setSelectedTime("");
      })
      .catch(() => {})
      .finally(() => setLoadingSlots(false));
  }, [selectedSpecialty]);

  const availableDates = React.useMemo(() => {
    if (availableSlots?.length) {
      const unique = [...new Set(availableSlots.map((s) => s.date))].sort();
      return unique;
    }
    // fallback: 7 ngày kế tiếp
    const days = [];
    for (let i = 1; i <= 7; i++) {
      const d = new Date();
      d.setDate(d.getDate() + i);
      days.push(d.toISOString().slice(0, 10));
    }
    return days;
  }, [availableSlots]);

  const timesForDate = React.useMemo(() => {
    if (!selectedDate) return [];
    if (availableSlots?.length) {
      return availableSlots
        .filter((s) => s.date === selectedDate)
        .map((s) => ({ time: s.time, slotObj: s }));
    }
    return ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "14:00", "14:30", "15:00"].map(
      (t) => ({ time: t, slotObj: null })
    );
  }, [selectedDate, availableSlots]);

  if (locked || confirmed) {
    return (
      <div className="form-confirmed">
        <CheckCircle2 size={16} className="icon-green" />
        <span>Đang xác nhận lịch hẹn...</span>
      </div>
    );
  }

  function handleConfirm() {
    if (!selectedSpecialty || !selectedDate || !selectedTime) return;
    setConfirmed(true);
    // Tìm slot object nếu có, không thì tự tạo
    const found = availableSlots?.find((s) => s.date === selectedDate && s.time === selectedTime);
    const slot = found || { date: selectedDate, time: selectedTime, specialty: selectedSpecialty, doctor: null };
    onConfirm(slot);
  }

  return (
    <div className="inline-form">
      <p className="form-title">
        <CalendarCheck size={14} />
        Hãy điền thông tin lịch hẹn vào đây
      </p>

      <label>
        Chọn chuyên khoa *
        <select
          value={selectedSpecialty}
          onChange={(e) => setSelectedSpecialty(e.target.value)}
          className="dt-select"
        >
          <option value="">-- Chọn chuyên khoa --</option>
          {specialties.map((sp) => (
            <option key={sp.id} value={sp.name}>{sp.name}</option>
          ))}
        </select>
      </label>

      {loadingSlots && (
        <p style={{ fontSize: 12, color: "var(--gray-400)" }}>Đang tải lịch trống...</p>
      )}

      <label>
        Chọn ngày khám
        <select
          value={selectedDate}
          onChange={(e) => { setSelectedDate(e.target.value); setSelectedTime(""); }}
          className="dt-select"
          disabled={!selectedSpecialty || loadingSlots}
        >
          <option value="">-- Chọn ngày --</option>
          {availableDates.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </label>

      <label>
        Chọn giờ khám
        <select
          value={selectedTime}
          onChange={(e) => setSelectedTime(e.target.value)}
          disabled={!selectedDate}
          className="dt-select"
        >
          <option value="">-- Chọn giờ --</option>
          {timesForDate.map(({ time }) => (
            <option key={time} value={time}>{time}</option>
          ))}
        </select>
      </label>

      <button
        className="confirm-btn"
        onClick={handleConfirm}
        disabled={!selectedSpecialty || !selectedDate || !selectedTime || loading || loadingSlots}
      >
        {loading ? "Đang đặt lịch..." : "Xác nhận đặt lịch"}
      </button>
    </div>
  );
}

// ─── ConfirmationCard ──────────────────────────────────────────────────────
function ConfirmationCard({ booking, slot }) {
  return (
    <div className="confirmation-card">
      <div className="confirmation-icon">
        <CheckCircle2 size={32} />
      </div>
      <h3>Đặt lịch thành công!</h3>
      <p className="conf-subtitle">Mã lịch hẹn của bạn</p>
      <div className="conf-code">{booking?.id?.slice(0, 8).toUpperCase()}</div>
      <div className="conf-details">
        <div className="conf-row"><span>Chuyên khoa</span><strong>{slot.specialty}</strong></div>
        {slot.doctor && <div className="conf-row"><span>Bác sĩ</span><strong>{slot.doctor}</strong></div>}
        <div className="conf-row"><span>Thời gian</span><strong>{slot.date} lúc {slot.time}</strong></div>
      </div>
      <p className="conf-note">Bệnh viện sẽ liên hệ xác nhận qua số điện thoại đã đăng ký.</p>
    </div>
  );
}

// ─── RichText ──────────────────────────────────────────────────────────────
function RichText({ text }) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={i}>{part.slice(2, -2)}</strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function BotAvatar() {
  return <div className="avatar bot-avatar"><Bot size={16} /></div>;
}

function UserAvatar() {
  return <div className="avatar user-avatar"><User size={16} /></div>;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

export default App;
