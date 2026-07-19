[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/05-tool-bridge.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/05-tool-bridge.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Cầu nối công cụ

Cầu nối công cụ phơi bày hộp đồ nghề bên trong của Hyperagent (shell, file, web,
media, tích hợp…) qua cơ chế **gọi hàm** chuẩn OpenAI (`tools` / `tool_calls`),
để các client OpenAI không chỉnh sửa vẫn thấy và điều khiển được.

## Ba chế độ

**A. Quan sát (tự động).** Với mọi câu chat, agent có thể dùng công cụ khi làm
việc. Cổng hiện hoạt động đó thành `tool_calls` trong câu trả lời.
```bash
curl .../v1/chat/completions -d '{"model":"hyperagent-default",
  "messages":[{"role":"user","content":"shell: ls -la"}]}'
# → message.tool_calls = [{function:{name:"shell",arguments:"{\"command\":\"ls -la\"}"}}], finish_reason:"tool_calls"
```

**B. Chỉ định (bạn ép một công cụ).** Gửi một công cụ trong danh mục + `tool_choice`
để hướng agent dùng nó.
```json
{ "model":"hyperagent-default",
  "messages":[{"role":"user","content":"một khối lập phương đỏ"}],
  "tools":[{"type":"function","function":{"name":"generate_image"}}],
  "tool_choice":{"type":"function","function":{"name":"generate_image"}} }
```

**C. Chạy (tool-runner).** Với `GATEWAY_EXEC_MODE=auto`, một tool-runner chạy thẳng
công cụ bị ép và trả kết quả làm tin nhắn assistant. Với mặc định `roundtrip`, cổng
trả về một `tool_call` để client của bạn tự chạy (bắt tay chuẩn OpenAI).

## Xem danh mục

```bash
curl .../v1/tools -H "authorization: Bearer sk-..."
```
Trả về định nghĩa tool OpenAI cho mọi năng lực. Tập ban đầu:

```
shell · write_file · read_file · edit_file · list_files
web_search · web_fetch · image_search
generate_image · generate_video · generate_audio · transcribe_audio · generate_avatar
create_table · update_table · create_document · update_document
publish_webpage · publish_slides · generate_map
geocode · directions · place_search · weather · timezone
search_integrations · execute_integration · search_knowledge · create_agent_thread
```

## An toàn & chính sách

- Giới hạn công cụ theo từng API key bằng `GATEWAY_DISABLED_TOOLS=shell,write_file`
  (hoặc theo từng danh tính trong `GATEWAY_KEYS_FILE`). Công cụ bị tắt sẽ ẩn khỏi
  `/v1/tools` và ép dùng nó sẽ trả `400 tool_disabled`.
- Công cụ chạy trong sandbox của chính agent Hyperagent với quyền của người dùng
  đó — không bao giờ chạy trên máy chủ cổng.
- Việc ghi qua tích hợp vẫn tuân theo quy tắc phê duyệt/không giám sát của
  Hyperagent.
