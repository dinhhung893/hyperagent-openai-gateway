[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/09-contributing.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/09-contributing.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Đóng góp & phát triển

## Cài môi trường dev

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio openai   # gói phụ cho dev
python3.11 -m pytest tests/ -q             # 46 test, tất cả xanh
```

Test dùng thượng nguồn **mock**, nên không cần mạng hay tài khoản.

## Bố cục mã nguồn

Xem [Kiến trúc](03-architecture.md). Quy tắc vàng: giữ phần dịch OpenAI *phía
trên* `UpstreamAdapter`, còn phần đặc thù Hyperagent *phía dưới* nó.

## Thêm một endpoint mới (công thức)

1. Thêm một route trong `gateway/app.py`.
2. Tái dùng `_run(...)` (mở/tiếp thread + chờ) hoặc dùng store cho trạng thái.
3. Dịch qua lại định dạng OpenAI trong `gateway/translate.py`.
4. Thêm test trong `tests/` dùng adapter mock (và nếu hướng tới người dùng, thêm
   test bằng `openai` SDK).
5. Cập nhật `docs/en` **và** `docs/vi`, cùng `docs/product/openai-compatibility.md`.

## Quy trình harness (cách repo được vận hành)

Repo dùng **[repository-harness](https://github.com/hoangnb24/repository-harness)** —
một tầng quy trình nhẹ cho agent lập trình. Tóm gọn:

1. **Intake** — phân loại thay đổi (tiny / normal / high-risk) và ghi lại:
   `scripts/bin/harness-cli intake …` (xem `docs/FEATURE_INTAKE.md`).
2. **Story** — với công việc thật, theo dõi bằng
   `harness-cli story add/update/complete`.
3. **Decision** — khi hành vi/kiến trúc đổi, viết `docs/decisions/NNNN-*.md` và
   `harness-cli decision add`.
4. **Proof** — giữ ma trận test trung thực (`harness-cli query matrix --active`).

> Binary `harness-cli` **không** được commit (bị gitignore). Trên bản clone mới,
> cài/bootstrap theo `AGENTS.md → Local Project Notes` (dự án này build từ source
> vì binary phát hành cần glibc mới hơn).

## Quy ước

- Trung thực về giới hạn: thà trả `501` rõ ràng còn hơn giả vờ có tính năng.
- Mỗi lượt thượng nguồn phải tự chứa đầy đủ (xem quyết định 0010).
- Giữ tài liệu Anh và Việt đồng bộ; cả hai đều có phần nút chuyển ngôn ngữ.

## Báo lỗi

Mở issue trên GitHub kèm: bạn đã làm gì, kỳ vọng gì, xảy ra gì, và header
`x-request-id` nếu lỗi đến từ thượng nguồn.
