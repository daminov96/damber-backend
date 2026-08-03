# Chat moduli — dizayn

**Sana**: 2026-07-30
**Holat**: Tasdiqlangan, amalga oshirilmoqda

## Kontekst

`admin`dan keyingi bosqich — rejalashtirilgan oxirgi backend moduli, foydalanuvchi so'ragan "chat qismini ham tayyorla". Chuqur frontend tadqiqoti (`src/store/chat.ts`, `ChatThread.tsx`, `ListingChat.tsx`, `ClientChats.tsx`, `HostChats.tsx`, `BookingModal.tsx`) shuni ko'rsatdi: bu — loyihadagi eng kam soni "dekorativ" funksiyalardan biri, to'liq ishlaydigan, real navigatsiyaga ulangan (har bir listing sahifasida + ikkala dashboard'da), o'z test to'plami bor.

## Frontend'dagi haqiqiy xulq-atvor

- Chat **listing egasiga** yoziladigan — `ListingChat` widjeti har bir listing sahifasida ko'rinadi, xohlagan client xohlagan listing egasiga yoza oladi (bron talab qilinmaydi, faqat "bu sizning e'loningiz emasligi" tekshiriladi).
- Suhbat **faqat client+owner juftligi** bilan aniqlanadi (`chatId = "${clientId}_${ownerId}"`) — **listingga bog'lanmagan**: bir xil egaga turli listinglar haqida yozsa ham bitta thread bo'ladi.
- Xabar modeli juda oddiy: `{sender, text, time}` — ID yo'q, haqiqiy timestamp yo'q (faqat ko'rinadigan vaqt satri), o'qilgan/o'qilmagan **thread darajasida** (`unread: Record<chatId, boolean>`), xabar darajasida emas.
- **Real-time/WebSocket YO'Q** — hammasi sinxron Zustand `set()`; yagona "jonlilik" illyuziyasi — `botReply` (`setTimeout(2000ms)`, faqat client tomonidan, kalit so'z bilan javob beradi). Host haqiqiy javob berganda hech qanday kechikish/websocket yo'q — oddiy sinxron yozuv.
- **Ilova ichi kontent filtri bor**: `detectSensitiveData(text)` — telefon/karta raqamini reglar bilan aniqlab, yuborishni block qiladi. Faqat client tomonda, backend chaqirilmasa bypass qilinadi.
- Bron yaratilganda (`BookingModal.tsx`) chatga avtomatik ikkita xabar qo'shiladi (mehmonning xosh xabari + "bron tasdiqlandi" xabari egadan kelganday) — bir tomonlama ulash (bron → chat), lekin chatga kirish bron bilan CHEKLANMAGAN.
- Turlar/operatorlar/gidlarga chat umuman ulanmagan — faqat `Listing` domenida.
- Adminda chatni ko'rish/moderatsiya qilish yo'q.
- Fayl/rasm biriktirish yo'q — faqat matn.

## Loyihachi qarorlar

1. **WebSocket kerak emas — REST yetarli**. Frontend hech qachon haqiqiy real-time/push talab qilmagan (faqat demo uchun soxta `setTimeout`). WebSocket infratuzilmasi qo'shish — so'ralmagan, asossiz murakkablik bo'lardi. Oddiy REST (xabar yuborish/olish, sahifalab tarix) yetarli.

2. **Suhbat modeli frontendga mos — client+owner juftligi, listingga bog'lanmagan** (`UniqueConstraint(client_id, owner_id)`), lekin `listing_id` ixtiyoriy kelib chiqish konteksti sifatida saqlanadi (yaratilishda o'rnatiladi, keyin o'zgarmaydi) — frontendning xatti-harakatini o'zgartirmaydi, faqat qaysi listing suhbatni boshlaganini kuzatish uchun qo'shimcha ma'lumot beradi.

3. **Owner_id klientdan qabul qilinmaydi — `listing_id`dan serverda hosil qilinadi**. `POST /chat/conversations` faqat `listing_id` qabul qiladi; `owner_id = listing.owner_id`. Wallet/Reviews'dagi "server-side authoritative" naqshining davomi.

4. **Xabar modeli "haqiqiy" qilinadi**: har bir xabarda `id` (UUID), haqiqiy `created_at` (DateTime), va xabar darajasida `read_at` (nullable DateTime) — frontenddagi "faqat thread darajasida boolean unread" o'rniga. Reviews modulidagi `rating`/`certified` bilan bir xil naqsh: frontendda "jonli ko'ringan, aslida qo'pol" narsa backend'da to'g'ri quriladi.

5. **Sezgir ma'lumot filtri serverda ham kuchga kiritiladi** (`_contains_sensitive_data()`). Xabar matnida telefon/karta raqami naqshi topilsa — 400 qaytariladi. "Client-trusted validation"ni serverda takrorlash naqshi.

6. **O'z-o'ziga yozish taqiqlanadi**: `listing.owner_id == current_user.id` bo'lsa — 409.

7. **Faqat ishtirokchilar ko'ra oladi — ADMIN uchun ham maxsus ko'rish yo'q**. Admin moduli tadqiqotida adminning chatga hech qanday aloqasi yo'qligi aniqlangan edi — xususiylikni saqlash va so'ralmagan qamrovni oldini olish uchun bypass qo'shilmaydi.

8. **Ishtirokchi ma'lumoti yengil chiqariladi** (`ChatParticipantOut`: faqat `id`/`name`/`surname`/`avatar_url`) — to'liq `UserOut` emas (balans/email/rol ko'rsatilmaydi).

9. **Turlar/operatorlar/gidlarga ulanmaydi** — frontendda yo'q, qo'shilmaydi.

## Ma'lumotlar modeli — `app/modules/chat/models.py`

```python
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("client_id", "owner_id", name="uq_conversations_client_owner"),
    )
    id: UUID (pk)
    client_id: UUID (FK users.id, index)
    owner_id: UUID (FK users.id, index)
    listing_id: UUID | None (FK listings.id, ondelete="SET NULL")
    created_at: DateTime server_default=func.now()

class Message(Base):
    __tablename__ = "messages"
    id: UUID (pk)
    conversation_id: UUID (FK conversations.id, ondelete="CASCADE", index)
    sender_id: UUID (FK users.id)
    text: str(2000)
    created_at: DateTime server_default=func.now(), index
    read_at: DateTime | None
```

## Endpoints — `app/modules/chat/router.py` (prefix `/api/v1/chat`, `CurrentUser`)

| Method | Path | Tavsif |
|---|---|---|
| POST | `/chat/conversations` | `{listing_id}` — mavjud suhbatni qaytaradi yoki yangi yaratadi (`owner_id` `listing.owner_id`dan olinadi) |
| GET | `/chat/conversations` | Mening suhbatlarim (client yoki owner sifatida), oxirgi xabar + `unread_count` bilan, sahifalab |
| GET | `/chat/conversations/{id}/messages` | Xabarlar tarixi (faqat ishtirokchi), sahifalab, `created_at` bo'yicha o'sish tartibida |
| POST | `/chat/conversations/{id}/messages` | `{text}` — yangi xabar yuborish (faqat ishtirokchi, sezgir ma'lumot filtri) |
| POST | `/chat/conversations/{id}/read` | Menga yo'naltirilgan o'qilmagan xabarlarni `read_at=now()` qiladi |

## Service — `app/modules/chat/service.py`

Namuna: `reviews/service.py` (oddiy CRUD+ruxsat naqshi), `listings/service.py::_validate_company` (FK orqali server-side validatsiya naqshi).

- `_check_participant(conversation, user)` — `user.id` ishtirokchilardan biri bo'lmasa 403
- `_contains_sensitive_data(text)` — telefon (`\d[\d\-\s\(\)]{6,}\d`) va karta (`\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}`) reglar
- `get_or_create_conversation(db, client, listing_id)` — listing orqali owner aniqlanadi, o'z-o'ziga 409, mavjud bo'lsa qaytariladi, aks holda yaratiladi (`IntegrityError` bilan musobaqa holatiga qarshi himoya)
- `list_conversations(db, user, page, page_size)` — `client_id == user.id OR owner_id == user.id`, har biri uchun oxirgi xabar + unread_count (kichik miqyosda N+1 qabul qilinadi — keraksiz murakkablik yo'q)
- `list_messages(db, conversation_id, user, page, page_size)`
- `send_message(db, conversation_id, user, text)`
- `mark_read(db, conversation_id, user)`

## Validatsiya

- `StartConversationRequest.listing_id: uuid.UUID`
- `SendMessageRequest.text: str = Field(min_length=1, max_length=2000)`

## Test strategiyasi

`tests/test_chat.py`:
1. Client listing egasiga suhbat boshlaydi — yangi yaratiladi
2. Xuddi shu client+listing bilan qayta chaqirilsa — bir xil suhbat qaytariladi (idempotent)
3. Bir xil egaga boshqa listingdan yozsa — bitta suhbat (client+owner juftligi)
4. O'z listingiga yozishga urinish — 409
5. Xabar yuborish, ikkinchi tomon o'qiydi
6. Begona (ishtirokchi bo'lmagan) userning kirish/yozishga urinishi — 403
7. Sezgir ma'lumot (telefon raqam) yuborish — 400
8. `mark_read` keyin `unread_count` 0
9. `GET /chat/conversations` — ikkala tomonda ham ko'rinishi, oxirgi xabar to'g'ri

## Migratsiya

`alembic revision --autogenerate -m "chat moduli - conversations va messages"` — yangi jadvallar, enum yo'q, `create_type` muammosi kutilmaydi.

## Doiradan tashqari

- WebSocket/real-time push
- Fayl/rasm biriktirish
- Admin chat moderatsiyasi/ko'rish
- Turlar/operatorlar/gidlarga ulash
