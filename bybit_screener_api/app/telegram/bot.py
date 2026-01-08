import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger: logging.Logger = logging.getLogger(__name__)


class TelegramBot:
    """Класс для работы с Telegram-ботом."""

    def __init__(self, token: str, user_tracker) -> None:
        """Инициализация бота."""
        logger.info("Инициализация TelegramBot")
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.threshold_factor = 8.0  # Множитель для крупных объёмов по умолчанию
        self.user_tracker = user_tracker  # Добавляем трекер пользователей
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Регистрация обработчиков команд и callback'ов."""
        @self.dp.message(Command(commands=['start']))
        async def send_welcome(message: types.Message) -> None:
            """Обработчик команды /start."""
            # Регистрируем нового пользователя
            await self.user_tracker.add_user(message.chat.id)

            user_name = message.from_user.first_name or "Пользователь"
            welcome_text = (
                f"<b>Привет, {user_name}!</b>\n\n"
                "<b>О боте</b>\n"
                "Я — бот для анализа крупных объёмов на фьючерсном рынке биржи Bybit. "
                "Моя цель — помочь трейдерам выявлять значительные скопления заявок в ордербуке, "
                "которые могут указывать на потенциальные уровни поддержки или сопротивления.\n\n"
                "<b>Что я умею:</b>\n"
                "📊 <b>Анализ крупных объёмов:</b> Определяю заявки в ордербуке, объём которых в несколько раз "
                "превышает средний (по умолчанию в 8 раз).\n"
                "🔢 <b>Выбор множителя:</b> Вы можете настроить множитель (от 3 до 16), чтобы регулировать "
                "чувствительность обнаружения крупных объёмов.\n"
                "📈 <b>Топ-10, топ-50, топ-100 пар:</b> Анализирую пары с наибольшим объёмом торгов и показываю "
                "крупные объёмы для них.\n"
                "🌐 <b>Все пары:</b> Анализирую все доступные фьючерсные пары (до 50 для оптимизации скорости).\n\n"
                "<b>Как пользоваться:</b>\n"
                "1. Нажмите <b>Выбрать множитель объёмов</b>, чтобы установить порог для обнаружения (текущий: 8.0).\n"
                "2. Выберите <b>Топ-10</b>, <b>Топ-50</b>, <b>Топ-100</b> или <b>Все пары</b>, чтобы получить данные "
                "по крупным объёмам.\n"
                "3. После любого действия используйте кнопку <b>МЕНЮ</b>, чтобы вернуться к основным функциям.\n"
                "4. 💰 Нажмите <b>Поддержи разработчика</b>, чтобы помочь улучшать бота.\n\n"
                "<b>Выбери действие:</b>"
            )
            keyboard = self._get_main_menu()
            try:
                await message.reply(welcome_text, reply_markup=keyboard, parse_mode="HTML")
                logger.info(f"Получена команда /start от {message.from_user.id}, отправлено приветственное сообщение")
            except Exception as e:
                logger.error(f"Ошибка при отправке приветственного сообщения: {str(e)}")
                # Запасной вариант с Markdown
                welcome_text_markdown = welcome_text.replace("<b>", "*").replace("</b>", "*")
                await message.reply(welcome_text_markdown, reply_markup=keyboard, parse_mode="MarkdownV2")
                logger.info(f"Отправлено приветственное сообщение в Markdown для {message.from_user.id}")

        @self.dp.callback_query()
        async def handle_callback(callback: types.CallbackQuery) -> None:
            """Обработчик инлайн-кнопок."""
            data = callback.data
            chat_id = callback.message.chat.id  # Получаем chat_id из callback
            logger.info(f"Получен callback с данными: {data} от {callback.from_user.id}")
            current_text = callback.message.text
            current_reply_markup = callback.message.reply_markup

            try:
                if data == "menu":
                    new_text = "<b>Выбери действие:</b>"
                    new_reply_markup = self._get_main_menu()
                    if current_text != new_text or current_reply_markup != new_reply_markup:
                        await callback.message.edit_text(
                            new_text, reply_markup=new_reply_markup, parse_mode="HTML"
                        )
                    logger.info(f"Пользователь {callback.from_user.id} открыл главное меню через кнопку МЕНЮ")

                elif data == "set_threshold":
                    new_text = "<b>Выберите множитель для крупных объёмов:</b>"
                    new_reply_markup = self._get_threshold_menu()
                    if current_text != new_text or current_reply_markup != new_reply_markup:
                        await callback.message.edit_text(
                            new_text, reply_markup=new_reply_markup, parse_mode="HTML"
                        )
                    logger.info(f"Пользователь {callback.from_user.id} открыл меню выбора множителя")

                elif data.startswith("set_threshold_"):
                    threshold = float(data.split("_")[-1])
                    self.threshold_factor = threshold
                    new_text = f"<b>Установлен множитель для крупных объёмов: {threshold}</b>\n<b>Выбери действие:</b>"
                    new_reply_markup = self._get_menu_button()
                    if current_text != new_text or current_reply_markup != new_reply_markup:
                        await callback.message.edit_text(
                            new_text, reply_markup=new_reply_markup, parse_mode="HTML"
                        )
                    logger.info(f"Установлен множитель {threshold} пользователем {callback.from_user.id}")

                elif data in ["top_10_pairs", "top_50_pairs", "top_100_pairs", "all_pairs"]:
                    new_text = (
                        f"<b>Запущен расчёт крупных объёмов для {data.replace('_', ' ')}.</b>\n"
                        "Результаты будут отправлены в этот чат после обработки.\n"
                        "<b>Вернись к меню:</b>"
                    )
                    new_reply_markup = self._get_menu_button()
                    if current_text != new_text or current_reply_markup != new_reply_markup:
                        await callback.message.edit_text(
                            new_text, reply_markup=new_reply_markup, parse_mode="HTML"
                        )
                    await callback.message.bot.send_message(
                        chat_id, "<b>Обработка начата, ждите результатов...</b>",
                        reply_markup=self._get_menu_button(), parse_mode="HTML"
                    )
                    await self.on_calculate_callback(data, self.threshold_factor, chat_id)

                elif data == "back":
                    new_text = "<b>Выбери действие:</b>"
                    new_reply_markup = self._get_main_menu()
                    if current_text != new_text or current_reply_markup != new_reply_markup:
                        await callback.message.edit_text(
                            new_text, reply_markup=new_reply_markup, parse_mode="HTML"
                        )
                    logger.info(f"Пользователь {callback.from_user.id} вернулся в главное меню")

                await callback.answer()
            except Exception as e:
                logger.error(f"Ошибка в handle_callback: {str(e)}")
                await callback.answer()

    def _get_main_menu(self) -> InlineKeyboardMarkup:
        """Создаёт основное меню с кнопками."""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Выбрать множитель объёмов", callback_data="set_threshold")
            ],
            [
                InlineKeyboardButton(text="Топ-10 пар по объёму", callback_data="top_10_pairs")
            ],
            [
                InlineKeyboardButton(text="Топ-50 пар по объёму", callback_data="top_50_pairs")
            ],
            [
                InlineKeyboardButton(text="Топ-100 пар по объёму", callback_data="top_100_pairs")
            ],
            [
                InlineKeyboardButton(text="Все пары", callback_data="all_pairs")
            ],
            [
                InlineKeyboardButton(text="💰💰💰 Поддержи разработчика 💰💰💰", url="https://boosty.to/bybit_screener/donate")
            ],
            [
                InlineKeyboardButton(text="МЕНЮ", callback_data="menu")
            ]
        ])
        return keyboard

    def _get_menu_button(self) -> InlineKeyboardMarkup:
        """Создаёт клавиатуру с одной кнопкой МЕНЮ."""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="МЕНЮ", callback_data="menu")
            ]
        ])
        return keyboard

    def _get_threshold_menu(self) -> InlineKeyboardMarkup:
        """Создаёт меню для выбора множителя."""
        buttons = [
            [InlineKeyboardButton(
                text=f"{i} ✅" if float(i) == self.threshold_factor else str(i),
                callback_data=f"set_threshold_{i}.0"
            )] for i in range(3, 17)  # Диапазон от 3 до 16
        ]
        buttons.append([InlineKeyboardButton(text="Назад", callback_data="back")])
        buttons.append([InlineKeyboardButton(text="Поддержи разработчика", url="https://boosty.to/bybit_screener/donate")])
        buttons.append([InlineKeyboardButton(text="МЕНЮ", callback_data="menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)


    async def send_message(self, chat_id: int, text: str, *, reply_markup=None, parse_mode: str | None = None) -> None:
        """Thin wrapper over aiogram.Bot.send_message.

        This keeps backward compatibility with the original project where TelegramBot
        was used as if it exposed Bot methods directly.
        """
        await self.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    async def send_large_volumes(self, density_list: list[dict], chat_id: int) -> None:
        """Отправляет данные о крупных объёмах в Telegram конкретному пользователю."""
        if not density_list:
            await self.bot.send_message(
                chat_id,
                "<b>Крупные объёмы не найдены.</b>",
                reply_markup=self._get_menu_button(),
                parse_mode="HTML"
            )
            return

        # Группировка данных по символам
        symbol_groups = {}
        for density in density_list:
            symbol = density['symbol']
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(density)

        # Формирование сообщения
        unique_symbols = list(symbol_groups.keys())
        message_prefix = (f"<b>Крупные объёмы (в {self.threshold_factor} раза выше среднего, найдено "
                          f"{len(unique_symbols)} пар):</b>\n")
        messages = []
        current_message = message_prefix
        max_message_length = 4000

        for symbol in symbol_groups:
            lines = [f"<b>{symbol}</b>"]
            for density in symbol_groups[symbol]:
                price = density.get('price', 0)
                if price == 0:
                    logger.warning(f"Нулевая цена для {symbol} ({density['side']}): {density}")
                side_emoji = "📈" if density['side'] == "bids" else "📉"
                line = f"{side_emoji} {density['side'].capitalize()}: {density['volume_usdt']:.2f} USDT @ {density['price']:.8f}"
                lines.append(line)
            symbol_text = "\n".join(lines)
            if len(current_message) + len(symbol_text) + 1 < max_message_length:
                current_message += symbol_text + "\n"
            else:
                messages.append(current_message)
                current_message = message_prefix + symbol_text + "\n"

        if current_message != message_prefix:
            messages.append(current_message)

        try:
            for message in messages:
                await self.bot.send_message(
                    chat_id,
                    message,
                    reply_markup=self._get_menu_button(),
                    parse_mode="HTML"
                )
            logger.info(f"Отправлено {len(messages)} сообщений о крупных объёмах в чат {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления в чат {chat_id}: {str(e)}")

    async def send_report_to_owner(self, owner_chat_id: int) -> None:
        """Отправляет отчёт о пользователях владельцу бота."""
        report = await self.user_tracker.generate_report()
        try:
            await self.bot.send_message(
                owner_chat_id,
                report,
                parse_mode="HTML"
            )
            logger.info(f"Отчёт о пользователях отправлен владельцу в чат {owner_chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке отчёта владельцу в чат {owner_chat_id}: {str(e)}")

    async def start(self) -> None:
        """Запускает поллинг бота."""
        try:
            await self.dp.start_polling(self.bot)
            logger.info("Бот запущен")
        finally:
            await self.bot.session.close()
            logger.info("Сессия бота закрыта")

    def set_calculate_callback(self, callback):
        """Устанавливает callback для уведомления о необходимости расчёта."""
        self.on_calculate_callback = callback
