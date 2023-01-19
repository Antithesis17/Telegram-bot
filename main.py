import datetime
import calendar
import logging
import sqlite3
from datetime import datetime, timedelta, date, time
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types
from aiogram.filters.text import Text
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.DEBUG)

Token = 'Bot-token'
bot = Bot(token=Token)
dp = Dispatcher()


# Стартовая функция. Выставляет меню команд
@dp.message(Command(commands=['start'], ignore_case=True))
async def setup_command(message: types.Message):
    bot_commands = [types.BotCommand(command="/shifts", description="Посмотреть график смен"), 
                    types.BotCommand(command="/change", description="Передать свою смену"),
                    types.BotCommand(command="/vacation", description="Передать все свои ближайшие смены"),
                    types.BotCommand(command="/handover", description="Сдать смену")]
    await bot.set_my_commands(bot_commands)
    await message.answer("Начало работы")

# Команда handover. Программа определяет пользователя, вызвавшего команду и пользователя, который соответствуя время, должен принять смену согласно графику
@dp.message(Command(commands=["handover"], ignore_case=True))
async def handover(message: types.Message):
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    username = message.from_user.username
    date_date = date.today()
    day_shift_time_start = time(20)    
    day_shift_time_end = time(22)    
    night_shift_time_start = time(8)   
    night_shift_time_end = time(10)
    current_datetime = datetime.now()
    date_time = current_datetime.time()
    if day_shift_time_start < date_time < day_shift_time_end:
        result = cursor.execute(f"SELECT Night_shift FROM Shifts WHERE Date LIKE '{date_date}'").fetchall()
        pos_nick = result[0][0].find("@")
        person_nick = result[0][0][pos_nick:]
        print(person_nick)
        await message.answer(f"@{username} смену сдал(а), {person_nick} смену принял(а)")
    elif night_shift_time_start < date_time < night_shift_time_end:
        result = cursor.execute(f"SELECT Day_shift FROM Shifts WHERE Date LIKE '{date_date}'").fetchall()
        pos_nick = result[0][0].find("@")
        person_nick = result[0][0][pos_nick:]
        print(person_nick)
        await message.answer(f"@{username} смену сдал(а), {person_nick} смену принял(а)")

# Команда Shifts для просмотра графика смен. Получает уникальные значения имен пользователей из бд и создает inline кнопку для каждого. Нажатие на кнопку продолжает команду
@dp.message(Command(commands=['shifts'], ignore_case=True))
async def send_shifts(message: types.Message):
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    result = cursor.execute(
        f"SELECT DISTINCT Day_shift FROM Shifts ").fetchall()
    builder = InlineKeyboardBuilder()
    for person in result:
        pos = person[0].find("@")
        person_nick = person[0][pos:]
        builder.add(InlineKeyboardButton(
            text=person[0][6:], callback_data='name_' + person_nick))
        builder.adjust(1)
    await message.answer("Чей график вы хотите просмотреть?", reply_markup=builder.as_markup())


# Продолжение команды Shifts. Создает inline кнопку для выбора графика, который пользователь хочет посмотреть. Нажатие на кнопку продолжает команду
@dp.callback_query(Text(contains="name_"))
async def callbacks_shifts(callback: types.CallbackQuery):
    person_nick = callback.data.split("_")[1]
    shift_variants = ['График дневных смен',
                      'График ночных смен', 'Смешанный график', 'График выходных']
    builder = InlineKeyboardBuilder()
    for variant in shift_variants:
        builder.add(InlineKeyboardButton(
            text=variant, callback_data='shift_' + variant + '_' + person_nick))
        builder.adjust(1)
    await callback.message.edit_text("Какой график вы хотите посмотреть?", reply_markup=builder.as_markup())


# Продолжение команды Shifts. Делает запрос из бд, в соответсвии с запросами пользователя. Выводит в сообщении полученный график
@dp.callback_query(Text(contains='shift_'))
async def callback_variant(callback: types.CallbackQuery):
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    variant = callback.data.split('_')[1]
    person_nick = callback.data.split('_')[2]
    if variant == 'График дневных смен':
        search_variant = f"SELECT Date FROM Shifts WHERE Day_shift LIKE '%{person_nick}' AND Date >= '{datetime.now().strftime('%Y-%m-%d')}'"
    elif variant == 'График ночных смен':
        search_variant = f"SELECT Date FROM Shifts WHERE Night_shift LIKE '%{person_nick}' AND Date >= '{datetime.now().strftime('%Y-%m-%d')}'"
    elif variant == 'График выходных':
        search_variant = f"SELECT Date FROM Shifts WHERE (Day_shift NOT LIKE '%{person_nick}' AND Night_shift NOT LIKE '%{person_nick}') AND Date >= '{datetime.now().strftime('%Y-%m-%d')}'"
    elif variant == 'Смешанный график':
        search_variant_day = f"SELECT Date FROM Shifts WHERE Day_shift LIKE '%{person_nick}' AND Date >= '{datetime.now().strftime('%Y-%m-%d')}'"
        search_variant_night = f"SELECT Date FROM Shifts WHERE Night_shift LIKE '%{person_nick}' AND Date >= '{datetime.now().strftime('%Y-%m-%d')}'"

    if variant == 'Смешанный график':
        day_shifts = [('Дневные смены:',)]
        night_shifts = [('Ночные смены:',)]
        needed_shifts = day_shifts + cursor.execute(search_variant_day).fetchall(
        ) + night_shifts + cursor.execute(search_variant_night).fetchall()
    else:
        needed_shifts = cursor.execute(search_variant).fetchall()
    final_answer = 'Ваш график: \n'
    for shift_date in needed_shifts:
        final_answer += shift_date[0] + '\n'
    connection.close()
    await callback.message.edit_text(final_answer)


# Команда Change для изменения смен. Получает уникальные значения имен пользователей из бд и создает inline кнопку для каждого. Нажатие на кнопку продолжает команду
@dp.message(Command(commands=['change'], ignore_case=True))
async def change_shifts(message: types.Message):
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    result = cursor.execute(
        f"SELECT DISTINCT Day_shift FROM Shifts ").fetchall()
    builder = InlineKeyboardBuilder()
    for person in result:
        pos = person[0].find("@")
        person_nick = person[0][pos:]
        builder.add(InlineKeyboardButton(
            text=person[0][6:], callback_data='nick_' + person_nick))
        builder.adjust(1)
    await message.answer("Чью смену вы хотите изменить?", reply_markup=builder.as_markup())


# Продолжение команды Change. Для выбранного пользователя выдает график ближайших смен и предлагает выбрать смену, которую он хочет заменить. Нажатие на кнопку продолжает команду
@dp.callback_query(Text(contains="nick_"))
async def choose_date(callback: types.CallbackQuery):
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    person_nick = callback.data.split("_")[1]
    builder = InlineKeyboardBuilder()
    date_variant_day = f"SELECT Date FROM Shifts WHERE Day_shift LIKE '%{person_nick}' AND Date >= '{datetime.now().strftime('%Y-%m-%d')}'"
    date_variant_night = f"SELECT Date FROM Shifts WHERE Night_shift LIKE '%{person_nick}' AND Date >= '{datetime.now().strftime('%Y-%m-%d')}'"
    day_shifts = 'Дневные смены:'
    night_shifts = 'Ночные смены:'
    day_date_variants = cursor.execute(date_variant_day).fetchall()
    night_date_variants = cursor.execute(date_variant_night).fetchall()
    for date_variant in day_date_variants:
        builder.add(InlineKeyboardButton(
            text=date_variant[0], callback_data='date_' + 'day_' + date_variant[0] + '_' + person_nick))
        builder.adjust(2)
    await callback.message.edit_text(text="В какой день вы хотите поменять смену?")
    await callback.message.answer(text=day_shifts, reply_markup=builder.as_markup())
    builder = InlineKeyboardBuilder()
    for date_variant in night_date_variants:
        builder.add(InlineKeyboardButton(
            text=date_variant[0], callback_data='date_' + 'night_' + date_variant[0] + '_' + person_nick))
        builder.adjust(2)
    await callback.message.answer(text=night_shifts, reply_markup=builder.as_markup())

# Продолжение команды Change. Пользователю дают выбор из имен людей. Он должен выбрать, кто заменит его в выбранную ранее дату. Нажатие на кнопку продолжает команду


@dp.callback_query(Text(contains="date_"))
async def choose_person(callback: types.CallbackQuery):
    print(callback.data)
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    date_variant = callback.data.split(
        '_')[1] + '_' + callback.data.split('_')[2]
    person_nick = callback.data.split('_')[3]
    builder = InlineKeyboardBuilder()
    result = cursor.execute(
        f"SELECT DISTINCT Day_shift FROM Shifts WHERE Day_shift NOT LIKE '%{person_nick}'").fetchall()
    for person in result:
        pos = person[0].find("@")
        shiftman = person[0][pos:]
        builder.add(InlineKeyboardButton(
            text=person[0][6:], callback_data='person_' + person_nick + '_' + date_variant + '_' + shiftman))
        builder.adjust(1)
    await callback.message.edit_text("Кто планирует взять вашу смену?", reply_markup=builder.as_markup())

# Продолжение команды Change. Происходит замена в бд, согласно выборам, который сделал пользователь ранее. В конце выдается сообщение об успешной замене


@dp.callback_query(Text(contains="person_"))
async def update_db(callback: types.CallbackQuery):
    print(callback.data)
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    date_variant = callback.data.split('_')[3]
    shiftman = callback.data.split('_')[4]
    shiftman = cursor.execute(
        f"SELECT DISTINCT Day_shift FROM Shifts WHERE Day_shift LIKE '%{shiftman}'").fetchall()
    if "day_" in callback.data:
        print(shiftman[0][0])
        print(date_variant)
        cursor.execute(
            f"UPDATE Shifts SET Day_shift = '{shiftman[0][0]}' WHERE Date LIKE '{date_variant}'")
        connection.commit()
    elif "night_" in callback.data:
        print(date_variant)
        cursor.execute(
            f"UPDATE Shifts SET Night_shift = '{shiftman[0][0]}' WHERE Date LIKE '{date_variant}'")
        connection.commit()
    connection.close()
    await callback.message.edit_text(text="Замена успешно проведена")

# Начало команды vacation. Из списка имен требуется выбрать имя уходящего в отпуск
@dp.message(Command(commands=['vacation'], ignore_case=True))
async def start_vacation(message: types.Message):
    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    result = cursor.execute("SELECT DISTINCT Day_shift FROM Shifts").fetchall()
    builder = InlineKeyboardBuilder()
    year: int = datetime.now().year
    month: int = datetime.now().month
    day: int = datetime.now().day
    for person in result:
        pos = person[0].find("@")
        person_nick = person[0][pos:]
        builder.add(InlineKeyboardButton(
            text=person[0][6:], callback_data=f'simple_calendar.act.{year}.{month}.{day}.' + person_nick))
        builder.adjust(1)
    await message.answer(text="Кто планирует пойти в отпуск?", reply_markup=builder.as_markup())

# Продолжение команды vacation. Создается календарь из кнопок и требуется выбрать дату начала отпуска
@dp.callback_query(Text(contains="simple_calendar."))
async def start_calendar(callback: types.CallbackQuery):
    year = int(callback.data.split(".")[2])
    month = int(callback.data.split(".")[3])
    await draw_calendar(callback, year, month)

# Функция создания календаря. Создается несколько линий из кнопок, чтобы внешний вид соответствовал классическому календарю
async def draw_calendar(callback: types.CallbackQuery, year, month):
    person_nick = callback.data.split(".")[5]
    ignore_callback = f"Calendar.Ignore.{year}.{month}.0.{person_nick}"
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=f'{calendar.month_name[int(month)]} {str(year)}', callback_data=ignore_callback), width=1)

    buttons = []
    for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
        buttons.append(InlineKeyboardButton(
            text=day, callback_data=ignore_callback))
    buttons = tuple(buttons)
    builder.row(*buttons, width=7)
    month_calendar = calendar.monthcalendar(year=year, month=month)
    buttons_day = []
    for week in month_calendar:
        for day in week:
            if (day == 0):
                buttons_day.append(InlineKeyboardButton(
                    text=" ", callback_data=ignore_callback))
                continue
            buttons_day.append(InlineKeyboardButton(text=str(
                day), callback_data=f"Calendar.DAY.{year}.{month}.{day}.{person_nick}"))

    builder.row(*tuple(buttons_day), width=7)
    builder.row(InlineKeyboardButton(text="<", callback_data=f"Calendar.PREV-MONTH.{year}.{month}.0.{person_nick}"),
                InlineKeyboardButton(text=">", callback_data=f"Calendar.NEXT-MONTH.{year}.{month}.0.{person_nick}"), width=2)
    await callback.message.edit_text(text="Выберите дату ухода в отпуск", reply_markup=builder.as_markup())

# Продолжение команды vacation. После нажатия на день в вызванном ранее календаре, эта дата передается далее. При нажатии на стрелку меняется месяц
@dp.callback_query(Text(contains="Calendar."))
async def process_selection(callback: types.CallbackQuery):
    act = callback.data.split(".")[1]
    year = int(callback.data.split(".")[2])
    month = int(callback.data.split(".")[3])
    day = callback.data.split(".")[4]
    person_nick = callback.data.split(".")[5]
    data = {'act': act, 'year': year, 'month': month, 'day': day}
    return_data = (False, None)
    temp_date = datetime(int(data["year"]), int(data["month"]), 1)
    if data['act'] == "IGNORE":
        await callback.answer(cache_time=60)
    if data['act'] == "DAY":
        await callback.message.edit_text('На сколько дней вы планируете отпуск?')
        return_data = str(year) + '-' + str(month) + '-' + str(day)
    if data['act'] == "PREV-YEAR":
        await draw_calendar(callback, year - 1, month)
    if data['act'] == "NEXT-YEAR":
        await draw_calendar(callback, year + 1, month)
    if data['act'] == "PREV-MONTH":
        if month == 1:
            month = 12
            year -= 1
            await draw_calendar(callback, year, month)
        else:
            await draw_calendar(callback, year, month - 1)
    if data['act'] == "NEXT-MONTH":
        if month == 12:
            month = 1
            year += 1
            await draw_calendar(callback, year, month)
        else:
            await draw_calendar(callback, year, month + 1)
    print(return_data)
    global vacation_date
    vacation_date = return_data
    global person_vacation
    person_vacation = person_nick

# Продолжение команды vacation. От пользователя требуется написать в чат сообщение с количеством дней, на которое он планирует уйти в отпуск
@dp.message()
async def date_count(message: types.Message):
    try:
        day_count = int(message.text)
        if 0 < day_count < 50:
            day_count = str(day_count)
            person_nick = person_vacation
            connection = sqlite3.connect("Shifts.db")
            cursor = connection.cursor()
            result = cursor.execute(
                f"SELECT DISTINCT Day_shift FROM Shifts WHERE Day_shift NOT LIKE '%{person_nick}'").fetchall()
            builder = InlineKeyboardBuilder()
            for person in result:
                pos = person[0].find("@")
                shiftman_vacation = person[0][pos:]
                builder.add(InlineKeyboardButton(
                    text=person[0][6:], callback_data='vac_' + person_vacation + '_' + day_count + '_' + vacation_date + '_' + shiftman_vacation))
                builder.adjust(1)
            await message.answer("Кто планирует заменить вас в эти дни?", reply_markup=builder.as_markup())
        else:
            await message.answer("Пожалуйста, используйте команду из списка")
    except ValueError:
        await message.answer("Пожалуйста, используйте команду из списка")
    except NameError:
        await message.answer("Пожалуйста, используйте команду из списка")

# Окончание команды vacation. Обновление базы данных в соответствии с указанными ранее данными
@dp.callback_query(Text(contains='vac_'))
async def vacation_update(callback: types.CallbackQuery):
    print(callback.data)
    person_vacation = callback.data.split("_")[1]
    day_count = int(callback.data.split("_")[2])
    vacation_start_date = datetime.strptime(
        callback.data.split("_")[3], "%Y-%m-%d")
    shiftman_vacation = callback.data.split("_")[4]
    vacation_end_date = vacation_start_date + timedelta(days=day_count)
    vacation_end_date = vacation_end_date.date()

    connection = sqlite3.connect("Shifts.db")
    cursor = connection.cursor()
    shiftman_vacation = cursor.execute(
        f"SELECT DISTINCT Day_shift FROM Shifts WHERE Day_shift LIKE '%{shiftman_vacation}'").fetchall()
    cursor.execute(
        f"UPDATE Shifts SET Night_shift = '{shiftman_vacation[0][0]}' WHERE (Date BETWEEN '{vacation_start_date}' AND '{vacation_end_date}') AND Night_shift LIKE '%{person_vacation}'")
    cursor.execute(
        f"UPDATE Shifts SET Day_shift = '{shiftman_vacation[0][0]}' WHERE (Date BETWEEN '{vacation_start_date}' AND '{vacation_end_date}') AND Day_shift LIKE '%{person_vacation}'")
    connection.commit()
    connection.close()
    await callback.message.edit_text(text='Данные обновлены. Хорошего отпуска')


if __name__ == '__main__':
    dp.run_polling(bot)
