[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/03-architecture.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/03-architecture.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Kiến trúc

## Các thành phần

| Mô-đun | Trách nhiệm |
| --- | --- |
| `gateway/app.py` | Toàn bộ route HTTP; nối mọi thứ lại. |
| `gateway/auth.py` | Kiểm tra khóa client; ánh xạ `model` → agent id. |
| `gateway/identities.py` | Đa người dùng: API key → danh tính + chính sách. |
| `gateway/upstream/base.py` | Giao diện `UpstreamAdapter` + kiểu dữ liệu chuẩn hóa. |
| `gateway/upstream/mcp.py` | Client MCP JSON-RPC thật + trình quản lý token OAuth. |
| `gateway/upstream/mock.py` | Adapter ngoại tuyến, tất định, cho test/dev. |
| `gateway/upstream/manager.py` | Một adapter/resolver cho mỗi danh tính (pool). |
| `gateway/translate.py` | Dịch tin nhắn/kết quả OpenAI ⇄ Hyperagent. |
| `gateway/streaming.py` | SSE mô phỏng cho chat và Responses. |
| `gateway/toolbridge.py` | Danh mục công cụ + ánh xạ `tool_calls`. |
| `gateway/media.py`, `fallbacks.py` | Trợ giúp ảnh/âm thanh; bản dự phòng embeddings + moderation. |
| `gateway/state.py` | SQLite: hội thoại, responses, file. |

**UpstreamAdapter** là đường nối then chốt: mọi thứ phía trên nó là dịch OpenAI
thuần túy; mọi thứ phía dưới là Hyperagent. Đổi `mock` ↔ `mcp` không ảnh hưởng
phần còn lại.

## Vòng đời một yêu cầu — chat (không streaming)

```mermaid
sequenceDiagram
  participant C as Client
  participant G as Cổng
  participant H as Hyperagent MCP
  C->>G: POST /v1/chat/completions (messages)
  G->>G: khóa → danh tính; model → agentId
  G->>G: gộp messages → một prompt tự chứa
  G->>H: create_thread(agentId, prompt)
  H-->>G: threadId
  loop poll đến khi có câu trả lời mới
    G->>H: get_thread(threadId)
    H-->>G: messages + isRunning
  end
  G-->>C: chat.completion (văn bản + tool_calls)
```

## Streaming

Hyperagent không nhả token. Cổng **poll** `get_thread`, so sánh phần văn bản mới
của assistant, rồi phát ra các sự kiện `chat.completion.chunk` (và với Responses
là `response.output_text.delta`), kết thúc bằng `data: [DONE]`. Trên đường truyền
đây là SSE thật — chỉ có điều "streaming" được dựng lại từ việc poll.

## Thiết kế phi trạng thái & tái dựng ngữ cảnh

Thử nghiệm thực tế cho thấy trí nhớ xuyên lượt của thread Hyperagent **không đáng
tin** với các lượt qua MCP, cộng thêm một tình huống "đua" khi lượt vừa xếp hàng
trông như đã "xong". Vì vậy cổng theo một quy tắc: **không dựa vào trí nhớ thượng
nguồn. Mỗi lượt là một thread mới, tự chứa đầy đủ.**

- **Chat Completions** phi trạng thái: client OpenAI vốn gửi lại toàn bộ
  `messages[]` mỗi lần, nên cổng gộp tất cả vào một thread mới. (Mỗi lần gọi có
  `system_fingerprint`/threadId khác nhau là bình thường.)
- **Responses API** có trạng thái *bằng cách tái dựng*: với `previous_response_id`,
  cổng đọc thread trước, gộp lại, rồi ghép vào đầu một thread mới.
- **Phát hiện câu trả lời mới:** việc chờ yêu cầu phải có một tin nhắn assistant
  *mới* vượt mốc đã ghi (`wait_for_new_assistant`), loại bỏ tình huống trả lời cũ.

Quyết định này được ghi tại
[`docs/decisions/0010`](../decisions/0010-stateless-gateway-context-reconstruction.md).

## Thượng nguồn (đã xác minh thực tế)

- Endpoint `https://hyperagent.com/api/mcp`, JSON-RPC 2.0 qua POST.
- OAuth 2.1 (Authorization Code + PKCE, Dynamic Client Registration, gia hạn qua
  `offline_access`); **không có API key**.
- Sáu công cụ; `get_thread` trả về `{thread, messages[], isRunning}`.
- Chi tiết: [`docs/product/upstream-mcp.md`](../product/upstream-mcp.md).

## Hai ranh giới xác thực

Hai tầng độc lập:
1. **Client → cổng:** một `Authorization: Bearer <khóa cổng>` kiểu OpenAI.
2. **Cổng → Hyperagent:** một token OAuth theo từng người dùng, cổng lưu & gia hạn.

Một khóa cổng ánh xạ tới một danh tính Hyperagent, nên một máy chủ phục vụ được
nhiều người dùng. Xem [Triển khai](06-deployment.md).
