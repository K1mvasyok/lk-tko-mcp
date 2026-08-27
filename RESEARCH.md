# RESEARCH.md — каталог кандидатов в MCP-инструменты (lk-tko-v2)

Результат многоагентного исследования lk-tko-v2 (2026-08-27): 5 параллельных
агентов прочитали REST-контроллеры, декларативные REST-сервисы, модель
сущностей, бизнес-логику lkUser/биллинга и существующие ad-hoc
Groovy-скрипты; шестой агент сверил покрытие с реальной структурой пакетов
и нашёл, что осталось не разобрано. Это рабочий каталог для планирования
следующих tools, не готовый код — прежде чем реализовывать что-либо,
перечитать соответствующий кусок lk-tko-v2 и свериться с текущим планом
в [README.md](README.md).

## TL;DR — что делать дальше

Уже готово: `get_contragent_status` (поиск контрагента по ИНН через generic
entity search). Дальше по ценности/переиспользуемости уже проверенного
REST-клиента:

1. **`get_contragent_debt`** — долг/пени/госпошлина по лицевому счёту, ИНН,
   телефону или email. Самый частый паттерн вообще: он всплыл независимо у
   трёх разных агентов (REST-контроллер `DebtController`, декларативный
   `getPaymentsByPersonalAccount`, и как ядро "lkUser billing logic"). Это
   буквально то, что делает саппорт по каждому звонку "сколько я должен".
2. **`get_contragent_bills`** / **`get_contract`** — счета и договоры
   контрагента, естественное продолжение после debt-lookup.
3. **`get_fine_details`** — детализация пеней (уже есть формула в
   `BillingInfoServiceBean`, легко объяснить клиенту "почему такая сумма").

Дальше — см. приоритеты ниже.

## Приоритет 1 — Долг и биллинг (ядро продукта)

| Tool | Источник | Чувствительность |
|---|---|---|
| `get_contragent_debt(pa_or_inn)` | `DebtController` /v3/debt/by-contragent → `BillingInfoService.getDebtByPaOrInn` | financial |
| `get_debt_by_phone(phone)` / `get_debt_by_email(email)` | `DebtController` /by-phone /by-email | personal_data |
| `get_calculations_tabs(contragent_id)` | `BillService.getDataForCalculationsTabsScreen` — те же 4 цифры, что видит клиент в ЛК (Начислено/Оплачено/Пени/Долг) | financial |
| `get_debt_breakdown_by_real_estate(cre_id)` | `BillingInfoService.getDataOnDebtsByContragentRealEstate` — разбивка "почему столько" по конкретному адресу | financial |
| `get_fine_details(contragent_id)` | `Fine` entity + `getFineContragentByPeriod` | financial |
| `get_serviced_periods(pa_or_inn)` | объясняет пробелы в биллинге клиенту | financial |
| `find_contragents_with_debt_older_than(months)` | `BillService.findContragentIdsWithDebtOlderThan` — коллекторская триаж-выборка | financial |

## Приоритет 2 — Документы и договоры

| Tool | Источник |
|---|---|
| `get_contragent_bills(contragent_id, from, to, is_paid)` | `BillController` /v3/bill |
| `get_contract(contragent_id)` | декларативный `getContract`, включает начисления/платежи/пени/долг на договор |
| `get_upd_document(bill_number)` | `AccrualController` /v3/accrual/upd, декларативный `getUPD` |
| `get_registration_info` / `get_requisites` / `get_head_organization_info` | `ContragentController`, декларативные аналоги — реквизиты для документов |
| `list_contragent_documents(contragent_id)` | `DocumentController` |

## Приоритет 3 — Недвижимость и контейнерные площадки (операционка)

`RealEstateController` (поиск по кадастровому номеру/адресу/лицевому
счёту), `get_renters_for_real_estate`, `ContainerYardController`
(площадки/контейнеры по адресу). Ниже приоритет — больше про операционные
сценарии (ОПС/логистика), чем про типичный саппорт-запрос.

## Категория: безопасная автоматизация ручных скриптов

Отдельная, самостоятельно ценная категория — не "спросить данные", а
**безопасно повторить то, что сейчас делают руками через Groovy-скрипты**
в `modules/core/.../scripts/`. Напрямую перекликается с тем, что я как
ассистент [[feedback_no_java_execution]] — сам такие скрипты не
запускаю; параметризованный MCP-tool с обязательным dry-run и лимитом
батча — это способ дать Claude помогать с такими задачами безопасно, под
контролем разработчика, а не через ручной хардкод.

Повторяющиеся паттерны (каждый сейчас — N похожих скриптов, скопированных
руками под каждую пару entity/field):

- `backfill_entity_field(entityType, jpqlWhere, field, value, batchSize)` —
  массовое заполнение пустого поля (5+ скриптов такого вида).
- `sanitize_text_field(entityType, field, allowedCharsRegex, dryRun)` —
  чистка "мусорных" символов (5 скриптов, включая имя/short_name/trade_name
  контрагента — **персональные данные**, здесь обязателен dry-run).
- `recompute_financial_aggregate(entityType, filter, rule, dryRun=true)` —
  пересчёт долга/НДС на Contragent/Bill/Accrual — именно то, что сейчас
  саппорт правит руками при инцидентах.
- `migrate_flat_field_to_related_entity(...)` — миграция текстового адреса
  в нормализованный Address (8 почти идентичных скриптов).
- `upsert_app_folder(...)` / `upsert_screen_filter(...)` — провижининг
  папок навигации и сохранённых фильтров в админке.

Каждый из этих tools должен по умолчанию требовать `dryRun=true` и
показывать diff/count перед реальным commit — это mutating-операции,
не read-only lookup.

## Что не тронуто вообще (gap-check по реальной структуре пакетов)

Шестой агент прошёлся по списку пакетов `modules/{global,core,web}` и
нашёл крупные поддомены, ни разу не всплывшие в основном исследовании —
каждый из них тянет на отдельный заход:

- **Chatbot/IVR** (`service/chatbot`, Stage/StageStatus/AtypicalQuestion) —
  похоже, сценарийный движок для звонков/чата по взысканию долга.
- **Телефония** — интеграция с Mango Office (CommunicationChannel/Status).
- **Весовой биллинг** (`WeighingComplexBillingService` + `Landfill`) —
  параллельный биллинг для полигонов, начисление по весу с весовой.
- **"Прочие отходы"** — отдельный контрактно-тарифный контур для
  партнёрских организаций (`OtherWasteContractService`).
- **Рассрочка и соглашения с должниками** — `InstallmentService`,
  `DebtorAgreementService` — структурированная реструктуризация долга.
- **Акты сверки / перерасчёта** — `ReconciliationAct`, `RecalculationAct`
  (включая периоды отсутствия жильца).
- **Сверка банковских реестров** — `service/bankregisters`, парсинг
  назначения платежа для автосопоставления.
- **Судебное делопроизводство** — `entity/proceedings` (реальные
  заседания, не только досудебный REST-lookup).
- **Самостоятельные заявки клиента** — отмена договора, аренда
  контейнера, запись на визит в офис, восстановление пароля.
- **Массовые рассылки и уведомления** — `MailingCampaignControlService`,
  `NotificationService`, интеграции DashaMail/Unisender.
- **Платёжные терминалы** — `TerminalOperationService` (ещё один канал
  оплаты помимо ЮKassa и 1С).
- **Полный цикл инспекции площадок** — `InspectionService` (сейчас виден
  только REST intake, не сам workflow).
- **OCR и электронная подпись** — `TextRecognitionService`, `SignService`.
- **Логистика** — `service/fact` сравнивает план/факт вывоза и шлёт во
  внешнюю систему.
- **НТО / МСУ** — два похожих внешних кадастровых интеграционных контура
  рядом с уже найденным Dataminer, назначение не до конца ясно без
  отдельного чтения.

## Что сознательно НЕ стоит оборачивать в generic-tool

Исследование REST-контроллеров попутно нашло несколько эндпоинтов,
которые проверяют логин/пароль или обрабатывают реальные деньги/SMS-код
напрямую (`ContragentController POST /accounts`, `CallCheckController`,
`PublicDebtorController`, `ClientController` регистрация платежа ЮKassa).
Это не баги — это существующая работающая функциональность — но именно
поэтому под них не стоит делать общий MCP-инструмент: они либо
аутентифицируют по сырому паролю, либо двигают реальные деньги/SMS.
Оставляем их вне tool-слоя.

Отдельно: `ContragentBillInfoController` (виджет для Tilda) и несколько
методов `rtneo_ApiRestService` помечены `anonymousAllowed="true"` — это
существующая конфигурация lk-tko-v2, не относится к lk-tko-mcp напрямую,
но стоит иметь в виду при выборе, чей REST-клиент переиспользовать для
будущих tools.
