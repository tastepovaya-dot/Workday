from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = Path("workday_tracker.csv")

COLUMNS = ["date", "category", "task", "minutes"]

CATEGORIES = [
    "Иностранный язык",
    "Программирование",
    "Рабочие задачи",
]


def load_data() -> pd.DataFrame:
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=COLUMNS)


def save_data(data: pd.DataFrame) -> None:
    data.to_csv(DATA_FILE, index=False)


def add_task(data: pd.DataFrame, category: str, task: str, minutes: int) -> pd.DataFrame:
    new_row = pd.DataFrame(
        [{
            "date": date.today().isoformat(),
            "category": category,
            "task": task,
            "minutes": minutes,
        }]
    )
    return pd.concat([data, new_row], ignore_index=True)


def get_today_data(data: pd.DataFrame) -> pd.DataFrame:
    return data[data["date"] == date.today().isoformat()].copy()


def get_day_summary(today_data: pd.DataFrame) -> pd.DataFrame:
    summary = (
        today_data
        .groupby("category", as_index=False)["minutes"]
        .sum()
    )

    all_categories = pd.DataFrame({"category": CATEGORIES})
    summary = all_categories.merge(summary, on="category", how="left")

    summary["minutes"] = summary["minutes"].fillna(0).astype(int)
    summary["hours"] = (summary["minutes"] / 60).round(2)

    return summary


def get_history(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame()

    history = data.pivot_table(
        index="date",
        columns="category",
        values="minutes",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    for category in CATEGORIES:
        if category not in history.columns:
            history[category] = 0

    history["Всего минут"] = history[CATEGORIES].sum(axis=1)
    history["Всего часов"] = (history["Всего минут"] / 60).round(2)
    history["Дата"] = pd.to_datetime(history["date"]).dt.strftime("%d-%m-%Y")

    return history[
        [
            "Дата",
            *CATEGORIES,
            "Всего минут",
            "Всего часов",
        ]
    ]


st.set_page_config(
    page_title="Трекер рабочего дня",
    page_icon="⏱️",
    layout="centered",
)

if "selected_category" not in st.session_state:
    st.session_state.selected_category = None

if "message" not in st.session_state:
    st.session_state.message = ""

if "show_result" not in st.session_state:
    st.session_state.show_result = False

st.title("⏱️ Трекер рабочего дня")
st.caption(
    "Записывай задачи и время, а приложение посчитает итог дня "
    "и сохранит историю."
)

data = load_data()

st.subheader("Добавить задачу")

task_text = st.text_input(
    "Задача",
    placeholder="Например: урок Python",
)

minutes = st.number_input(
    "Время, минут",
    min_value=1,
    step=5,
    value=30,
)

st.write("Категория")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("1. Иностранный язык", use_container_width=True):
        st.session_state.selected_category = CATEGORIES[0]

with col2:
    if st.button("2. Программирование", use_container_width=True):
        st.session_state.selected_category = CATEGORIES[1]

with col3:
    if st.button("3. Рабочие задачи", use_container_width=True):
        st.session_state.selected_category = CATEGORIES[2]

if st.session_state.selected_category:
    st.info(f"Выбрано: {st.session_state.selected_category}")
else:
    st.warning("Сначала выбери категорию.")

if st.button("Добавить задачу", type="primary", use_container_width=True):
    if not task_text.strip():
        st.error("Введите название задачи.")
    elif st.session_state.selected_category is None:
        st.error("Выберите категорию.")
    else:
        data = add_task(
            data=data,
            category=st.session_state.selected_category,
            task=task_text.strip(),
            minutes=int(minutes),
        )
        save_data(data)
        st.session_state.selected_category = None
        st.session_state.message = "Задача добавлена."
        st.rerun()

if st.session_state.message:
    st.success(st.session_state.message)
    st.session_state.message = ""

st.divider()

today_data = get_today_data(data)

st.subheader(f"Сегодня — {date.today().strftime('%d-%m-%Y')}")

if today_data.empty:
    st.write("Сегодня пока нет записей.")
else:
    today_table = today_data[["category", "task", "minutes"]].copy()
    today_table.columns = ["Категория", "Задача", "Минуты"]
    st.dataframe(today_table, use_container_width=True, hide_index=True)

st.divider()

if st.button("4. Результат дня", use_container_width=True):
    st.session_state.show_result = True

if st.session_state.show_result:
    st.subheader("Результат дня")

    if today_data.empty:
        st.write("Сегодня ещё нет записей.")
    else:
        summary = get_day_summary(today_data)

        for _, row in summary.iterrows():
            st.write(
                f"**{row['category']}** — "
                f"{row['minutes']} мин. / {row['hours']} ч"
            )

        total_minutes = int(today_data["minutes"].sum())
        total_hours = round(total_minutes / 60, 2)

        st.metric(
            "Всего за день",
            f"{total_hours} ч",
            f"{total_minutes} мин.",
        )

st.divider()

st.subheader("История дней")

history = get_history(data)

if history.empty:
    st.write("История пока пуста.")
else:
    st.dataframe(history, use_container_width=True, hide_index=True)

    chart_data = history.set_index("Дата")[["Всего часов"]]
    st.bar_chart(chart_data)

st.divider()

with st.expander("Резервная копия"):
    st.write(
        "Можно иногда скачивать CSV-файл с историей как резервную копию."
    )

    csv_data = data.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Скачать workday_tracker.csv",
        data=csv_data,
        file_name="workday_tracker.csv",
        mime="text/csv",
    )

st.caption(
    "Важно: при размещении на бесплатном облачном хостинге "
    "локальный CSV может не быть постоянным хранилищем. "
    "Для полноценной версии позже лучше подключить базу данных."
)
