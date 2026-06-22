# Changelog

## [2026-06-22] - AI đặt lịch + JWT + tools mới

### Added
- Tools: `suggest_expertise_tool`, `get_available_slots_tool` (doctor/expertise/service), `book_appointment_tool`
- `ChatRequest.access_token` — web/mobile gửi JWT; server inject vào book tool
- `book_appointment_tool`: `suggestedExpertiseId`, `isAiSuggested=true`

### Changed
- `prompts/system.txt`: luồng suggest → slots → book
- `BackendClient`: slots linh hoạt, `create_appointment` Bearer token

### Docs
- `docs/integration-guide.md`, `docs/knowledge-base.md`, `CHANGELOG.md`

## [2026-06-22] - Ket noi Patient Web & Mobile App