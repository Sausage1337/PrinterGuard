import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

DB_FILE = "office.db"

def plot_cartridge_usage():
    """Построить график расхода картриджей по месяцам."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT datetime, writeoff_cartridge FROM writeoff_history WHERE writeoff_cartridge > 0",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных о списании картриджей.")
        return
    df["date"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    usage = df.groupby("date")["writeoff_cartridge"].sum()
    usage.plot(kind="bar", title="Расход картриджей по месяцам", ylabel="Штук", xlabel="Месяц")
    plt.tight_layout()
    plt.show()

def plot_drum_usage():
    """Построить график расхода драмов по месяцам."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT datetime, writeoff_drum FROM writeoff_history WHERE writeoff_drum > 0",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных о списании драмов.")
        return
    df["date"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    usage = df.groupby("date")["writeoff_drum"].sum()
    usage.plot(kind="bar", title="Расход драмов по месяцам", ylabel="Штук", xlabel="Месяц")
    plt.tight_layout()
    plt.show()

def top5_cartridge_models():
    """Вывести топ-5 расходуемых моделей картриджей."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        """SELECT p.cartridge AS model, SUM(w.writeoff_cartridge) AS total
        FROM writeoff_history w
        JOIN printers p ON w.printer_id = p.id
        WHERE w.writeoff_cartridge > 0
        GROUP BY p.cartridge
        ORDER BY total DESC
        LIMIT 5""",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных по расходу картриджей.")
        return
    print("Топ-5 моделей картриджей по расходу:")
    print(df.to_string(index=False))

def top5_drum_models():
    """Вывести топ-5 расходуемых моделей драмов."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        """SELECT p.drum AS model, SUM(w.writeoff_drum) AS total
        FROM writeoff_history w
        JOIN printers p ON w.printer_id = p.id
        WHERE w.writeoff_drum > 0
        GROUP BY p.drum
        ORDER BY total DESC
        LIMIT 5""",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных по расходу драмов.")
        return
    print("Топ-5 моделей драмов по расходу:")
    print(df.to_string(index=False))

def forecast_next_month(model_name, type_):
    """
    Прогноз расхода расходника model_name (type_ = 'cartridge' или 'drum') на следующий месяц.
    """
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        f"""
        SELECT w.datetime, w.writeoff_cartridge, w.writeoff_drum
        FROM writeoff_history w
        JOIN printers p ON w.printer_id = p.id
        WHERE p.{type_} = ?
        """,
        conn, params=(model_name,)
    )
    conn.close()
    if df.empty:
        print(f"Нет списаний по {model_name} ({type_}).")
        return
    col = "writeoff_cartridge" if type_ == "cartridge" else "writeoff_drum"
    df["date"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    monthly = df.groupby("date")[col].sum()
    avg = monthly.tail(3).mean()
    print(f"Средний расход {model_name} за месяц: {avg:.1f}")
    print(f"Рекомендуемый запас на 1 месяц: {round(avg * 1.2)} (с запасом)")

def export_cartridge_usage_to_excel():
    """Экспортировать помесячную статистику расхода картриджей в Excel."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT datetime, writeoff_cartridge FROM writeoff_history WHERE writeoff_cartridge > 0",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных для экспорта.")
        return
    df["date"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    usage = df.groupby("date")["writeoff_cartridge"].sum()
    usage.to_excel("cartridge_usage.xlsx")
    print("Готово! Файл cartridge_usage.xlsx сохранён.")

def export_drum_usage_to_excel():
    """Экспортировать помесячную статистику расхода драмов в Excel."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT datetime, writeoff_drum FROM writeoff_history WHERE writeoff_drum > 0",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных для экспорта.")
        return
    df["date"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    usage = df.groupby("date")["writeoff_drum"].sum()
    usage.to_excel("drum_usage.xlsx")
    print("Готово! Файл drum_usage.xlsx сохранён.")

def save_cartridge_usage_plot():
    """Сохранить график расхода картриджей в PNG."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT datetime, writeoff_cartridge FROM writeoff_history WHERE writeoff_cartridge > 0",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных.")
        return
    df["date"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    usage = df.groupby("date")["writeoff_cartridge"].sum()
    usage.plot(kind="bar", title="Расход картриджей по месяцам", ylabel="Штук", xlabel="Месяц")
    plt.tight_layout()
    plt.savefig("cartridge_usage.png")
    plt.close()
    print("График сохранён в файл cartridge_usage.png")

def save_drum_usage_plot():
    """Сохранить график расхода драмов в PNG."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT datetime, writeoff_drum FROM writeoff_history WHERE writeoff_drum > 0",
        conn
    )
    conn.close()
    if df.empty:
        print("Нет данных.")
        return
    df["date"] = pd.to_datetime(df["datetime"]).dt.to_period("M")
    usage = df.groupby("date")["writeoff_drum"].sum()
    usage.plot(kind="bar", title="Расход драмов по месяцам", ylabel="Штук", xlabel="Месяц")
    plt.tight_layout()
    plt.savefig("drum_usage.png")
    plt.close()
    print("График сохранён в файл drum_usage.png")

if __name__ == "__main__":
    print("Аналитика:\n1. График картриджей\n2. График драмов\n3. Топ-5 картриджей\n4. Топ-5 драмов\n5. Прогноз\n6. Экспорт в Excel\n7. Сохранить график")
    print("Для вызова функций импортируйте analytics.py или раскомментируйте нужные вызовы.")
    # Пример:
    # plot_cartridge_usage()
    # top5_cartridge_models()
    # forecast_next_month("Canon 725", "cartridge")