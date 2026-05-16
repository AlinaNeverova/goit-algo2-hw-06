import json
import math
import time
import hashlib
import ipaddress
from pathlib import Path


LOG_FILE = "lms-stage-access.log"


def is_valid_ip(value):
    # Перевіряємо, що значення є коректною IP-адресою
    if not isinstance(value, str) or value.strip() == "":
        return False

    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def load_ip_addresses(file_path):
    # Читаємо файл построково, щоб не завантажувати все у пам'ять
    path = Path(file_path)

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            ip = row.get("remote_addr")

            if is_valid_ip(ip):
                yield ip.strip()


def exact_count_unique_ips(file_path):
    # Рахуємо унікальні IP через set
    start_time = time.perf_counter()

    unique_ips = set()

    for ip in load_ip_addresses(file_path):
        unique_ips.add(ip)

    elapsed_time = time.perf_counter() - start_time

    return len(unique_ips), elapsed_time


class HyperLogLog:
    def __init__(self, p=14):
        if not isinstance(p, int) or p < 4 or p > 20:
            raise ValueError("p має бути цілим числом від 4 до 20")

        self.p = p
        self.m = 1 << p

        # Зберігаємо регістри у bytearray для економії пам'яті
        self.registers = bytearray(self.m)

        if self.m == 16:
            self.alpha = 0.673
        elif self.m == 32:
            self.alpha = 0.697
        elif self.m == 64:
            self.alpha = 0.709
        else:
            self.alpha = 0.7213 / (1 + 1.079 / self.m)

    def _hash(self, value):
        # Отримуємо стабільний хеш для одного й того самого рядка
        digest = hashlib.sha1(value.encode("utf-8")).digest()
        return int.from_bytes(digest, byteorder="big")

    def add(self, value):
        # Додаємо значення до HyperLogLog
        if not isinstance(value, str):
            return

        hash_value = self._hash(value)

        index = hash_value >> (160 - self.p)

        remaining_bits_count = 160 - self.p
        remaining_bits = hash_value & ((1 << remaining_bits_count) - 1)

        if remaining_bits == 0:
            rank = remaining_bits_count + 1
        else:
            rank = remaining_bits_count - remaining_bits.bit_length() + 1

        if rank > self.registers[index]:
            self.registers[index] = rank

    def count(self):
        # Обчислюємо наближену кількість унікальних елементів
        indicator_sum = 0

        for register in self.registers:
            indicator_sum += 2.0 ** (-register)

        raw_estimate = self.alpha * self.m * self.m / indicator_sum

        zero_registers = self.registers.count(0)

        if raw_estimate <= 2.5 * self.m and zero_registers > 0:
            return self.m * math.log(self.m / zero_registers)

        return raw_estimate


def hyperloglog_count_unique_ips(file_path, p=14):
    # Рахуємо унікальні IP через HyperLogLog
    start_time = time.perf_counter()

    hll = HyperLogLog(p=p)

    for ip in load_ip_addresses(file_path):
        hll.add(ip)

    unique_count = hll.count()
    elapsed_time = time.perf_counter() - start_time

    return unique_count, elapsed_time


def print_results(exact_count, exact_time, hll_count, hll_time):
    # Виводимо результати у вигляді таблиці
    if exact_count == 0:
        error_percent = 0
    else:
        error_percent = abs(hll_count - exact_count) / exact_count * 100

    print("Результати порівняння:")
    print(f"{'':30}{'Точний підрахунок':>20}{'HyperLogLog':>15}")
    print(f"{'Унікальні елементи':30}{float(exact_count):>20.1f}{float(hll_count):>15.1f}")
    print(f"{'Час виконання (сек.)':30}{exact_time:>20.4f}{hll_time:>15.4f}")
    print(f"{'Похибка HyperLogLog (%)':30}{'':>20}{error_percent:>15.2f}")


if __name__ == "__main__":
    file_path = Path(LOG_FILE)

    if not file_path.exists():
        print(f"Файл '{LOG_FILE}' не знайдено.")
        print("Переконайтесь, що файл lms-stage-access.log лежить у корені проєкту.")
    else:
        exact_count, exact_time = exact_count_unique_ips(file_path)
        hll_count, hll_time = hyperloglog_count_unique_ips(file_path)

        print_results(exact_count, exact_time, hll_count, hll_time)