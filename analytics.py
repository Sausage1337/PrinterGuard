import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('QtAgg')  # Для PySide6 или PyQt5/6 GUI
import matplotlib.pyplot as plt
import datetime
import logging
from typing import List, Dict, Any, Optional

DB_FILE = "office.db"
logging.basicConfig(level=logging.ERROR)

def get_cartridge_usage_by_month() -> pd.DataFrame:
    """Возвращает DataFrame с расходом картриджей по месяцам."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT datetime, writeoff_cartridge FROM writeoff_history WHERE writeoff_cartridge > 0",
        conn
    )
    conn.close()
    if df.empty:
        return pd.DataFrame(columns=["month", "usage"])
    df["month"] = pd.to_datetime(df["datetime"], format="%Y-%m-%d %H:%M:%S").dt.to_period("M")
    usage = df.groupby("month")["writeoff_cartridge"].sum().reset_index()
    usage.rename(columns={"writeoff_cartridge": "usage"}, inplace=True)
    return usage

def get_top5_cartridge_models() -> pd.DataFrame:
    """Возвращает DataFrame с топ-5 моделей картриджей по расходу."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        """
        SELECT p.cartridge AS model, SUM(w.writeoff_cartridge) AS total
        FROM writeoff_history w
        JOIN printers p ON w.printer_id = p.id
        WHERE w.writeoff_cartridge > 0
        GROUP BY p.cartridge
        ORDER BY total DESC
        LIMIT 5
        """,
        conn
    )
    conn.close()
    return df

def get_cartridge_forecast(model_name: str) -> Optional[Dict[str, Any]]:
    """Прогноз расхода картриджа по модели на следующий месяц."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        """
        SELECT w.datetime, w.writeoff_cartridge
        FROM writeoff_history w
        JOIN printers p ON w.printer_id = p.id
        WHERE p.cartridge = ?
        """,
        conn, params=(model_name,)
    )
    conn.close()
    if df.empty:
        return None
    df["month"] = pd.to_datetime(df["datetime"], format="%Y-%m-%d %H:%M:%S").dt.to_period("M")
    monthly = df.groupby("month")["writeoff_cartridge"].sum()
    avg = monthly.tail(3).mean()
    return {
        "model": model_name,
        "avg_per_month": avg,
        "recommended_stock": round(avg * 1.2) if avg else 0
    }

def get_cartridge_change_report() -> List[Dict[str, Any]]:
    """Отчёт по заменам картриджей: кабинет, принтер, модель, дата последней замены, дней с замены, всего замен."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.name, p.cartridge, c.name as cabinet
        FROM printers p
        LEFT JOIN cabinets c ON p.cabinet_id = c.id
        ORDER BY cabinet, p.name
    """)
    printers = c.fetchall()
    report = []
    for pid, pname, cartr, cab in printers:
        c.execute("""
            SELECT datetime FROM writeoff_history
            WHERE printer_id=? AND writeoff_cartridge>0
            ORDER BY datetime DESC LIMIT 1
        """, (pid,))
        last_row = c.fetchone()
        c.execute("""
            SELECT COUNT(*) FROM writeoff_history
            WHERE printer_id=? AND writeoff_cartridge>0
        """, (pid,))
        total_changes = c.fetchone()[0]
        last_date_str = last_row[0] if last_row else None
        if last_date_str:
            last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d %H:%M:%S")
            days_ago = (datetime.datetime.now() - last_date).days
        else:
            days_ago = None
        report.append({
            "cabinet": cab or "-",
            "printer": pname,
            "cartridge": cartr or "-",
            "total_changes": total_changes,
            "last_change": last_date_str or "-",
            "days_since_last": days_ago if days_ago is not None else "-"
        })
    conn.close()
    return report

def plot_cartridge_usage(usage_df: pd.DataFrame):
    if usage_df.empty:
        return None
    usage_df.plot(x="month", y="usage", kind="bar", legend=False)
    plt.title("Расход картриджей по месяцам")
    plt.ylabel("Штук")
    plt.xlabel("Месяц")
    plt.tight_layout()
    plt.show()

def export_cartridge_usage_to_excel(usage_df: pd.DataFrame, filename: str = "cartridge_usage.xlsx"):
    if not usage_df.empty:
        usage_df.to_excel(filename, index=False)

def plot_drum_usage():
    """Построить график расхода драмов по месяцам."""
    try:
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
    except Exception as e:
        logging.error(f"Ошибка построения графика драмов: {e}")

def top5_cartridge_models():
    """Вывести топ-5 расходуемых моделей картриджей."""
    try:
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
    except Exception as e:
        logging.error(f"Ошибка топ-5 картриджей: {e}")

def top5_drum_models():
    """Вывести топ-5 расходуемых моделей драмов."""
    try:
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
    except Exception as e:
        logging.error(f"Ошибка топ-5 драмов: {e}")

def forecast_next_month(model_name, type_):
    """
    Прогноз расхода расходника model_name (type_ = 'cartridge' или 'drum') на следующий месяц.
    """
    try:
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
    except Exception as e:
        logging.error(f"Ошибка прогноза расхода: {e}")

def export_drum_usage_to_excel():
    """Экспортировать помесячную статистику расхода драмов в Excel."""
    try:
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
    except Exception as e:
        logging.error(f"Ошибка экспорта драмов: {e}")

def save_cartridge_usage_plot():
    """Сохранить график расхода картриджей в PNG."""
    try:
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
    except Exception as e:
        logging.error(f"Ошибка сохранения графика картриджей: {e}")

def save_drum_usage_plot():
    """Сохранить график расхода драмов в PNG."""
    try:
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
    except Exception as e:
        logging.error(f"Ошибка сохранения графика драмов: {e}")

def cartridge_change_report():
    """
    Подробный отчет по замене картриджей:
    - Кабинет, принтер, модель картриджа
    - Дата последней замены
    - Сколько дней прошло с последней замены
    - Всего замен за всю историю
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Получаем все принтеры с их кабинетами и моделями картриджей
    c.execute("""
        SELECT p.id, p.name, p.cartridge, c.name as cabinet
        FROM printers p
        LEFT JOIN cabinets c ON p.cabinet_id = c.id
        ORDER BY cabinet, p.name
    """)
    printers = c.fetchall()

    print("{:20} | {:20} | {:15} | {:10} | {:20} | {:10}".format(
        "Кабинет", "Принтер", "Картридж", "Замен", "Последняя замена", "Дней прошло"
    ))
    print("-"*110)
    for pid, pname, cartr, cab in printers:
        c.execute("""
            SELECT datetime FROM writeoff_history
            WHERE printer_id=? AND writeoff_cartridge>0
            ORDER BY datetime DESC LIMIT 1
        """, (pid,))
        last_row = c.fetchone()
        c.execute("""
            SELECT COUNT(*) FROM writeoff_history
            WHERE printer_id=? AND writeoff_cartridge>0
        """, (pid,))
        total_changes = c.fetchone()[0]

        last_date_str = last_row[0] if last_row else "—"
        if last_date_str != "—":
            last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d %H:%M:%S")
            days_ago = (datetime.datetime.now() - last_date).days
        else:
            days_ago = "—"
        print("{:20} | {:20} | {:15} | {:10} | {:20} | {:10}".format(
            cab or "-", pname, cartr or "-", total_changes, last_date_str, days_ago
        ))
    conn.close()

if __name__ == "__main__":
    print("Аналитика:\n1. График картриджей\n2. График драмов\n3. Топ-5 картриджей\n4. Топ-5 драмов\n5. Прогноз\n6. Экспорт в Excel\n7. Сохранить график\n8. Отчет по заменам картриджей")
    # Для вызова функций раскомментируйте нужные строки:
    # plot_cartridge_usage()
    # plot_drum_usage()
    # top5_cartridge_models()
    # top5_drum_models()
    # forecast_next_month("Canon 725", "cartridge")
    # export_cartridge_usage_to_excel()
    # export_drum_usage_to_excel()
    # save_cartridge_usage_plot()
    # save_drum_usage_plot()
    # cartridge_change_report()