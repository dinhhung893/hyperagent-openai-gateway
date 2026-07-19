[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/08-glossary.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/08-glossary.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Thuật ngữ

Giải nghĩa bằng lời đơn giản, đại khái từ dễ đến khó.

- **API** — cách để các chương trình nói chuyện với một dịch vụ qua Internet theo
  quy tắc thống nhất.
- **Endpoint** — một URL cụ thể của API làm một việc, ví dụ `/v1/chat/completions`.
- **HTTP / HTTPS** — giao thức mà yêu cầu web dùng; HTTPS là bản mã hóa.
- **JSON** — định dạng văn bản đơn giản cho dữ liệu có cấu trúc (`{"key":"value"}`).
- **Client / SDK** — chương trình (hoặc thư viện) gọi API, ví dụ gói `openai` của
  Python.
- **LLM (Mô hình ngôn ngữ lớn)** — AI dự đoán văn bản; "bộ não" đằng sau chat.
- **Token** — một mẩu văn bản (~¾ từ) mà mô hình đọc/sinh ra; mức dùng đo bằng
  token.
- **Streaming / SSE** — gửi câu trả lời theo từng phần khi đang sinh ra.
  **SSE (Server-Sent Events)** là kỹ thuật HTTP được dùng.
- **Agent** — một AI biết *hành động*: dùng công cụ, chạy nhiều bước, tạo kết quả,
  không chỉ trò chuyện.
- **Thread (luồng)** — không gian làm việc bền bỉ nơi một lượt chạy agent diễn ra
  (tin nhắn, lời gọi công cụ, sản phẩm).
- **Hyperagent** — nền tảng vận hành các agent này (`hyperagent.com`).
- **MCP (Model Context Protocol)** — chuẩn mở nối "khách" AI với công cụ/dịch vụ.
  Hyperagent cung cấp một máy chủ MCP.
- **JSON-RPC** — giao thức "gọi một hàm qua mạng bằng JSON" đơn giản; MCP dùng nó.
- **OAuth 2.1** — quy trình "đăng nhập và cấp quyền" chuẩn. Hyperagent dùng nó
  (không có API key).
- **PKCE** — phần bảo mật thêm cho OAuth dành cho ứng dụng không giữ được bí mật;
  một đoạn mã chứng minh cùng một ứng dụng bắt đầu và kết thúc đăng nhập.
- **Access token / Refresh token** — khóa ngắn hạn để gọi API / khóa dài hạn để
  lấy access token mới mà không phải đăng nhập lại.
- **Gateway (cổng)** — chính dự án này: bộ chuyển đổi biến lời gọi OpenAI thành
  lời gọi Hyperagent.
- **Upstream adapter** — thành phần thay được, nói chuyện với Hyperagent (`mcp`)
  hoặc giả lập (`mock`).
- **Poll** — hỏi đi hỏi lại "xong chưa?" cho tới khi tác vụ nền hoàn tất.
- **`tool_calls`** — định dạng của OpenAI khi AI xin chạy một hàm/công cụ.
- **Cầu nối công cụ** — cách cổng này phơi bày công cụ Hyperagent thành
  `tool_calls` của OpenAI.
- **Embeddings** — vector số biểu diễn ý nghĩa văn bản (để tìm kiếm/độ tương tự).
- **Moderation** — kiểm tra văn bản có gây hại/được phép hay không.
- **Đa người dùng (multi-tenant)** — một máy chủ phục vụ an toàn nhiều
  người dùng/tài khoản tách biệt.
- **Phi trạng thái (stateless)** — mỗi yêu cầu đứng độc lập; máy chủ không giữ trí
  nhớ theo người dùng giữa các lần gọi.
- **`repository-harness`** — bộ khung dùng để *phát triển* repo này (intake, story,
  quyết định, test). Xem [Đóng góp](09-contributing.md).
