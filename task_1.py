class BloomFilter:
    def __init__(self, size, num_hashes):
        if not isinstance(size, int) or size <= 0:
            raise ValueError("size має бути додатним цілим числом")

        if not isinstance(num_hashes, int) or num_hashes <= 0:
            raise ValueError("num_hashes має бути додатним цілим числом")

        self.size = size
        self.num_hashes = num_hashes

        # Створюємо масив байтів для економії пам'яті
        self.bit_array = bytearray((size + 7) // 8)

    def _is_valid_item(self, item):
        # Перевіряємо, що пароль є непорожнім рядком
        return isinstance(item, str) and item != ""

    def _hashes(self, item):
        # Створюємо кілька простих хеш-функцій через різні seed
        for seed in range(self.num_hashes):
            value = 0
            text = f"{seed}:{item}"

            for char in text:
                value = (value * 31 + ord(char)) % self.size

            yield value

    def _set_bit(self, index):
        # Встановлюємо потрібний біт
        byte_index = index // 8
        bit_index = index % 8
        self.bit_array[byte_index] |= 1 << bit_index

    def _get_bit(self, index):
        # Перевіряємо значення потрібного біта
        byte_index = index // 8
        bit_index = index % 8
        return (self.bit_array[byte_index] & (1 << bit_index)) != 0

    def add(self, item):
        # Додаємо елемент тільки якщо він коректний
        if not self._is_valid_item(item):
            return False

        for index in self._hashes(item):
            self._set_bit(index)

        return True

    def contains(self, item):
        # Некоректні значення не шукаємо у фільтрі
        if not self._is_valid_item(item):
            return False

        return all(self._get_bit(index) for index in self._hashes(item))


def check_password_uniqueness(bloom_filter, passwords):
    if not isinstance(bloom_filter, BloomFilter):
        raise TypeError("bloom_filter має бути екземпляром BloomFilter")

    results = {}

    if passwords is None:
        return results

    if isinstance(passwords, str):
        passwords = [passwords]

    try:
        iterator = iter(passwords)
    except TypeError:
        return {"input": "некоректний список паролів"}

    for password in iterator:
        key = password if isinstance(password, str) else str(password)

        if not isinstance(password, str) or password == "":
            results[key] = "некоректне значення"
        elif bloom_filter.contains(password):
            results[password] = "вже використаний"
        else:
            results[password] = "унікальний"

            # Додаємо новий пароль, щоб він вважався використаним надалі
            bloom_filter.add(password)

    return results


if __name__ == "__main__":
    # Ініціалізація фільтра Блума
    bloom = BloomFilter(size=1000, num_hashes=3)

    # Додавання існуючих паролів
    existing_passwords = ["password123", "admin123", "qwerty123"]

    for password in existing_passwords:
        bloom.add(password)

    # Перевірка нових паролів
    new_passwords_to_check = ["password123", "newpassword", "admin123", "guest"]
    results = check_password_uniqueness(bloom, new_passwords_to_check)

    # Виведення результатів
    for password, status in results.items():
        print(f"Пароль '{password}' - {status}.")