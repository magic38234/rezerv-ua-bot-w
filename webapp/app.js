const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const initData = tg.initData || "";
let botUsername = null;

const ICONS = {
  bolt: '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M13 2 3 14h7l-1 8 11-13h-7l1-7z"/></svg>',
  bell: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
  newspaper: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h4"/></svg>',
  test: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12 2v6M12 22v-6M4.9 4.9l4.2 4.2M14.9 14.9l4.2 4.2M2 12h6M16 12h6M4.9 19.1l4.2-4.2M14.9 9.1l4.2-4.2"/></svg>',
  trash: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/></svg>',
  channel: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h4"/></svg>',
  telegram: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4 20-7Z"/><path d="M22 2 11 13"/></svg>',
  warning: '<svg class="icon-sm" viewBox="0 0 24 24" style="width:12px;height:12px;stroke:currentColor;fill:none;stroke-width:2;"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4M12 17h.01"/></svg>',
  save: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/></svg>',
  channelDefault: '<svg class="icon" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  location: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0Z"/><circle cx="12" cy="10" r="3"/></svg>',
  droplet: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12 2s7 7.58 7 12a7 7 0 1 1-14 0c0-4.42 7-12 7-12Z"/></svg>',
  check: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>',
  pencil: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>',
  send: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>',
  image: '<svg class="icon icon-sm" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/></svg>',
  video: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m22 8-6 4 6 4V8Z"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>',
  fileText: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></svg>',
  clock: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
  plus: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  pin: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12 17v5M9 3h6l1 6 3 2v2H5v-2l3-2 1-6Z"/></svg>',
  drone: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M5 5 9.5 9.5M19 5l-4.5 4.5M5 19l4.5-4.5M19 19l-4.5-4.5"/><circle cx="4" cy="4" r="2"/><circle cx="20" cy="4" r="2"/><circle cx="4" cy="20" r="2"/><circle cx="20" cy="20" r="2"/></svg>',
  radar: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12 12 20 8"/><path d="M12 3a9 9 0 1 0 9 9"/><path d="M12 7a5 5 0 1 0 5 5"/><circle cx="12" cy="12" r="1"/></svg>',
  rocket: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09Z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2Z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>',
  meteor: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12.5 3a9.5 9.5 0 1 0 9.5 9.5"/><path d="M17 3v4M21 7h-4"/><circle cx="12.5" cy="12.5" r="3.5"/></svg>',
  bomb: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="11" cy="13" r="8"/><path d="M14.5 6.5 17 4M17 4l1.5 1.5M17 4l1-3"/></svg>',
  jet: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M22 12 2 8v4l7 2-3 6 2.5 1L12 15l3.5 6L18 20l-3-6 7-2Z"/></svg>',
  home: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/></svg>',
  target: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>',
  chevronRight: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',
  team: '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
};

// Аватарка адміна в топбарі — беремо photo_url прямо з Telegram WebApp initData
// (це фото людина вже сама показує в Telegram, окремого дозволу не треба).
// Немає фото — показуємо першу літеру імені; немає й імені — іконку дзвіночка.
function initTopbarAvatar() {
  const box = document.getElementById("topbar-avatar");
  if (!box) return;
  const user = tg.initDataUnsafe && tg.initDataUnsafe.user;
  const photoUrl = user && user.photo_url;

  if (photoUrl) {
    const img = document.createElement("img");
    img.src = photoUrl;
    img.alt = "";
    img.style.cssText = "width:100%;height:100%;object-fit:cover;";
    img.onerror = () => { box.innerHTML = ICONS.bell; };
    box.innerHTML = "";
    box.appendChild(img);
    return;
  }

  const letter = user && user.first_name ? user.first_name.charAt(0).toUpperCase() : "";
  box.innerHTML = letter
    ? `<span style="font-weight:800;font-size:18px;color:#fff;">${escapeHtml(letter)}</span>`
    : ICONS.bell;
}
initTopbarAvatar();

// ---------- Багатомовність UI (п.3 патчу ТЗ) ----------
let currentLang = "ua";

const TRANSLATIONS = {
  ua: {
    "header.title": "Бот тривог і новин",
    "header.subtitle": "панель керування",
    "nav.home": "Головна",
    "nav.sources": "Джерела",
    "nav.editorial": "Редакція",
    "nav.profile": "Профіль",
    "nav.dev": "Технічний розділ",
    "queue.segFeed": "Джерела",
    "queue.segReaders": "Читачі",
    "channels.statLabelTotal": "Всього каналів",
    "channels.statLabelActive": "Активні",
    "channels.addBtn": "Додати канал",
    "channels.hint": "Натисни кнопку вище, обери канал зі списку своїх Telegram-каналів і підтверди права адміністратора.",
    "sources.statLabel": "Активні джерела",
    "sources.tgSectionLabel": "Telegram-канал (публічний, за посиланням)",
    "sources.linkPlaceholder": "t.me/username або @username",
    "sources.addByLinkBtn": "Додати за посиланням",
    "sources.listLabel": "Джерела новин",
    "sources.filterAll": "Всі",
    "sources.filterEditorial": "Редакційні",
    "sources.filterPublic": "Публічні канали",
    "sources.recommendedLabel": "Рекомендовані джерела: війна й політика",
    "sourceModal.title": "Джерело новин",
    "moderation.new": "Вхідні",
    "moderation.approved": "Схвалено",
    "settings.languageLabel": "Мова",
    "profile.idLabel": "ID",
    "profile.channelsShort": "каналів",
    "profile.sourcesShort": "джерел",
    "profile.automationLabel": "Автоматизація",
    "profile.autoApproveLabel": "Автосхвалення новин",
    "profile.autopostLabel": "Автопостинг з черги",
    "profile.delayLabel": "Затримка публікацій",
    "profile.queueStatusLabel": "Черга",
    "profile.serviceLabel": "Сервіс",
    "autoApprove.hint": "Поки застосунок відкритий — новини чекають вашого ручного схвалення. Через хвилину після закриття застосунку новини для ваших каналів починають схвалюватись самі. Систему ще допрацьовуємо — тут можна вимкнути цю автоматику для себе повністю.",
    "dev.statsLabel": "Статистика платформи",
    "dev.channelsTotal": "Каналів усього",
    "dev.activeAdmins": "Активних адмінів",
    "dev.subsToday": "Предложок сьогодні",
    "dev.subsTotal": "Предложок усього",
    "dev.maintenanceLabel": "Технічний перерив",
    "dev.manualAddLabel": "Ручне додавання каналу",
    "dev.chatIdPlaceholder": "chat_id каналу (наприклад -1001234567890)",
    "dev.titlePlaceholder": "Назва каналу",
    "dev.adminIdPlaceholder": "user_id адміна-власника",
    "dev.addManualBtn": "Додати вручну",
    "dev.allChannelsLabel": "Усі канали платформи",
    "dev.userSearchLabel": "Пошук користувача",
    "dev.userSearchPlaceholder": "user_id або ім'я",
    "dev.findBtn": "Знайти",
    "dev.errorsLabel": "Останні помилки",
    "channelModal.title": "Налаштування каналу",
    "editor.title": "Редагування посту",
    "editor.channelLabel": "Канали",
    "editor.footerToggle": "Підпис каналу",
    "editor.publishBtn": "Схвалити і опублікувати",
    "editor.rejectBtn": "Відхилити",
    "editor.selectAll": "Всі",
    "editor.deselectAll": "Жодного",
    "editor.scheduleToggle": "Запланувати",
    "editor.soon": "скоро",
    "editor.previewTitle": "Попередній перегляд",
    "editor.tbBold": "Жирний",
    "editor.tbItalic": "Курсив",
    "editor.tbUnderline": "Підкреслений",
    "editor.tbStrike": "Закреслений",
    "editor.tbMono": "Моноширинний",
    "editor.tbSpoiler": "Спойлер",
    "editor.tbLink": "Посилання",
    "editor.tbEmoji": "Емодзі",
    "editor.tbCustomEmoji": "Кастомні емодзі",
    "editor.textPlaceholder": "Текст новини…",
    "editor.styleNeutral": "Звичайний",
    "editor.styleOfficial": "Офіційно",
    "editor.styleUrgent": "Терміново",
    "editor.styleSummary": "Стисло",
    "editor.aiRewriteBtn": "ІІ-рерайт",
    "editor.aiTitleBtnTitle": "Заголовок і хештеги",
    "editor.aiTitleBtn": "Заголовок",
    "editor.previewBtnTitle": "Повний перегляд",
    "editor.previewBtn": "Перегляд",
    "memberPerms.title": "Права адміністратора",
    "categoryPicker.title": "Обрати категорію",
    "dev.backBtn": "← Профіль",
    "common.loading": "Завантаження...",
    "common.save": "Зберегти",
    "common.hide": "Сховати",
    "common.show": "Показати",
    "common.on": "Увімкнено",
    "common.off": "Вимкнено",
    "common.cancel": "Скасувати",
    "common.delete": "Видалити",
    "common.edit": "Редагувати",
    "common.add": "Додати",
    "common.close": "Закрити",
    "common.yes": "Так",
    "common.no": "Ні",
    "common.error": "Помилка",
    "common.success": "Готово",
    "common.confirm": "Підтвердити",
    "common.notSpecified": "Не вказано",
    "common.noAccess": "Немає доступу",
    "channels.empty": "Каналів ще немає",
    "channels.noCategory": "Без категорії",
    "channelStyle.noData": "Ще немає накопичених постів для аналізу стилю (з'являться після нових постів у каналі).",
    "channelStyle.analyzed": "Проаналізовано постів",
    "channelStyle.topEmoji": "частий емодзі",
    "channelStyle.boldStart": "жирний заголовок",
    "channelStyle.withLink": "з посиланням",
    "categoryPicker.hint": "Обери категорію одним кліком — без ручного вводу.",
    "categoryPicker.yourCategories": "Твої категорії",
    "categoryPicker.presetTags": "Готові теги",
    "categoryPicker.deleteCategoryAria": "Видалити категорію",
    "categoryPicker.deleteConfirm": "Видалити категорію",
    "categoryPicker.deleteConfirmSuffix": "Канали залишаться — просто без категорії.",
    "categoryPicker.deleteFailed": "Не вдалося видалити категорію",
    "categoryPicker.addCategoryBtn": "Додати категорію",
    "categoryPicker.folderExists": "Така папка вже є",
    "channels.botRemoved": "бот видалений",
    "channels.subscribers": "підписників",
    "channels.deleteFailed": "не вдалося видалити канал",
    "channels.moveFailed": "Не вдалося перенести канал у категорію",
    "channelModal.tabMain": "Головна",
    "channelModal.tabAlerts": "Тривоги",
    "channelModal.tabMedia": "Медіа",
    "channelModal.tabTeam": "Команда",
    "channelModal.subscribersLabel": "Підписники",
    "channelModal.automationTitle": "Автоматизація",
    "channelModal.automationDesc": "Автосхвалення предложок і автопостинг з черги — окремо для цього каналу",
    "channelModal.autoApproveLabel": "Автосхвалення предложок читачів",
    "channelModal.autoApproveHint": "Поки застосунок відкритий — предложки чекають ручного схвалення. Через хвилину після закриття вони починають публікуватись самі.",
    "channelModal.autopostLabel": "Автопостинг новин з черги",
    "common.minutesShort": "хв",
    "channelModal.cdHint": "КД між публікаціями саме в цей канал",
    "channelModal.queuePendingLabel": "У черзі для цього каналу",
    "channelModal.publishTitle": "Публікація новин",
    "channelModal.publishDescBase": "Автопостинг у цей канал",
    "channelModal.publishDescExtra": ", тестова публікація й посилання для читачів",
    "channelModal.sendTestNewsBtn": "Надіслати тестову новину",
    "channelModal.copyLinkBtn": "Скопіювати посилання для читачів",
    "channelModal.alertMonitorTitle": "Моніторинг повітряних тривог",
    "channelModal.alertMonitorDesc": "NEPTUN — офіційні тривоги/відбій і рух цілей по обраних областях (налаштовується у вкладці «Тривоги»)",
    "channelModal.oblastsNone": "Області: не обрано",
    "channelModal.oblastsSelected": "Області: обрано",
    "channelModal.oblastsOf": "з",
    "channelModal.oblastsDesc": "Які області моніторити",
    "channelModal.oblastSearchPlaceholder": "Пошук області…",
    "channelModal.selectAll": "Обрати всі",
    "channelModal.deselectAll": "Зняти всі",
    "channelModal.sirenTitle": "Сирена",
    "channelModal.sirenDesc": "Тривога / відбій по області чи району",
    "channelModal.targetsTitle": "Конкретні цілі",
    "channelModal.targetsDesc": "Шахед / ракета / КАБ у русі",
    "channelModal.showMapLabel": "Карта руху цілі",
    "channelModal.showMapHint": "Замість тексту — фото-карта з маршрутом цілі (якщо NEPTUN дає координати)",
    "channelModal.testAlertBtn": "Тест: надіслати тестову тривогу",
    "channelModal.typeUav": "БпЛА (шахед)",
    "channelModal.typeRecon": "Розвідувальний БпЛА",
    "channelModal.typeMissile": "Крилата ракета",
    "channelModal.typeBallistic": "Балістична ракета",
    "channelModal.typeKab": "КАБ",
    "channelModal.typeMig31k": "МіГ-31К",
    "common.saving": "Збереження…",
    "common.savedCheck": "✓ Збережено",
    "channelModal.testAlertSent": "Тестове сповіщення надіслано в канал",
    "channelModal.watermarkTitle": "Водяний знак",
    "channelModal.watermarkDesc": "Накладається на кожне фото й відео цього каналу",
    "channelModal.uploadLogoBtn": "Завантажити логотип",
    "channelModal.saveWatermarkBtn": "Зберегти знак",
    "channelModal.removeWatermarkBtn": "Прибрати знак",
    "channelModal.livePreviewTitle": "Живий попередній перегляд",
    "channelModal.livePreviewDesc": "Прозорість, розмір і позиція знака",
    "channelModal.opacityLabel": "Прозорість",
    "channelModal.sizeLabel": "Розмір",
    "channelModal.sizeLabelSuffix": "від ширини фото",
    "channelModal.positionsLabel": "Позиції на фото/відео (можна декілька)",
    "channelModal.saveWmSettingsBtn": "Зберегти налаштування знака",
    "channelModal.demoPhotoText": "Приклад фото",
    "channelModal.fileChosenPrefix": "Обрано",
    "channelModal.noWatermarkYet": "Ще не завантажено — поки що використовується назва каналу текстом",
    "channelModal.wmPreviewFailed": "Знак є, але прев'ю завантажити не вдалося",
    "channelModal.chooseFileFirst": "Спочатку обери файл картинки.",
    "common.networkError": "Мережева помилка",
    "channelModal.wmSaved": "Водяний знак збережено — тепер накладатиметься на кожне фото й відео цього каналу.",
    "channelModal.wmRemoved": "Водяний знак прибрано.",
    "channelModal.wmSettingsSaved": "Налаштування знака збережено",
    "channelModal.linkCopied": "Посилання скопійовано! Постав його на кнопку в каналі — читачі зможуть надсилати новини саме для нього.",
    "channelModal.testMsgSent": "Тестове повідомлення надіслано",
    "channelModal.teamAddTitle": "Додати учасника",
    "channelModal.teamAddDesc": "За user_id або @username (спрацює, якщо людина вже хоч раз відкривала цю панель чи писала боту)",
    "channelModal.roleEditor": "Редактор",
    "channelModal.roleModerator": "Модератор",
    "channelModal.teamMembersTitle": "Учасники каналу",
    "channelModal.invalidUserId": "Вкажи коректний user_id",
    "channelModal.addingMember": "Додаємо…",
    "channelModal.addedWithTgWarning": "Додано в панелі, але права в самому Telegram-каналі видати не вдалось (людина ще не підписана на канал або бот не має права додавати адмінів)",
    "channelModal.addMemberFailed": "Не вдалося додати",
    "channelModal.teamLoadFailed": "Не вдалося завантажити команду",
    "channelModal.teamEmpty": "Поки що нікого не додано",
    "channelModal.removeMemberBtn": "Прибрати",
    "common.saveFailedGeneric": "не вдалося зберегти",
    "common.nonJsonResponse": "Сервер повернув не-JSON відповідь",
    "channels.dataStillLoading": "Зачекай секунду, дані ще завантажуються, спробуй ще раз.",
    "memberPerms.loadFailed": "Не вдалося завантажити права",
    "memberPerms.notYetAdminHint": "Ще не адміністратор у самому Telegram-каналі (можливо, ще не підписаний) — нижче типовий набір прав для його ролі, буде видано, щойно Telegram підтвердить.",
    "memberPerms.addAdmins": "Додавання адміністраторів",
    "memberPerms.addAdminsLocked": "Заблоковано: через панель не можна давати змогу комусь ще додавати адміністраторів",
    "common.sendFailedGeneric": "не вдалося надіслати",
    "common.unknownError": "невідома",
    "channelModal.removeFailedGeneric": "не вдалося прибрати",
    "queue.empty": "Черга порожня",
    "queue.statusPending": "Очікує",
    "queue.statusApproved": "Схвалено",
    "queue.pinnedTitle": "Закріплено в чаті редакції",
    "queue.publishAt": "Вихід о",
    "queue.approveBtn": "Схвалити",
    "queue.publishNowBtn": "Опублікувати зараз",
    "queue.publishUrgentBtn": "Виставити терміново",
    "queue.publishUrgentTitle": "Публікує негайно, не збиваючи розклад решти черги",
    "queue.noTitle": "(без заголовка)",
    "queue.inQueueSince": "у черзі",
    "queue.deleteFailed": "не вдалося видалити",
    "queue.approvedMsg": "Схвалено! Вийде по черзі, з урахуванням КД каналу.",
    "queue.approveFailed": "не вдалося схвалити",
    "queue.publishedMsg": "Опубліковано!",
    "queue.publishFailed": "не вдалося опублікувати",
    "queue.publishedUrgentAt": "Опубліковано позачергово о",
    "type.text": "Текст",
    "type.photo": "Фото",
    "type.video": "Відео",
    "type.location": "Локація",
    "type.album": "Альбом",
    "submissions.empty": "Тут поки що порожньо",
    "submissions.channelFallback": "канал",
    "submissions.unknownChannel": "невідомий канал",
    "submissions.anonymous": "Аноним",
    "submissions.forChannel": "Для каналу",
    "submissions.publishedIn": "Опубліковано в",
    "submissions.scamWarning": "Підозра на скам",
    "submissions.scamWarningTitle": "Текст містить посилання поруч із типовими фішинг/крипто-скам фразами — перевір уважно перед схваленням",
    "sources.empty": "Джерел ще немає",
    "sources.typeAdminChannel": "Telegram-канал (бот в адмінах)",
    "sources.typePublicChannel": "Публічний канал",
    "sources.editorialBadge": "Редакційне",
    "sources.noRecommendations": "Немає рекомендацій",
    "sources.added": "Додано",
    "sources.addFailed": "не вдалося додати",
    "time.justNow": "щойно",
    "time.minAgo": "хв тому",
    "time.hourAgo": "год тому",
    "time.publishingSoon": "публікується найближчим часом",
    "time.publishIn": "публікація через",
    "time.secShort": "сек",
    "sourceModal.editNameTitle": "Редагувати назву/посилання",
    "sourceModal.namePlaceholder": "Назва",
    "sourceModal.usernamePlaceholder": "username каналу",
    "sourceModal.urlPlaceholder": "URL RSS-стрічки",
    "sourceModal.editorialTitle": "Редакційне джерело",
    "sourceModal.editorialDescOn": "Новини йдуть у чергу без перевірки на схожість і показуються першими.",
    "sourceModal.editorialDescOff": "Новини перевіряються на дублі, як і всі сторонні джерела.",
    "sourceModal.testSendTitle": "Тестова відправка",
    "sourceModal.testSendDesc": "Надіслати останню новину джерела обраним каналам, не чекаючи автопостингу",
    "sourceModal.testSendBtn": "Надіслати останню новину",
    "sourceModal.nameEmpty": "Назва не може бути порожньою",
    "sourceModal.saveFailed": "Не вдалося зберегти",
    "sourceModal.categoryChangeFailed": "не вдалося змінити категорію",
    "sourceModal.selectChannelFirst": "Спочатку обери хоча б один канал для тесту (або цілу категорію одним натисканням).",
    "sourceModal.sending": "Надсилання...",
    "sourceModal.testSentResult": "Готово! Надіслано в",
    "sourceModal.testSentResultSuffix": "Кожен канал отримав свою підпис і посилання.",
    "sourceModal.pasteLinkPrompt": "Встав посилання або @username каналу.",
    "sourceModal.checkingChannel": "Перевіряємо канал…",
    "sourceModal.addedPrefix": "Додано",
    "sourceModal.addFailedDetailed": "не вдалося додати (можливо, канал приватний або вже доданий)",
    "dev.maintenanceOn": "Увімкнено (адміни не мають доступу)",
    "dev.banned": "забанений",
    "dev.inactive": "неактивний",
    "dev.owner": "Власник",
    "dev.added": "Додано",
    "dev.reassignBtn": "Перепривласнити",
    "dev.unbanBtn": "Розбанити",
    "dev.banBtn": "Забанити",
    "dev.reassignPrompt": "Новий user_id власника каналу:",
    "dev.reassignFailed": "Помилка перепривласнення",
    "dev.fillAllFields": "Заповни всі поля.",
    "dev.nothingFound": "Нічого не знайдено",
    "dev.roleAdmin": "адмін",
    "dev.roleReader": "читач",
    "dev.channelsShort": "каналів",
    "dev.submissionsShort": "предложок",
    "dev.noErrors": "Помилок не зафіксовано",
    "editor.submitLink": "Надіслати новину",
    "editor.applyWatermark": "Накласти водяний знак",
    "editor.photoLoadFailed": "Не вдалося завантажити фото",
    "editor.videoLoadFailed": "Не вдалося завантажити відео",
    "editor.notValidImage": "Файл завантажено, але це не коректне зображення.",
    "common.unknownErrorFull": "невідома помилка",
    "editor.watermarkAlbumsUnsupported": "Водяний знак для альбомів поки не підтримується",
    "editor.albumMinOneFile": "В альбомі має залишитись хоча б один файл.",
    "editor.addFileFailed": "не вдалося додати файл",
    "editor.coordinates": "Координати",
    "editor.scheduleMediaUnsupported": "Планування поки підтримує лише текстові пости без медіа",
    "editor.defaultTextWord": "текст",
    "editor.pasteLinkPrompt": "Вставте посилання:",
    "editor.defaultLinkWord": "посилання",
    "editor.nothingToRewrite": "Спочатку введи текст — рерайтити нічого.",
    "editor.aiRewriteFailed": "Не вдалося виконати ІІ-рерайт",
    "editor.enterTextFirst": "Спочатку введи текст.",
    "editor.aiTitleFailed": "Не вдалося згенерувати заголовок",
    "editor.selectChannelFirst": "Спочатку обери хоча б один канал для публікації.",
    "editor.specifyDateTime": "Вкажи дату й час публікації.",
    "editor.publishTimeMustBeFuture": "Час публікації має бути в майбутньому.",
    "editor.scheduledPostDefaultTitle": "Заплановий пост",
    "editor.scheduleError": "Помилка планування",
    "editor.scheduleFailed": "не вдалося запланувати",
    "editor.scheduledFor": "Заплановано на",
    "editor.textSavedChannelsNot": "Текст збережено, але канали — ні",
    "editor.savedAndQueued": "Збережено та додано в чергу публікації",
    "editor.watermarkSingleChannelOnly": "З водяним знаком поки можна публікувати лише в один канал за раз — обери один.",
    "editor.approvedAndQueued": "Пост схвалено та додано в чергу публікацій",
    "editor.confirmDeleteFromQueue": "Видалити цю новину з черги?",
    "editor.confirmReject": "Відхилити цю новину? Її не буде опубліковано.",
    "editor.buildingPreview": "Формування прев'ю…",
    "editor.emptyText": "порожній текст",
    "editor.quickEmoji": "Швидкі емодзі",
    "editor.customEmoji": "Кастомні емодзі",
    "editor.customEmojiSetHint": "Встав посилання на набір кастомних емодзі з Telegram (t.me/addemoji/…), яким ти володієш чи маєш доступ.",
    "editor.connectSetBtn": "Підключити пак",
    "editor.checkingSet": "Перевіряємо пак…",
    "editor.connectSetFailed": "Не вдалося підключити пак",
    "editor.setHasNoEmoji": "У цьому паку немає кастомних емодзі",
    "editor.changeSetBtn": "Змінити пак",
    "editor.emptyFile": "Порожній файл",
    "editor.lockedByPrefix": "Зараз редагує:",
    "editor.lockedByUnknown": "інший адмін",
    "common.or": "або",
    "channelModal.usernameNotFound": "Бот не знає такого користувача — попроси його спершу написати боту чи відкрити цю панель, або дізнайся числовий user_id.",
    "channelModal.statsTitle": "Ефективність команди",
    "channelModal.statsHint": "Скільки схвалень/відхилень зробив кожен і середній час реакції. Дані про перегляди/охоплення Telegram Bot API не надає, тому тут їх немає.",
    "channelModal.statsEmpty": "Поки що немає жодної дії — статистика з'явиться після перших схвалень.",
    "channelModal.statsQueueApproved": "Схвалено новин",
    "channelModal.statsSubmissionsApproved": "Схвалено предложок",
    "channelModal.statsSubmissionsRejected": "Відхилено предложок",
    "channelModal.statsAvgReaction": "Сер. час реакції",
    "channelModal.hoursShort": "год",
    "push.title": "Push-сповіщення",
    "push.desc": "Тривоги й нові новини — прямо на телефон. Працює лише якщо панель встановлена як окремий застосунок («Додати на головний екран»), а не відкрита через кнопку в Telegram.",
    "push.testBtn": "Надіслати тестове сповіщення",
    "push.permissionDenied": "Сповіщення заблоковано в налаштуваннях браузера — дозволь їх для цього сайту вручну.",
    "push.subscribeFailed": "Не вдалося підключити push-сповіщення.",
    "push.testSent": "Тестове сповіщення надіслано!",
    "push.testFailed": "Не вдалося надіслати тестове сповіщення.",
  },
  ru: {
    "header.title": "Бот тревог и новостей",
    "header.subtitle": "панель управления",
    "nav.home": "Главная",
    "nav.sources": "Источники",
    "nav.editorial": "Редакция",
    "nav.profile": "Профиль",
    "nav.dev": "Тех.раздел",
    "queue.segFeed": "Источники",
    "queue.segReaders": "Читатели",
    "channels.statLabelTotal": "Всего каналов",
    "channels.statLabelActive": "Активные",
    "channels.addBtn": "Добавить канал",
    "channels.hint": "Нажми кнопку выше, выбери канал из списка своих Telegram-каналов и подтверди права администратора.",
    "sources.statLabel": "Активные источники",
    "sources.tgSectionLabel": "Telegram-канал (публичный, по ссылке)",
    "sources.linkPlaceholder": "t.me/username или @username",
    "sources.addByLinkBtn": "Добавить по ссылке",
    "sources.listLabel": "Источники новостей",
    "sources.filterAll": "Все",
    "sources.filterEditorial": "Редакционные",
    "sources.filterPublic": "Публичные каналы",
    "sources.recommendedLabel": "Рекомендованные источники: война и политика",
    "sourceModal.title": "Источник новостей",
    "moderation.new": "Входящие",
    "moderation.approved": "Одобрено",
    "settings.languageLabel": "Язык",
    "profile.idLabel": "ID",
    "profile.channelsShort": "каналов",
    "profile.sourcesShort": "источников",
    "profile.automationLabel": "Автоматизация",
    "profile.autoApproveLabel": "Автоодобрение новостей",
    "profile.autopostLabel": "Автопостинг из очереди",
    "profile.delayLabel": "Задержка публикаций",
    "profile.queueStatusLabel": "Очередь",
    "profile.serviceLabel": "Сервис",
    "autoApprove.hint": "Пока приложение открыто — новости ждут вашего ручного одобрения. Через минуту после закрытия приложения новости для ваших каналов начинают одобряться сами. Система ещё дорабатывается — тут можно выключить эту автоматику для себя полностью.",
    "dev.statsLabel": "Статистика платформы",
    "dev.channelsTotal": "Каналов всего",
    "dev.activeAdmins": "Активных админов",
    "dev.subsToday": "Предложек сегодня",
    "dev.subsTotal": "Предложек всего",
    "dev.maintenanceLabel": "Технический перерыв",
    "dev.manualAddLabel": "Ручное добавление канала",
    "dev.chatIdPlaceholder": "chat_id канала (например -1001234567890)",
    "dev.titlePlaceholder": "Название канала",
    "dev.adminIdPlaceholder": "user_id админа-владельца",
    "dev.addManualBtn": "Добавить вручную",
    "dev.allChannelsLabel": "Все каналы платформы",
    "dev.userSearchLabel": "Поиск пользователя",
    "dev.userSearchPlaceholder": "user_id или имя",
    "dev.findBtn": "Найти",
    "dev.errorsLabel": "Последние ошибки",
    "channelModal.title": "Настройки канала",
    "editor.title": "Редактирование поста",
    "editor.channelLabel": "Каналы",
    "editor.footerToggle": "Подпись канала",
    "editor.publishBtn": "Одобрить и опубликовать",
    "editor.rejectBtn": "Отклонить",
    "editor.selectAll": "Все",
    "editor.deselectAll": "Никого",
    "editor.scheduleToggle": "Запланировать",
    "editor.soon": "скоро",
    "editor.previewTitle": "Предпросмотр",
    "editor.tbBold": "Жирный",
    "editor.tbItalic": "Курсив",
    "editor.tbUnderline": "Подчёркнутый",
    "editor.tbStrike": "Зачёркнутый",
    "editor.tbMono": "Моноширинный",
    "editor.tbSpoiler": "Спойлер",
    "editor.tbLink": "Ссылка",
    "editor.tbEmoji": "Эмодзи",
    "editor.tbCustomEmoji": "Кастомные эмодзи",
    "editor.textPlaceholder": "Текст новости…",
    "editor.styleNeutral": "Обычный",
    "editor.styleOfficial": "Официально",
    "editor.styleUrgent": "Срочно",
    "editor.styleSummary": "Кратко",
    "editor.aiRewriteBtn": "ИИ-рерайт",
    "editor.aiTitleBtnTitle": "Заголовок и хештеги",
    "editor.aiTitleBtn": "Заголовок",
    "editor.previewBtnTitle": "Полный просмотр",
    "editor.previewBtn": "Просмотр",
    "memberPerms.title": "Права администратора",
    "categoryPicker.title": "Выбрать категорию",
    "dev.backBtn": "← Профиль",
    "common.loading": "Загрузка...",
    "common.save": "Сохранить",
    "common.hide": "Скрыть",
    "common.show": "Показать",
    "common.on": "Включено",
    "common.off": "Выключено",
    "common.cancel": "Отмена",
    "common.delete": "Удалить",
    "common.edit": "Редактировать",
    "common.add": "Добавить",
    "common.close": "Закрыть",
    "common.yes": "Да",
    "common.no": "Нет",
    "common.error": "Ошибка",
    "common.success": "Готово",
    "common.confirm": "Подтвердить",
    "common.notSpecified": "Не указано",
    "common.noAccess": "Нет доступа",
    "channels.empty": "Каналов пока нет",
    "channels.noCategory": "Без категории",
    "channelStyle.noData": "Ещё нет накопленных постов для анализа стиля (появятся после новых постов в канале).",
    "channelStyle.analyzed": "Проанализировано постов",
    "channelStyle.topEmoji": "частое эмодзи",
    "channelStyle.boldStart": "жирный заголовок",
    "channelStyle.withLink": "со ссылкой",
    "categoryPicker.hint": "Выбери категорию одним кликом — без ручного ввода.",
    "categoryPicker.yourCategories": "Твои категории",
    "categoryPicker.presetTags": "Готовые теги",
    "categoryPicker.deleteCategoryAria": "Удалить категорию",
    "categoryPicker.deleteConfirm": "Удалить категорию",
    "categoryPicker.deleteConfirmSuffix": "Каналы останутся — просто без категории.",
    "categoryPicker.deleteFailed": "Не удалось удалить категорию",
    "categoryPicker.addCategoryBtn": "Добавить категорию",
    "categoryPicker.folderExists": "Такая папка уже есть",
    "channels.botRemoved": "бот удалён",
    "channels.subscribers": "подписчиков",
    "channels.deleteFailed": "не удалось удалить канал",
    "channels.moveFailed": "Не удалось перенести канал в категорию",
    "channelModal.tabMain": "Главная",
    "channelModal.tabAlerts": "Тревоги",
    "channelModal.tabMedia": "Медиа",
    "channelModal.tabTeam": "Команда",
    "channelModal.subscribersLabel": "Подписчики",
    "channelModal.automationTitle": "Автоматизация",
    "channelModal.automationDesc": "Автоодобрение предложек и автопостинг из очереди — отдельно для этого канала",
    "channelModal.autoApproveLabel": "Автоодобрение предложек читателей",
    "channelModal.autoApproveHint": "Пока приложение открыто — предложки ждут ручного одобрения. Через минуту после закрытия они начинают публиковаться сами.",
    "channelModal.autopostLabel": "Автопостинг новостей из очереди",
    "common.minutesShort": "мин",
    "channelModal.cdHint": "КД между публикациями именно в этот канал",
    "channelModal.queuePendingLabel": "В очереди для этого канала",
    "channelModal.publishTitle": "Публикация новостей",
    "channelModal.publishDescBase": "Автопостинг в этот канал",
    "channelModal.publishDescExtra": ", тестовая публикация и ссылка для читателей",
    "channelModal.sendTestNewsBtn": "Отправить тестовую новость",
    "channelModal.copyLinkBtn": "Скопировать ссылку для читателей",
    "channelModal.alertMonitorTitle": "Мониторинг воздушных тревог",
    "channelModal.alertMonitorDesc": "NEPTUN — официальные тревоги/отбой и движение целей по выбранным областям (настраивается во вкладке «Тревоги»)",
    "channelModal.oblastsNone": "Области: не выбрано",
    "channelModal.oblastsSelected": "Области: выбрано",
    "channelModal.oblastsOf": "из",
    "channelModal.oblastsDesc": "Какие области мониторить",
    "channelModal.oblastSearchPlaceholder": "Поиск области…",
    "channelModal.selectAll": "Выбрать все",
    "channelModal.deselectAll": "Снять все",
    "channelModal.sirenTitle": "Сирена",
    "channelModal.sirenDesc": "Тревога / отбой по области или району",
    "channelModal.targetsTitle": "Конкретные цели",
    "channelModal.targetsDesc": "Шахед / ракета / КАБ в движении",
    "channelModal.showMapLabel": "Карта движения цели",
    "channelModal.showMapHint": "Вместо текста — фото-карта с маршрутом цели (если NEPTUN даёт координаты)",
    "channelModal.testAlertBtn": "Тест: отправить тестовую тревогу",
    "channelModal.typeUav": "БпЛА (шахед)",
    "channelModal.typeRecon": "Разведывательный БпЛА",
    "channelModal.typeMissile": "Крылатая ракета",
    "channelModal.typeBallistic": "Баллистическая ракета",
    "channelModal.typeKab": "КАБ",
    "channelModal.typeMig31k": "МиГ-31К",
    "common.saving": "Сохранение…",
    "common.savedCheck": "✓ Сохранено",
    "channelModal.testAlertSent": "Тестовое уведомление отправлено в канал",
    "channelModal.watermarkTitle": "Водяной знак",
    "channelModal.watermarkDesc": "Накладывается на каждое фото и видео этого канала",
    "channelModal.uploadLogoBtn": "Загрузить логотип",
    "channelModal.saveWatermarkBtn": "Сохранить знак",
    "channelModal.removeWatermarkBtn": "Убрать знак",
    "channelModal.livePreviewTitle": "Живой предпросмотр",
    "channelModal.livePreviewDesc": "Прозрачность, размер и позиция знака",
    "channelModal.opacityLabel": "Прозрачность",
    "channelModal.sizeLabel": "Размер",
    "channelModal.sizeLabelSuffix": "от ширины фото",
    "channelModal.positionsLabel": "Позиции на фото/видео (можно несколько)",
    "channelModal.saveWmSettingsBtn": "Сохранить настройки знака",
    "channelModal.demoPhotoText": "Пример фото",
    "channelModal.fileChosenPrefix": "Выбрано",
    "channelModal.noWatermarkYet": "Ещё не загружено — пока используется название канала текстом",
    "channelModal.wmPreviewFailed": "Знак есть, но превью загрузить не удалось",
    "channelModal.chooseFileFirst": "Сначала выбери файл картинки.",
    "common.networkError": "Сетевая ошибка",
    "channelModal.wmSaved": "Водяной знак сохранён — теперь будет накладываться на каждое фото и видео этого канала.",
    "channelModal.wmRemoved": "Водяной знак убран.",
    "channelModal.wmSettingsSaved": "Настройки знака сохранены",
    "channelModal.linkCopied": "Ссылка скопирована! Поставь её на кнопку в канале — читатели смогут отправлять новости именно для него.",
    "channelModal.testMsgSent": "Тестовое сообщение отправлено",
    "channelModal.teamAddTitle": "Добавить участника",
    "channelModal.teamAddDesc": "По user_id или @username (сработает, если человек уже хоть раз открывал эту панель или писал боту)",
    "channelModal.roleEditor": "Редактор",
    "channelModal.roleModerator": "Модератор",
    "channelModal.teamMembersTitle": "Участники канала",
    "channelModal.invalidUserId": "Укажи корректный user_id",
    "channelModal.addingMember": "Добавляем…",
    "channelModal.addedWithTgWarning": "Добавлено в панели, но права в самом Telegram-канале выдать не удалось (человек ещё не подписан на канал или бот не имеет прав добавлять админов)",
    "channelModal.addMemberFailed": "Не удалось добавить",
    "channelModal.teamLoadFailed": "Не удалось загрузить команду",
    "channelModal.teamEmpty": "Пока никого не добавлено",
    "channelModal.removeMemberBtn": "Убрать",
    "common.saveFailedGeneric": "не удалось сохранить",
    "common.nonJsonResponse": "Сервер вернул не-JSON ответ",
    "channels.dataStillLoading": "Подожди секунду, данные ещё загружаются, попробуй ещё раз.",
    "memberPerms.loadFailed": "Не удалось загрузить права",
    "memberPerms.notYetAdminHint": "Ещё не администратор в самом Telegram-канале (возможно, ещё не подписан) — ниже типовой набор прав для его роли, будет выдан, как только Telegram подтвердит.",
    "memberPerms.addAdmins": "Добавление администраторов",
    "memberPerms.addAdminsLocked": "Заблокировано: через панель нельзя давать возможность кому-то ещё добавлять администраторов",
    "common.sendFailedGeneric": "не удалось отправить",
    "common.unknownError": "неизвестная",
    "channelModal.removeFailedGeneric": "не удалось убрать",
    "queue.empty": "Очередь пуста",
    "queue.statusPending": "Ожидает",
    "queue.statusApproved": "Одобрено",
    "queue.pinnedTitle": "Закреплено в редакционном чате",
    "queue.publishAt": "Выход в",
    "queue.approveBtn": "Одобрить",
    "queue.publishNowBtn": "Опубликовать сейчас",
    "queue.publishUrgentBtn": "Выставить срочно",
    "queue.publishUrgentTitle": "Публикует немедленно, не сбивая расписание остальной очереди",
    "queue.noTitle": "(без заголовка)",
    "queue.inQueueSince": "в очереди",
    "queue.deleteFailed": "не удалось удалить",
    "queue.approvedMsg": "Одобрено! Выйдет по очереди, с учётом КД канала.",
    "queue.approveFailed": "не удалось одобрить",
    "queue.publishedMsg": "Опубликовано!",
    "queue.publishFailed": "не удалось опубликовать",
    "queue.publishedUrgentAt": "Опубликовано вне очереди в",
    "type.text": "Текст",
    "type.photo": "Фото",
    "type.video": "Видео",
    "type.location": "Локация",
    "type.album": "Альбом",
    "submissions.empty": "Здесь пока пусто",
    "submissions.channelFallback": "канал",
    "submissions.unknownChannel": "неизвестный канал",
    "submissions.anonymous": "Аноним",
    "submissions.forChannel": "Для канала",
    "submissions.publishedIn": "Опубликовано в",
    "submissions.scamWarning": "Подозрение на скам",
    "submissions.scamWarningTitle": "Текст содержит ссылку рядом с типичными фишинг/крипто-скам фразами — проверь внимательно перед одобрением",
    "sources.empty": "Источников пока нет",
    "sources.typeAdminChannel": "Telegram-канал (бот в админах)",
    "sources.typePublicChannel": "Публичный канал",
    "sources.editorialBadge": "Редакционное",
    "sources.noRecommendations": "Нет рекомендаций",
    "sources.added": "Добавлено",
    "sources.addFailed": "не удалось добавить",
    "time.justNow": "только что",
    "time.minAgo": "мин назад",
    "time.hourAgo": "ч назад",
    "time.publishingSoon": "публикуется в ближайшее время",
    "time.publishIn": "публикация через",
    "time.secShort": "сек",
    "sourceModal.editNameTitle": "Редактировать название/ссылку",
    "sourceModal.namePlaceholder": "Название",
    "sourceModal.usernamePlaceholder": "username канала",
    "sourceModal.urlPlaceholder": "URL RSS-ленты",
    "sourceModal.editorialTitle": "Редакционный источник",
    "sourceModal.editorialDescOn": "Новости идут в очередь без проверки на схожесть и показываются первыми.",
    "sourceModal.editorialDescOff": "Новости проверяются на дубли, как и все сторонние источники.",
    "sourceModal.testSendTitle": "Тестовая отправка",
    "sourceModal.testSendDesc": "Отправить последнюю новость источника выбранным каналам, не дожидаясь автопостинга",
    "sourceModal.testSendBtn": "Отправить последнюю новость",
    "sourceModal.nameEmpty": "Название не может быть пустым",
    "sourceModal.saveFailed": "Не удалось сохранить",
    "sourceModal.categoryChangeFailed": "не удалось изменить категорию",
    "sourceModal.selectChannelFirst": "Сначала выбери хотя бы один канал для теста (или целую категорию одним нажатием).",
    "sourceModal.sending": "Отправка...",
    "sourceModal.testSentResult": "Готово! Отправлено в",
    "sourceModal.testSentResultSuffix": "Каждый канал получил свою подпись и ссылку.",
    "sourceModal.pasteLinkPrompt": "Вставь ссылку или @username канала.",
    "sourceModal.checkingChannel": "Проверяем канал…",
    "sourceModal.addedPrefix": "Добавлено",
    "sourceModal.addFailedDetailed": "не удалось добавить (возможно, канал приватный или уже добавлен)",
    "dev.maintenanceOn": "Включено (админы не имеют доступа)",
    "dev.banned": "забанен",
    "dev.inactive": "неактивен",
    "dev.owner": "Владелец",
    "dev.added": "Добавлено",
    "dev.reassignBtn": "Переприсвоить",
    "dev.unbanBtn": "Разбанить",
    "dev.banBtn": "Забанить",
    "dev.reassignPrompt": "Новый user_id владельца канала:",
    "dev.reassignFailed": "Ошибка переприсвоения",
    "dev.fillAllFields": "Заполни все поля.",
    "dev.nothingFound": "Ничего не найдено",
    "dev.roleAdmin": "админ",
    "dev.roleReader": "читатель",
    "dev.channelsShort": "каналов",
    "dev.submissionsShort": "предложек",
    "dev.noErrors": "Ошибок не зафиксировано",
    "editor.submitLink": "Отправить новость",
    "editor.applyWatermark": "Наложить водяной знак",
    "editor.photoLoadFailed": "Не удалось загрузить фото",
    "editor.videoLoadFailed": "Не удалось загрузить видео",
    "editor.notValidImage": "Файл загружен, но это некорректное изображение.",
    "common.unknownErrorFull": "неизвестная ошибка",
    "editor.watermarkAlbumsUnsupported": "Водяной знак для альбомов пока не поддерживается",
    "editor.albumMinOneFile": "В альбоме должен остаться хотя бы один файл.",
    "editor.addFileFailed": "не удалось добавить файл",
    "editor.coordinates": "Координаты",
    "editor.scheduleMediaUnsupported": "Планирование пока поддерживает только текстовые посты без медиа",
    "editor.defaultTextWord": "текст",
    "editor.pasteLinkPrompt": "Вставьте ссылку:",
    "editor.defaultLinkWord": "ссылка",
    "editor.nothingToRewrite": "Сначала введи текст — рерайтить нечего.",
    "editor.aiRewriteFailed": "Не удалось выполнить ИИ-рерайт",
    "editor.enterTextFirst": "Сначала введи текст.",
    "editor.aiTitleFailed": "Не удалось сгенерировать заголовок",
    "editor.selectChannelFirst": "Сначала выбери хотя бы один канал для публикации.",
    "editor.specifyDateTime": "Укажи дату и время публикации.",
    "editor.publishTimeMustBeFuture": "Время публикации должно быть в будущем.",
    "editor.scheduledPostDefaultTitle": "Запланированный пост",
    "editor.scheduleError": "Ошибка планирования",
    "editor.scheduleFailed": "не удалось запланировать",
    "editor.scheduledFor": "Запланировано на",
    "editor.textSavedChannelsNot": "Текст сохранён, но каналы — нет",
    "editor.savedAndQueued": "Сохранено и добавлено в очередь публикации",
    "editor.watermarkSingleChannelOnly": "С водяным знаком пока можно публиковать только в один канал за раз — выбери один.",
    "editor.approvedAndQueued": "Пост одобрен и добавлен в очередь публикаций",
    "editor.confirmDeleteFromQueue": "Удалить эту новость из очереди?",
    "editor.confirmReject": "Отклонить эту новость? Она не будет опубликована.",
    "editor.buildingPreview": "Формирование превью…",
    "editor.emptyText": "пустой текст",
    "editor.quickEmoji": "Быстрые эмодзи",
    "editor.customEmoji": "Кастомные эмодзи",
    "editor.customEmojiSetHint": "Вставь ссылку на набор кастомных эмодзи из Telegram (t.me/addemoji/…), которым ты владеешь или имеешь доступ.",
    "editor.connectSetBtn": "Подключить пак",
    "editor.checkingSet": "Проверяем пак…",
    "editor.connectSetFailed": "Не удалось подключить пак",
    "editor.setHasNoEmoji": "В этом паке нет кастомных эмодзи",
    "editor.changeSetBtn": "Изменить пак",
    "editor.emptyFile": "Пустой файл",
    "editor.lockedByPrefix": "Сейчас редактирует:",
    "editor.lockedByUnknown": "другой админ",
    "common.or": "или",
    "channelModal.usernameNotFound": "Бот не знает такого пользователя — попроси его сначала написать боту или открыть эту панель, либо узнай числовой user_id.",
    "channelModal.statsTitle": "Эффективность команды",
    "channelModal.statsHint": "Сколько одобрений/отклонений сделал каждый и среднее время реакции. Данных о просмотрах/охвате Telegram Bot API не даёт, поэтому их здесь нет.",
    "channelModal.statsEmpty": "Пока нет ни одного действия — статистика появится после первых одобрений.",
    "channelModal.statsQueueApproved": "Одобрено новостей",
    "channelModal.statsSubmissionsApproved": "Одобрено предложек",
    "channelModal.statsSubmissionsRejected": "Отклонено предложек",
    "channelModal.statsAvgReaction": "Сред. время реакции",
    "channelModal.hoursShort": "ч",
    "push.title": "Push-уведомления",
    "push.desc": "Тревоги и новые новости — прямо на телефон. Работает только если панель установлена как отдельное приложение («Добавить на главный экран»), а не открыта через кнопку в Telegram.",
    "push.testBtn": "Отправить тестовое уведомление",
    "push.permissionDenied": "Уведомления заблокированы в настройках браузера — разреши их для этого сайта вручную.",
    "push.subscribeFailed": "Не удалось подключить push-уведомления.",
    "push.testSent": "Тестовое уведомление отправлено!",
    "push.testFailed": "Не удалось отправить тестовое уведомление.",
  },
  en: {
    "header.title": "Alerts & News Bot",
    "header.subtitle": "control panel",
    "nav.home": "Home",
    "nav.sources": "Sources",
    "nav.editorial": "Editorial",
    "nav.profile": "Profile",
    "nav.dev": "Tech section",
    "queue.segFeed": "Sources",
    "queue.segReaders": "Readers",
    "channels.statLabelTotal": "Total channels",
    "channels.statLabelActive": "Active",
    "channels.addBtn": "Add channel",
    "channels.hint": "Tap the button above, pick a channel from your list of Telegram channels, and confirm admin rights.",
    "sources.statLabel": "Active sources",
    "sources.tgSectionLabel": "Telegram channel (public, by link)",
    "sources.linkPlaceholder": "t.me/username or @username",
    "sources.addByLinkBtn": "Add by link",
    "sources.listLabel": "News sources",
    "sources.filterAll": "All",
    "sources.filterEditorial": "Editorial",
    "sources.filterPublic": "Public channels",
    "sources.recommendedLabel": "Recommended sources: war & politics",
    "sourceModal.title": "News source",
    "moderation.new": "Incoming",
    "moderation.approved": "Approved",
    "settings.languageLabel": "Language",
    "profile.idLabel": "ID",
    "profile.channelsShort": "channels",
    "profile.sourcesShort": "sources",
    "profile.automationLabel": "Automation",
    "profile.autoApproveLabel": "Auto-approve news",
    "profile.autopostLabel": "Auto-post from queue",
    "profile.delayLabel": "Publish delay",
    "profile.queueStatusLabel": "Queue",
    "profile.serviceLabel": "Service",
    "autoApprove.hint": "While the app is open, news wait for your manual approval. A minute after you close the app, news for your channels start getting approved automatically. This system is still being refined — you can turn this automation off for yourself entirely here.",
    "dev.statsLabel": "Platform stats",
    "dev.channelsTotal": "Total channels",
    "dev.activeAdmins": "Active admins",
    "dev.subsToday": "Submissions today",
    "dev.subsTotal": "Submissions total",
    "dev.maintenanceLabel": "Maintenance mode",
    "dev.manualAddLabel": "Manually add a channel",
    "dev.chatIdPlaceholder": "channel chat_id (e.g. -1001234567890)",
    "dev.titlePlaceholder": "Channel title",
    "dev.adminIdPlaceholder": "owner admin's user_id",
    "dev.addManualBtn": "Add manually",
    "dev.allChannelsLabel": "All platform channels",
    "dev.userSearchLabel": "Search user",
    "dev.userSearchPlaceholder": "user_id or name",
    "dev.findBtn": "Find",
    "dev.errorsLabel": "Recent errors",
    "channelModal.title": "Channel settings",
    "editor.title": "Edit post",
    "editor.channelLabel": "Channels",
    "editor.footerToggle": "Channel signature",
    "editor.publishBtn": "Approve and publish",
    "editor.rejectBtn": "Reject",
    "editor.selectAll": "All",
    "editor.deselectAll": "None",
    "editor.scheduleToggle": "Schedule",
    "editor.soon": "soon",
    "editor.previewTitle": "Preview",
    "editor.tbBold": "Bold",
    "editor.tbItalic": "Italic",
    "editor.tbUnderline": "Underline",
    "editor.tbStrike": "Strikethrough",
    "editor.tbMono": "Monospace",
    "editor.tbSpoiler": "Spoiler",
    "editor.tbLink": "Link",
    "editor.tbEmoji": "Emoji",
    "editor.tbCustomEmoji": "Custom emoji",
    "editor.textPlaceholder": "News text…",
    "editor.styleNeutral": "Neutral",
    "editor.styleOfficial": "Official",
    "editor.styleUrgent": "Urgent",
    "editor.styleSummary": "Summary",
    "editor.aiRewriteBtn": "AI rewrite",
    "editor.aiTitleBtnTitle": "Title and hashtags",
    "editor.aiTitleBtn": "Title",
    "editor.previewBtnTitle": "Full preview",
    "editor.previewBtn": "Preview",
    "memberPerms.title": "Admin rights",
    "categoryPicker.title": "Choose category",
    "dev.backBtn": "← Profile",
    "common.loading": "Loading...",
    "common.save": "Save",
    "common.hide": "Hide",
    "common.show": "Show",
    "common.on": "On",
    "common.off": "Off",
    "common.cancel": "Cancel",
    "common.delete": "Delete",
    "common.edit": "Edit",
    "common.add": "Add",
    "common.close": "Close",
    "common.yes": "Yes",
    "common.no": "No",
    "common.error": "Error",
    "common.success": "Done",
    "common.confirm": "Confirm",
    "common.notSpecified": "Not specified",
    "common.noAccess": "No access",
    "channels.empty": "No channels yet",
    "channels.noCategory": "No category",
    "channelStyle.noData": "Not enough posts yet to analyze style (will appear after new posts in the channel).",
    "channelStyle.analyzed": "Posts analyzed",
    "channelStyle.topEmoji": "top emoji",
    "channelStyle.boldStart": "bold headline",
    "channelStyle.withLink": "with a link",
    "categoryPicker.hint": "Pick a category with one tap — no manual typing.",
    "categoryPicker.yourCategories": "Your categories",
    "categoryPicker.presetTags": "Preset tags",
    "categoryPicker.deleteCategoryAria": "Delete category",
    "categoryPicker.deleteConfirm": "Delete category",
    "categoryPicker.deleteConfirmSuffix": "Channels will stay — just without a category.",
    "categoryPicker.deleteFailed": "Failed to delete category",
    "categoryPicker.addCategoryBtn": "Add category",
    "categoryPicker.folderExists": "This folder already exists",
    "channels.botRemoved": "bot removed",
    "channels.subscribers": "subscribers",
    "channels.deleteFailed": "failed to remove channel",
    "channels.moveFailed": "Failed to move channel to category",
    "channelModal.tabMain": "Home",
    "channelModal.tabAlerts": "Alerts",
    "channelModal.tabMedia": "Media",
    "channelModal.tabTeam": "Team",
    "channelModal.subscribersLabel": "Subscribers",
    "channelModal.automationTitle": "Automation",
    "channelModal.automationDesc": "Auto-approve submissions and auto-post from the queue — set separately for this channel",
    "channelModal.autoApproveLabel": "Auto-approve reader submissions",
    "channelModal.autoApproveHint": "While the app is open, submissions wait for manual approval. A minute after closing the app, they start getting published automatically.",
    "channelModal.autopostLabel": "Auto-post news from the queue",
    "common.minutesShort": "min",
    "channelModal.cdHint": "Cooldown between publications in this channel",
    "channelModal.queuePendingLabel": "In queue for this channel",
    "channelModal.publishTitle": "News publishing",
    "channelModal.publishDescBase": "Auto-posting to this channel",
    "channelModal.publishDescExtra": ", test publication and a link for readers",
    "channelModal.sendTestNewsBtn": "Send test news",
    "channelModal.copyLinkBtn": "Copy the readers' link",
    "channelModal.alertMonitorTitle": "Air alert monitoring",
    "channelModal.alertMonitorDesc": "NEPTUN — official alerts/all-clear and target movement across selected oblasts (configured in the «Alerts» tab)",
    "channelModal.oblastsNone": "Oblasts: none selected",
    "channelModal.oblastsSelected": "Oblasts: selected",
    "channelModal.oblastsOf": "of",
    "channelModal.oblastsDesc": "Which oblasts to monitor",
    "channelModal.oblastSearchPlaceholder": "Search oblast…",
    "channelModal.selectAll": "Select all",
    "channelModal.deselectAll": "Deselect all",
    "channelModal.sirenTitle": "Siren",
    "channelModal.sirenDesc": "Alert / all-clear by oblast or district",
    "channelModal.targetsTitle": "Specific targets",
    "channelModal.targetsDesc": "Shahed / missile / KAB in motion",
    "channelModal.showMapLabel": "Target movement map",
    "channelModal.showMapHint": "A photo map with the target's route instead of text (if NEPTUN provides coordinates)",
    "channelModal.testAlertBtn": "Test: send a test alert",
    "channelModal.typeUav": "UAV (Shahed)",
    "channelModal.typeRecon": "Recon UAV",
    "channelModal.typeMissile": "Cruise missile",
    "channelModal.typeBallistic": "Ballistic missile",
    "channelModal.typeKab": "KAB",
    "channelModal.typeMig31k": "MiG-31K",
    "common.saving": "Saving…",
    "common.savedCheck": "✓ Saved",
    "channelModal.testAlertSent": "Test notification sent to the channel",
    "channelModal.watermarkTitle": "Watermark",
    "channelModal.watermarkDesc": "Applied to every photo and video in this channel",
    "channelModal.uploadLogoBtn": "Upload logo",
    "channelModal.saveWatermarkBtn": "Save watermark",
    "channelModal.removeWatermarkBtn": "Remove watermark",
    "channelModal.livePreviewTitle": "Live preview",
    "channelModal.livePreviewDesc": "Watermark opacity, size and position",
    "channelModal.opacityLabel": "Opacity",
    "channelModal.sizeLabel": "Size",
    "channelModal.sizeLabelSuffix": "of photo width",
    "channelModal.positionsLabel": "Positions on the photo/video (multiple allowed)",
    "channelModal.saveWmSettingsBtn": "Save watermark settings",
    "channelModal.demoPhotoText": "Sample photo",
    "channelModal.fileChosenPrefix": "Chosen",
    "channelModal.noWatermarkYet": "Not uploaded yet — the channel name is used as text for now",
    "channelModal.wmPreviewFailed": "There's a watermark, but the preview failed to load",
    "channelModal.chooseFileFirst": "Choose an image file first.",
    "common.networkError": "Network error",
    "channelModal.wmSaved": "Watermark saved — it will now be applied to every photo and video in this channel.",
    "channelModal.wmRemoved": "Watermark removed.",
    "channelModal.wmSettingsSaved": "Watermark settings saved",
    "channelModal.linkCopied": "Link copied! Put it on a button in the channel — readers will be able to submit news specifically to it.",
    "channelModal.testMsgSent": "Test message sent",
    "channelModal.teamAddTitle": "Add a member",
    "channelModal.teamAddDesc": "By user_id or @username (works if that person has already opened this panel or messaged the bot at least once)",
    "channelModal.roleEditor": "Editor",
    "channelModal.roleModerator": "Moderator",
    "channelModal.teamMembersTitle": "Channel members",
    "channelModal.invalidUserId": "Enter a valid user_id",
    "channelModal.addingMember": "Adding…",
    "channelModal.addedWithTgWarning": "Added in the panel, but couldn't grant rights in the Telegram channel itself (the person isn't subscribed yet, or the bot lacks rights to add admins)",
    "channelModal.addMemberFailed": "Failed to add",
    "channelModal.teamLoadFailed": "Failed to load the team",
    "channelModal.teamEmpty": "No one added yet",
    "channelModal.removeMemberBtn": "Remove",
    "common.saveFailedGeneric": "failed to save",
    "common.nonJsonResponse": "The server returned a non-JSON response",
    "channels.dataStillLoading": "Wait a second, data is still loading, try again.",
    "memberPerms.loadFailed": "Failed to load permissions",
    "memberPerms.notYetAdminHint": "Not yet an admin in the Telegram channel itself (may not have subscribed yet) — below is the default rights set for their role, granted as soon as Telegram confirms.",
    "memberPerms.addAdmins": "Adding admins",
    "memberPerms.addAdminsLocked": "Locked: the panel can't grant someone the ability to add more admins",
    "common.sendFailedGeneric": "failed to send",
    "common.unknownError": "unknown",
    "channelModal.removeFailedGeneric": "failed to remove",
    "queue.empty": "Queue is empty",
    "queue.statusPending": "Pending",
    "queue.statusApproved": "Approved",
    "queue.pinnedTitle": "Pinned in the editorial chat",
    "queue.publishAt": "Publishes at",
    "queue.approveBtn": "Approve",
    "queue.publishNowBtn": "Publish now",
    "queue.publishUrgentBtn": "Publish urgently",
    "queue.publishUrgentTitle": "Publishes immediately without disrupting the rest of the queue's schedule",
    "queue.noTitle": "(no title)",
    "queue.inQueueSince": "in queue",
    "queue.deleteFailed": "failed to delete",
    "queue.approvedMsg": "Approved! Will go out in queue order, per the channel's cooldown.",
    "queue.approveFailed": "failed to approve",
    "queue.publishedMsg": "Published!",
    "queue.publishFailed": "failed to publish",
    "queue.publishedUrgentAt": "Published out of order at",
    "type.text": "Text",
    "type.photo": "Photo",
    "type.video": "Video",
    "type.location": "Location",
    "type.album": "Album",
    "submissions.empty": "Nothing here yet",
    "submissions.channelFallback": "channel",
    "submissions.unknownChannel": "unknown channel",
    "submissions.anonymous": "Anonymous",
    "submissions.forChannel": "For channel",
    "submissions.publishedIn": "Published in",
    "submissions.scamWarning": "Possible scam",
    "submissions.scamWarningTitle": "The text contains a link next to typical phishing/crypto-scam phrases — review carefully before approving",
    "sources.empty": "No sources yet",
    "sources.typeAdminChannel": "Telegram channel (bot is an admin)",
    "sources.typePublicChannel": "Public channel",
    "sources.editorialBadge": "Editorial",
    "sources.noRecommendations": "No recommendations",
    "sources.added": "Added",
    "sources.addFailed": "failed to add",
    "time.justNow": "just now",
    "time.minAgo": "min ago",
    "time.hourAgo": "h ago",
    "time.publishingSoon": "publishing soon",
    "time.publishIn": "publishing in",
    "time.secShort": "sec",
    "sourceModal.editNameTitle": "Edit name/link",
    "sourceModal.namePlaceholder": "Name",
    "sourceModal.usernamePlaceholder": "channel username",
    "sourceModal.urlPlaceholder": "RSS feed URL",
    "sourceModal.editorialTitle": "Editorial source",
    "sourceModal.editorialDescOn": "News goes straight to the queue without a duplicate check and shows up first.",
    "sourceModal.editorialDescOff": "News is checked for duplicates, like any third-party source.",
    "sourceModal.testSendTitle": "Test send",
    "sourceModal.testSendDesc": "Send the source's latest news to selected channels without waiting for auto-posting",
    "sourceModal.testSendBtn": "Send latest news",
    "sourceModal.nameEmpty": "Name can't be empty",
    "sourceModal.saveFailed": "Failed to save",
    "sourceModal.categoryChangeFailed": "failed to change category",
    "sourceModal.selectChannelFirst": "First choose at least one channel to test (or a whole category with one tap).",
    "sourceModal.sending": "Sending...",
    "sourceModal.testSentResult": "Done! Sent to",
    "sourceModal.testSentResultSuffix": "Each channel got its own signature and link.",
    "sourceModal.pasteLinkPrompt": "Paste a link or @username of the channel.",
    "sourceModal.checkingChannel": "Checking the channel…",
    "sourceModal.addedPrefix": "Added",
    "sourceModal.addFailedDetailed": "failed to add (the channel may be private or already added)",
    "dev.maintenanceOn": "On (admins have no access)",
    "dev.banned": "banned",
    "dev.inactive": "inactive",
    "dev.owner": "Owner",
    "dev.added": "Added",
    "dev.reassignBtn": "Reassign",
    "dev.unbanBtn": "Unban",
    "dev.banBtn": "Ban",
    "dev.reassignPrompt": "New user_id of the channel owner:",
    "dev.reassignFailed": "Reassignment error",
    "dev.fillAllFields": "Fill in all fields.",
    "dev.nothingFound": "Nothing found",
    "dev.roleAdmin": "admin",
    "dev.roleReader": "reader",
    "dev.channelsShort": "channels",
    "dev.submissionsShort": "submissions",
    "dev.noErrors": "No errors recorded",
    "editor.submitLink": "Submit news",
    "editor.applyWatermark": "Apply watermark",
    "editor.photoLoadFailed": "Failed to load the photo",
    "editor.videoLoadFailed": "Failed to load the video",
    "editor.notValidImage": "File uploaded, but it isn't a valid image.",
    "common.unknownErrorFull": "unknown error",
    "editor.watermarkAlbumsUnsupported": "Watermark isn't supported for albums yet",
    "editor.albumMinOneFile": "At least one file must remain in the album.",
    "editor.addFileFailed": "failed to add the file",
    "editor.coordinates": "Coordinates",
    "editor.scheduleMediaUnsupported": "Scheduling currently only supports text posts without media",
    "editor.defaultTextWord": "text",
    "editor.pasteLinkPrompt": "Paste a link:",
    "editor.defaultLinkWord": "link",
    "editor.nothingToRewrite": "Enter some text first — nothing to rewrite.",
    "editor.aiRewriteFailed": "Failed to run the AI rewrite",
    "editor.enterTextFirst": "Enter some text first.",
    "editor.aiTitleFailed": "Failed to generate a title",
    "editor.selectChannelFirst": "First choose at least one channel to publish to.",
    "editor.specifyDateTime": "Specify the publish date and time.",
    "editor.publishTimeMustBeFuture": "The publish time must be in the future.",
    "editor.scheduledPostDefaultTitle": "Scheduled post",
    "editor.scheduleError": "Scheduling error",
    "editor.scheduleFailed": "failed to schedule",
    "editor.scheduledFor": "Scheduled for",
    "editor.textSavedChannelsNot": "Text saved, but channels weren't",
    "editor.savedAndQueued": "Saved and added to the publish queue",
    "editor.watermarkSingleChannelOnly": "With a watermark you can currently publish to only one channel at a time — pick one.",
    "editor.approvedAndQueued": "Post approved and added to the publish queue",
    "editor.confirmDeleteFromQueue": "Delete this item from the queue?",
    "editor.confirmReject": "Reject this news item? It won't be published.",
    "editor.buildingPreview": "Building preview…",
    "editor.emptyText": "empty text",
    "editor.quickEmoji": "Quick emoji",
    "editor.customEmoji": "Custom emoji",
    "editor.customEmojiSetHint": "Paste a link to a custom emoji set from Telegram (t.me/addemoji/…) that you own or have access to.",
    "editor.connectSetBtn": "Connect pack",
    "editor.checkingSet": "Checking the pack…",
    "editor.connectSetFailed": "Failed to connect the pack",
    "editor.setHasNoEmoji": "This pack has no custom emoji",
    "editor.changeSetBtn": "Change pack",
    "editor.emptyFile": "Empty file",
    "editor.lockedByPrefix": "Currently being edited by:",
    "editor.lockedByUnknown": "another admin",
    "common.or": "or",
    "channelModal.usernameNotFound": "The bot doesn't know this user — ask them to message the bot or open this panel first, or get their numeric user_id.",
    "channelModal.statsTitle": "Team effectiveness",
    "channelModal.statsHint": "How many approvals/rejections each person made and their average reaction time. View/reach data isn't provided by the Telegram Bot API, so it's not shown here.",
    "channelModal.statsEmpty": "No actions yet — stats will appear after the first approvals.",
    "channelModal.statsQueueApproved": "News approved",
    "channelModal.statsSubmissionsApproved": "Submissions approved",
    "channelModal.statsSubmissionsRejected": "Submissions rejected",
    "channelModal.statsAvgReaction": "Avg. reaction time",
    "channelModal.hoursShort": "h",
    "push.title": "Push notifications",
    "push.desc": "Alerts and new news — straight to your phone. Only works if the panel is installed as a separate app (\"Add to Home Screen\"), not opened via the Telegram button.",
    "push.testBtn": "Send a test notification",
    "push.permissionDenied": "Notifications are blocked in browser settings — allow them for this site manually.",
    "push.subscribeFailed": "Failed to enable push notifications.",
    "push.testSent": "Test notification sent!",
    "push.testFailed": "Failed to send the test notification.",
  },
};

function t(key) {
  return (TRANSLATIONS[currentLang] && TRANSLATIONS[currentLang][key]) || (TRANSLATIONS.ua[key]) || key;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-dp]").forEach((el) => {
    el.dataset.placeholder = t(el.dataset.i18nDp);
  });
  document.getElementById("lang-ua-btn").className = "segment" + (currentLang === "ua" ? " active" : "");
  document.getElementById("lang-ru-btn").className = "segment" + (currentLang === "ru" ? " active" : "");
  document.getElementById("lang-en-btn").className = "segment" + (currentLang === "en" ? " active" : "");
}

async function setLanguage(lang) {
  currentLang = lang;
  applyTranslations();
  await api("/api/settings/language", { method: "POST", body: JSON.stringify({ language: lang }) });
}

document.getElementById("lang-ua-btn").addEventListener("click", () => setLanguage("ua"));
document.getElementById("lang-ru-btn").addEventListener("click", () => setLanguage("ru"));
document.getElementById("lang-en-btn").addEventListener("click", () => setLanguage("en"));

const AVATAR_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#06b6d4", "#ef4444", "#3b82f6"];

function letterAvatarHtml(title) {
  const clean = (title || "?").trim();
  const letter = clean ? clean.charAt(0).toUpperCase() : "?";
  let hash = 0;
  for (let i = 0; i < clean.length; i++) hash = clean.charCodeAt(i) + ((hash << 5) - hash);
  const color = AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
  return `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:${color};color:#fff;font-weight:700;font-size:16px;border-radius:50%;">${escapeHtml(letter)}</div>`;
}

async function loadAvatarInto(container, chatId, title) {
  await loadAvatarFromUrlInto(container, `/api/channel-avatar/${chatId}`, title);
}

// Кеш "url -> Promise<об'єкт-URL блобу | null>" на весь час сесії (SPA, без
// перезавантажень сторінки) — щоб та сама аватарка (той самий канал повторюється
// в кожному рядку черги/аватар-стеку) підвантажувалась з мережі РІВНО ОДИН РАЗ,
// а не окремим запитом на кожен елемент DOM. Без цього довгий список черги з
// 4-5 однаковими каналами на рядок бив десятками одночасних запитів по тому ж
// самому /api/channel-avatar — частина впиралась у тайм-аут чи лімiти Telegram
// на бекенді (get_chat дергається наживо щоразу) і сипалась буквеними фолбеками.
const _avatarBlobCache = new Map();

function _fetchAvatarBlobUrl(url) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000);
  return fetch(url, {
    headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
    signal: controller.signal,
  })
    .then((res) => (res.ok ? res.blob() : null))
    .then((blob) => (blob ? URL.createObjectURL(blob) : null))
    .catch(() => null)
    .finally(() => clearTimeout(timeoutId))
    .then((result) => {
      // Невдачу (тайм-аут/лімiт Telegram саме ЗАРАЗ) не кешуємо назавжди — інакше
      // канал назавжди застряг би на буквеному фолбеці до перезавантаження сторінки,
      // хоча за секунду той самий запит цілком міг би пройти успішно.
      if (!result) _avatarBlobCache.delete(url);
      return result;
    });
}

async function loadAvatarFromUrlInto(container, url, title) {
  const showFallback = () => { container.innerHTML = letterAvatarHtml(title); };
  if (!_avatarBlobCache.has(url)) {
    _avatarBlobCache.set(url, _fetchAvatarBlobUrl(url));
  }
  const objUrl = await _avatarBlobCache.get(url);
  if (!objUrl) { showFallback(); return; }
  const img = document.createElement("img");
  img.src = objUrl;
  img.alt = "";
  img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
  img.onerror = showFallback;
  container.innerHTML = "";
  container.appendChild(img);
}

async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Init-Data": initData,
        "ngrok-skip-browser-warning": "true",
        ...(options.headers || {}),
      },
    });
  } catch (networkErr) {
    console.error("api() network error:", path, networkErr);
    return { ok: false, error: `${t("common.networkError")}: ${networkErr.message}` };
  }

  let data;
  try {
    data = await res.json();
  } catch (parseErr) {
    const rawText = await res.text().catch(() => "");
    console.error("api() non-JSON response:", path, res.status, rawText.slice(0, 300));
    return {
      ok: false,
      error: `${t("common.nonJsonResponse")} (HTTP ${res.status}).`,
    };
  }

  if (!res.ok && data.ok === undefined) {
    data.ok = false;
  }
  return data;
}

document.getElementById("add-channel-btn").addEventListener("click", () => {
  if (!botUsername) {
    tg.showAlert(t("channels.dataStillLoading"));
    return;
  }
  const rights = [
    "change_info", "post_messages", "edit_messages", "delete_messages",
    "invite_users", "restrict_members", "pin_messages", "promote_members",
    "manage_chat", "manage_video_chats", "anonymous",
  ].join("+");
  const link = `https://t.me/${botUsername}?startchannel&admin=${rights}`;
  tg.openTelegramLink(link);
});

function switchTab(tab) {
  document.querySelectorAll(".tab-screen").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach((el) => el.classList.remove("active"));
  document.getElementById(`tab-${tab}`).classList.add("active");
  const navBtn = document.querySelector(`.nav-btn[data-tab="${tab}"]`);
  (navBtn || document.querySelector('.nav-btn[data-tab="profile"]')).classList.add("active");

  if (tab === "channels") loadChannels();
  if (tab === "sources") { loadSources(); loadRecommendedSources(); }
  if (tab === "editorial") loadEditorialSegment();
  if (tab === "profile") loadSettings();
  if (tab === "dev") loadDevTab();
}

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ---------- Канали ----------

async function loadChannelStyleStats(channelId) {
  const el = document.getElementById(`style-stats-${channelId}`);
  if (!el) return;
  const style = await api(`/api/channels/style/${channelId}`);
  if (style.error || !style.stats || style.stats.sample_count === 0) {
    el.textContent = t("channelStyle.noData");
    return;
  }
  const s = style.stats;
  el.innerHTML = `${t("channelStyle.analyzed")}: ${s.sample_count}` +
    (s.top_emoji ? ` · ${t("channelStyle.topEmoji")}: ${escapeHtml(s.top_emoji)}` : "") +
    ` · ${t("channelStyle.boldStart")}: ${s.bold_start_pct}% · ${t("channelStyle.withLink")}: ${s.link_pct}%`;
}

let channelsCache = [];
let currentChannelFolderFilter = "all";

// Заздалегідь підготовлені теги категорій (п.1.3/2.2 ТЗ — жодного ручного вводу тексту)
const PRESET_CATEGORIES = [
  "Новини", "Новини про війну", "Місцеві новини", "Тривоги",
  "Політика", "Економіка", "Спорт", "Розваги", "Погода",
];

// Універсальний пікер категорій: показує вже створені папки + готові теги, які
// ще не додано. Клік по будь-якому тегу — єдиний спосіб обрати/створити категорію.
async function openCategoryPicker(onSelect) {
  const modal = document.getElementById("category-picker-modal");
  const body = document.getElementById("category-picker-body");
  const folders = await api("/api/channels/folders");
  const existing = Array.isArray(folders) ? folders : [];
  const suggested = PRESET_CATEGORIES.filter((c) => !existing.includes(c));

  function renderSection(title, items) {
    if (!items.length) return "";
    return `
      <div class="section-label" style="margin-top:14px;">${title}</div>
      <div class="chip-grid">
        ${items.map((c) => `<div class="chip-compact" data-cat="${escapeHtml(c)}"><span>📁 ${escapeHtml(c)}</span></div>`).join("")}
      </div>`;
  }

  body.innerHTML = `
    <div class="muted" style="font-size:13px;margin-bottom:4px;">${t("categoryPicker.hint")}</div>
    ${renderSection(t("categoryPicker.yourCategories"), existing)}
    ${renderSection(t("categoryPicker.presetTags"), suggested)}
  `;

  body.querySelectorAll("[data-cat]").forEach((chip) => {
    chip.onclick = () => {
      modal.style.display = "none";
      onSelect(chip.dataset.cat);
    };
  });

  modal.style.display = "flex";
}
document.getElementById("category-picker-close-btn").addEventListener("click", () => {
  document.getElementById("category-picker-modal").style.display = "none";
});

async function loadChannels() {
  const list = document.getElementById("channels-list");
  const channels = await api("/api/channels");

  if (channels.error) {
    list.innerHTML = `<div class="card-row muted">${t("common.noAccess")}</div>`;
    return;
  }

  channelsCache = channels;

  const folders = await api("/api/channels/folders");
  const knownFolders = Array.isArray(folders) ? folders : [];

  const groups = {};
  for (const ch of channels) {
    const cat = (ch.category || "").trim() || t("channels.noCategory");
    (groups[cat] = groups[cat] || []).push(ch);
  }
  for (const f of knownFolders) if (!groups[f]) groups[f] = []; // порожні папки теж показуємо як таб

  const sortedCats = Object.keys(groups).filter((c) => c !== t("channels.noCategory")).sort((a, b) => a.localeCompare(b, "uk"));
  if (groups[t("channels.noCategory")]) sortedCats.push(t("channels.noCategory"));

  // ---------- Таби папок ----------
  const tabsEl = document.getElementById("channels-folder-tabs");
  tabsEl.innerHTML = `<button class="segment ${currentChannelFolderFilter === "all" ? "active" : ""}" data-folder="all">${t("sources.filterAll")} (${channels.length})</button>`;
  for (const cat of sortedCats) {
    const wrap = document.createElement("div");
    wrap.className = "segment-wrap";

    const btn = document.createElement("button");
    btn.className = "segment" + (currentChannelFolderFilter === cat ? " active" : "");
    btn.dataset.folder = cat;
    btn.textContent = `${cat} (${groups[cat].length})`;
    wrap.appendChild(btn);

    // "Без категорії" — не справжня папка (нема що видаляти), хрестик тільки на
    // реальних категоріях, створених через "+ Додати категорію".
    if (cat !== t("channels.noCategory")) {
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "segment-delete-x";
      delBtn.setAttribute("aria-label", `${t("categoryPicker.deleteCategoryAria")} ${cat}`);
      delBtn.innerHTML = '<svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M18 6 6 18M6 6l12 12"/></svg>';
      delBtn.onclick = (e) => {
        e.stopPropagation();
        tg.showConfirm(`${t("categoryPicker.deleteConfirm")} «${cat}»? ${t("categoryPicker.deleteConfirmSuffix")}`, (confirmed) => {
          if (!confirmed) return;
          api("/api/channels/folders/remove", { method: "POST", body: JSON.stringify({ name: cat }) }).then((r) => {
            if (r.ok) {
              if (currentChannelFolderFilter === cat) currentChannelFolderFilter = "all";
              loadChannels();
            } else {
              tg.showAlert(r.error || t("categoryPicker.deleteFailed"));
            }
          });
        });
      };
      wrap.appendChild(delBtn);

      // Тач-пристрої: довге натискання (500мс) показує хрестик, оскільки :hover
      // з CSS (для десктопа) на мобільному не спрацьовує.
      let pressTimer = null;
      const cancelPress = () => { if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; } };
      btn.addEventListener("touchstart", () => {
        cancelPress();
        pressTimer = setTimeout(() => {
          document.querySelectorAll(".segment-wrap.show-delete").forEach((w) => w.classList.remove("show-delete"));
          wrap.classList.add("show-delete");
        }, 500);
      }, { passive: true });
      btn.addEventListener("touchend", cancelPress);
      btn.addEventListener("touchmove", cancelPress);
    }

    tabsEl.appendChild(wrap);
  }
  const addBtn = document.createElement("button");
  addBtn.className = "segment add-folder";
  addBtn.textContent = "+ " + t("categoryPicker.addCategoryBtn");
  addBtn.onclick = () => {
    openCategoryPicker((name) => {
      api("/api/channels/folders/add", { method: "POST", body: JSON.stringify({ name }) }).then((r) => {
        if (r.ok) { currentChannelFolderFilter = name; loadChannels(); }
        else tg.showAlert(r.error || t("categoryPicker.folderExists"));
      });
    });
  };
  tabsEl.appendChild(addBtn);
  tabsEl.querySelectorAll(".segment[data-folder]").forEach((btn) => {
    btn.onclick = () => { currentChannelFolderFilter = btn.dataset.folder; loadChannels(); };
  });

  // ---------- Плаский список (без акордеонів) ----------
  list.innerHTML = "";
  if (!channels.length) {
    list.innerHTML = `<div class="card-row muted">${t("channels.empty")}</div>`;
    return;
  }

  const flatContainer = document.createElement("div");
  flatContainer.className = "card-list";

  const catsToRender = currentChannelFolderFilter === "all" ? sortedCats : [currentChannelFolderFilter];
  for (const cat of catsToRender) {
    const chList = groups[cat] || [];
    if (!chList.length) continue;
    if (currentChannelFolderFilter === "all") {
      const label = document.createElement("div");
      label.className = "channel-group-label";
      label.textContent = `${cat} · ${chList.length}`;
      flatContainer.appendChild(label);
    }
    for (const ch of chList) flatContainer.appendChild(renderChannelCard(ch));
  }
  list.appendChild(flatContainer);
}

// Клік поза пілюлею категорії ховає її хрестик видалення (єдиний обробник на
// весь документ — реєструється раз, а не всередині loadChannels(), інакше при
// кожному оновленні списку накопичувався б ще один слухач).
document.addEventListener("click", (e) => {
  if (!e.target.closest(".segment-wrap")) {
    document.querySelectorAll(".segment-wrap.show-delete").forEach((w) => w.classList.remove("show-delete"));
  }
});

function renderChannelCard(ch) {
  const wrap = document.createElement("div");
  wrap.className = "swipe-wrap";

  const bg = document.createElement("div");
  bg.className = "swipe-delete-bg";
  bg.innerHTML = ICONS.trash;

  const row = document.createElement("div");
  row.className = "channel-card swipe-content";

  const inactiveBadge = ch.status === "inactive"
    ? `<span class="badge-inactive">${ICONS.warning} ${t("channels.botRemoved")}</span>`
    : "";
  const subsCount = ch.subscribers != null ? ch.subscribers : "—";
  const subsIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>';

  row.innerHTML = `
    <div class="submission-summary">
      <div class="channel-avatar" data-role="avatar">${ICONS.channelDefault}</div>
      <div class="submission-summary-body">
        <div class="submission-title">${escapeHtml(ch.title)} ${inactiveBadge}</div>
        <div class="channel-subs-meta">${subsIcon}${subsCount} ${t("channels.subscribers")}</div>
      </div>
      <svg class="icon submission-chevron" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>
    </div>
  `;

  loadAvatarInto(row.querySelector('[data-role="avatar"]'), ch.id, ch.title);
  row.querySelector(".submission-summary").addEventListener("click", () => openChannelModal(ch.id));

  wrap.appendChild(bg);
  wrap.appendChild(row);

  // Свайп вліво видаляє канал (бот виходить з нього) — той самий жест, що й у
  // черзі публікацій; без окремого підтвердження, послідовно з рештою застосунку.
  // Довге утримання + перетягування нагору, на таб потрібної категорії — переносить
  // канал у неї, як перетягування іконки застосунку в папку на телефоні.
  attachSwipeToDelete(wrap, row, bg, async () => {
    const r = await api("/api/channels/remove", { method: "POST", body: JSON.stringify({ id: ch.id }) });
    if (!r.ok) tg.showAlert(`${t("common.error")}: ${r.error || t("channels.deleteFailed")}`);
  }, {
    onDragStart: () => {
      document.getElementById("channels-folder-tabs").classList.add("drop-armed");
      if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred("light");
      _startCategoryDragAutoScroll();
    },
    onDragMove: (x, y) => {
      document.querySelectorAll("#channels-folder-tabs .segment.drop-target-active")
        .forEach((t) => t.classList.remove("drop-target-active"));
      const tab = _findFolderTabAt(x, y);
      if (tab) tab.classList.add("drop-target-active");
      _categoryDragPointerY = y;
    },
    onDrop: (x, y) => {
      _stopCategoryDragAutoScroll();
      document.getElementById("channels-folder-tabs").classList.remove("drop-armed");
      document.querySelectorAll("#channels-folder-tabs .segment.drop-target-active")
        .forEach((t) => t.classList.remove("drop-target-active"));
      const tab = _findFolderTabAt(x, y);
      if (!tab) return false;
      const category = tab.dataset.folder === t("channels.noCategory") ? "" : tab.dataset.folder;
      if ((ch.category || "").trim() === category) return true;  // вже там — нічого не робимо
      api("/api/channels/category", { method: "POST", body: JSON.stringify({ id: ch.id, category }) }).then((r) => {
        if (r && r.ok) { ch.category = category; loadChannels(); }
        else tg.showAlert((r && r.error) || t("channels.moveFailed"));
      });
      if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
      return true;
    },
  });

  return wrap;
}

// Хіттест drop-зони для перетягування картки каналу в категорію: шукає таб
// категорії під координатами пальця/курсора (крім "Всі" та кнопки "+ Додати категорію").
function _findFolderTabAt(clientX, clientY) {
  const el = document.elementFromPoint(clientX, clientY);
  const tab = el && el.closest && el.closest("#channels-folder-tabs .segment[data-folder]");
  if (!tab || tab.dataset.folder === "all" || tab.classList.contains("add-folder")) return null;
  return tab;
}

// Автоскрол сторінки вгору під час перетягування картки каналу — таби категорій
// завжди вгорі списку, а список часто довший за екран (див. скрін з 6+ каналами),
// тож без автоскролу перенести канал у категорію, гортаючи його з середини/низу
// списку, було б фізично неможливо одним жестом.
let _categoryDragPointerY = null;
let _categoryDragRaf = null;
const _CATEGORY_DRAG_EDGE_PX = 90;

function _categoryDragScrollTick() {
  if (_categoryDragPointerY !== null && _categoryDragPointerY < _CATEGORY_DRAG_EDGE_PX) {
    const speed = Math.max(4, (_CATEGORY_DRAG_EDGE_PX - _categoryDragPointerY) / 3);
    window.scrollBy(0, -speed);
  }
  _categoryDragRaf = requestAnimationFrame(_categoryDragScrollTick);
}

function _startCategoryDragAutoScroll() {
  _categoryDragPointerY = null;
  if (_categoryDragRaf === null) _categoryDragRaf = requestAnimationFrame(_categoryDragScrollTick);
}

function _stopCategoryDragAutoScroll() {
  if (_categoryDragRaf !== null) cancelAnimationFrame(_categoryDragRaf);
  _categoryDragRaf = null;
  _categoryDragPointerY = null;
}

document.getElementById("channels-hint-btn").addEventListener("click", () => {
  document.getElementById("channels-hint-sheet").style.display = "flex";
});
document.getElementById("channels-hint-sheet").addEventListener("click", (e) => {
  if (e.target.id === "channels-hint-sheet") e.target.style.display = "none";
});

// Детальні права учасника команди в самому Telegram-каналі — той самий список
// перемикачів, що й у нативному екрані Telegram "Возможности администратора",
// щоб власнику не довелось перевчатись (він сам показав нам цей скрін як зразок).
async function openMemberPermissionsModal(channelId, userId, displayName) {
  const overlay = document.getElementById("member-permissions-modal");
  const body = document.getElementById("member-permissions-body");
  body.innerHTML = `<div class="muted" style="padding:20px 0;text-align:center;">${t("common.loading")}</div>`;
  overlay.style.display = "flex";

  const res = await api(`/api/channels/team/permissions?channel_id=${channelId}&user_id=${userId}`);
  if (!res || !res.ok) {
    body.innerHTML = `<div class="muted" style="padding:20px 0;text-align:center;">${t("memberPerms.loadFailed")}</div>`;
    return;
  }

  const rows = res.labels.map((p) => `
    <label class="watermark-toggle" style="margin-bottom:10px;">
      <span class="watermark-switch ${p.value ? "on" : ""}" data-perm="${p.key}"></span>
      <span>${escapeHtml(p.label)}</span>
    </label>
  `).join("");

  body.innerHTML = `
    <div class="channel-title" style="margin-bottom:6px;">
      <div class="channel-avatar" data-role="perm-avatar"></div>
      <span>${escapeHtml(displayName)}</span>
    </div>
    ${res.live ? "" : `<div class="muted" style="margin-bottom:14px;font-size:12.5px;line-height:1.4;">${t("memberPerms.notYetAdminHint")}</div>`}
    <div style="margin-top:${res.live ? "14" : "0"}px;">${rows}</div>
    <label class="watermark-toggle disabled" style="margin-bottom:4px;opacity:.5;pointer-events:none;">
      <span class="watermark-switch"></span>
      <span>${t("memberPerms.addAdmins")}</span>
    </label>
    <div class="muted" style="font-size:11.5px;margin:-6px 0 16px 52px;line-height:1.4;">${t("memberPerms.addAdminsLocked")}</div>
    <button class="pill on" data-action="save-permissions" style="width:100%;justify-content:center;">${ICONS.check} ${t("common.save")}</button>
    <div class="muted" data-role="perm-status" style="font-size:12px;margin-top:8px;text-align:center;min-height:16px;"></div>
  `;
  loadAvatarFromUrlInto(body.querySelector('[data-role="perm-avatar"]'), `/api/user-avatar/${userId}`, displayName);

  body.querySelectorAll(".watermark-switch[data-perm]").forEach((sw) => {
    sw.onclick = () => sw.classList.toggle("on");
  });

  body.querySelector('[data-action="save-permissions"]').onclick = async () => {
    const statusEl = body.querySelector('[data-role="perm-status"]');
    const permissions = {};
    body.querySelectorAll(".watermark-switch[data-perm]").forEach((sw) => {
      permissions[sw.dataset.perm] = sw.classList.contains("on");
    });
    statusEl.textContent = t("common.saving");
    const r = await api("/api/channels/team/permissions", {
      method: "POST",
      body: JSON.stringify({ channel_id: channelId, user_id: userId, permissions }),
    });
    statusEl.textContent = r && r.ok ? t("common.success") : `${t("common.error")}: ${(r && r.error) || t("common.saveFailedGeneric")}`;
  };
}

document.getElementById("member-permissions-close-btn").addEventListener("click", () => {
  document.getElementById("member-permissions-modal").style.display = "none";
});

function openChannelModal(channelId) {
  const ch = channelsCache.find((c) => c.id === channelId);
  if (!ch) return;

  const body = document.getElementById("channel-modal-body");
  const newsOn = !!ch.news_enabled;
  // Тривоги/Команда — тільки Owner (require_role(..., "owner") на бекенді для цих
  // ендпоінтів); Медіа (водяний знак) і кнопка "Тест" — Owner або Editor. Роль
  // приходить з /api/channels (ch.role), який тепер віддає її для КОЖНОГО каналу
  // окремо (той самий адмін може бути власником одного каналу й редактором іншого).
  const isOwner = ch.role === "owner";
  const canEdit = ch.role === "owner" || ch.role === "editor";

  body.innerHTML = `
    <div class="modal-hero">
      <div class="modal-hero-avatar" data-role="modal-avatar">${ICONS.channelDefault}</div>
      <div class="modal-hero-info">
        <div class="modal-hero-title">${escapeHtml(ch.title)}</div>
        <div class="modal-hero-meta">
          <span class="modal-hero-dot" data-role="hero-status-dot"></span>
          <span data-role="modal-subscribers">${t("channelModal.subscribersLabel")}: —</span>
        </div>
      </div>
    </div>

    <div class="modal-tab-bar" data-role="modal-tabs">
      <button class="modal-tab-btn active" data-tab="main">${ICONS.home} ${t("channelModal.tabMain")}</button>
      ${isOwner ? `<button class="modal-tab-btn" data-tab="alerts">${ICONS.bell} ${t("channelModal.tabAlerts")}</button>` : ""}
      ${canEdit ? `<button class="modal-tab-btn" data-tab="media">${ICONS.droplet} ${t("channelModal.tabMedia")}</button>` : ""}
      ${isOwner ? `<button class="modal-tab-btn" data-tab="team">${ICONS.team} ${t("channelModal.tabTeam")}</button>` : ""}
    </div>

    <div class="modal-tab-panel active" data-panel="main">
      ${isOwner ? `
      <div class="settings-card">
        <div class="settings-card-header">
          <div class="settings-card-icon"><svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div>
          <div class="settings-card-body">
            <div class="settings-card-title">${t("channelModal.automationTitle")}</div>
            <div class="settings-card-desc">${t("channelModal.automationDesc")}</div>
          </div>
        </div>
        <div class="settings-card-extra">
          <label class="watermark-toggle" style="margin-bottom:12px;">
            <span class="watermark-switch" data-role="auto-approve-switch"></span>
            <span>${t("channelModal.autoApproveLabel")}</span>
          </label>
          <div class="muted" style="font-size:11.5px;margin:-8px 0 12px 52px;line-height:1.4;">${t("channelModal.autoApproveHint")}</div>

          <label class="watermark-toggle" style="margin-bottom:4px;">
            <span class="watermark-switch" data-role="autopost-enabled-switch"></span>
            <span>${t("channelModal.autopostLabel")}</span>
          </label>

          <div data-role="autopost-cd-block" style="margin-top:12px;">
            <div class="stepper" style="justify-content:center;">
              <button class="stepper-btn" type="button" data-role="cd-minus">−</button>
              <span class="stepper-value" data-role="cd-value">— ${t("common.minutesShort")}</span>
              <button class="stepper-btn" type="button" data-role="cd-plus">+</button>
            </div>
            <div class="muted" style="font-size:11px;text-align:center;margin-top:4px;">${t("channelModal.cdHint")}</div>
          </div>

          <div class="muted" style="font-size:12px;margin-top:12px;padding-top:12px;border-top:1px solid var(--card-border);">
            ${t("channelModal.queuePendingLabel")}: <b data-role="queue-pending-value">—</b>
          </div>
        </div>
      </div>` : ""}

      ${(isOwner || canEdit) ? `
      <div class="settings-card" style="margin-top:14px;">
        <div class="settings-card-header">
          <div class="settings-card-icon">${ICONS.newspaper}</div>
          <div class="settings-card-body">
            <div class="settings-card-title">${t("channelModal.publishTitle")}</div>
            <div class="settings-card-desc">${t("channelModal.publishDescBase")}${canEdit ? t("channelModal.publishDescExtra") : ""}</div>
          </div>
          ${isOwner ? `<label class="watermark-toggle" style="margin:0;">
            <span class="watermark-switch ${newsOn ? "on" : ""}" data-role="news-toggle-switch"></span>
          </label>` : ""}
        </div>
        ${canEdit ? `
        <div class="settings-card-extra">
          <button class="pill" data-action="test" style="width:100%;justify-content:center;">${ICONS.test} ${t("channelModal.sendTestNewsBtn")}</button>
          ${ch.submit_link ? `<button class="pill" data-action="copy-link" style="width:100%;justify-content:center;margin-top:8px;"><svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg> ${t("channelModal.copyLinkBtn")}</button>` : ""}
        </div>` : ""}
      </div>` : ""}
      ${isOwner ? `
      <div class="settings-card" style="margin-top:14px;">
        <div class="settings-card-header">
          <div class="settings-card-icon">${ICONS.bell}</div>
          <div class="settings-card-body">
            <div class="settings-card-title">${t("channelModal.alertMonitorTitle")}</div>
            <div class="settings-card-desc">${t("channelModal.alertMonitorDesc")}</div>
          </div>
          <label class="watermark-toggle" style="margin:0;">
            <span class="watermark-switch" data-role="alerts-quick-toggle"></span>
          </label>
        </div>
      </div>` : ""}
    </div>

    <div class="modal-tab-panel" data-panel="alerts">
      <div data-role="alerts-config-block">
        <div class="settings-card">
          <div class="settings-card-header clickable" data-role="oblast-summary-btn" role="button" tabindex="0">
            <div class="settings-card-icon">${ICONS.location}</div>
            <div class="settings-card-body">
              <div class="settings-card-title" data-role="oblast-summary-text">${t("channelModal.oblastsNone")}</div>
              <div class="settings-card-desc">${t("channelModal.oblastsDesc")}</div>
            </div>
            <span class="oblast-summary-chevron" data-role="oblast-chevron">${ICONS.chevronRight}</span>
          </div>
          <div data-role="alerts-oblast-panel" class="settings-card-extra collapsed">
            <input type="text" placeholder="${t("channelModal.oblastSearchPlaceholder")}" data-role="oblast-search" style="margin-bottom:8px;" />
            <div class="chip-actions-row">
              <button type="button" class="chip-action-btn" data-role="alerts-select-all">${t("channelModal.selectAll")}</button>
              <button type="button" class="chip-action-btn" data-role="alerts-deselect-all">${t("channelModal.deselectAll")}</button>
            </div>
            <div class="chip-grid" data-role="alerts-oblast-list"></div>
          </div>
        </div>

        <div class="settings-card">
          <div class="settings-card-header">
            <div class="settings-card-icon">${ICONS.bell}</div>
            <div class="settings-card-body">
              <div class="settings-card-title">${t("channelModal.sirenTitle")}</div>
              <div class="settings-card-desc">${t("channelModal.sirenDesc")}</div>
            </div>
            <span class="watermark-switch" data-role="notify-siren-switch"></span>
          </div>
        </div>

        <div class="settings-card">
          <div class="settings-card-header">
            <div class="settings-card-icon">${ICONS.target}</div>
            <div class="settings-card-body">
              <div class="settings-card-title">${t("channelModal.targetsTitle")}</div>
              <div class="settings-card-desc">${t("channelModal.targetsDesc")}</div>
            </div>
            <span class="watermark-switch" data-role="notify-threats-switch"></span>
          </div>
          <div data-role="alerts-types-block" class="settings-card-extra">
            <div class="chip-grid" data-role="alerts-type-list"></div>
            <label class="watermark-toggle" style="margin-top:12px;">
              <span class="watermark-switch" data-role="show-threat-map-switch"></span>
              <span>${t("channelModal.showMapLabel")}</span>
            </label>
            <div class="muted" style="font-size:11.5px;margin:-4px 0 0 52px;line-height:1.4;">${t("channelModal.showMapHint")}</div>
          </div>
        </div>

        <div class="pill-row">
          <button class="pill" data-action="test-alert">${ICONS.test} ${t("channelModal.testAlertBtn")}</button>
        </div>
        <div class="muted" data-role="alerts-save-status" style="font-size:12px;margin-top:6px;min-height:16px;"></div>
      </div>
    </div>

    <div class="modal-tab-panel" data-panel="media">
      <div class="settings-card">
        <div class="settings-card-header">
          <div class="settings-card-icon">${ICONS.droplet}</div>
          <div class="settings-card-body">
            <div class="settings-card-title">${t("channelModal.watermarkTitle")}</div>
            <div class="settings-card-desc">${t("channelModal.watermarkDesc")}</div>
          </div>
        </div>
        <div class="settings-card-extra">
          <div id="wm-preview-wrap" style="margin-bottom:10px;min-height:1px;">${t("common.loading")}</div>
          <label class="file-upload-btn">
            📁 ${t("channelModal.uploadLogoBtn")}
            <input type="file" accept="image/*" data-role="watermark-file" style="display:none;" />
          </label>
          <div class="muted" data-role="watermark-filename" style="margin:6px 0;font-size:12.5px;"></div>
          <div class="pill-row" style="margin-bottom:0;">
            <button class="pill" data-action="watermark-upload">${ICONS.save} ${t("channelModal.saveWatermarkBtn")}</button>
            <button class="pill danger" data-action="watermark-remove">${ICONS.trash} ${t("channelModal.removeWatermarkBtn")}</button>
          </div>
        </div>
      </div>

      <div class="settings-card">
        <div class="settings-card-header">
          <div class="settings-card-icon">${ICONS.image}</div>
          <div class="settings-card-body">
            <div class="settings-card-title">${t("channelModal.livePreviewTitle")}</div>
            <div class="settings-card-desc">${t("channelModal.livePreviewDesc")}</div>
          </div>
        </div>
        <div class="settings-card-extra">
          <div class="wm-live-preview-wrap">
            <canvas data-role="wm-live-canvas" width="320" height="240"></canvas>
          </div>

          <div class="section-label" style="margin-top:16px;font-size:12px;">${t("channelModal.opacityLabel")}: <span data-role="wm-opacity-value">50%</span></div>
          <input type="range" min="10" max="100" value="50" data-role="wm-opacity-slider" style="width:100%;" />

          <div class="section-label" style="margin-top:14px;font-size:12px;">${t("channelModal.sizeLabel")}: <span data-role="wm-scale-value">40%</span> ${t("channelModal.sizeLabelSuffix")}</div>
          <input type="range" min="10" max="50" value="40" data-role="wm-scale-slider" style="width:100%;" />

          <div class="section-label" style="margin-top:14px;font-size:12px;">${t("channelModal.positionsLabel")}</div>
          <div class="position-grid" data-role="wm-position-grid"></div>

          <button class="pill" data-action="save-watermark-settings" style="margin-top:10px;">${ICONS.save} ${t("channelModal.saveWmSettingsBtn")}</button>
        </div>
      </div>
    </div>

    ${isOwner ? `
    <div class="modal-tab-panel" data-panel="team">
      <div class="settings-card">
        <div class="settings-card-header">
          <div class="settings-card-icon">${ICONS.team}</div>
          <div class="settings-card-body">
            <div class="settings-card-title">${t("channelModal.teamAddTitle")}</div>
            <div class="settings-card-desc">${t("channelModal.teamAddDesc")}</div>
          </div>
        </div>
        <div class="settings-card-extra">
          <input type="text" placeholder="user_id ${t("common.or")} @username" data-role="team-add-userid" style="width:100%;margin-bottom:10px;" />
          <div class="channel-title" data-role="team-add-preview" style="display:none;margin:-2px 0 10px;">
            <div class="channel-avatar" data-role="preview-avatar" style="width:36px;height:36px;min-width:36px;min-height:36px;"></div>
            <div style="min-width:0;">
              <div data-role="preview-name" style="font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></div>
              <div class="muted" data-role="preview-username" style="font-size:12px;"></div>
            </div>
          </div>
          <div class="segmented" data-role="team-add-role-segmented" style="margin-bottom:10px;">
            <button type="button" class="segment active" data-role="editor">${t("channelModal.roleEditor")}</button>
            <button type="button" class="segment" data-role="moderator">${t("channelModal.roleModerator")}</button>
          </div>
          <button class="pill" data-action="team-add" style="width:100%;justify-content:center;">${ICONS.check || ""} ${t("common.add")}</button>
          <div class="muted" data-role="team-add-status" style="font-size:12px;margin-top:6px;min-height:16px;"></div>
        </div>
      </div>
      <div class="section-label" style="margin-top:16px;">${t("channelModal.teamMembersTitle")}</div>
      <div id="team-members-list" data-role="team-members-list"></div>

      <div class="section-label" style="margin-top:16px;">${t("channelModal.statsTitle")}</div>
      <div class="muted" style="font-size:11.5px;margin:-8px 0 10px;line-height:1.4;">${t("channelModal.statsHint")}</div>
      <div data-role="team-stats-list"></div>
    </div>` : ""}
  `;

  // ---------- Ledacтe завантаження вкладок (план оптимізації, п.2) ----------
  // Дані для «Тривоги» й «Медіа» тепер підвантажуються лише при першому переході
  // на відповідну вкладку, а не одразу при відкритті модалки — так відкриття
  // картки каналу не тягне за собою одразу 4 зайвих мережевих запити, коли
  // адмін просто дивиться «Головна» і закриває вікно.
  let alertsTabLoaded = false;
  let mediaTabLoaded = false;
  let teamTabLoaded = false;

  body.querySelectorAll(".modal-tab-btn").forEach((btn) => {
    btn.onclick = () => {
      body.querySelectorAll(".modal-tab-btn").forEach((b) => b.classList.remove("active"));
      body.querySelectorAll(".modal-tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      body.querySelector(`[data-panel="${btn.dataset.tab}"]`).classList.add("active");
      if (btn.dataset.tab === "alerts" && !alertsTabLoaded) { alertsTabLoaded = true; initAlertsTab(); }
      if (btn.dataset.tab === "media" && !mediaTabLoaded) { mediaTabLoaded = true; initMediaTabData(); }
      if (btn.dataset.tab === "team" && !teamTabLoaded) { teamTabLoaded = true; initTeamTab(); }
    };
  });

  function initTeamTab() {
    const userIdInput = body.querySelector('[data-role="team-add-userid"]');
    const roleSegmented = body.querySelector('[data-role="team-add-role-segmented"]');
    const addStatus = body.querySelector('[data-role="team-add-status"]');
    let selectedRole = "editor";

    // Прев'ю особи ПЕРЕД додаванням (щоб не додавати наосліп) — приймає або
    // голий user_id, або @username. Дебаунс 500мс, щоб не смикати lookup на
    // кожен надрукований символ. Резолвлений id кешується в dataset, щоб
    // кнопка "Додати" не робила зайвий запит, якщо прев'ю вже все знайшло.
    const previewBox = body.querySelector('[data-role="team-add-preview"]');
    const previewAvatar = body.querySelector('[data-role="preview-avatar"]');
    const previewName = body.querySelector('[data-role="preview-name"]');
    const previewUsername = body.querySelector('[data-role="preview-username"]');
    let previewDebounce = null;

    async function lookupInput(raw) {
      if (/^\d+$/.test(raw)) {
        const r = await api(`/api/user-lookup/${raw}`);
        return r && r.ok ? { user_id: parseInt(raw, 10), first_name: r.first_name, last_name: r.last_name, username: r.username } : null;
      }
      const uname = raw.replace(/^@/, "");
      if (!uname) return null;
      const r = await api(`/api/user-lookup-by-username/${encodeURIComponent(uname)}`);
      return r && r.ok ? r : null;
    }

    userIdInput.addEventListener("input", () => {
      clearTimeout(previewDebounce);
      delete userIdInput.dataset.resolvedId;
      const raw = userIdInput.value.trim();
      if (!raw) {
        previewBox.style.display = "none";
        return;
      }
      previewDebounce = setTimeout(async () => {
        const info = await lookupInput(raw);
        if (userIdInput.value.trim() !== raw) return; // відповідь застаріла — юзер уже набрав щось інше
        if (!info) {
          previewBox.style.display = "none";
          return;
        }
        const fullName = [info.first_name, info.last_name].filter(Boolean).join(" ") || `ID ${info.user_id}`;
        previewName.textContent = fullName;
        previewUsername.textContent = info.username ? `@${info.username}` : "";
        previewAvatar.innerHTML = "";
        loadAvatarFromUrlInto(previewAvatar, `/api/user-avatar/${info.user_id}`, fullName);
        previewBox.style.display = "flex";
        userIdInput.dataset.resolvedId = info.user_id;
        userIdInput.dataset.resolvedRaw = raw;
      }, 500);
    });

    roleSegmented.querySelectorAll(".segment").forEach((seg) => {
      seg.onclick = () => {
        roleSegmented.querySelectorAll(".segment").forEach((s) => s.classList.remove("active"));
        seg.classList.add("active");
        selectedRole = seg.dataset.role;
      };
    });

    body.querySelector('[data-action="team-add"]').onclick = async () => {
      const raw = userIdInput.value.trim();
      let userId = null;
      if (userIdInput.dataset.resolvedId && userIdInput.dataset.resolvedRaw === raw) {
        userId = parseInt(userIdInput.dataset.resolvedId, 10);
      } else {
        const info = await lookupInput(raw);
        userId = info ? info.user_id : null;
      }
      if (!userId) {
        addStatus.textContent = /^\d+$/.test(raw) ? t("channelModal.invalidUserId") : t("channelModal.usernameNotFound");
        return;
      }
      addStatus.textContent = t("channelModal.addingMember");
      const r = await api("/api/channels/team/add", {
        method: "POST",
        body: JSON.stringify({ channel_id: ch.id, user_id: userId, role: selectedRole }),
      });
      if (r && r.ok) {
        userIdInput.value = "";
        delete userIdInput.dataset.resolvedId;
        previewBox.style.display = "none";
        addStatus.textContent = r.tg_warning
          ? t("channelModal.addedWithTgWarning")
          : "";
        loadTeamList();
      } else {
        addStatus.textContent = (r && r.error) || t("channelModal.addMemberFailed");
      }
    };

    loadTeamList();
    loadTeamStats();
  }

  async function loadTeamStats() {
    const box = body.querySelector('[data-role="team-stats-list"]');
    if (!box) return;
    const res = await api(`/api/channels/team/stats?id=${ch.id}`);
    if (!res || !res.ok || !res.stats.length) {
      box.innerHTML = `<div class="muted" style="font-size:13px;">${t("channelModal.statsEmpty")}</div>`;
      return;
    }
    box.innerHTML = res.stats.map((s) => {
      const displayName = s.name && !s.name.startsWith("ID ") ? escapeHtml(s.name) + (s.username ? ` <span class="muted">@${escapeHtml(s.username)}</span>` : "") : `ID ${s.admin_id}`;
      const reaction = s.avg_reaction_minutes != null
        ? (s.avg_reaction_minutes < 60 ? `${s.avg_reaction_minutes} ${t("common.minutesShort")}` : `${(s.avg_reaction_minutes / 60).toFixed(1)} ${t("channelModal.hoursShort")}`)
        : "—";
      return `
      <div class="card-row" style="align-items:flex-start;flex-direction:column;gap:4px;margin-top:8px;">
        <div style="font-weight:600;">${displayName}</div>
        <div class="muted" style="font-size:12.5px;">
          ${t("channelModal.statsQueueApproved")}: <b>${s.queue_approved}</b> ·
          ${t("channelModal.statsSubmissionsApproved")}: <b>${s.submissions_approved}</b> ·
          ${t("channelModal.statsSubmissionsRejected")}: <b>${s.submissions_rejected}</b> ·
          ${t("channelModal.statsAvgReaction")}: <b>${reaction}</b>
        </div>
      </div>`;
    }).join("");
  }

  async function loadTeamList() {
    const list = body.querySelector('[data-role="team-members-list"]');
    const res = await api(`/api/channels/team?id=${ch.id}`);
    if (!res || !res.ok) {
      list.innerHTML = `<div class="muted" style="font-size:13px;">${t("channelModal.teamLoadFailed")}</div>`;
      return;
    }
    if (!res.members.length) {
      list.innerHTML = `<div class="muted" style="font-size:13px;">${t("channelModal.teamEmpty")}</div>`;
      return;
    }
    list.innerHTML = res.members.map((m) => {
      const p = m.profile;
      const displayName = p && p.first_name ? escapeHtml(p.first_name) + (p.username ? ` <span class="muted">@${escapeHtml(p.username)}</span>` : "") : `ID ${m.user_id}`;
      const roleBadge = m.role === "editor"
        ? `<span class="role-badge editor">${t("channelModal.roleEditor")}</span>`
        : `<span class="role-badge moderator">${t("channelModal.roleModerator")}</span>`;
      return `
      <div class="settings-card" data-user-id="${m.user_id}" style="margin-top:8px;">
        <div class="settings-card-header clickable" data-action="open-permissions" role="button" tabindex="0">
          <div class="channel-avatar" data-role="avatar" style="width:36px;height:36px;min-width:36px;min-height:36px;font-size:13px;font-weight:700;"></div>
          <div class="settings-card-body">
            <div class="settings-card-title" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">${displayName} ${roleBadge}</div>
            ${p && p.first_name ? `<div class="settings-card-desc">ID ${m.user_id}</div>` : ""}
          </div>
          <span class="oblast-summary-chevron">${ICONS.chevronRight}</span>
        </div>
        <div class="settings-card-extra">
          <div class="segmented" data-role="member-role-segmented" style="margin-bottom:10px;">
            <button type="button" class="segment ${m.role === "editor" ? "active" : ""}" data-role="editor">${t("channelModal.roleEditor")}</button>
            <button type="button" class="segment ${m.role === "moderator" ? "active" : ""}" data-role="moderator">${t("channelModal.roleModerator")}</button>
          </div>
          <button class="pill danger" data-action="member-remove" style="width:100%;justify-content:center;">${ICONS.trash} ${t("channelModal.removeMemberBtn")}</button>
        </div>
      </div>
    `;
    }).join("");

    list.querySelectorAll("[data-user-id]").forEach((row) => {
      const userId = parseInt(row.dataset.userId, 10);
      const member = res.members.find((mm) => mm.user_id === userId);
      const nameForFallback = (member && member.profile && member.profile.first_name) || `ID ${userId}`;
      loadAvatarFromUrlInto(row.querySelector('[data-role="avatar"]'), `/api/user-avatar/${userId}`, nameForFallback);
      row.querySelector('[data-action="open-permissions"]').addEventListener("click", () => {
        openMemberPermissionsModal(ch.id, userId, nameForFallback);
      });
      row.querySelectorAll('[data-role="member-role-segmented"] .segment').forEach((seg) => {
        seg.onclick = async () => {
          row.querySelectorAll('[data-role="member-role-segmented"] .segment').forEach((s) => s.classList.remove("active"));
          seg.classList.add("active");
          const badge = row.querySelector(".role-badge");
          if (badge) {
            const isEditor = seg.dataset.role === "editor";
            badge.className = `role-badge ${seg.dataset.role}`;
            badge.textContent = isEditor ? t("channelModal.roleEditor") : t("channelModal.roleModerator");
          }
          await api("/api/channels/team/update-role", {
            method: "POST",
            body: JSON.stringify({ channel_id: ch.id, user_id: userId, role: seg.dataset.role }),
          });
        };
      });
      row.querySelector('[data-action="member-remove"]').onclick = async () => {
        await api("/api/channels/team/remove", { method: "POST", body: JSON.stringify({ channel_id: ch.id, user_id: userId }) });
        loadTeamList();
      };
    });
  }

  api(`/api/channels/stats?id=${ch.id}`).then((stats) => {
    if (!stats || !stats.ok) return;
    const heroDot = body.querySelector('[data-role="hero-status-dot"]');
    if (heroDot) heroDot.className = "modal-hero-dot " + (stats.enabled ? "active" : "inactive");
  });
  body.querySelector('[data-role="modal-subscribers"]').textContent =
    `${t("channelModal.subscribersLabel")}: ${ch.subscribers != null ? ch.subscribers : "—"}`;

  // Автоматизація каналу — автосхвалення предложок, автопостинг з черги і його
  // персональний КД; раніше все це жило одним спільним перемикачем на ВСІ
  // канали адміна одразу в Тех.розділі, тепер — окремо для кожного каналу.
  // Усе нижче — тільки для Owner: DOM-вузлів просто немає в розмітці для
  // Editor/Moderator (див. умовний рендеринг вище), тож і код тут не запускаємо.
  let alertsEnabledCache = null;
  if (isOwner) {
    const autoApproveSwitch = body.querySelector('[data-role="auto-approve-switch"]');
    const autopostEnabledSwitch = body.querySelector('[data-role="autopost-enabled-switch"]');
    const autopostCdBlock = body.querySelector('[data-role="autopost-cd-block"]');
    const cdValueEl = body.querySelector('[data-role="cd-value"]');
    const cdMinusBtn = body.querySelector('[data-role="cd-minus"]');
    const cdPlusBtn = body.querySelector('[data-role="cd-plus"]');
    const queuePendingEl = body.querySelector('[data-role="queue-pending-value"]');
    let cdMinutes = 15;

    api(`/api/channels/automation?id=${ch.id}`).then((r) => {
      if (!r || !r.ok) return;
      autoApproveSwitch.classList.toggle("on", !!r.auto_approve);
      autoApproveSwitch.dataset.on = r.auto_approve ? "true" : "false";
      autopostEnabledSwitch.classList.toggle("on", !!r.autopost_enabled);
      autopostEnabledSwitch.dataset.on = r.autopost_enabled ? "true" : "false";
      autopostCdBlock.style.display = r.autopost_enabled ? "block" : "none";
      cdMinutes = r.cd_minutes;
      cdValueEl.textContent = `${cdMinutes} ${t("common.minutesShort")}`;
      queuePendingEl.textContent = r.queue_pending;
    });

    autoApproveSwitch.onclick = async () => {
      const on = autoApproveSwitch.dataset.on !== "true";
      autoApproveSwitch.classList.toggle("on", on);
      autoApproveSwitch.dataset.on = on ? "true" : "false";
      await api("/api/channels/automation", { method: "POST", body: JSON.stringify({ id: ch.id, auto_approve: on }) });
    };
    autopostEnabledSwitch.onclick = async () => {
      const on = autopostEnabledSwitch.dataset.on !== "true";
      autopostEnabledSwitch.classList.toggle("on", on);
      autopostEnabledSwitch.dataset.on = on ? "true" : "false";
      autopostCdBlock.style.display = on ? "block" : "none";
      await api("/api/channels/automation", { method: "POST", body: JSON.stringify({ id: ch.id, autopost_enabled: on }) });
    };
    const saveCd = async (newVal) => {
      newVal = Math.max(5, Math.min(180, newVal));
      cdValueEl.textContent = `${newVal} ${t("common.minutesShort")}`;
      const r = await api("/api/channels/automation", { method: "POST", body: JSON.stringify({ id: ch.id, cd_minutes: newVal }) });
      if (r && r.ok) cdMinutes = newVal;
    };
    cdMinusBtn.onclick = () => saveCd(cdMinutes - 5);
    cdPlusBtn.onclick = () => saveCd(cdMinutes + 5);

    // Швидкий тумблер моніторингу тривог видно одразу на вкладці «Головна» (за
    // замовчуванням активна), тож для НЬОГО налаштування підвантажуємо одразу —
    // лінива підвантага нижче стосується лише важчого вмісту вкладки «Тривоги»
    // (список областей і типів цілей), який поки не видно.
    const quickToggle = body.querySelector('[data-role="alerts-quick-toggle"]');
    api(`/api/channels/alert-settings?id=${ch.id}`).then((settings) => {
      alertsEnabledCache = settings;
      quickToggle.classList.toggle("on", !!(settings && settings.enabled));
      quickToggle.dataset.on = (settings && settings.enabled) ? "true" : "false";
      quickToggle.onclick = async () => {
        const on = quickToggle.dataset.on !== "true";
        quickToggle.classList.toggle("on", on);
        quickToggle.dataset.on = on ? "true" : "false";
        await api("/api/channels/alert-settings", { method: "POST", body: JSON.stringify({ id: ch.id, enabled: on }) });
        // Якщо адмін вже встиг відкрити вкладку «Тривоги» — синхронізуємо і її тумблер.
        const fullEnabledSwitch = body.querySelector('[data-role="notify-siren-switch"]');
        if (alertsTabLoaded && fullEnabledSwitch) {
          body.querySelector('[data-role="alerts-config-block"]').style.display = on ? "block" : "none";
        }
      };
    });
  }

  loadAvatarInto(body.querySelector('[data-role="modal-avatar"]'), ch.id, ch.title);

  async function initAlertsTab() {
    const [oblastsResp, settings] = await Promise.all([
      api("/api/alerts/oblasts"),
      api(`/api/channels/alert-settings?id=${ch.id}`),
    ]);
    const allOblasts = (oblastsResp && oblastsResp.oblasts) || [];
    const allTypes = (oblastsResp && oblastsResp.types) || [];
    const typeLabels = {
      uav: { icon: ICONS.drone, text: t("channelModal.typeUav") },
      recon: { icon: ICONS.radar, text: t("channelModal.typeRecon") },
      missile: { icon: ICONS.rocket, text: t("channelModal.typeMissile") },
      ballistic: { icon: ICONS.meteor, text: t("channelModal.typeBallistic") },
      kab: { icon: ICONS.bomb, text: t("channelModal.typeKab") },
      mig31k: { icon: ICONS.jet, text: t("channelModal.typeMig31k") },
    };
    let selectedOblasts = (settings && settings.oblasts) || [];
    let selectedTypes = (settings && settings.types) || allTypes.slice();

    const enabledSwitch = body.querySelector('[data-role="alerts-quick-toggle"]');
    const configBlock = body.querySelector('[data-role="alerts-config-block"]');
    const sirenSwitch = body.querySelector('[data-role="notify-siren-switch"]');
    const threatsSwitch = body.querySelector('[data-role="notify-threats-switch"]');
    const showMapSwitch = body.querySelector('[data-role="show-threat-map-switch"]');
    const typesBlock = body.querySelector('[data-role="alerts-types-block"]');
    const oblastList = body.querySelector('[data-role="alerts-oblast-list"]');
    const typeList = body.querySelector('[data-role="alerts-type-list"]');
    const oblastPanel = body.querySelector('[data-role="alerts-oblast-panel"]');
    const oblastSummaryBtn = body.querySelector('[data-role="oblast-summary-btn"]');
    const oblastSummaryText = body.querySelector('[data-role="oblast-summary-text"]');
    const oblastChevron = body.querySelector('[data-role="oblast-chevron"]');
    const oblastSearch = body.querySelector('[data-role="oblast-search"]');

    function syncSwitch(el, on) {
      el.classList.toggle("on", on);
      el.dataset.on = on ? "true" : "false";
    }
    function bindSwitch(el, initial, onChange) {
      syncSwitch(el, initial);
      el.onclick = () => {
        const on = el.dataset.on !== "true";
        syncSwitch(el, on);
        onChange(on);
      };
    }

    function updateOblastSummary() {
      const n = selectedOblasts.length;
      oblastSummaryText.textContent = n === 0 ? t("channelModal.oblastsNone") : `${t("channelModal.oblastsSelected")} ${n} ${t("channelModal.oblastsOf")} ${allOblasts.length}`;
    }

    function renderOblastChips(filterText = "") {
      oblastList.innerHTML = "";
      const q = filterText.trim().toLowerCase();
      for (const name of allOblasts) {
        if (q && !name.toLowerCase().includes(q)) continue;
        const on = selectedOblasts.includes(name);
        const chip = document.createElement("div");
        chip.className = "chip-compact" + (on ? " checked" : "");
        chip.innerHTML = `<span>${escapeHtml(name)}</span>${on ? `<span class="channel-chip-check">${ICONS.check}</span>` : ""}`;
        chip.onclick = () => {
          const idx = selectedOblasts.indexOf(name);
          if (idx >= 0) selectedOblasts.splice(idx, 1); else selectedOblasts.push(name);
          renderOblastChips(oblastSearch.value);
          updateOblastSummary();
          scheduleAlertsSave();
        };
        oblastList.appendChild(chip);
      }
    }
    function renderTypeChips() {
      typeList.innerHTML = "";
      for (const t of allTypes) {
        const on = selectedTypes.includes(t);
        const chip = document.createElement("div");
        chip.className = "chip-compact" + (on ? " checked" : "");
        const label = typeLabels[t] || { icon: "", text: t };
        chip.innerHTML = `${label.icon}<span>${escapeHtml(label.text)}</span>${on ? `<span class="channel-chip-check">${ICONS.check}</span>` : ""}`;
        chip.onclick = () => {
          const idx = selectedTypes.indexOf(t);
          if (idx >= 0) selectedTypes.splice(idx, 1); else selectedTypes.push(t);
          renderTypeChips();
          scheduleAlertsSave();
        };
        typeList.appendChild(chip);
      }
    }
    renderOblastChips();
    renderTypeChips();
    updateOblastSummary();

    // ---------- Автозбереження (замість окремої кнопки «Зберегти», п.1 плану редизайну) ----------
    // Дебаунс на 600мс: клікання по кільком чипам поспіль шле один запит, а не по
    // одному на кожен клік — і водночас користувач не чекає на явну кнопку "Зберегти".
    const saveStatusEl = body.querySelector('[data-role="alerts-save-status"]');
    let saveDebounceTimer = null;
    let saveStatusFadeTimer = null;
    function scheduleAlertsSave() {
      if (saveDebounceTimer) clearTimeout(saveDebounceTimer);
      saveStatusEl.textContent = t("common.saving");
      saveDebounceTimer = setTimeout(async () => {
        const r = await api("/api/channels/alert-settings", {
          method: "POST",
          body: JSON.stringify({
            id: ch.id,
            enabled: enabledSwitch.dataset.on === "true",
            oblasts: selectedOblasts,
            types: selectedTypes,
            notify_siren: sirenSwitch.dataset.on === "true",
            notify_threats: threatsSwitch.dataset.on === "true",
            show_threat_map: showMapSwitch.dataset.on === "true",
          }),
        });
        if (saveStatusFadeTimer) clearTimeout(saveStatusFadeTimer);
        saveStatusEl.textContent = r && r.ok ? t("common.savedCheck") : `${t("common.error")}: ${(r && r.error) || t("common.saveFailedGeneric")}`;
        saveStatusFadeTimer = setTimeout(() => { saveStatusEl.textContent = ""; }, 2000);
      }, 600);
    }

    oblastSummaryBtn.onclick = () => {
      const open = !oblastPanel.classList.contains("collapsed");
      oblastPanel.classList.toggle("collapsed", open);
      oblastChevron.style.transform = open ? "rotate(0deg)" : "rotate(90deg)";
    };
    oblastSummaryBtn.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); oblastSummaryBtn.onclick(); }
    };
    oblastSearch.oninput = () => renderOblastChips(oblastSearch.value);

    bindSwitch(enabledSwitch, !!(settings && settings.enabled), () => scheduleAlertsSave());
    configBlock.style.display = (settings && settings.enabled) ? "block" : "none";
    enabledSwitch.addEventListener("click", () => {
      configBlock.style.display = enabledSwitch.dataset.on === "true" ? "block" : "none";
    });

    bindSwitch(sirenSwitch, settings ? settings.notify_siren !== false : true, () => scheduleAlertsSave());
    bindSwitch(threatsSwitch, !!(settings && settings.notify_threats), (on) => {
      typesBlock.style.display = on ? "block" : "none";
      scheduleAlertsSave();
    });
    typesBlock.style.display = (settings && settings.notify_threats) ? "block" : "none";
    bindSwitch(showMapSwitch, !!(settings && settings.show_threat_map), () => scheduleAlertsSave());

    body.querySelector('[data-role="alerts-select-all"]').onclick = () => { selectedOblasts = allOblasts.slice(); renderOblastChips(oblastSearch.value); updateOblastSummary(); scheduleAlertsSave(); };
    body.querySelector('[data-role="alerts-deselect-all"]').onclick = () => { selectedOblasts = []; renderOblastChips(oblastSearch.value); updateOblastSummary(); scheduleAlertsSave(); };

    body.querySelector('[data-action="test-alert"]').onclick = async () => {
      const r = await api("/api/alerts/test", { method: "POST", body: JSON.stringify({ id: ch.id }) });
      tg.showAlert(r.ok ? t("channelModal.testAlertSent") : `${t("common.error")}: ${r.error || t("common.sendFailedGeneric")}`);
    };
  }

  const fileInput = body.querySelector('[data-role="watermark-file"]');
  const filenameEl = body.querySelector('[data-role="watermark-filename"]');
  fileInput.onchange = () => {
    filenameEl.textContent = fileInput.files[0] ? `${t("channelModal.fileChosenPrefix")}: ${fileInput.files[0].name}` : "";
    const file = fileInput.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => loadLogoIntoPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const copyBtn = body.querySelector('[data-action="copy-link"]');
  if (copyBtn) copyBtn.onclick = () => {
    navigator.clipboard.writeText(ch.submit_link).then(() => {
      tg.showAlert(t("channelModal.linkCopied"));
    });
  };

  const newsToggleSwitch = body.querySelector('[data-role="news-toggle-switch"]');
  if (newsToggleSwitch) {
    newsToggleSwitch.onclick = async () => {
      const on = !newsToggleSwitch.classList.contains("on");
      newsToggleSwitch.classList.toggle("on", on);
      await api("/api/channels/newstoggle", { method: "POST", body: JSON.stringify({ id: ch.id }) });
      loadChannels(); // оновлює список каналів у фоні — модалку більше НЕ закриваємо заради
                       // одного тумблера, це було зайвим переривом роботи адміна
    };
  }
  body.querySelector('[data-action="test"]').onclick = async () => {
    const r = await api("/api/channels/test", { method: "POST", body: JSON.stringify({ id: ch.id }) });
    tg.showAlert(r.ok ? t("channelModal.testMsgSent") : `${t("common.error")}: ${r.error || t("common.unknownError")}`);
  };

  // ---------- Водяний знак каналу ----------
  const wmPreviewWrap = body.querySelector("#wm-preview-wrap");
  const wmCanvas = body.querySelector('[data-role="wm-live-canvas"]');
  const wmCtx = wmCanvas.getContext("2d");
  let wmLogoImage = null;  // Image поточного логотипа (щойно обраний файл АБО вже збережений на сервері)

  function drawDemoBackground() {
    const grad = wmCtx.createLinearGradient(0, 0, wmCanvas.width, wmCanvas.height);
    grad.addColorStop(0, "#1e2536");
    grad.addColorStop(1, "#0f1320");
    wmCtx.fillStyle = grad;
    wmCtx.fillRect(0, 0, wmCanvas.width, wmCanvas.height);
    wmCtx.fillStyle = "rgba(255,255,255,0.25)";
    wmCtx.font = "13px sans-serif";
    wmCtx.textAlign = "center";
    wmCtx.fillText(t("channelModal.demoPhotoText"), wmCanvas.width / 2, wmCanvas.height / 2);
  }

  function renderWmPreview() {
    drawDemoBackground();
    if (!wmLogoImage) return;
    const scalePct = Number(wmScaleSlider.value) / 100;
    const opacityPct = Number(wmOpacitySlider.value) / 100;
    const targetW = wmCanvas.width * scalePct;
    const ratio = targetW / wmLogoImage.width;
    const targetH = wmLogoImage.height * ratio;
    const margin = wmCanvas.width * 0.04;

    wmCtx.globalAlpha = opacityPct;
    for (const pos of selectedWmPositions) {
      let x, y;
      if (pos === "top-left") { x = margin; y = margin; }
      else if (pos === "top-right") { x = wmCanvas.width - targetW - margin; y = margin; }
      else if (pos === "bottom-left") { x = margin; y = wmCanvas.height - targetH - margin; }
      else if (pos === "bottom-right") { x = wmCanvas.width - targetW - margin; y = wmCanvas.height - targetH - margin; }
      else { x = (wmCanvas.width - targetW) / 2; y = (wmCanvas.height - targetH) / 2; }
      wmCtx.drawImage(wmLogoImage, x, y, targetW, targetH);
    }
    wmCtx.globalAlpha = 1;
  }

  function loadLogoIntoPreview(url) {
    const img = new Image();
    img.onload = () => { wmLogoImage = img; renderWmPreview(); };
    img.src = url;
  }
  drawDemoBackground();

  async function refreshWatermarkPreview() {
    wmPreviewWrap.innerHTML = t("common.loading");
    let status;
    try {
      status = await api(`/api/channels/watermark/${ch.id}`);
    } catch (e) {
      status = null;
    }
    if (!status || !status.has_watermark) {
      wmPreviewWrap.innerHTML = `<span class="muted">${t("channelModal.noWatermarkYet")}</span>`;
      wmLogoImage = null;
      renderWmPreview();
      return;
    }
    try {
      const res = await fetch(`/api/channels/watermark/image/${ch.id}`, {
        headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
      });
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      wmPreviewWrap.innerHTML = `<img src="${url}" alt="${t("channelModal.watermarkTitle")}" style="max-width:140px;max-height:140px;border-radius:8px;background:repeating-conic-gradient(#2a2f3a 0% 25%, transparent 0% 50%) 50% / 16px 16px;" />`;
      loadLogoIntoPreview(url);
    } catch (e) {
      wmPreviewWrap.innerHTML = `<span class="muted">${t("channelModal.wmPreviewFailed")}</span>`;
    }
  }

  body.querySelector('[data-action="watermark-upload"]').onclick = async () => {
    const fileInput = body.querySelector('[data-role="watermark-file"]');
    const file = fileInput.files[0];
    if (!file) {
      tg.showAlert(t("channelModal.chooseFileFirst"));
      return;
    }
    const form = new FormData();
    form.append("channel_id", ch.id);
    form.append("image", file);
    let r;
    try {
      const res = await fetch("/api/channels/watermark/upload", {
        method: "POST",
        headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
        body: form,
      });
      r = await res.json();
    } catch (e) {
      tg.showAlert(`${t("common.networkError")}: ${e.message}`);
      return;
    }
    if (r.ok) {
      tg.showAlert(t("channelModal.wmSaved"));
      fileInput.value = "";
      filenameEl.textContent = "";
      refreshWatermarkPreview();
    } else {
      tg.showAlert(`${t("common.error")}: ${r.error || t("common.saveFailedGeneric")}`);
    }
  };

  body.querySelector('[data-action="watermark-remove"]').onclick = async () => {
    const r = await api("/api/channels/watermark/remove", {
      method: "POST",
      body: JSON.stringify({ channel_id: ch.id }),
    });
    if (r.ok) {
      tg.showAlert(t("channelModal.wmRemoved"));
      refreshWatermarkPreview();
    } else {
      tg.showAlert(`${t("common.error")}: ${r.error || t("channelModal.removeFailedGeneric")}`);
    }
  };

  // --- Прозорість, мультипозиції та масштаб водяного знака (п.2.2-2.3 ТЗ) ---
  const wmOpacitySlider = body.querySelector('[data-role="wm-opacity-slider"]');
  const wmOpacityValue = body.querySelector('[data-role="wm-opacity-value"]');
  const wmScaleSlider = body.querySelector('[data-role="wm-scale-slider"]');
  const wmScaleValue = body.querySelector('[data-role="wm-scale-value"]');
  const wmPositionGrid = body.querySelector('[data-role="wm-position-grid"]');
  const POSITION_CELLS = {
    "top-left": [1, 1], "top-right": [1, 3], "center": [2, 2],
    "bottom-left": [3, 1], "bottom-right": [3, 3],
  };
  let selectedWmPositions = ["center"];

  function renderPositionGrid() {
    wmPositionGrid.innerHTML = "";
    for (const [pos, [row, col]] of Object.entries(POSITION_CELLS)) {
      const btn = document.createElement("div");
      btn.className = "position-btn" + (selectedWmPositions.includes(pos) ? " active" : "");
      btn.style.gridRow = row;
      btn.style.gridColumn = col;
      btn.innerHTML = '<span class="dot"></span>';
      btn.onclick = () => {
        // Мультивибір (п.2.2 ТЗ) — клік перемикає точку, а не замінює вибір одною.
        const idx = selectedWmPositions.indexOf(pos);
        if (idx >= 0) {
          if (selectedWmPositions.length > 1) selectedWmPositions.splice(idx, 1);  // хоч одна точка має лишитись
        } else {
          selectedWmPositions.push(pos);
        }
        renderPositionGrid();
        renderWmPreview();
      };
      wmPositionGrid.appendChild(btn);
    }
  }
  renderPositionGrid();

  wmOpacitySlider.oninput = () => {
    wmOpacityValue.textContent = `${wmOpacitySlider.value}%`;
    renderWmPreview();
  };
  wmScaleSlider.oninput = () => {
    wmScaleValue.textContent = `${wmScaleSlider.value}%`;
    renderWmPreview();
  };

  // Прев'ю поточного знака й збережені налаштування (позиції/прозорість/масштаб) —
  // мережеві виклики, тож підвантажуються лише коли адмін реально відкриє вкладку
  // «Медіа» (initMediaTabData викликається лениво з обробника вкладок вище).
  function initMediaTabData() {
    refreshWatermarkPreview();
    api(`/api/channels/watermark/settings?id=${ch.id}`).then((wmSettings) => {
      if (!wmSettings) return;
      const opacityPct = Math.round((wmSettings.opacity || 0.5) * 100);
      wmOpacitySlider.value = opacityPct;
      wmOpacityValue.textContent = `${opacityPct}%`;
      const scalePct = Math.round((wmSettings.scale || 0.4) * 100);
      wmScaleSlider.value = scalePct;
      wmScaleValue.textContent = `${scalePct}%`;
      selectedWmPositions = (wmSettings.positions && wmSettings.positions.length) ? wmSettings.positions.slice() : ["center"];
      renderPositionGrid();
      renderWmPreview();
    });
  }

  body.querySelector('[data-action="save-watermark-settings"]').onclick = async () => {
    const r = await api("/api/channels/watermark/settings", {
      method: "POST",
      body: JSON.stringify({
        id: ch.id,
        opacity: Number(wmOpacitySlider.value) / 100,
        scale: Number(wmScaleSlider.value) / 100,
        positions: selectedWmPositions,
      }),
    });
    tg.showAlert(r.ok ? t("channelModal.wmSettingsSaved") : `${t("common.error")}: ${r.error || t("common.saveFailedGeneric")}`);
  };

  document.getElementById("channel-modal").style.display = "flex";
}

document.getElementById("channel-modal-close-btn").addEventListener("click", () => {
  document.getElementById("channel-modal").style.display = "none";
});

// ---------- Джерела ----------

let sourcesCache = [];
let testChannelsCache = [];

async function loadSources() {
  const list = document.getElementById("sources-list");
  const countEl = document.getElementById("sources-count");
  const sources = await api("/api/sources");

  if (sources.error) {
    list.innerHTML = `<div class="card-row muted">${t("common.noAccess")}</div>`;
    countEl.textContent = "—";
    return;
  }

  sourcesCache = sources;
  countEl.textContent = sources.filter((s) => s.enabled !== false).length;

  const filtered = currentSourceCategoryFilter === "all"
    ? sources
    : sources.filter((s) => (s.category || "public_channel") === currentSourceCategoryFilter);

  if (!filtered.length) {
    list.innerHTML = `<div class="card-row muted">${t("sources.empty")}</div>`;
    return;
  }

  const channelsRes = await api("/api/channels");
  testChannelsCache = Array.isArray(channelsRes) ? channelsRes.filter((c) => c.status !== "inactive") : [];

  list.innerHTML = "";
  for (const s of filtered) {
    const row = document.createElement("div");
    row.className = "channel-card";
    const on = s.enabled !== false;
    const isEditorial = (s.category || "public_channel") === "editorial_chat";
    const typeIcon = s.type === "telegram" || s.type === "telegram_public" ? ICONS.telegram : ICONS.channel;
    const typeLabel = s.type === "telegram" ? t("sources.typeAdminChannel")
      : s.type === "telegram_public" ? `${t("sources.typePublicChannel")}: @${s.username}`
      : (s.url || "");
    const statusBadge = on
      ? `<span class="badge-inactive" style="color:var(--success);background:var(--success-bg);">${t("common.on")}</span>`
      : `<span class="badge-inactive">${t("common.off")}</span>`;
    const editorialBadge = isEditorial
      ? `<span class="badge-inactive" style="color:var(--accent-2);background:rgba(47,111,237,0.12);">${t("sources.editorialBadge")}</span>`
      : "";

    row.innerHTML = `
      <div class="submission-summary">
        <div class="channel-avatar" data-role="avatar">${typeIcon}</div>
        <div class="submission-summary-body">
          <div class="submission-title">${escapeHtml(s.name)} ${statusBadge} ${editorialBadge}</div>
          <div class="submission-meta">${escapeHtml(typeLabel)}</div>
        </div>
        <svg class="icon submission-chevron" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>
      </div>
    `;

    if (s.type === "telegram" || s.type === "telegram_public") {
      loadAvatarFromUrlInto(row.querySelector('[data-role="avatar"]'), `/api/source-avatar/${s.id}`, s.name);
    }

    row.querySelector(".submission-summary").addEventListener("click", () => openSourceModal(s.name));
    list.appendChild(row);
  }
}

let currentSourceCategoryFilter = "all";
document.getElementById("sources-category-segmented").addEventListener("click", (e) => {
  const btn = e.target.closest(".segment");
  if (!btn) return;
  document.querySelectorAll("#sources-category-segmented .segment").forEach((s) => s.classList.remove("active"));
  btn.classList.add("active");
  currentSourceCategoryFilter = btn.dataset.category;
  loadSources();
});

async function loadRecommendedSources() {
  const list = document.getElementById("recommended-sources-list");
  if (!list) return;
  const items = await api("/api/sources/recommended");
  if (!Array.isArray(items) || !items.length) {
    list.innerHTML = `<div class="card-row muted">${t("sources.noRecommendations")}</div>`;
    return;
  }

  list.innerHTML = "";
  for (const rec of items) {
    const row = document.createElement("div");
    row.className = "card-row";
    row.innerHTML = `
      <div>
        <div style="font-weight:600;">${escapeHtml(rec.name)}</div>
        <div class="muted" style="margin-top:2px;">@${escapeHtml(rec.username)}</div>
      </div>
      ${rec.already_added
        ? `<span class="badge-inactive" style="color:var(--success);background:var(--success-bg);">${t("sources.added")}</span>`
        : `<button class="pill" data-action="add-recommended">${ICONS.plus} ${t("common.add")}</button>`}
    `;
    const btn = row.querySelector('[data-action="add-recommended"]');
    if (btn) {
      btn.onclick = async () => {
        btn.disabled = true;
        const r = await api("/api/sources/add-public-tg", {
          method: "POST",
          body: JSON.stringify({ name: rec.name, link: rec.username }),
        });
        if (r.ok) {
          loadSources();
          loadRecommendedSources();
        } else {
          btn.disabled = false;
          tg.showAlert(`${t("common.error")}: ${r.error || t("sources.addFailed")}`);
        }
      };
    }
    list.appendChild(row);
  }
}

document.getElementById("toggle-recommended-btn").addEventListener("click", (e) => {
  const list = document.getElementById("recommended-sources-list");
  const collapsed = list.style.display === "none";
  list.style.display = collapsed ? "" : "none";
  e.target.textContent = collapsed ? t("common.hide") : t("common.show");
});

// ---------- Черга публікації ----------

function _asUtcIso(isoString) {
  // Сервер пише created_at/published_at через datetime.now().isoformat() на VPS з
  // TZ=UTC — рядок БЕЗ 'Z'/офсету. Браузер в іншому поясі (напр. Київ, UTC+3)
  // трактує такий рядок як ЛОКАЛЬНИЙ час, через що timeAgo "старить" новини на
  // величину зсуву пояса (у Києві — рівно на 3 години). Домальовуємо 'Z', якщо
  // офсету нема, щоб new Date() парсив рядок як UTC незалежно від пояса браузера.
  if (!isoString) return isoString;
  return /[Zz]|[+-]\d{2}:?\d{2}$/.test(isoString) ? isoString : `${isoString}Z`;
}

function timeAgo(isoString) {
  if (!isoString) return "";
  const diffMin = Math.max(0, Math.round((Date.now() - new Date(_asUtcIso(isoString)).getTime()) / 60000));
  if (diffMin < 1) return t("time.justNow");
  if (diffMin < 60) return `${diffMin} ${t("time.minAgo")}`;
  return `${Math.round(diffMin / 60)} ${t("time.hourAgo")}`;
}

function formatCountdown(seconds) {
  if (seconds <= 0) return t("time.publishingSoon");
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${t("time.publishIn")} ${mins} ${t("common.minutesShort")} ${secs} ${t("time.secShort")}`;
}

function _mediaKindIcon(kind, count) {
  if (kind === "mixed") return `${ICONS.image}${ICONS.video} ${t("type.album")} (${count})`;
  if (kind === "video") return count > 1 ? `${ICONS.video} ${t("type.video")} ×${count}` : `${ICONS.video} ${t("type.video")}`;
  if (kind === "photo") return count > 1 ? `${ICONS.image} ${t("type.photo")} ×${count}` : `${ICONS.image} ${t("type.photo")}`;
  return `${ICONS.fileText} ${t("type.text")}`;
}

function sortNewsDesc(items, dateField = "created_at") {
  if (!Array.isArray(items)) return items;
  return [...items].sort((a, b) => {
    const aPriority = a.priority ? 1 : 0;
    const bPriority = b.priority ? 1 : 0;
    if (aPriority !== bPriority) return bPriority - aPriority;
    const aApproved = a.status !== "pending" ? 1 : 0;
    const bApproved = b.status !== "pending" ? 1 : 0;
    if (aApproved !== bApproved) return bApproved - aApproved;
    return new Date(b[dateField] || 0) - new Date(a[dateField] || 0);
  });
}

async function loadQueue() {
  const list = document.getElementById("queue-list");
  if (!list) return;
  const items = sortNewsDesc(await api("/api/queue"));
  const channelsRes = await api("/api/channels");
  activeChannelsCache = Array.isArray(channelsRes)
    ? channelsRes.filter((c) => c.status !== "inactive" && c.news_enabled)
    : activeChannelsCache;
  if (!Array.isArray(items) || items.length === 0) {
    list.innerHTML = `<div class="card-row muted">${t("queue.empty")}</div>`;
    return;
  }

  list.innerHTML = "";
  for (const it of items) {
    const wrap = document.createElement("div");
    wrap.className = "swipe-wrap";

    const row = document.createElement("div");
    row.className = "submission-card swipe-content";
    const isPending = it.status === "pending";
    // viewer_role приходить з /api/queue (найвища роль адміна серед усіх каналів-
    // цілей цього запису) — Moderator бачить лише "Схвалити"/"Опублікувати",
    // Editor і Owner додатково "Редагувати" й можуть видалити свайпом.
    const canModerate = it.viewer_role === "owner" || it.viewer_role === "editor" || it.viewer_role === "moderator";
    const canEditItem = it.viewer_role === "owner" || it.viewer_role === "editor";
    const statusList = it.channel_status || [];
    const avatarStack = statusList.length
      ? `<div class="avatar-stack">${statusList.map((cs) => {
          // delivered → зелена; все інше (очікує/схвалено-в черзі) → жовта.
          // Червона зарезервована під явну помилку публікації (cs.error), якщо бекенд її колись віддасть.
          const state = cs.delivered ? "delivered" : (cs.error ? "error" : "pending");
          return `<div class="avatar-stack-item ${state}" data-role="stack-avatar" data-chat-id="${cs.id}" title="${escapeHtml(cs.title)}">${ICONS.channelDefault}</div>`;
        }).join("")}</div>`
      : "";
    const badge = isPending
      ? `<span class="status-badge pending">${t("queue.statusPending")}</span>`
      : `<span class="status-badge approved">${t("queue.statusApproved")}</span>`;
    const timeRow = (!isPending && statusList.length) ? (() => {
      const pending = statusList.filter((cs) => !cs.delivered);
      if (!pending.length) return "";
      const soonestSeconds = Math.min(...pending.map((cs) => cs.seconds_left || 0));
      const publishAt = new Date(Date.now() + soonestSeconds * 1000);
      const timeLabel = publishAt.toLocaleTimeString("uk-UA", { hour: "2-digit", minute: "2-digit" });
      const pinIcon = it.pinned_message_id ? `<span class="pin-indicator" title="${t("queue.pinnedTitle")}">${ICONS.pin}</span>` : "";
      return `<div class="queue-time-row">${ICONS.clock} ${t("queue.publishAt")} ${timeLabel}${pinIcon}</div>`;
    })() : "";
    const actionButtons = isPending
      ? `${canModerate ? `<button class="btn-primary" data-action="queue-approve">${ICONS.check} ${t("queue.approveBtn")}</button>` : ""}
         ${canEditItem ? `<button class="btn-secondary" data-action="queue-edit">${ICONS.pencil} ${t("common.edit")}</button>` : ""}`
      : `${canEditItem ? `<button class="btn-secondary" data-action="queue-edit">${ICONS.pencil} ${t("common.edit")}</button>` : ""}
         ${canModerate ? `<button class="btn-primary" data-action="queue-publish-now">${ICONS.send} ${t("queue.publishNowBtn")}</button>` : ""}`;
    const urgentButton = (isPending || !canModerate) ? "" : `
      <button class="btn-urgent" data-action="queue-publish-nocd" title="${t("queue.publishUrgentTitle")}">${ICONS.bolt} ${t("queue.publishUrgentBtn")}</button>`;
    row.innerHTML = `
      <div class="submission-title submission-title-clip">${escapeHtml(it.title || t("queue.noTitle"))}</div>
      <div class="submission-meta">${escapeHtml(it.source_name || "")} · ${_mediaKindIcon(it.media_kind, it.media_count)} · ${t("queue.inQueueSince")} ${escapeHtml(timeAgo(it.created_at))}</div>
      ${badge}
      ${timeRow}
      ${avatarStack}
      <div class="card-actions">
        ${actionButtons}
        ${urgentButton}
      </div>
    `;

    const bg = document.createElement("div");
    bg.className = "swipe-delete-bg";
    bg.innerHTML = ICONS.trash;

    wrap.appendChild(bg);
    wrap.appendChild(row);
    list.appendChild(wrap);

    row.querySelectorAll('[data-role="stack-avatar"]').forEach((el) => {
      loadAvatarFromUrlInto(el, `/api/channel-avatar/${el.dataset.chatId}`, el.title);
    });

    const editBtn = row.querySelector('[data-action="queue-edit"]');
    if (editBtn) editBtn.onclick = () => openEditPostModal(it, "queue");
    if (canEditItem) {
      attachSwipeToDelete(wrap, row, bg, async () => {
        const r = await api("/api/queue/remove", { method: "POST", body: JSON.stringify({ id: it.id }) });
        if (!r.ok) tg.showAlert(`${t("common.error")}: ${r.error || t("queue.deleteFailed")}`);
      });
    }
    const approveBtn = row.querySelector('[data-action="queue-approve"]');
    if (approveBtn) {
      approveBtn.onclick = async () => {
        const r = await api("/api/queue/approve", { method: "POST", body: JSON.stringify({ id: it.id }) });
        if (r.ok) {
          tg.showAlert(t("queue.approvedMsg"));
          loadQueue();
        } else {
          tg.showAlert(`${t("common.error")}: ${r.error || t("queue.approveFailed")}`);
        }
      };
    }
    const publishBtn = row.querySelector('[data-action="queue-publish-now"]');
    if (publishBtn) {
      publishBtn.onclick = async () => {
        const r = await api("/api/queue/publish-now", { method: "POST", body: JSON.stringify({ id: it.id }) });
        if (r.ok) {
          tg.showAlert(t("queue.publishedMsg"));
          loadQueue();
        } else {
          tg.showAlert(`${t("common.error")}: ${r.error || t("queue.publishFailed")}`);
        }
      };
    }
    const publishNoCdBtn = row.querySelector('[data-action="queue-publish-nocd"]');
    if (publishNoCdBtn) {
      publishNoCdBtn.onclick = async () => {
        const r = await api("/api/queue/publish-now-nocd", { method: "POST", body: JSON.stringify({ id: it.id }) });
        if (r.ok) {
          const timeLabel = new Date(r.published_at ? _asUtcIso(r.published_at) : Date.now()).toLocaleTimeString("uk-UA", { hour: "2-digit", minute: "2-digit" });
          tg.showAlert(`${t("queue.publishedUrgentAt")} ${timeLabel}`);
          loadQueue();
        } else {
          tg.showAlert(`${t("common.error")}: ${r.error || t("queue.publishFailed")}`);
        }
      };
    }
  }
}

// Swipe-to-delete: тягнемо картку вліво (pointer events — працює і на тач, і мишкою).
// Поріг спрацювання — 80px. При спрацюванні картка вилітає вліво, тоді обгортка
// схлопується по висоті з fade-out, і виконується сам виклик видалення.
//
// Якщо переданий dragOptions — картка ще й підтримує ДРУГИЙ жест: довге утримання
// (без руху ~450мс) переводить її в режим "перетягування" — картка йде за пальцем/
// мишкою, а drop-зоною є таби категорій вгорі (getDropTargets/onDrop) — той самий
// принцип, що й перенесення іконки застосунку в папку на телефоні. Два жести не
// конфліктують: свайп розпізнається по РУХУ одразу, довге утримання — навпаки, по
// ВІДСУТНОСТІ руху певний час, тож який спрацює першим — залежить від дій людини.
function attachSwipeToDelete(wrapEl, contentEl, bgEl, onDelete, dragOptions) {
  const THRESHOLD = -80;
  const DRAG_START_PX = 8; // поріг руху, з якого жест визнається свайпом. Без нього
  // pointerdown одразу викликав setPointerCapture на КОЖНОМУ кліку (і мишкою теж) —
  // на тачскріні це непомітно, а в Telegram Desktop (клік мишкою, без руху) заважало
  // звичайному відкриттю картки/меню одним кліком.
  const LONG_PRESS_MS = 450;
  let startX = 0, startY = 0, dx = 0, dy = 0, dragging = false, pointerId = null, mode = null;
  let longPressTimer = null;

  contentEl.addEventListener("pointerdown", (e) => {
    startX = e.clientX;
    startY = e.clientY;
    dx = 0;
    dy = 0;
    dragging = false;
    mode = null;
    pointerId = e.pointerId;
    if (dragOptions) {
      longPressTimer = setTimeout(() => {
        if (pointerId === null) return;
        mode = "category";
        dragging = true;
        contentEl.classList.add("category-dragging");
        contentEl.style.pointerEvents = "none";  // інакше elementFromPoint (drop-хіттест) на
        // фінальних координатах пальця влучає в саму картку, яка туди ж і приїхала, а не в таб під нею
        contentEl.setPointerCapture(pointerId);
        if (dragOptions.onDragStart) dragOptions.onDragStart();
      }, LONG_PRESS_MS);
    }
  });

  contentEl.addEventListener("pointermove", (e) => {
    if (pointerId === null || e.pointerId !== pointerId) return;
    const rawDx = e.clientX - startX;
    const rawDy = e.clientY - startY;

    if (mode === null) {
      if (Math.abs(rawDx) < DRAG_START_PX && Math.abs(rawDy) < DRAG_START_PX) return;
      clearTimeout(longPressTimer);  // реальний рух ДО спрацювання довгого утримання — це свайп/скрол, не drag
      if (Math.abs(rawDx) >= DRAG_START_PX && Math.abs(rawDx) > Math.abs(rawDy)) {
        mode = "swipe";
        dragging = true;
        contentEl.classList.add("swiping");
        contentEl.setPointerCapture(pointerId);
      } else {
        mode = "cancelled";  // переважно вертикальний рух — віддаємо жест нативному скролу
        return;
      }
    }

    if (mode === "swipe") {
      dx = Math.min(0, rawDx);
      contentEl.style.transform = `translateX(${dx}px)`;
      bgEl.style.opacity = String(Math.min(1, Math.abs(dx) / 80));
    } else if (mode === "category") {
      dx = rawDx;
      dy = rawDy;
      contentEl.style.transform = `translate(${dx}px, ${dy}px) scale(1.03)`;
      if (dragOptions.onDragMove) dragOptions.onDragMove(e.clientX, e.clientY);
    }
  });

  const finish = (e) => {
    clearTimeout(longPressTimer);
    const finishedMode = mode;
    pointerId = null;
    mode = null;
    if (!dragging) return;
    dragging = false;

    if (finishedMode === "swipe") {
      contentEl.classList.remove("swiping");
      if (dx < THRESHOLD) {
        contentEl.style.transform = "translateX(-100%)";
        onDelete();
        contentEl.addEventListener("transitionend", () => {
          wrapEl.style.overflow = "hidden";
          wrapEl.style.maxHeight = wrapEl.offsetHeight + "px";
          void wrapEl.offsetHeight;
          wrapEl.style.transition = "max-height .25s ease, opacity .25s ease, margin .25s ease";
          wrapEl.style.maxHeight = "0px";
          wrapEl.style.opacity = "0";
          wrapEl.style.marginBottom = "0px";
          wrapEl.addEventListener("transitionend", () => wrapEl.remove(), { once: true });
        }, { once: true });
      } else {
        contentEl.style.transform = "translateX(0)";
        bgEl.style.opacity = "0";
      }
    } else if (finishedMode === "category") {
      contentEl.classList.remove("category-dragging");
      contentEl.style.pointerEvents = "";
      const dropped = dragOptions.onDrop ? dragOptions.onDrop(e.clientX, e.clientY) : false;
      contentEl.style.transition = "transform .2s ease";
      contentEl.style.transform = "";
      setTimeout(() => { contentEl.style.transition = ""; }, 220);
      void dropped;
    }
    dx = 0;
    dy = 0;
  };

  contentEl.addEventListener("pointerup", finish);
  contentEl.addEventListener("pointercancel", finish);
}

const QUICK_EMOJI_SET = ["⚡️", "🚨", "📌", "‼️", "🇺🇦", "➡️", "🔥", "👇"];

function toggleEmojiPicker(container, textarea) {
  const existing = container.querySelector(".emoji-quickbar-card");
  if (existing) {
    existing.remove();
    return;
  }
  const card = document.createElement("div");
  card.className = "emoji-quickbar-card";

  const header = document.createElement("div");
  header.className = "emoji-quickbar-header";
  header.innerHTML = `<span>${t("editor.quickEmoji")}</span>`;
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "emoji-quickbar-close";
  closeBtn.setAttribute("aria-label", t("common.close"));
  closeBtn.innerHTML = '<svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  closeBtn.onclick = () => card.remove();
  header.appendChild(closeBtn);
  card.appendChild(header);

  const bar = document.createElement("div");
  bar.className = "emoji-quickbar";
  for (const emoji of QUICK_EMOJI_SET) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "emoji-quickbar-btn";
    btn.textContent = emoji;
    btn.onmousedown = (e) => e.preventDefault();  // не забирати фокус/виділення з поля до click
    btn.onclick = () => {
      textarea.focus();
      document.execCommand("insertText", false, emoji);
      updateEditorCharCounter();
    };
    bar.appendChild(btn);
  }
  card.appendChild(bar);
  container.appendChild(card);
}

/** Завантажує картинку через fetch з X-Init-Data (як аватарки) і повертає blob-URL —
 * прямий <img src="/api/..."> не спрацює, бо ендпоінт вимагає авторизаційний заголовок,
 * якого браузер сам для <img> не додасть. */
async function fetchAuthedBlobUrl(url) {
  try {
    const res = await fetch(url, { headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" } });
    if (!res.ok) return null;
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  } catch (e) {
    return null;
  }
}

/** Палітра кастомних (преміум) емодзі — бере список з паку, який адмін вказав
 * один раз (посилання на набір кастомних емодзі з Telegram). Вставляє в текст
 * <tg-emoji emoji-id="...">фолбек</tg-emoji> — це нативний HTML-тег Telegram
 * Bot API: клієнти з Premium бачать кастомну іконку, решта — символ-фолбек
 * усередині тега (сам Telegram це вже робить, окремого коду для цього не треба). */
async function toggleCustomEmojiPicker(container, textarea) {
  const existing = container.querySelector(".emoji-quickbar-card");
  if (existing) {
    existing.remove();
    return;
  }
  const card = document.createElement("div");
  card.className = "emoji-quickbar-card";
  const header = document.createElement("div");
  header.className = "emoji-quickbar-header";
  header.innerHTML = `<span>${t("editor.customEmoji")}</span>`;
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "emoji-quickbar-close";
  closeBtn.setAttribute("aria-label", t("common.close"));
  closeBtn.innerHTML = '<svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  closeBtn.onclick = () => card.remove();
  header.appendChild(closeBtn);
  card.appendChild(header);

  const body = document.createElement("div");
  body.innerHTML = `<div class="muted" style="padding:10px 2px;">${t("common.loading")}</div>`;
  card.appendChild(body);
  container.appendChild(card);

  const insertEmoji = (item) => {
    textarea.focus();
    document.execCommand("insertHTML", false, `<tg-emoji emoji-id="${item.id}">${item.emoji}</tg-emoji>`);
    updateEditorCharCounter();
  };

  function renderSetForm(errorMsg) {
    body.innerHTML = `
      <div class="muted" style="font-size:12.5px;margin-bottom:8px;line-height:1.4;">
        ${t("editor.customEmojiSetHint")}
      </div>
      <input type="text" data-role="custom-emoji-set-input" placeholder="t.me/addemoji/..." style="margin-bottom:8px;" />
      ${errorMsg ? `<div style="color:var(--danger);font-size:12px;margin-bottom:8px;">${escapeHtml(errorMsg)}</div>` : ""}
      <button type="button" class="pill" data-role="custom-emoji-set-save">${ICONS.save} ${t("editor.connectSetBtn")}</button>
    `;
    body.querySelector('[data-role="custom-emoji-set-save"]').onclick = async () => {
      const val = body.querySelector('[data-role="custom-emoji-set-input"]').value.trim();
      if (!val) return;
      body.innerHTML = `<div class="muted" style="padding:10px 2px;">${t("editor.checkingSet")}</div>`;
      const r = await api("/api/custom-emoji/set", { method: "POST", body: JSON.stringify({ set_name: val }) });
      if (r && r.ok) renderGrid();
      else renderSetForm(r && r.error ? r.error : t("editor.connectSetFailed"));
    };
  }

  async function renderGrid() {
    body.innerHTML = `<div class="muted" style="padding:10px 2px;">${t("common.loading")}</div>`;
    const r = await api("/api/custom-emoji/list");
    if (!r || !r.ok) { renderSetForm(r && r.error); return; }
    if (!r.set_name) { renderSetForm(); return; }
    if (!r.items.length) { renderSetForm(t("editor.setHasNoEmoji")); return; }

    body.innerHTML = `
      <div class="custom-emoji-grid" data-role="custom-emoji-grid"></div>
      <button type="button" class="chip-action-btn" data-role="custom-emoji-change-set" style="margin-top:8px;">${t("editor.changeSetBtn")}</button>
    `;
    const grid = body.querySelector('[data-role="custom-emoji-grid"]');
    for (const item of r.items) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "custom-emoji-btn";
      btn.title = item.emoji;
      grid.appendChild(btn);
      btn.onmousedown = (e) => e.preventDefault();
      btn.onclick = () => insertEmoji(item);
      fetchAuthedBlobUrl(`/api/custom-emoji/thumb/${item.file_id}`).then((blobUrl) => {
        btn.innerHTML = blobUrl ? `<img src="${blobUrl}" alt="" />` : item.emoji;
      });
    }
    body.querySelector('[data-role="custom-emoji-change-set"]').onclick = () => renderSetForm();
  }

  renderGrid();
}

function openMediaLightbox(url, kind) {
  const overlay = document.createElement("div");
  overlay.className = "media-lightbox";
  overlay.innerHTML = kind === "video"
    ? `<video src="${url}" controls autoplay></video>`
    : `<img src="${url}" />`;
  overlay.onclick = (e) => {
    // Клік по самому відео (пауза/грати) не повинен закривати перегляд — тільки клік по тлу.
    if (e.target === overlay) overlay.remove();
  };
  document.body.appendChild(overlay);
}

async function loadQueueMediaInto(imgOrVideoEl, itemId, index) {
  try {
    const url = `/api/queue-media/${itemId}?index=${index}`;
    const res = await fetch(url, {
      headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
    });
    if (!res.ok) {
      let detail = "";
      try { detail = (await res.json()).error || ""; } catch (e) {}
      return { url: null, error: `HTTP ${res.status}${detail ? " — " + detail : ""}` };
    }
    const blob = await res.blob();
    if (blob.size === 0) return { url: null, error: t("editor.emptyFile") };
    const objUrl = URL.createObjectURL(blob);
    if (imgOrVideoEl) {
      imgOrVideoEl.src = objUrl;
      // Деякі мобільні WebView (зокрема всередині Telegram) не малюють кадр-прев'ю
      // відео, поки не почалось відтворення, — лишається суцільний чорний
      // прямокутник замість кадру. Явний seek на майже нульовий момент часу
      // після завантаження метаданих примушує браузер відрендерити цей кадр.
      if (imgOrVideoEl.tagName === "VIDEO") {
        imgOrVideoEl.addEventListener("loadedmetadata", () => {
          try { imgOrVideoEl.currentTime = 0.01; } catch (e) {}
        }, { once: true });
      }
    }
    return { url: objUrl, error: null };
  } catch (e) {
    return { url: null, error: e.message || t("common.networkError") };
  }
}

let testSelectedChannelIds = []; // канали, обрані для тестової відправки (може бути кілька)

function openSourceModal(sourceName) {
  const s = sourcesCache.find((x) => x.name === sourceName);
  if (!s) return;

  testSelectedChannelIds = [];
  const body = document.getElementById("source-modal-body");
  const on = s.enabled !== false;
  const typeIcon = s.type === "telegram" || s.type === "telegram_public" ? ICONS.telegram : ICONS.channel;
  const typeLabel = s.type === "telegram" ? t("sources.typeAdminChannel")
    : s.type === "telegram_public" ? `${t("sources.typePublicChannel")}: @${s.username}`
    : (s.url || "");

  // Категорії серед власних каналів — для швидкого вибору "усі канали цієї категорії"
  const categories = {};
  for (const c of testChannelsCache) {
    const cat = (c.category || "").trim() || t("channels.noCategory");
    (categories[cat] = categories[cat] || []).push(c.id);
  }
  const categoryChips = Object.keys(categories).map((cat) =>
    `<button class="pill" data-role="cat-chip" data-cat="${escapeHtml(cat)}">${escapeHtml(cat)} (${categories[cat].length})</button>`
  ).join("");

  const isEditorial = (s.category || "public_channel") === "editorial_chat";
  const canRename = s.type !== "telegram";  // редакційний чат прив'язаний по chat_id — його не можна "перейменувати посиланням"

  body.innerHTML = `
    <div class="channel-title" style="margin-bottom:6px;">
      <div class="channel-avatar">${typeIcon}</div>
      <span style="flex:1;min-width:0;">${escapeHtml(s.name)}</span>
      ${canRename ? `<button type="button" class="modal-close" data-action="edit-source-toggle" title="${t("sourceModal.editNameTitle")}">${ICONS.pencil}</button>` : ""}
    </div>
    <div class="muted" data-role="type-label" style="margin-bottom:14px;">${escapeHtml(typeLabel)}</div>
    ${canRename ? `
    <div data-role="edit-source-form" style="display:none;margin:-6px 0 14px;">
      <input type="text" data-role="edit-name-input" placeholder="${t("sourceModal.namePlaceholder")}" value="${escapeHtml(s.name)}" style="width:100%;margin-bottom:8px;" />
      <input type="text" data-role="edit-link-input" placeholder="${s.type === "telegram_public" ? t("sourceModal.usernamePlaceholder") : t("sourceModal.urlPlaceholder")}" value="${escapeHtml(s.type === "telegram_public" ? (s.username || "") : (s.url || ""))}" style="width:100%;margin-bottom:8px;" />
      <div class="pill-row" style="margin-bottom:0;">
        <button class="pill on" data-action="edit-source-save" style="flex:1;justify-content:center;">${ICONS.check} ${t("common.save")}</button>
        <button class="pill" data-action="edit-source-cancel" style="flex:1;justify-content:center;">${t("common.cancel")}</button>
      </div>
      <div class="muted" data-role="edit-source-status" style="font-size:12px;margin-top:6px;min-height:16px;"></div>
    </div>` : ""}
    <div class="pill-row">
      <button class="pill ${on ? "on" : "off"}" data-action="toggle">${on ? t("common.on") : t("common.off")}</button>
      <button class="pill danger" data-action="remove">${ICONS.trash} ${t("common.delete")}</button>
    </div>

    <div class="settings-card" style="margin-top:14px;">
      <div class="settings-card-header">
        <div class="settings-card-icon">${ICONS.bolt}</div>
        <div class="settings-card-body">
          <div class="settings-card-title">${t("sourceModal.editorialTitle")}</div>
          <div class="settings-card-desc">${isEditorial
            ? t("sourceModal.editorialDescOn")
            : t("sourceModal.editorialDescOff")}</div>
        </div>
        <label class="watermark-toggle" style="margin:0;">
          <span class="watermark-switch ${isEditorial ? "on" : ""}" data-role="editorial-switch"></span>
        </label>
      </div>
    </div>

    ${(s.type === "rss" || s.type === "telegram_public") ? `
    <div class="settings-card" style="margin-top:14px;">
      <div class="settings-card-header">
        <div class="settings-card-icon">${ICONS.test}</div>
        <div class="settings-card-body">
          <div class="settings-card-title">${t("sourceModal.testSendTitle")}</div>
          <div class="settings-card-desc">${t("sourceModal.testSendDesc")}</div>
        </div>
      </div>
      <div class="settings-card-extra">
        ${categoryChips ? `<div class="pill-row" data-role="cat-chips">${categoryChips}</div>` : ""}
        <div class="channel-multiselect" data-role="test-channel-list"></div>
        <button class="pill" data-action="test-source" style="width:100%;justify-content:center;margin-top:4px;">${ICONS.test} ${t("sourceModal.testSendBtn")}</button>
        <div class="muted" data-role="test-result"></div>
      </div>
    </div>` : ""}
  `;

  const editForm = body.querySelector('[data-role="edit-source-form"]');
  const editToggleBtn = body.querySelector('[data-action="edit-source-toggle"]');
  if (editToggleBtn) {
    editToggleBtn.onclick = () => {
      editForm.style.display = editForm.style.display === "none" ? "block" : "none";
    };
    body.querySelector('[data-action="edit-source-cancel"]').onclick = () => {
      editForm.style.display = "none";
    };
    body.querySelector('[data-action="edit-source-save"]').onclick = async () => {
      const statusEl = body.querySelector('[data-role="edit-source-status"]');
      const name = body.querySelector('[data-role="edit-name-input"]').value.trim();
      const link = body.querySelector('[data-role="edit-link-input"]').value.trim();
      if (!name) {
        statusEl.textContent = t("sourceModal.nameEmpty");
        return;
      }
      statusEl.textContent = t("common.saving");
      const r = await api("/api/sources/edit", { method: "POST", body: JSON.stringify({ id: s.id, name, link }) });
      if (r && r.ok) {
        await loadSources();
        openSourceModal(name);  // перемальовуємо модалку з оновленими даними (ім'я могло змінитись)
      } else {
        statusEl.textContent = (r && r.error) || t("sourceModal.saveFailed");
      }
    };
  }

  body.querySelector('[data-role="editorial-switch"]').onclick = async (e) => {
    const newCategory = isEditorial ? "public_channel" : "editorial_chat";
    const r = await api("/api/sources/category", { method: "POST", body: JSON.stringify({ id: s.id, category: newCategory }) });
    if (r.ok) {
      s.category = newCategory;
      await loadSources();
      openSourceModal(s.name);  // перемальовуємо модалку — текст-пояснення нижче тумблера теж має оновитись
    } else {
      tg.showAlert(`${t("common.error")}: ${r.error || t("sourceModal.categoryChangeFailed")}`);
    }
  };

  body.querySelector('[data-action="toggle"]').onclick = async () => {
    await api("/api/sources/toggle", { method: "POST", body: JSON.stringify({ id: s.id, name: s.name }) });
    document.getElementById("source-modal").style.display = "none";
    loadSources();
  };
  body.querySelector('[data-action="remove"]').onclick = async () => {
    await api("/api/sources/remove", { method: "POST", body: JSON.stringify({ id: s.id, name: s.name }) });
    document.getElementById("source-modal").style.display = "none";
    loadSources();
  };

  const testChannelList = body.querySelector('[data-role="test-channel-list"]');
  function renderTestChannelList() {
    if (!testChannelList) return;
    testChannelList.innerHTML = "";
    for (const c of testChannelsCache) {
      const checked = testSelectedChannelIds.includes(c.id);
      const chip = document.createElement("div");
      chip.className = "channel-chip" + (checked ? " checked" : "");
      chip.innerHTML = `
        <span class="channel-chip-avatar" data-role="avatar">${ICONS.channelDefault}</span>
        <span>${escapeHtml(c.title)}</span>
        <span class="channel-chip-check">${checked ? ICONS.check : ""}</span>
      `;
      loadAvatarFromUrlInto(chip.querySelector('[data-role="avatar"]'), `/api/channel-avatar/${c.id}`, c.title);
      chip.onclick = () => {
        const idx = testSelectedChannelIds.indexOf(c.id);
        if (idx >= 0) testSelectedChannelIds.splice(idx, 1);
        else testSelectedChannelIds.push(c.id);
        renderTestChannelList();
      };
      testChannelList.appendChild(chip);
    }
  }
  renderTestChannelList();

  for (const chip of body.querySelectorAll('[data-role="cat-chip"]')) {
    chip.onclick = () => {
      const ids = categories[chip.dataset.cat] || [];
      const allSelected = ids.every((id) => testSelectedChannelIds.includes(id));
      if (allSelected) {
        // усі канали цієї категорії вже обрані — знімаємо їх
        testSelectedChannelIds = testSelectedChannelIds.filter((id) => !ids.includes(id));
      } else {
        // додаємо ті, яких ще немає в списку
        for (const id of ids) {
          if (!testSelectedChannelIds.includes(id)) testSelectedChannelIds.push(id);
        }
      }
      renderTestChannelList();
    };
  }

  const testBtn = body.querySelector('[data-action="test-source"]');
  if (testBtn) {
    testBtn.onclick = async () => {
      const resultEl = body.querySelector('[data-role="test-result"]');
      if (!testSelectedChannelIds.length) {
        tg.showAlert(t("sourceModal.selectChannelFirst"));
        return;
      }
      resultEl.textContent = t("sourceModal.sending");
      const r = await api("/api/sources/test", {
        method: "POST",
        body: JSON.stringify({ id: s.id, name: s.name, channel_ids: testSelectedChannelIds }),
      });
      if (r.ok) {
        resultEl.textContent = `${t("sourceModal.testSentResult")} ${r.sent}/${r.total}. ${t("sourceModal.testSentResultSuffix")}`;
      } else {
        resultEl.textContent = `${t("common.error")}: ${r.error || t("common.sendFailedGeneric")}`;
      }
    };
  }

  document.getElementById("source-modal").style.display = "flex";
}

document.getElementById("source-modal-close-btn").addEventListener("click", () => {
  document.getElementById("source-modal").style.display = "none";
});

document.getElementById("add-public-tg-btn").addEventListener("click", async () => {
  const link = document.getElementById("new-public-tg-link").value.trim();
  const resultEl = document.getElementById("add-public-tg-result");
  const btn = document.getElementById("add-public-tg-btn");
  if (!link) {
    resultEl.textContent = t("sourceModal.pasteLinkPrompt");
    return;
  }
  // Назву більше не питаємо окремим полем (план оптимізації, п.1) — бекенд сам
  // підтягує справжню назву каналу через Telegram API за username.
  btn.disabled = true;
  resultEl.textContent = t("sourceModal.checkingChannel");
  const r = await api("/api/sources/add-public-tg", { method: "POST", body: JSON.stringify({ link }) });
  btn.disabled = false;
  if (r.ok) {
    resultEl.textContent = `${t("sourceModal.addedPrefix")}: ${r.name ? escapeHtml(r.name) + " " : ""}(@${r.username})`;
    document.getElementById("new-public-tg-link").value = "";
    loadSources();
  } else {
    resultEl.textContent = `${t("common.error")}: ${r.error || t("sourceModal.addFailedDetailed")}`;
  }
});

// ---------- Налаштування ----------

async function loadSettings() {
  const res = await api("/api/me");
  if (res.error) return;
  botUsername = res.bot_username;
  document.getElementById("settings-userid").textContent = res.user_id;
  document.getElementById("settings-channels").textContent = res.channels_count;
  document.getElementById("settings-sources").textContent = res.sources_count;
  if (res.bot_name) document.getElementById("profile-header-title").textContent = res.bot_name;
  initProfileHeaderAvatar();

  if (res.is_superadmin) {
    document.getElementById("profile-dev-row").style.display = "flex";
  }
  initPushUI();
}

// ---------- Web Push (PWA) ----------
// Реально працює лише коли панель відкрита як окремий встановлений PWA у
// звичайному браузері (не всередині embedded WebView Telegram) — див.
// коментар на початку services/push.py. Тому картку показуємо ЛИШЕ якщо
// браузер підтримує Service Worker + Push API І бекенд має VAPID-ключі.

function _urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

let _pushVapidKey = null;

async function initPushUI() {
  const card = document.getElementById("push-settings-card");
  const label = document.getElementById("push-section-label");
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;

  const keyRes = await api("/api/push/vapid-public-key");
  if (!keyRes || !keyRes.ok) return;
  _pushVapidKey = keyRes.key;

  card.style.display = "block";
  label.style.display = "block";

  let registration;
  try {
    registration = await navigator.serviceWorker.register("sw.js");
  } catch (e) {
    return; // немає SW — немає й push, картку вже показали з вимкненим тумблером
  }

  const toggle = document.getElementById("push-toggle-switch");
  const extra = document.getElementById("push-extra");
  const statusEl = document.getElementById("push-status");

  const existingSub = await registration.pushManager.getSubscription();
  const isOn = !!existingSub && Notification.permission === "granted";
  toggle.classList.toggle("on", isOn);
  extra.style.display = isOn ? "block" : "none";

  toggle.onclick = async () => {
    const turningOn = !toggle.classList.contains("on");
    if (turningOn) {
      if (Notification.permission === "denied") {
        tg.showAlert(t("push.permissionDenied"));
        return;
      }
      const permission = await Notification.requestPermission();
      if (permission !== "granted") return;
      let sub;
      try {
        sub = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: _urlBase64ToUint8Array(_pushVapidKey),
        });
      } catch (e) {
        tg.showAlert(t("push.subscribeFailed"));
        return;
      }
      await api("/api/push/subscribe", { method: "POST", body: JSON.stringify({ subscription: sub.toJSON() }) });
      toggle.classList.add("on");
      extra.style.display = "block";
    } else {
      const sub = await registration.pushManager.getSubscription();
      if (sub) {
        await api("/api/push/unsubscribe", { method: "POST", body: JSON.stringify({ endpoint: sub.endpoint }) });
        await sub.unsubscribe();
      }
      toggle.classList.remove("on");
      extra.style.display = "none";
    }
  };

  document.getElementById("push-test-btn").onclick = async () => {
    statusEl.textContent = t("common.saving");
    const r = await api("/api/push/test", { method: "POST" });
    statusEl.textContent = r && r.ok ? t("push.testSent") : t("push.testFailed");
  };
}

function initProfileHeaderAvatar() {
  const box = document.getElementById("profile-header-avatar");
  if (!box) return;
  const user = tg.initDataUnsafe && tg.initDataUnsafe.user;
  const photoUrl = user && user.photo_url;
  if (photoUrl) {
    const img = document.createElement("img");
    img.src = photoUrl;
    img.alt = "";
    img.onerror = () => { box.innerHTML = ICONS.bell; };
    box.innerHTML = "";
    box.appendChild(img);
    return;
  }
  const letter = user && user.first_name ? user.first_name.charAt(0).toUpperCase() : "";
  box.innerHTML = letter ? `<span>${escapeHtml(letter)}</span>` : ICONS.bell;
}

document.getElementById("profile-dev-row").addEventListener("click", () => switchTab("dev"));
document.getElementById("dev-back-btn").addEventListener("click", () => switchTab("profile"));

async function fetchBotUsername() {
  const res = await api("/api/me");
  if (!res.error) {
    botUsername = res.bot_username;
    if (res.bot_name) {
      document.querySelector(".topbar-title").textContent = res.bot_name;
    }
    if (res.language) {
      currentLang = res.language;
      applyTranslations();
    }
    if (res.is_superadmin) {
      document.getElementById("profile-dev-row").style.display = "flex";
    }
  }
}

fetchBotUsername();
loadChannels();

// Heartbeat присутності адміна в панелі — поки застосунок відкритий, шлемо пінг
// раз на ~20 сек. Бот на своєму боці бачить, коли пінги перестають надходити
// (адмін закрив застосунок), і з певної паузи вмикає автосхвалення новин у черзі
// замість очікування ручного "Схвалити" (див. bot.py: auto_approve_when_admin_away).
function _sendPresencePing() {
  api("/api/presence/ping", { method: "POST", keepalive: true }).catch(() => {});
}
_sendPresencePing();
setInterval(_sendPresencePing, 20000);
// Повертаєшся у вкладку/розгортаєш застосунок — пінгаємо одразу, не чекаючи інтервалу.
// Троттлінг таймерів у фонових вкладках (Chrome після ~1хв бекграундуریже
// setInterval до 1 разу/хв) компенсується запасом timeout на бекенді (90с при пінгу
// раз на 20с — до 4 пропущених пінгів), а не тільки цим слухачем.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") _sendPresencePing();
});
window.addEventListener("focus", _sendPresencePing);

// ---------- Редакція (Джерела + Читачі) ----------

let currentEditorialSource = "feed";
const currentModStatus = "new"; // читацькі предложки в Редакції показуємо лише нові (актуальні)

function loadEditorialSegment() {
  document.getElementById("queue-list").style.display = currentEditorialSource === "feed" ? "" : "none";
  document.getElementById("submissions-list").style.display = currentEditorialSource === "readers" ? "" : "none";
  if (currentEditorialSource === "feed") loadQueue();
  else loadSubmissions(currentModStatus);
}

document.getElementById("editorial-segmented").addEventListener("click", (e) => {
  const btn = e.target.closest(".segment");
  if (!btn) return;
  document.querySelectorAll("#editorial-segmented .segment").forEach((s) => s.classList.remove("active"));
  btn.classList.add("active");
  currentEditorialSource = btn.dataset.source;
  loadEditorialSegment();
});

function _typeLabel(type) {
  const map = { text: "type.text", photo: "type.photo", video: "type.video", location: "type.location", album: "type.album" };
  return map[type] ? t(map[type]) : type;
}

async function loadMediaInto(imgOrVideoEl, submissionId, index = null) {
  try {
    const url = index !== null
      ? `/api/submission-media/${submissionId}?index=${index}`
      : `/api/submission-media/${submissionId}`;
    const res = await fetch(url, {
      headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
    });
    if (!res.ok) {
      let detail = "";
      try { detail = (await res.json()).error || ""; } catch (e) {}
      return { url: null, error: `HTTP ${res.status}${detail ? " — " + detail : ""}` };
    }
    const blob = await res.blob();
    if (blob.size === 0) return { url: null, error: t("editor.emptyFile") };
    const objUrl = URL.createObjectURL(blob);
    if (imgOrVideoEl) {
      imgOrVideoEl.src = objUrl;
      // Деякі мобільні WebView (зокрема всередині Telegram) не малюють кадр-прев'ю
      // відео, поки не почалось відтворення, — лишається суцільний чорний
      // прямокутник замість кадру. Явний seek на майже нульовий момент часу
      // після завантаження метаданих примушує браузер відрендерити цей кадр.
      if (imgOrVideoEl.tagName === "VIDEO") {
        imgOrVideoEl.addEventListener("loadedmetadata", () => {
          try { imgOrVideoEl.currentTime = 0.01; } catch (e) {}
        }, { once: true });
      }
    }
    return { url: objUrl, error: null };
  } catch (e) {
    return { url: null, error: e.message || t("common.networkError") };
  }
}

function stripHtml(str) {
  return (str || "").replace(/<[^>]*>/g, "");
}

/** п.4.1 ТЗ: декодування HTML-сутностей (&#x27; тощо) ПЕРЕД виведенням у полях
 * редагування чи будь-де в UI. Реалізовано чистим регулярним виразом (без
 * DOM-трюку через detached <textarea>) — так надійніше в різних WebView-рушіях,
 * якими Telegram відкриває Mini Apps, і функція гарантовано ніколи не кидає
 * виняток, навіть на "кривому" чи вже частково розекранованому вхідному рядку. */
function decodeHtmlEntities(str) {
  if (!str) return str;
  const named = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
  return String(str).replace(/&(#x[0-9a-fA-F]+|#[0-9]+|[a-zA-Z]+);/g, (match, entity) => {
    try {
      if (entity[0] === "#") {
        const code = (entity[1] === "x" || entity[1] === "X")
          ? parseInt(entity.slice(2), 16)
          : parseInt(entity.slice(1), 10);
        return Number.isFinite(code) ? String.fromCodePoint(code) : match;
      }
      return Object.prototype.hasOwnProperty.call(named, entity) ? named[entity] : match;
    } catch (e) {
      return match; // будь-яка аномалія в коді сутності — просто лишаємо як є, а не падаємо
    }
  });
}

function escapeHtml(str) {
  try {
    return decodeHtmlEntities(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  } catch (e) {
    // Захист від регресії на кшталт тієї, що ламала всі списки одразу (Головна/
    // Джерела/Редакція): будь-яка несподівана помилка тут НЕ повинна валити весь
    // цикл рендеру списку — краще показати сирий текст без екранування спецсимволів,
    // ніж лишити список порожнім.
    return String(str || "");
  }
}

async function loadThumbInto(wrapEl, submissionId, index = null) {
  if (!wrapEl) return;
  const result = await loadMediaInto(null, submissionId, index);
  if (result.url) {
    wrapEl.innerHTML = `<img src="${result.url}" alt="" />`;
  }
  // якщо не вдалося — залишаємо дефолтну іконку, без порожньої рамки
}

function shortTitle(it) {
  const source = it.type === "text" ? it.content : (it.caption || "");
  const clean = escapeHtml(stripHtml(source));
  if (!clean) return _typeLabel(it.type);
  return clean.length > 48 ? clean.slice(0, 48) + "…" : clean;
}

let activeChannelsCache = [];
let currentEditingItem = null;
let currentEditingKind = "submission"; // "submission" | "queue" — який ендпоінт дергати при збереженні

async function loadSubmissions(status) {
  const list = document.getElementById("submissions-list");
  const items = await api(`/api/submissions?status=${status}`);

  if (items.error) {
    list.innerHTML = `<div class="card-row muted">${t("common.noAccess")}</div>`;
    return;
  }

  const channelsRes = await api("/api/channels");
  activeChannelsCache = Array.isArray(channelsRes) ? channelsRes.filter((c) => c.status !== "inactive") : [];

  if (!items.length) {
    list.innerHTML = `<div class="card-row muted">${t("submissions.empty")}</div>`;
    return;
  }

  list.innerHTML = "";
  for (const it of items) {
    const row = document.createElement("div");
    row.className = "channel-card";

    const thumbHtml = ICONS.channelDefault;

    const publishedIds = it.published_channel_ids || [];
    const publishedNote = publishedIds.length
      ? publishedIds.map((id) => activeChannelsCache.find((c) => c.id === id)?.title || id).join(", ")
      : null;
    const targetChannelTitle = it.target_channel_id
      ? (activeChannelsCache.find((c) => c.id === it.target_channel_id)?.title || `${t("submissions.channelFallback")} ${it.target_channel_id}`)
      : t("submissions.unknownChannel");

    row.innerHTML = `
      <div class="submission-summary">
        <div class="submission-thumb" data-role="thumb-wrap">${thumbHtml}</div>
        <div class="submission-summary-body">
          <div class="submission-title">${shortTitle(it)} <span class="status-badge ${status === "new" ? "pending" : "approved"}">${status === "new" ? t("queue.statusPending") : t("queue.statusApproved")}</span>${it.scam_suspected ? `<span class="status-badge" style="color:var(--danger,#ef4444);background:rgba(239,68,68,0.12);" title="${t("submissions.scamWarningTitle")}">⚠️ ${t("submissions.scamWarning")}</span>` : ""}</div>
          <div class="submission-meta">${escapeHtml(it.author_name) || t("submissions.anonymous")} · ${_typeLabel(it.type)} · ${it.created_at}</div>
          <div class="muted">${t("submissions.forChannel")}: ${escapeHtml(targetChannelTitle)}</div>
          ${publishedNote ? `<div class="muted">${t("submissions.publishedIn")}: ${escapeHtml(publishedNote)}</div>` : ""}
        </div>
        <svg class="icon submission-chevron" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>
      </div>
    `;

    if (it.type === "photo" || it.type === "video") {
      loadThumbInto(row.querySelector('[data-role="thumb-wrap"]'), it.id);
    } else if (it.type === "album") {
      loadThumbInto(row.querySelector('[data-role="thumb-wrap"]'), it.id, 0);
    }

    row.querySelector(".submission-summary").addEventListener("click", () => openEditPostModal(it, status));
    list.appendChild(row);
  }
}

// ---------- Повноекранний редактор ----------

const modal = document.getElementById("editor-modal");
const editorTextarea = document.getElementById("editor-textarea");
const editorMediaBlock = document.getElementById("editor-media-block");
const editorChannelMultiselect = document.getElementById("editor-channel-multiselect");

let watermarkEnabled = false;
let watermarkImageEl = null; // <img> з оригінальним фото, з якого малюємо canvas
let queueEditWatermarkOn = true; // стан тумблера водяного знаку для kind="queue" (сервер накладає сам, без canvas-прев'ю)
let selectedChannelIds = []; // масив id каналів, обраних для публікації (може бути кілька)

function currentChannelLabel() {
  // Для водяного знаку беремо перший обраний канал (водяний знак поки одна картинка на всіх)
  if (!selectedChannelIds.length) return "@channel";
  const ch = activeChannelsCache.find((c) => c.id === selectedChannelIds[0]);
  return (ch && ch.footer_text) ? ch.footer_text : (ch ? ch.title : "@channel");
}

function renderChannelMultiselect() {
  editorChannelMultiselect.innerHTML = "";
  for (const c of activeChannelsCache) {
    const checked = selectedChannelIds.includes(c.id);
    const chip = document.createElement("div");
    chip.className = "channel-chip" + (checked ? " checked" : "");
    chip.innerHTML = `
      <span class="channel-chip-avatar" data-role="avatar">${ICONS.channelDefault}</span>
      <span>${escapeHtml(c.title)}</span>
      <span class="channel-chip-check">${checked ? ICONS.check : ""}</span>
    `;
    loadAvatarFromUrlInto(chip.querySelector('[data-role="avatar"]'), `/api/channel-avatar/${c.id}`, c.title);
    chip.onclick = () => {
      const idx = selectedChannelIds.indexOf(c.id);
      if (idx >= 0) selectedChannelIds.splice(idx, 1);
      else selectedChannelIds.push(c.id);
      renderChannelMultiselect();
      redrawWatermarkCanvas();
    };
    editorChannelMultiselect.appendChild(chip);
  }
}

document.getElementById("editor-select-all-channels").addEventListener("click", () => {
  selectedChannelIds = activeChannelsCache.map((c) => c.id);
  renderChannelMultiselect();
  redrawWatermarkCanvas();
});
document.getElementById("editor-deselect-all-channels").addEventListener("click", () => {
  selectedChannelIds = [];
  renderChannelMultiselect();
  redrawWatermarkCanvas();
});

// ---------- WYSIWYG-редактор (contenteditable) ----------
// Поле редактора тепер показує СПРАВЖНЄ форматування (жирний/курсив/спойлер) одразу
// під час друку, а не сирі <b>/<i> теги. editorGetHTML()/editorSetHTML() — єдина
// точка конвертації між тим, що реально лежить у DOM contenteditable-поля, і
// Telegram-сумісним HTML-рядком, який очікує бекенд (той самий формат, що й раніше
// зберігався в item.text).
const _EDITOR_TAG_MAP = { B: "b", STRONG: "b", I: "i", EM: "i", U: "u", S: "s", STRIKE: "s", DEL: "s", CODE: "code" };

function _escapeEditorText(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function serializeEditorContent(root) {
  function walk(node) {
    if (node.nodeType === Node.TEXT_NODE) return _escapeEditorText(node.textContent);
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const tag = node.tagName;
    const inner = () => Array.from(node.childNodes).map(walk).join("");
    if (tag === "BR") return "\n";
    // Перенос СТАВИМО ПЕРЕД вмістом блоку, а не після — саме так контент, що йде
    // прямо ПЕРЕД цим div (наприклад, голий текстовий вузол без жодного тега —
    // типова структура Chrome для першого рядка перед натисканням Enter), не
    // склеюється з наступним рядком в одне слово без розриву.
    if (tag === "DIV" || tag === "P") return "\n" + inner();
    if (tag === "A") {
      const href = node.getAttribute("href") || "";
      return href ? `<a href="${_escapeEditorText(href)}">${inner()}</a>` : inner();
    }
    if (tag === "TG-SPOILER") return `<tg-spoiler>${inner()}</tg-spoiler>`;
    if (tag === "TG-EMOJI") {
      const emojiId = node.getAttribute("emoji-id") || "";
      return emojiId ? `<tg-emoji emoji-id="${_escapeEditorText(emojiId)}">${inner()}</tg-emoji>` : inner();
    }
    if (_EDITOR_TAG_MAP[tag]) {
      const t = _EDITOR_TAG_MAP[tag];
      return `<${t}>${inner()}</${t}>`;
    }
    // Невідомий тег (span зі стилями після вставки тощо) — знімаємо обгортку,
    // лишаємо тільки вміст: той самий захисний підхід, що й на бекенді для
    // чужого HTML зі скрапнутих джерел.
    return inner();
  }
  return Array.from(root.childNodes).map(walk).join("").replace(/\n{3,}/g, "\n\n");
}

function editorGetHTML() {
  return serializeEditorContent(editorTextarea).trim();
}

function editorSetHTML(html) {
  editorTextarea.innerHTML = (html || "").replace(/\n/g, "<br>");
}

// Для повного прев'ю (кнопка "Перегляд") — той самий рядок, що піде на сервер,
// але з \n назад у <br> для показу як реального HTML.
function renderTgPreview(html) {
  return html.replace(/\n/g, "<br>");
}

function updateEditorCharCounter() {
  const counter = document.getElementById("editor-char-counter");
  if (!counter) return;
  const hasMedia = currentEditingItem && (
    currentEditingKind === "queue" ? (currentEditingItem.media_count || 0) > 0 : currentEditingItem.type !== "text"
  );
  const limit = hasMedia ? 1024 : 4096;
  // textContent, а не HTML-рядок з тегами — рахуємо ТІЛЬКИ видимі символи,
  // так само, як це робить сам Telegram (розмітка в ліміт не входить).
  const len = editorTextarea.textContent.length;
  counter.textContent = `${len} / ${limit}`;
  counter.classList.toggle("over-limit", len > limit);
}

editorTextarea.addEventListener("input", updateEditorCharCounter);

function buildTgPreviewGallery() {
  const mediaEls = Array.from(document.querySelectorAll("#editor-media-preview img[src], #editor-media-preview video[src]"));
  if (!mediaEls.length) return "";
  const n = Math.min(mediaEls.length, 10);
  const gridClass = n === 1 ? "tg-preview-gallery-1" : n === 2 ? "tg-preview-gallery-2" : n === 3 ? "tg-preview-gallery-3" : "tg-preview-gallery-grid";
  const items = mediaEls.slice(0, n).map((el) => {
    if (el.tagName === "VIDEO") {
      return `<div class="tg-preview-item"><video src="${el.src}" controls></video></div>`;
    }
    return `<div class="tg-preview-item"><img src="${el.src}" /></div>`;
  }).join("");
  return `<div class="tg-preview-gallery ${gridClass}">${items}</div>`;
}

/** п.4.2 ТЗ: те саме, що buildTgPreviewGallery, але з реально накладеним
 * водяним знаком — тим самим логотипом, прозорістю, масштабом і мультипозиціями,
 * що збережені для каналу, — щоб прев'ю відповідало фінальному вигляду поста
 * в каналі, а не просто показувало сирі завантажені файли. */
async function buildFullTgPreviewGallery() {
  const mediaEls = Array.from(document.querySelectorAll("#editor-media-preview img[src], #editor-media-preview video[src]"));
  if (!mediaEls.length) return "";

  const targetChannelId = selectedChannelIds[0];
  const watermarkAllowedForItem = currentEditingKind !== "queue" || queueEditWatermarkOn;
  let wmImg = null;
  let wmSettings = null;

  if (targetChannelId && watermarkAllowedForItem) {
    try {
      const status = await api(`/api/channels/watermark/${targetChannelId}`);
      if (status && status.has_watermark && status.auto_watermark) {
        wmSettings = await api(`/api/channels/watermark/settings?id=${targetChannelId}`);
        // Звичайний img.src= тут не працює: цей ендпоінт вимагає X-Init-Data (роль
        // editor+ на каналі), а <img> не вміє слати кастомні заголовки — запит завжди
        // йшов без авторизації і сервер тихо відповідав 403 (водяний знак у прев'ю
        // просто не з'являвся, без жодної помилки на екрані). Тягнемо байти через
        // fetch() з тим самим заголовком, що й решта захищених картинок у панелі.
        const res = await fetch(`/api/channels/watermark/image/${targetChannelId}?t=${Date.now()}`, {
          headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
        });
        if (res.ok) {
          const blob = await res.blob();
          const objUrl = URL.createObjectURL(blob);
          wmImg = await new Promise((resolve) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = () => resolve(null);
            img.src = objUrl;
          });
        }
      }
    } catch (e) {
      wmImg = null;
    }
  }

  const n = Math.min(mediaEls.length, 10);
  const gridClass = n === 1 ? "tg-preview-gallery-1" : n === 2 ? "tg-preview-gallery-2" : n === 3 ? "tg-preview-gallery-3" : "tg-preview-gallery-grid";
  const items = mediaEls.slice(0, n).map((el) => {
    if (el.tagName === "VIDEO") {
      // Відео так само штампується на сервері (окремою логікою поверх кадрів), але
      // накладати водяний знак на відео в браузері живим прев'ю нема сенсу — тут
      // просто показуємо сам ролик, як у Telegram-бабблі.
      return `<div class="tg-preview-item"><video src="${el.src}" controls></video></div>`;
    }
    const dataUrl = wmImg ? _renderWatermarkedImageDataUrl(el, wmImg, wmSettings || {}) : null;
    return `<div class="tg-preview-item"><img src="${dataUrl || el.src}" /></div>`;
  }).join("");
  return `<div class="tg-preview-gallery ${gridClass}">${items}</div>`;
}

function _renderWatermarkedImageDataUrl(imgEl, wmImg, settings) {
  try {
    const canvas = document.createElement("canvas");
    canvas.width = imgEl.naturalWidth || imgEl.width || 800;
    canvas.height = imgEl.naturalHeight || imgEl.height || 600;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(imgEl, 0, 0, canvas.width, canvas.height);

    const opacity = (settings.opacity != null ? settings.opacity : 50) / 100;
    const scale = (settings.scale != null ? settings.scale : 40) / 100;
    const positions = (settings.positions && settings.positions.length) ? settings.positions : ["center"];
    const targetW = canvas.width * scale;
    const ratio = targetW / wmImg.width;
    const targetH = wmImg.height * ratio;
    const margin = canvas.width * 0.04;

    ctx.globalAlpha = opacity;
    for (const pos of positions) {
      let x, y;
      if (pos === "top-left") { x = margin; y = margin; }
      else if (pos === "top-right") { x = canvas.width - targetW - margin; y = margin; }
      else if (pos === "bottom-left") { x = margin; y = canvas.height - targetH - margin; }
      else if (pos === "bottom-right") { x = canvas.width - targetW - margin; y = canvas.height - targetH - margin; }
      else { x = (canvas.width - targetW) / 2; y = (canvas.height - targetH) / 2; }
      ctx.drawImage(wmImg, x, y, targetW, targetH);
    }
    ctx.globalAlpha = 1;
    return canvas.toDataURL("image/png");
  } catch (e) {
    return null; // напр. canvas "заплямований" через CORS на картинці — показуємо оригінал без знаку
  }
}

/** п.4.2 ТЗ: футер повідомлення (брендування/підпис) — так само, як він реально
 * додається сервером при публікації, щоб прев'ю не забувало цей блок. */
function buildTgPreviewFooter() {
  const footerOn = document.getElementById("footer-switch").dataset.on === "true";
  if (!footerOn || !selectedChannelIds.length) return "";
  const ch = activeChannelsCache.find((c) => c.id === selectedChannelIds[0]);
  if (!ch) return "";
  const label = escapeHtml((ch.footer_text || ch.title || "").trim());
  const parts = [ch.footer_link ? `<a href="${ch.footer_link}">${label}</a>` : label];
  if (ch.submit_link) parts.push(`<a href="${ch.submit_link}">${t("editor.submitLink")}</a>`);
  return `<div class="tg-preview-footer">${parts.join(" | ")}</div>`;
}

function redrawWatermarkCanvas() {
  const canvas = document.getElementById("wm-canvas");
  if (!canvas || !watermarkImageEl) return;
  const ctx = canvas.getContext("2d");
  canvas.width = watermarkImageEl.naturalWidth;
  canvas.height = watermarkImageEl.naturalHeight;
  ctx.drawImage(watermarkImageEl, 0, 0);

  if (watermarkEnabled) {
    const label = currentChannelLabel();
    const fontSize = Math.max(18, Math.round(canvas.width * 0.035));
    ctx.font = `700 ${fontSize}px Inter, sans-serif`;
    const paddingX = fontSize * 0.8;
    const paddingY = fontSize * 0.6;
    const textWidth = ctx.measureText(label).width;
    const boxW = textWidth + paddingX * 2;
    const boxH = fontSize + paddingY * 2;
    const x = canvas.width - boxW - fontSize * 0.6;
    const y = canvas.height - boxH - fontSize * 0.6;

    ctx.fillStyle = "rgba(0,0,0,0.45)";
    ctx.fillRect(x, y, boxW, boxH);
    ctx.fillStyle = "#ffffff";
    ctx.textBaseline = "middle";
    ctx.fillText(label, x + paddingX, y + boxH / 2);
  }
}

function renderMediaPreview(item, kind = "submission") {
  const container = document.getElementById("editor-media-preview");
  container.innerHTML = "";
  watermarkImageEl = null;
  watermarkEnabled = false;

  if (kind === "queue") {
    renderQueueMediaPreview(item);
    return;
  }

  if (item.type === "photo") {
    const card = document.createElement("div");
    card.className = "media-preview-card";
    card.innerHTML = `
      <div class="media-preview-canvas-wrap"><canvas id="wm-canvas"></canvas></div>
      <div class="media-preview-controls">
        <label class="watermark-toggle">
          <span class="watermark-switch" id="wm-switch"></span>
          <span>${ICONS.droplet} ${t("editor.applyWatermark")}</span>
        </label>
      </div>
    `;
    container.appendChild(card);

    loadMediaInto(null, item.id).then((result) => {
      if (!result.url) {
        card.querySelector(".media-preview-canvas-wrap").innerHTML =
          `<div class="hint-banner" style="margin:12px;">${t("editor.photoLoadFailed")}: ${escapeHtml(result.error || t("common.unknownErrorFull"))}</div>`;
        return;
      }
      const img = new Image();
      img.onload = () => {
        watermarkImageEl = img;
        redrawWatermarkCanvas();
      };
      img.onerror = () => {
        card.querySelector(".media-preview-canvas-wrap").innerHTML =
          `<div class="hint-banner" style="margin:12px;">${t("editor.notValidImage")}</div>`;
      };
      img.src = result.url;
    });

    document.getElementById("wm-switch").onclick = () => {
      watermarkEnabled = !watermarkEnabled;
      document.getElementById("wm-switch").classList.toggle("on", watermarkEnabled);
      redrawWatermarkCanvas();
    };
  } else if (item.type === "video") {
    const card = document.createElement("div");
    card.className = "media-preview-card";
    card.innerHTML = `<div class="media-preview-canvas-wrap"><video controls muted playsinline preload="metadata" data-role="video-preview"></video></div>`;
    container.appendChild(card);
    loadMediaInto(card.querySelector("video"), item.id).then((result) => {
      if (!result.url) {
        card.querySelector(".media-preview-canvas-wrap").innerHTML =
          `<div class="hint-banner" style="margin:12px;">${t("editor.videoLoadFailed")}: ${escapeHtml(result.error || t("common.unknownErrorFull"))}</div>`;
      }
    });
  } else if (item.type === "album") {
    const card = document.createElement("div");
    card.className = "media-preview-card";
    card.innerHTML = `
      <div class="album-gallery" id="album-gallery"></div>
      <div class="media-preview-controls">
        <label class="watermark-toggle disabled" title="${t("editor.watermarkAlbumsUnsupported")}">
          <span class="watermark-switch" aria-disabled="true"></span>
          <span>${ICONS.droplet} ${t("editor.applyWatermark")}</span>
          <span class="soon-badge" title="${t("editor.watermarkAlbumsUnsupported")}">ⓘ</span>
        </label>
      </div>
    `;
    container.appendChild(card);

    const gallery = card.querySelector("#album-gallery");
    const albumBadge = document.createElement("div");
    albumBadge.className = "album-badge";
    albumBadge.textContent = `${t("type.album")} (${item.content.length}/10)`;
    gallery.style.position = "relative";
    gallery.appendChild(albumBadge);

    item.content.forEach((mediaItem, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "album-thumb";

      const mediaEl = document.createElement(mediaItem.type === "video" ? "video" : "img");
      if (mediaItem.type === "video") {
        mediaEl.controls = true;
        mediaEl.muted = true;
        mediaEl.playsInline = true;
        mediaEl.preload = "metadata";
      }
      wrap.appendChild(mediaEl);

      const typeBadge = document.createElement("div");
      typeBadge.className = "album-type-badge";
      typeBadge.innerHTML = mediaItem.type === "video" ? ICONS.video : ICONS.image;
      wrap.appendChild(typeBadge);

      const removeBtn = document.createElement("button");
      removeBtn.className = "album-thumb-remove";
      removeBtn.innerHTML = `<svg class="icon-sm" viewBox="0 0 24 24" style="width:14px;height:14px;stroke:#fff;fill:none;stroke-width:2.5;"><path d="M18 6 6 18M6 6l12 12"/></svg>`;
      wrap.appendChild(removeBtn);

      loadMediaInto(mediaEl, item.id, idx).then((result) => {
        if (!result.url) {
          mediaEl.replaceWith(Object.assign(document.createElement("div"), {
            className: "album-thumb-error",
            textContent: result.error || t("common.error"),
          }));
        }
      });

      removeBtn.onclick = async () => {
        if (item.content.length <= 1) {
          tg.showAlert(t("editor.albumMinOneFile"));
          return;
        }
        const r = await api("/api/submissions/remove-album-item", {
          method: "POST",
          body: JSON.stringify({ id: item.id, index: idx }),
        });
        if (r.ok) {
          item.content = r.item.content;
          renderMediaPreview(item);
        } else {
          tg.showAlert(`${t("common.error")}: ${r.error || t("queue.deleteFailed")}`);
        }
      };

      gallery.appendChild(wrap);
    });
  }
}

async function refreshQueueItem(id) {
  const items = await api("/api/queue");
  return Array.isArray(items) ? items.find((it) => it.id === id) : null;
}

function renderQueueMediaPreview(item) {
  const container = document.getElementById("editor-media-preview");
  const count = item.media_count || 0;
  const types = item.media_types || [];

  const tiles = types.map((mkind, i) => {
    const tag = mkind === "video"
      ? `<video data-media-index="${i}" controls muted playsinline preload="metadata"></video>`
      : `<img data-media-index="${i}" />`;
    return `<div class="album-thumb">
      ${tag}
      <div class="album-type-badge">${mkind === "video" ? ICONS.video : ICONS.image}</div>
      <button class="album-thumb-remove" data-remove-index="${i}"><svg class="icon-sm" viewBox="0 0 24 24" style="width:14px;height:14px;stroke:#fff;fill:none;stroke-width:2.5;"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
    </div>`;
  }).join("");

  const addTile = `
    <label class="album-thumb album-thumb-add" style="display:flex;align-items:center;justify-content:center;cursor:pointer;border:2px dashed rgba(255,255,255,0.25);">
      <span style="font-size:32px;line-height:1;color:rgba(255,255,255,0.6);">+</span>
      <input type="file" accept="image/*,video/*" data-role="queue-add-media-input" style="display:none;" />
    </label>
  `;

  const card = document.createElement("div");
  card.className = "media-preview-card";
  card.innerHTML = `
    <div class="album-gallery" id="queue-album-gallery" style="position:relative;">
      ${count > 1 ? `<div class="album-badge">${t("type.album")} (${count}/10)</div>` : ""}
      ${tiles}${addTile}
    </div>
    ${count > 0 ? `
    <div class="media-preview-controls">
      <label class="watermark-toggle">
        <span class="watermark-switch ${item.skip_watermark ? "" : "on"}" data-role="queue-watermark-switch"></span>
        <span>${ICONS.droplet} ${t("editor.applyWatermark")}</span>
      </label>
    </div>` : ""}
  `;
  container.appendChild(card);

  queueEditWatermarkOn = !item.skip_watermark;
  const wmSwitch = card.querySelector('[data-role="queue-watermark-switch"]');
  if (wmSwitch) {
    wmSwitch.onclick = () => {
      queueEditWatermarkOn = !queueEditWatermarkOn;
      wmSwitch.classList.toggle("on", queueEditWatermarkOn);
    };
  }

  types.forEach((mkind, idx) => {
    const el = card.querySelector(`[data-media-index="${idx}"]`);
    loadQueueMediaInto(el, item.id, idx).then((result) => {
      if (!result.url) {
        el.replaceWith(Object.assign(document.createElement("div"), { className: "album-thumb-error", textContent: result.error || t("common.error") }));
        return;
      }
      if (mkind !== "video") el.parentElement.onclick = () => openMediaLightbox(result.url, mkind);
    });
  });

  card.querySelectorAll('[data-remove-index]').forEach((btn) => {
    btn.onclick = async (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.removeIndex, 10);
      const r = await api("/api/queue/remove-media", { method: "POST", body: JSON.stringify({ id: item.id, index: idx }) });
      if (!r.ok) { tg.showAlert(`${t("common.error")}: ${r.error || t("queue.deleteFailed")}`); return; }
      const fresh = await refreshQueueItem(item.id);
      if (fresh) openEditPostModal(fresh, "queue");
      loadQueue();
    };
  });

  const addInput = card.querySelector('[data-role="queue-add-media-input"]');
  addInput.onchange = async () => {
    const file = addInput.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("id", item.id);
    form.append("file", file);
    const res = await fetch("/api/queue/add-media", {
      method: "POST",
      headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
      body: form,
    });
    const r = await res.json();
    if (!r.ok) { tg.showAlert(`${t("common.error")}: ${r.error || t("editor.addFileFailed")}`); return; }
    const fresh = await refreshQueueItem(item.id);
    if (fresh) openEditPostModal(fresh, "queue");
    loadQueue();
  };
}

let editLockHeartbeatTimer = null;

function stopEditLockHeartbeat() {
  if (editLockHeartbeatTimer) { clearInterval(editLockHeartbeatTimer); editLockHeartbeatTimer = null; }
}

// Проста pessimistic-блокування (не realtime-merge, як у Google Docs): хто
// відкрив пост першим — той редагує, решта бачать банер і не можуть зберегти.
async function acquireEditLock(kind, id) {
  stopEditLockHeartbeat();
  const banner = document.getElementById("editor-lock-banner");
  const publishBtn = document.getElementById("editor-publish-btn");
  const rejectBtn = document.getElementById("editor-reject-btn");
  const user = tg.initDataUnsafe && tg.initDataUnsafe.user;
  const adminName = (user && user.first_name) || "";
  const r = await api("/api/edit-lock/acquire", { method: "POST", body: JSON.stringify({ kind, id, admin_name: adminName }) });
  if (r && r.ok === false && r.locked_by) {
    banner.textContent = `${t("editor.lockedByPrefix")} ${r.locked_by.admin_name || t("editor.lockedByUnknown")}`;
    banner.style.display = "block";
    publishBtn.disabled = true;
    rejectBtn.disabled = true;
    return;
  }
  banner.style.display = "none";
  publishBtn.disabled = false;
  rejectBtn.disabled = false;
  editLockHeartbeatTimer = setInterval(() => {
    api("/api/edit-lock/heartbeat", { method: "POST", body: JSON.stringify({ kind, id }) });
  }, 20000);
}

function releaseEditLock() {
  stopEditLockHeartbeat();
  if (currentEditingItem && currentEditingKind) {
    api("/api/edit-lock/release", { method: "POST", body: JSON.stringify({ kind: currentEditingKind, id: currentEditingItem.id }) });
  }
  const banner = document.getElementById("editor-lock-banner");
  if (banner) banner.style.display = "none";
  const publishBtn = document.getElementById("editor-publish-btn");
  const rejectBtn = document.getElementById("editor-reject-btn");
  if (publishBtn) publishBtn.disabled = false;
  if (rejectBtn) rejectBtn.disabled = false;
}

async function openEditPostModal(item, statusOrKind) {
  const kind = statusOrKind === "queue" ? "queue" : "submission";
  currentEditingItem = item;
  currentEditingKind = kind;
  acquireEditLock(kind, item.id);

  editorMediaBlock.innerHTML = "";
  if (kind === "submission" && item.type === "location") {
    editorMediaBlock.innerHTML = `<div class="hint-banner">${ICONS.location} ${t("editor.coordinates")}: ${item.content}</div>`;
  }
  renderMediaPreview(item, kind);

  if (kind === "queue") {
    editorSetHTML(item.text || "");
  } else {
    editorSetHTML(item.type === "text" ? item.content : (item.caption || ""));
  }
  editorTextarea.style.display = (kind === "submission" && item.type === "location") ? "none" : "block";
  updateEditorCharCounter();

  const isSubmissionNew = kind === "submission" && statusOrKind === "new";
  const showFullUI = kind === "queue" || isSubmissionNew;

  document.getElementById("editor-channel-card").style.display = showFullUI ? "block" : "none";
  selectedChannelIds = kind === "queue"
    ? (item.channel_ids || []).slice()
    : (isSubmissionNew ? (item.published_channel_ids || []).slice() : []);
  if (showFullUI) renderChannelMultiselect();

  // Планування (POST /api/schedule) підтримує лише текстові пости без медіа —
  // для постів із фото/відео/альбомом тумблер ховаємо, а не обіцяємо те, чого не вміємо.
  const itemHasMedia = kind === "queue" ? (item.media_count || 0) > 0 : item.type !== "text";
  const scheduleSupported = showFullUI && !itemHasMedia;
  const scheduleRow = document.getElementById("editor-schedule-row");
  const scheduleDatetimeRow = document.getElementById("editor-schedule-datetime-row");
  const scheduleSwitch = document.getElementById("schedule-switch");
  const scheduleDatetimeInput = document.getElementById("editor-schedule-datetime");
  scheduleRow.style.display = scheduleSupported ? "flex" : "none";
  scheduleRow.classList.toggle("disabled", !scheduleSupported);
  scheduleRow.title = scheduleSupported ? "" : t("editor.scheduleMediaUnsupported");
  scheduleSwitch.classList.remove("on");
  scheduleSwitch.dataset.on = "false";
  scheduleDatetimeRow.style.display = "none";
  const now = new Date(Date.now() + 10 * 60000 - new Date().getTimezoneOffset() * 60000);
  scheduleDatetimeInput.value = now.toISOString().slice(0, 16);
  scheduleSwitch.onclick = () => {
    if (!scheduleSupported) return;
    const on = scheduleSwitch.dataset.on !== "true";
    scheduleSwitch.dataset.on = on ? "true" : "false";
    scheduleSwitch.classList.toggle("on", on);
    scheduleDatetimeRow.style.display = on ? "block" : "none";
  };

  document.querySelector("#editor-modal .toolbar").style.display = showFullUI ? "flex" : "none";
  document.getElementById("templates-bar").style.display = showFullUI ? "flex" : "none";

  const footerSwitch = document.getElementById("footer-switch");
  const footerOn = kind === "queue" ? (item.append_footer !== false) : false;
  footerSwitch.classList.toggle("on", footerOn);
  footerSwitch.dataset.on = footerOn ? "true" : "false";
  footerSwitch.onclick = () => {
    const on = footerSwitch.dataset.on !== "true";
    footerSwitch.dataset.on = on ? "true" : "false";
    footerSwitch.classList.toggle("on", on);
  };
  footerSwitch.parentElement.style.display = showFullUI ? "flex" : "none";

  const publishBtn = document.getElementById("editor-publish-btn");
  const publishLabel = publishBtn.querySelector("span");
  const rejectBtn = document.getElementById("editor-reject-btn");
  // viewer_role приходить з /api/queue та /api/submissions — ховаємо дії, на які
  // в поточного глядача бракує ролі (queue: Зберегти/Видалити — editor+;
  // submissions: Схвалити/Відхилити — moderator+), а не просто показуємо всім.
  if (kind === "queue") {
    const canEditItem = item.viewer_role === "owner" || item.viewer_role === "editor";
    publishLabel.textContent = t("common.save");
    publishBtn.style.display = canEditItem ? "flex" : "none";
    rejectBtn.title = t("common.delete");
    rejectBtn.style.display = canEditItem ? "flex" : "none";
  } else {
    const canModerateItem = item.viewer_role === "owner" || item.viewer_role === "editor" || item.viewer_role === "moderator";
    publishLabel.textContent = t("editor.publishBtn");
    publishBtn.style.display = (isSubmissionNew && canModerateItem) ? "flex" : "none";
    rejectBtn.title = t("editor.rejectBtn");
    rejectBtn.style.display = (isSubmissionNew && canModerateItem) ? "flex" : "none";
  }

  if (showFullUI) await loadTemplatesBar();
  modal.style.display = "flex";
}

document.getElementById("editor-close-btn").addEventListener("click", () => {
  releaseEditLock();
  modal.style.display = "none";
  currentEditingItem = null;
});

document.querySelectorAll(".tb-btn[data-tag]").forEach((btn) => {
  // preventDefault на mousedown — інакше клік по кнопці панелі забирає фокус (а з
  // ним і виділення тексту) з поля РАНІШЕ, ніж встигне спрацювати click і застосувати
  // форматування саме до виділеного фрагмента.
  btn.addEventListener("mousedown", (e) => e.preventDefault());
  btn.addEventListener("click", () => {
    const tag = btn.dataset.tag;
    const sel = window.getSelection();
    const selectedText = (sel && sel.toString()) || t("editor.defaultTextWord");
    document.execCommand("insertHTML", false, `<${tag}>${_escapeEditorText(selectedText)}</${tag}>`);
    updateEditorCharCounter();
  });
});

document.querySelector('.tb-btn[data-action="link"]').addEventListener("mousedown", (e) => e.preventDefault());
document.querySelector('.tb-btn[data-action="link"]').addEventListener("click", () => {
  const url = prompt(t("editor.pasteLinkPrompt"));
  if (!url) return;
  const sel = window.getSelection();
  const selectedText = (sel && sel.toString()) || t("editor.defaultLinkWord");
  document.execCommand("insertHTML", false, `<a href="${_escapeEditorText(url)}">${_escapeEditorText(selectedText)}</a>`);
  updateEditorCharCounter();
});

document.querySelector('.tb-btn[data-action="emoji"]').addEventListener("click", () => {
  toggleEmojiPicker(document.getElementById("editor-emoji-picker-container"), editorTextarea);
});
document.querySelector('.tb-btn[data-action="custom-emoji"]').addEventListener("click", () => {
  toggleCustomEmojiPicker(document.getElementById("editor-custom-emoji-picker-container"), editorTextarea);
});

const aiStyleSegmented = document.getElementById("editor-ai-style-segmented");
aiStyleSegmented.addEventListener("click", (e) => {
  const seg = e.target.closest(".segment");
  if (!seg) return;
  aiStyleSegmented.querySelectorAll(".segment").forEach((s) => s.classList.remove("active"));
  seg.classList.add("active");
});

document.getElementById("editor-ai-rewrite-btn").addEventListener("click", async () => {
  const btn = document.getElementById("editor-ai-rewrite-btn");
  const text = editorGetHTML();
  if (!text) {
    tg.showAlert(t("editor.nothingToRewrite"));
    return;
  }
  const activeStyleBtn = aiStyleSegmented.querySelector(".segment.active");
  const style = (activeStyleBtn && activeStyleBtn.dataset.style) || "neutral";
  btn.disabled = true;
  btn.classList.add("loading");
  const r = await api("/api/ai-rewrite", { method: "POST", body: JSON.stringify({ text, style }) });
  btn.disabled = false;
  btn.classList.remove("loading");
  if (r && r.ok) {
    editorSetHTML(r.text);
    updateEditorCharCounter();
  } else {
    tg.showAlert((r && r.error) || t("editor.aiRewriteFailed"));
  }
});

document.getElementById("editor-ai-title-btn").addEventListener("click", async () => {
  const btn = document.getElementById("editor-ai-title-btn");
  const text = editorGetHTML();
  if (!text) {
    tg.showAlert(t("editor.enterTextFirst"));
    return;
  }
  btn.disabled = true;
  btn.classList.add("loading");
  const r = await api("/api/ai-title-tags", { method: "POST", body: JSON.stringify({ text }) });
  btn.disabled = false;
  btn.classList.remove("loading");
  if (r && r.ok) {
    const addition = (r.title ? `<b>${r.title}</b>` : "") + (r.hashtags ? `\n\n${r.hashtags}` : "");
    if (addition) {
      editorSetHTML(editorGetHTML() + "\n\n" + addition);
      updateEditorCharCounter();
    }
  } else {
    tg.showAlert((r && r.error) || t("editor.aiTitleFailed"));
  }
});

document.getElementById("editor-publish-btn").addEventListener("click", async () => {
  if (!currentEditingItem) return;
  if (!selectedChannelIds.length) {
    tg.showAlert(t("editor.selectChannelFirst"));
    return;
  }

  const appendFooter = document.getElementById("footer-switch").dataset.on === "true";
  const scheduleOn = document.getElementById("schedule-switch").dataset.on === "true";

  if (scheduleOn) {
    const publishAtLocal = document.getElementById("editor-schedule-datetime").value;
    if (!publishAtLocal) {
      tg.showAlert(t("editor.specifyDateTime"));
      return;
    }
    const publishAtDate = new Date(publishAtLocal);
    if (publishAtDate.getTime() <= Date.now()) {
      tg.showAlert(t("editor.publishTimeMustBeFuture"));
      return;
    }
    const scheduledText = editorGetHTML();
    const title = (scheduledText.split("\n")[0] || t("editor.scheduledPostDefaultTitle")).slice(0, 200);
    const sr = await api("/api/schedule", {
      method: "POST",
      body: JSON.stringify({
        title, text: scheduledText, channel_ids: selectedChannelIds,
        publish_at: publishAtDate.toISOString().slice(0, 19),
      }),
    });
    if (!sr.ok) {
      tg.showAlert(`${t("editor.scheduleError")}: ${sr.error || t("editor.scheduleFailed")}`);
      return;
    }
    if (currentEditingKind === "queue") {
      await api("/api/queue/remove", { method: "POST", body: JSON.stringify({ id: currentEditingItem.id }) });
      loadQueue();
    } else {
      await api("/api/submissions/status", { method: "POST", body: JSON.stringify({ id: currentEditingItem.id, status: "approved" }) });
      loadSubmissions(currentModStatus);
    }
    tg.showAlert(`${t("editor.scheduledFor")} ${publishAtDate.toLocaleString("uk-UA")}`);
    releaseEditLock();
    modal.style.display = "none";
    return;
  }

  if (currentEditingKind === "queue") {
    const payload = { id: currentEditingItem.id, text: editorGetHTML(), append_footer: appendFooter };
    if ((currentEditingItem.media_count || 0) > 0) payload.skip_watermark = !queueEditWatermarkOn;
    const r = await api("/api/queue/edit", { method: "POST", body: JSON.stringify(payload) });
    if (!r.ok) {
      tg.showAlert(`${t("common.error")}: ${r.error || t("common.saveFailedGeneric")}`);
      return;
    }
    const original = (currentEditingItem.channel_ids || []).slice().sort().join(",");
    const updated = selectedChannelIds.slice().sort().join(",");
    if (original !== updated) {
      const cr = await api("/api/queue/set-channels", {
        method: "POST",
        body: JSON.stringify({ id: currentEditingItem.id, channel_ids: selectedChannelIds }),
      });
      if (!cr.ok) {
        tg.showAlert(`${t("editor.textSavedChannelsNot")}: ${cr.error || t("common.error")}`);
        releaseEditLock();
        modal.style.display = "none";
        loadQueue();
        return;
      }
    }
    tg.showAlert(r.approved ? t("editor.savedAndQueued") : t("common.success"));
    releaseEditLock();
    modal.style.display = "none";
    loadQueue();
    return;
  }

  if (currentEditingItem.type === "photo" && watermarkEnabled) {
    if (selectedChannelIds.length > 1) {
      tg.showAlert(t("editor.watermarkSingleChannelOnly"));
      return;
    }
    const canvas = document.getElementById("wm-canvas");
    canvas.toBlob(async (blob) => {
      const form = new FormData();
      form.append("id", currentEditingItem.id);
      form.append("channel_id", selectedChannelIds[0]);
      form.append("content", editorGetHTML());
      form.append("append_footer", appendFooter ? "true" : "false");
      form.append("image", blob, "post.jpg");

      const res = await fetch("/api/submissions/approve-with-media", {
        method: "POST",
        headers: { "X-Init-Data": initData, "ngrok-skip-browser-warning": "true" },
        body: form,
      });
      const r = await res.json();
      if (r.ok) {
        tg.showAlert(t("editor.approvedAndQueued"));
        releaseEditLock();
        modal.style.display = "none";
        loadSubmissions(currentModStatus);
      } else {
        tg.showAlert(`${t("common.error")}: ${r.error || t("queue.publishFailed")}`);
      }
    }, "image/jpeg", 0.92);
    return;
  }

  const r = await api("/api/submissions/approve", {
    method: "POST",
    body: JSON.stringify({ id: currentEditingItem.id, channel_ids: selectedChannelIds, content: editorGetHTML(), append_footer: appendFooter }),
  });
  if (r.ok) {
    tg.showAlert(t("editor.approvedAndQueued"));
    releaseEditLock();
    modal.style.display = "none";
    loadSubmissions(currentModStatus);
  } else {
    tg.showAlert(`${t("common.error")}: ${r.error || t("queue.publishFailed")}`);
  }
});

document.getElementById("editor-reject-btn").addEventListener("click", () => {
  if (!currentEditingItem) return;

  if (currentEditingKind === "queue") {
    tg.showConfirm(t("editor.confirmDeleteFromQueue"), async (confirmed) => {
      if (!confirmed) return;
      const r = await api("/api/queue/remove", { method: "POST", body: JSON.stringify({ id: currentEditingItem.id }) });
      if (!r.ok) { tg.showAlert(`${t("common.error")}: ${r.error || t("queue.deleteFailed")}`); return; }
      releaseEditLock();
      modal.style.display = "none";
      loadQueue();
    });
    return;
  }

  tg.showConfirm(t("editor.confirmReject"), async (confirmed) => {
    if (!confirmed) return;
    await api("/api/submissions/status", { method: "POST", body: JSON.stringify({ id: currentEditingItem.id, status: "rejected" }) });
    releaseEditLock();
    modal.style.display = "none";
    loadSubmissions(currentModStatus);
  });
});

document.getElementById("editor-preview-btn").addEventListener("click", async () => {
  const previewBody = document.getElementById("editor-preview-body");
  previewBody.innerHTML = `<div class="muted" style="padding:24px;text-align:center;">${t("editor.buildingPreview")}</div>`;
  document.getElementById("editor-preview-modal").style.display = "flex";

  const gallery = await buildFullTgPreviewGallery();
  const text = renderTgPreview(editorGetHTML() || `<span style="color:var(--hint);">(${t("editor.emptyText")})</span>`);
  const footer = buildTgPreviewFooter();
  previewBody.innerHTML = gallery + `<div class="tg-preview-text">${text}${footer}</div>`;
});
document.getElementById("editor-preview-close-btn").addEventListener("click", () => {
  document.getElementById("editor-preview-modal").style.display = "none";
});

// ---------- Шаблони ----------

async function loadTemplatesBar() {
  const bar = document.getElementById("templates-bar");
  const templates = await api("/api/templates");
  if (!Array.isArray(templates) || !templates.length) {
    bar.innerHTML = "";
    return;
  }
  bar.innerHTML = templates.map((t) =>
    `<button class="template-chip" data-text="${encodeURIComponent(t.text_pattern)}">${t.title}</button>`
  ).join("");
  bar.querySelectorAll(".template-chip").forEach((chip) => {
    chip.addEventListener("mousedown", (e) => e.preventDefault());
    chip.addEventListener("click", () => {
      const text = decodeURIComponent(chip.dataset.text);
      editorTextarea.focus();
      document.execCommand("insertHTML", false, text.replace(/\n/g, "<br>"));
      updateEditorCharCounter();
    });
  });
}

// ---------- Тех. Розділ (суперадмін) ----------

async function loadDevTab() {
  await loadDevStats();
  await loadDevChannelsList();
  await loadDevErrors();
}

async function loadDevStats() {
  const stats = await api("/api/dev/stats");
  if (stats.error) return;
  document.getElementById("dev-channels-count").textContent = stats.channels_count;
  document.getElementById("dev-admins-count").textContent = stats.active_admins_count;
  document.getElementById("dev-subs-today").textContent = stats.submissions_today;
  document.getElementById("dev-subs-total").textContent = stats.submissions_total;

  const btn = document.getElementById("dev-maintenance-btn");
  const on = stats.maintenance_mode;
  btn.textContent = on ? t("dev.maintenanceOn") : t("common.off");
  btn.className = `pill ${on ? "danger" : "off"}`;
  btn.style.width = "100%";
  btn.style.justifyContent = "center";
  btn.style.padding = "12px";
  btn.onclick = async () => {
    const r = await api("/api/dev/maintenance", { method: "POST", body: JSON.stringify({ enabled: !on }) });
    if (r.ok) loadDevStats();
  };
}

async function loadDevChannelsList() {
  const list = document.getElementById("dev-channels-list");
  const channels = await api("/api/dev/channels");
  if (channels.error) {
    list.innerHTML = `<div class="card-row muted">${t("common.noAccess")}</div>`;
    return;
  }
  if (!channels.length) {
    list.innerHTML = `<div class="card-row muted">${t("channels.empty")}</div>`;
    return;
  }
  list.innerHTML = "";
  for (const ch of channels) {
    const row = document.createElement("div");
    row.className = "dev-channel-row";
    const bannedBadge = ch.banned ? `<span class="badge-inactive">${ICONS.warning} ${t("dev.banned")}</span>` : "";
    const statusBadge = ch.status === "inactive" ? `<span class="badge-inactive">${t("dev.inactive")}</span>` : "";
    row.innerHTML = `
      <div class="dev-channel-title">${escapeHtml(ch.title)} ${bannedBadge} ${statusBadge}</div>
      <div class="dev-channel-meta">
        chat_id: ${ch.id}<br>
        ${t("dev.owner")}: ${ch.added_by || "—"}<br>
        ${t("dev.added")}: ${ch.added_at || "—"}
      </div>
      <div class="pill-row">
        <button class="pill" data-action="reassign">${t("dev.reassignBtn")}</button>
        <button class="pill ${ch.banned ? "on" : "danger"}" data-action="ban">${ch.banned ? t("dev.unbanBtn") : t("dev.banBtn")}</button>
      </div>
    `;
    row.querySelector('[data-action="reassign"]').onclick = async () => {
      const newAdminId = prompt(t("dev.reassignPrompt"));
      if (!newAdminId) return;
      const r = await api("/api/dev/reassign-channel", {
        method: "POST",
        body: JSON.stringify({ channel_id: ch.id, new_admin_id: parseInt(newAdminId, 10) }),
      });
      if (r.ok) loadDevChannelsList();
      else tg.showAlert(t("dev.reassignFailed"));
    };
    row.querySelector('[data-action="ban"]').onclick = async () => {
      const r = await api("/api/dev/ban-channel", {
        method: "POST",
        body: JSON.stringify({ channel_id: ch.id, banned: !ch.banned }),
      });
      if (r.ok) loadDevChannelsList();
    };
    list.appendChild(row);
  }
}

document.getElementById("dev-add-channel-btn").addEventListener("click", async () => {
  const chatId = document.getElementById("dev-add-chatid").value.trim();
  const title = document.getElementById("dev-add-title").value.trim();
  const adminId = document.getElementById("dev-add-adminid").value.trim();
  if (!chatId || !title || !adminId) {
    tg.showAlert(t("dev.fillAllFields"));
    return;
  }
  const r = await api("/api/dev/add-channel", {
    method: "POST",
    body: JSON.stringify({ chat_id: parseInt(chatId, 10), title, admin_id: parseInt(adminId, 10) }),
  });
  if (r.ok) {
    document.getElementById("dev-add-chatid").value = "";
    document.getElementById("dev-add-title").value = "";
    document.getElementById("dev-add-adminid").value = "";
    loadDevChannelsList();
  } else {
    tg.showAlert(`${t("common.error")}: ${r.error || t("common.saveFailedGeneric")}`);
  }
});

document.getElementById("dev-user-search-btn").addEventListener("click", async () => {
  const query = document.getElementById("dev-user-search").value.trim();
  const list = document.getElementById("dev-users-list");
  if (!query) return;
  const results = await api(`/api/dev/users?query=${encodeURIComponent(query)}`);
  if (!Array.isArray(results) || !results.length) {
    list.innerHTML = `<div class="card-row muted">${t("dev.nothingFound")}</div>`;
    return;
  }
  list.innerHTML = results.map((u) => `
    <div class="card-row">
      <span>${escapeHtml(u.name || String(u.user_id))} (${u.role === "admin" ? t("dev.roleAdmin") : t("dev.roleReader")})</span>
      <span class="muted">ID ${u.user_id} · ${t("dev.channelsShort")}: ${u.channels} · ${t("dev.submissionsShort")}: ${u.submissions}</span>
    </div>
  `).join("");
});

async function loadDevErrors() {
  const list = document.getElementById("dev-errors-list");
  const errors = await api("/api/dev/errors");
  if (!Array.isArray(errors) || !errors.length) {
    list.innerHTML = `<div class="card-row muted">${t("dev.noErrors")}</div>`;
    return;
  }
  list.innerHTML = errors.map((e) => `
    <div class="card-row" style="align-items:flex-start;">
      <span style="flex:1;">${escapeHtml(e.message)}</span>
      <span class="muted">${e.ts}</span>
    </div>
  `).join("");
}