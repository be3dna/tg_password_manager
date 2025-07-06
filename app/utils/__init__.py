import random
import string


def generate_password():
    # Определяем количество символов
    num_special_chars = random.randint(1, 3)  # от 1 до 3 специальных символов
    num_digits = random.randint(1, 3)           # от 1 до 3 цифр
    num_letters = 12 - num_special_chars - num_digits  # оставшиеся символы - буквы

    # Генерируем символы
    special_chars = random.choices(string.punctuation, k=num_special_chars)
    digits = random.choices(string.digits, k=num_digits)
    letters = random.choices(string.ascii_letters, k=num_letters)

    # Объединяем все символы
    password_list = special_chars + digits + letters

    # Перемешиваем символы
    random.shuffle(password_list)

    # Преобразуем список в строку
    password = ''.join(password_list)
    return password