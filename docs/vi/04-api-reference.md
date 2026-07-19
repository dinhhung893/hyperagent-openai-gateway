[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/04-api-reference.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/04-api-reference.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Tham chiếu API

Base URL: `http://<host>:8000/v1`. Xác thực: `Authorization: Bearer <khóa cổng>`.
Mọi kết quả dùng định dạng OpenAI. Lỗi dùng khung OpenAI:

```json
{ "error": { "message": "…", "type": "invalid_request_error", "param": "model", "code": "model_not_found" } }
```

## `GET /v1/models` · `GET /v1/models/{id}`
Liệt kê các agent Hyperagent dưới dạng model OpenAI (`id`,
`owned_by:"hyperagent"`, `metadata` gồm tên/mô tả). Dùng một `id` làm trường
`model`, hoặc bí danh `hyperagent-default`.

## `POST /v1/chat/completions`
Endpoint cốt lõi. Các trường chính:

| Trường | Hành vi |
| --- | --- |
| `model` | Agent id hoặc `hyperagent-default`. |
| `messages[]` | Vai trò `system`/`developer`/`user`/`assistant`/`tool`; chuỗi hoặc mảng phần nội dung (`text`, `image_url`, `input_audio`, `file`). |
| `stream` | `true` → SSE `chat.completion.chunk` + `[DONE]` (mô phỏng). |
| `stream_options.include_usage` | Thêm một mẩu usage cuối. |
| `tools`, `tool_choice`, `parallel_tool_calls` | [Cầu nối công cụ](05-tool-bridge.md). |
| `response_format` | `text`, `json_object`, hoặc `json_schema` (có kiểm tra). |
| `max_tokens`/`max_completion_tokens`, `reasoning_effort` | Ánh xạ sang budget/effort của agent (tương đối). |
| `temperature`, `top_p`, `seed`, các penalty, `logit_bias` | Chấp nhận, không tác dụng. |
| `n`, `stop` | Tương đối. |

**Ví dụ**
```bash
curl .../v1/chat/completions -H "authorization: Bearer sk-..." -H "content-type: application/json" -d '{
  "model":"hyperagent-default",
  "messages":[{"role":"system","content":"Trả lời ngắn."},{"role":"user","content":"2+2?"}]
}'
```
Kết quả: một `chat.completion` chuẩn với `choices[0].message.content`. Nếu agent
có dùng công cụ, sẽ có `choices[0].message.tool_calls[]` và `finish_reason` là
`tool_calls`.

## `POST /v1/responses` (+ vòng đời)
Bề mặt có trạng thái, thiên về agent — khớp nhất với thread Hyperagent.

- `input` (chuỗi hoặc mảng item), `instructions`, `tools`, `tool_choice`
- `stream: true` → sự kiện `response.created` → `response.output_text.delta` → `response.completed`
- `background: true` → trả `status:"in_progress"`; poll `GET /v1/responses/{id}`
- `previous_response_id` → **chuỗi có trạng thái** (ngữ cảnh trước được tái dựng)
- `POST /v1/responses/{id}/cancel` → đánh dấu hủy (tương đối)
- `GET /v1/responses/{id}/input_items` → các tin nhắn đầu vào

**Ví dụ có trạng thái** (đã xác minh thực tế):
```bash
# 1) ghi nhớ một dữ kiện
curl .../v1/responses -d '{"model":"hyperagent-default","input":"Nhớ mã SPARROW-42. Trả lời: đã lưu."}'
# → {"id":"resp_abc",...,"output_text":"đã lưu."}
# 2) nhớ lại
curl .../v1/responses -d '{"model":"hyperagent-default","input":"Mã là gì?","previous_response_id":"resp_abc"}'
# → output_text: "SPARROW-42"
```

## `POST /v1/completions` (kiểu cũ)
Nhận prompt, trả một lựa chọn văn bản. Ánh xạ sang một lượt chạy thread.

## `GET /v1/tools`
Trả về danh mục công cụ Hyperagent dưới dạng định nghĩa tool OpenAI (tôn trọng
danh sách công cụ bị tắt theo khóa). Xem [Cầu nối công cụ](05-tool-bridge.md).

## `POST /v1/images/generations` · `/v1/images/edits`
Chạy công cụ tạo ảnh của agent và trả về URL công khai tải được:
```json
{ "created": 0, "data": [ { "url": "https://pub.hyperagent.com/...png", "revised_prompt": "…" } ] }
```

## `POST /v1/audio/speech` · `/transcriptions` · `/translations`
- **speech**: văn bản → âm thanh; trả về bytes khi tải được, nếu không thì JSON `{url}`.
- **transcriptions/translations**: tải lên `file` (multipart) → `{ "text": "…" }`.

## `POST /v1/files` · `GET /v1/files` · `GET /v1/files/{id}` · `/content` · `DELETE`
Tải lên sẽ lưu file với Hyperagent (`create_attachment_upload`) và giữ một bản ghi
cục bộ; tham chiếu `id` trả về trong một phần nội dung `file` của chat để đính kèm
vào yêu cầu.

## `POST /v1/embeddings`
Vector **hashing** cục bộ, tất định (không mang nghĩa ngữ nghĩa) để client chạy
thông suốt. Đặt `GATEWAY_EMBEDDINGS=off` để trả `501`, hoặc cắm nhà cung cấp thật.

## `POST /v1/moderations`
**Heuristic** từ khóa minh bạch theo bộ category OpenAI. Trả về
`results[].flagged` + điểm từng category.

## `GET /v1/health`
Kiểm tra sống: `{ "status": "ok", "version": "…", "upstream": "mcp|mock" }`.
