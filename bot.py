import telebot

import sqlite3

# Создаем экземпляр бота
bot = telebot.TeleBot("TOKEN")

# Приветствие
def welcome(chat_id):
    if not auth(chat_id):
        return bot.send_message(chat_id, 'Добро пожаловать в Библиотеку. Ваш аккаунт не найден в базе данных. Пожалуйста, введите свое имя.')
    else:
        return bot.send_message(chat_id, 'С возвращением!\nСписок доступных команд:\n📚 /books - список книг\n✅ /available - список доступных книг\n📖 /me - мои книги')

# Регистрация
def registration(chat_id, full_name):
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()

        # Добавление новой записи в таблицу users
        cursor.execute("INSERT INTO users (chat_id, full_name, menu) VALUES (?, ?, 'main')", (chat_id, full_name))
        conn.commit()

        cursor.close()

    return bot.send_message(chat_id, f'{full_name}, вы успешно зарегестрированы в Библиотеке!\nЧтобы просмотреть список доступных книг, введите команду /books')

# Авторизация
def auth(chat_id):
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()

        # Выполнение запроса на поиск записи с заданным chat_id
        cursor.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()

        cursor.close()

    return user[0] if user else None

# Получение текущего меню пользователя
def menu(chat_id):
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()

        # Выполнение запроса на получение текущего меню пользователя
        cursor.execute("SELECT menu FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()

        cursor.close()

    return user[0] if user else None

# Обновить меню пользователя
def set_menu(chat_id, menu):
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()

        # Запись перехода пользователя в указанное меню
        cursor.execute("UPDATE users SET menu = ? WHERE chat_id = ?", (menu, chat_id))
        conn.commit()

        cursor.close()

# Получение списка книг
def get_books(chat_id, available = False):
    if not auth(chat_id):
        return welcome(chat_id)
    
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()

        # Запрос для получения списка книг
        query = """
        SELECT b.id, b.title, a.full_name, g.name, strftime('%Y', b.publication_date), b.description, b.pages_number,
            CASE 
                WHEN EXISTS (SELECT 1 FROM book_user AS bu WHERE bu.book_id = b.id AND bu.end_date IS NULL) THEN 0
                ELSE 1
            END AS is_available
        FROM books AS b 
        INNER JOIN authors AS a ON b.author_id = a.id 
        INNER JOIN genres AS g ON b.genre_id = g.id
        """
        
        if available:
            query += """
            WHERE is_available = 1
            """
        
        # Получаем список книг с данными об авторах и жанрах
        cursor.execute(query)
        books = cursor.fetchall()

        cursor.close()

    # Отправляем список книг пользователю
    if not available:
        bot.send_message(chat_id, 'Отправляю список книг...')
    else:
        bot.send_message(chat_id, 'Отправляю список доступных книг...')
    
    return bot.send_message(chat_id, format_books(books), 'HTML')

# Получение списка книг, которые взял пользователь
def get_user_books(chat_id):
    if not auth(chat_id):
        return welcome(chat_id)
    
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        
        # Получаем список книг пользователя
        cursor.execute("""
        SELECT b.id, b.title, strftime('%d.%m.%Y', bu.start_date)
        FROM books AS b
        LEFT JOIN book_user AS bu ON b.id = bu.book_id
        WHERE bu.user_id = ? AND bu.end_date IS NULL
        """, (auth(chat_id),))
        books = cursor.fetchall()
        
        user_books = ""
        for book in books:
            id, title, start_date = book
            user_books += f'[№{id}] {title} (дата начала: {start_date})\n'

        cursor.close()

    if len(user_books) == 0:
        user_books = "список пуст );"

    bot.send_message(chat_id, 'Отправляю список ваших книг...')
    return bot.send_message(chat_id, user_books)

# Начало бронирования книги пользователем
def reserve_start(chat_id):
    if not auth(chat_id):
        return welcome(chat_id)
    
    set_menu(chat_id, 'reserve')

    return bot.send_message(chat_id, 'Чтобы забронировать книгу, отправьте мне её номер.')


# Бронирование книги пользователем
def reserve(chat_id, book_id):
    if not auth(chat_id):
        return welcome(chat_id)
    
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()

        # Выполнение запроса на поиск книги в базе данных
        cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
        book_exists = cursor.fetchone()
        
        if not book_exists:
            set_menu(chat_id, 'main')
            return bot.send_message(chat_id, f'Книга под номером {book_id} не найдена в базе данных.\nЧтобы просмотреть список доступных книг, введите команду /available')

        # Выполнение запроса на поиск записи с заданным book_id
        cursor.execute("SELECT book_id FROM book_user WHERE book_id = ? AND end_date IS NULL", (book_id,))
        book_reserved = cursor.fetchone()

        if book_reserved:
            set_menu(chat_id, 'main')
            return bot.send_message(chat_id, f'Книга под номером {book_id} в данный момент недоступна.\nЧтобы просмотреть список доступных книг, введите команду /available')

        # Запись бронирования книги
        cursor.execute("INSERT INTO book_user (book_id, user_id, start_date) VALUES (?, ?, DATE('now'))", (book_id, auth(chat_id)))
        conn.commit()

        cursor.close()
        
    set_menu(chat_id, 'main')

    return bot.send_message(chat_id, f'Книга под номером {book_id} успешно забронирована.\nЧтобы просмотреть список забронированных книг, введите команду /me')

# Начало сдачи книги пользователем
def back_start(chat_id):
    if not auth(chat_id):
        return welcome(chat_id)
    
    set_menu(chat_id, 'back')

    return bot.send_message(chat_id, 'Чтобы сдать книгу, отправьте мне её номер.')

# Сдача книги пользователем
def back(chat_id, book_id):
    if not auth(chat_id):
        return welcome(chat_id)
    
    # Открываем базу данных
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()

        # Выполнение запроса на поиск записи с заданным book_id
        cursor.execute("SELECT book_id FROM book_user WHERE book_id = ? AND user_id = ? AND end_date IS NULL", (book_id, auth(chat_id)))
        book_reserved = cursor.fetchone()

        if not book_reserved:
            set_menu(chat_id, 'main')
            return bot.send_message(chat_id, f'Книга под номером {book_id} не была забронирована вами ранее.\nЧтобы просмотреть список забронированных книг, введите команду /me')

        # Запись окончания бронирования книги
        cursor.execute("UPDATE book_user SET end_date = DATE('now') WHERE book_id = ? AND user_id = ?", (book_id, auth(chat_id)))
        conn.commit()

        cursor.close()
        
    set_menu(chat_id, 'main')

    return bot.send_message(chat_id, f'Книга под номером {book_id} успешно возвращена.\nЧтобы просмотреть список доступных книг, введите команду /available')

# Форматирование списка книг
def format_books(books):
    books_info = ""
    
    # Обходим список книг и формируем строку
    for book in books:
        id, title, author, genre, publication_date, description, pages_number, is_reserved = book
        books_info += f"<b>№{id}</b>\n"
        books_info += f"<b>Название книги:</b> {title}\n"
        books_info += f"<b>Автор:</b> {author}\n"
        books_info += f"<b>Жанр:</b> {genre}\n"
        books_info += f"<b>Дата публикации:</b> {publication_date} год\n"
        books_info += f"<b>Описание:</b> {description}\n"
        books_info += f"<b>Количество страниц:</b> {pages_number}\n\n"
    
    return books_info

# Обработка команды "/start"
@bot.message_handler(commands=['start'])
def start_message(message):
    return welcome(message.chat.id)
    
# Обработка команды "/books"
@bot.message_handler(commands=['books'])
def books_message(message):
    return get_books(message.chat.id)

# Обработка команды "/available"
@bot.message_handler(commands=['available'])
def available_message(message):
    return get_books(message.chat.id, True)

# Обработка команды "/me"
@bot.message_handler(commands=['me'])
def me_message(message):
    return get_user_books(message.chat.id)

# Обработка команды "/reserve"
@bot.message_handler(commands=['reserve'])
def reserve_message(message):
    return reserve_start(message.chat.id)

# Обработка команды "/back"
@bot.message_handler(commands=['back'])
def back_message(message):
    return back_start(message.chat.id)

# Обработка текстового сообщения
@bot.message_handler(func=lambda message: True)
def message(message):
    if not auth(message.chat.id):
        return registration(message.chat.id, message.text)
    
    current_menu = menu(message.chat.id)
        
    if current_menu == 'reserve':
        return reserve(message.chat.id, message.text)
    elif current_menu == 'back':
        return back(message.chat.id, message.text)
    else:
        return welcome(message.chat.id)
        

# Запуск бота
bot.polling()