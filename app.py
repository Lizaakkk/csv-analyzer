import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

# Настройка страницы
st.set_page_config(
    page_title="Анализ CSV-файлов",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Заголовок приложения
st.title("Анализ CSV-файлов")
st.markdown("Загрузите CSV-файл для анализа данных")

# Инициализация состояния сеанса
if "df" not in st.session_state:
    st.session_state.df = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "column_types" not in st.session_state:
    st.session_state.column_types = {}


# Функция для безопасной загрузки CSV
@st.cache_data
def load_csv(file, encodings=["utf-8", "cp1251", "iso-8859-1"]):
    for encoding in encodings:
        try:
            for sep in [',', ';', '\t', '|']:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, encoding=encoding, sep=sep)
                    if len(df.columns) > 1:
                        return df, encoding, sep
                except:
                    continue
        except:
            continue
    return None, None, None


# Функция для определения типа столбца
def get_column_type(series):
    # Сначала проверяем на числовой тип
    try:
        numeric_result = pd.to_numeric(series, errors='coerce')
        # Если больше 80% значений успешно преобразовались - это числовой столбец
        if numeric_result.notna().sum() / len(series) > 0.8:
            return "numeric"
    except:
        pass

    # Проверяем на дату
    try:
        sample = series.dropna().head(10)
        if len(sample) > 0:
            sample_str = sample.astype(str)
            # Проверяем наличие типичных паттернов дат
            date_patterns = [
                sample_str.str.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}').any(),
                sample_str.str.match(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}').any(),
                sample_str.str.contains(r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', case=False).any()
            ]
            if any(date_patterns):
                # Проверяем, что это не просто числа с разделителями
                if not numeric_result.notna().all():
                    return "datetime"
    except:
        pass

    return "text"


# Функция для статистического анализа
@st.cache_data
def calculate_statistics(df, column, col_type):
    if col_type == "numeric":
        data = pd.to_numeric(df[column], errors='coerce').dropna()
        if len(data) > 0:
            stats = {
                "Тип": "Числовой",
                "Количество значений": len(data),
                "Количество уникальных": data.nunique(),
                "Среднее": round(data.mean(), 2),
                "Медиана": round(data.median(), 2),
                "Стандартное отклонение": round(data.std(), 2),
                "Минимум": round(data.min(), 2),
                "Максимум": round(data.max(), 2)
            }
        else:
            stats = {"Ошибка": "Нет числовых данных"}
    elif col_type == "datetime":
        try:
            data = pd.to_datetime(df[column], errors='coerce').dropna()
            if len(data) > 0:
                stats = {
                    "Тип": "Дата/время",
                    "Количество значений": len(data),
                    "Количество уникальных": data.nunique(),
                    "Минимальная дата": data.min().strftime("%Y-%m-%d"),
                    "Максимальная дата": data.max().strftime("%Y-%m-%d")
                }
            else:
                stats = {"Ошибка": "Нет данных для анализа"}
        except:
            stats = {"Ошибка": "Не удалось преобразовать даты"}
    else:
        data = df[column].dropna()
        top_values = data.value_counts().head(3).to_dict()
        top_values_str = ", ".join([f"{k}: {v}" for k, v in top_values.items()])
        stats = {
            "Тип": "Текстовый",
            "Количество значений": len(data),
            "Количество уникальных": data.nunique(),
            "Наиболее частые": top_values_str
        }

    return stats


# Функция для преобразования в числовой тип
def safe_numeric(series):
    return pd.to_numeric(series, errors='coerce')


# Боковая панель
with st.sidebar:
    st.header("Загрузка данных")

    uploaded_file = st.file_uploader(
        "Выберите CSV-файл",
        type=["csv"],
        help="Поддерживаются файлы с кодировками UTF-8, Windows-1251, ISO-8859-1"
    )

    if uploaded_file is not None:
        if st.session_state.file_name != uploaded_file.name:
            with st.spinner("Загружаем файл..."):
                df, encoding, separator = load_csv(uploaded_file)
                if df is not None:
                    st.session_state.df = df
                    st.session_state.file_name = uploaded_file.name
                    # Определяем типы для всех столбцов один раз
                    st.session_state.column_types = {}
                    for col in df.columns:
                        st.session_state.column_types[col] = get_column_type(df[col])
                    st.success(f"Файл загружен! Кодировка: {encoding}, Разделитель: '{separator}'")
                else:
                    st.error("Не удалось загрузить файл. Проверьте формат.")

    if st.session_state.df is not None:
        st.markdown("---")
        st.info(f"**Текущий файл:** {st.session_state.file_name}")
        st.info(f"**Размер:** {st.session_state.df.shape[0]} строк × {st.session_state.df.shape[1]} столбцов")

# Основная область
if st.session_state.df is not None:
    df = st.session_state.df
    column_types = st.session_state.column_types

    tab1, tab2, tab3, tab4 = st.tabs(["Данные", "Статистика", "Графики", "Скачать"])

    # Вкладка 1: Данные
    with tab1:
        st.header("Просмотр данных")

        col1, col2 = st.columns(2)
        with col1:
            rows_to_show = st.number_input("Количество строк", min_value=5, max_value=100, value=10)
        with col2:
            show_full = st.checkbox("Показать полную таблицу", value=False)

        if show_full:
            st.dataframe(df, use_container_width=True)
        else:
            st.dataframe(df.head(rows_to_show), use_container_width=True)

        with st.expander("Информация о столбцах"):
            col_info = []
            for col in df.columns:
                col_type = column_types.get(col, "unknown")
                col_info.append({
                    "Столбец": col,
                    "Тип": col_type,
                    "Уникальных значений": df[col].nunique(),
                    "Пустых значений": df[col].isna().sum()
                })
            st.dataframe(pd.DataFrame(col_info), use_container_width=True, hide_index=True)

    # Вкладка 2: Статистика
    with tab2:
        st.header("Статистический анализ")

        # Разделяем столбцы по типам
        numeric_cols = [col for col, typ in column_types.items() if typ == "numeric"]
        datetime_cols = [col for col, typ in column_types.items() if typ == "datetime"]
        text_cols = [col for col, typ in column_types.items() if typ == "text"]

        all_cols = numeric_cols + datetime_cols + text_cols

        if all_cols:
            selected_col = st.selectbox("Выберите столбец для анализа", all_cols)

            if selected_col:
                col_type = column_types.get(selected_col, "text")
                stats = calculate_statistics(df, selected_col, col_type)

                st.subheader(f"Анализ столбца: {selected_col}")

                if "Ошибка" not in stats:
                    num_cols = 2
                    cols = st.columns(num_cols)

                    for i, (key, value) in enumerate(stats.items()):
                        with cols[i % num_cols]:
                            st.write(f"**{key}:** {value}")
                else:
                    st.error(stats["Ошибка"])

                # Дополнительные графики для числовых данных
                if col_type == "numeric":
                    st.subheader("Распределение данных")
                    numeric_data = safe_numeric(df[selected_col]).dropna()
                    if len(numeric_data) > 0:
                        fig = px.histogram(
                            x=numeric_data,
                            title=f"Распределение {selected_col}",
                            nbins=30
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        fig_box = px.box(y=numeric_data, title=f"Box-plot для {selected_col}")
                        st.plotly_chart(fig_box, use_container_width=True)

                elif col_type == "datetime":
                    st.subheader("Временной ряд")
                    try:
                        date_series = pd.to_datetime(df[selected_col], errors='coerce')
                        date_counts = date_series.dt.date.value_counts().sort_index()
                        if len(date_counts) > 0:
                            fig_date = px.line(
                                x=date_counts.index, y=date_counts.values,
                                title=f"Распределение по датам: {selected_col}"
                            )
                            st.plotly_chart(fig_date, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Не удалось построить временной ряд: {e}")

                elif col_type == "text":
                    st.subheader("Топ-10 частых значений")
                    top_values = df[selected_col].value_counts().head(10)
                    if len(top_values) > 0:
                        fig_text = px.bar(
                            x=top_values.values, y=top_values.index,
                            orientation='h',
                            title=f"Частота значений в {selected_col}"
                        )
                        st.plotly_chart(fig_text, use_container_width=True)
        else:
            st.warning("Нет столбцов для анализа")

    # Вкладка 3: Графики
    with tab3:
        st.header("Построение графиков")

        # Используем сохранённые типы
        numeric_for_charts = [col for col, typ in column_types.items() if typ == "numeric"]
        datetime_for_charts = [col for col, typ in column_types.items() if typ == "datetime"]

        if len(numeric_for_charts) >= 1:
            chart_type = st.selectbox(
                "Тип графика",
                ["Линейный график", "Точечная диаграмма", "Столбчатая диаграмма"]
            )

            col1, col2 = st.columns(2)

            with col1:
                x_options = datetime_for_charts + numeric_for_charts
                x_axis = st.selectbox("Ось X", x_options if x_options else numeric_for_charts)

            with col2:
                y_axis = st.selectbox("Ось Y", numeric_for_charts)

            if x_axis and y_axis:
                try:
                    plot_df = df.copy()
                    if x_axis in datetime_for_charts:
                        plot_df[x_axis] = pd.to_datetime(plot_df[x_axis], errors='coerce')
                    if y_axis in numeric_for_charts:
                        plot_df[y_axis] = safe_numeric(plot_df[y_axis])

                    plot_df = plot_df.dropna(subset=[x_axis, y_axis])

                    if len(plot_df) > 0:
                        if chart_type == "Линейный график":
                            fig = px.line(plot_df, x=x_axis, y=y_axis, title=f"{y_axis} от {x_axis}")
                            st.plotly_chart(fig, use_container_width=True)

                            img_bytes = fig.to_image(format="png", width=800, height=500)
                            st.download_button("Скачать график (PNG)", data=img_bytes,
                                               file_name="line_chart.png", mime="image/png")

                        elif chart_type == "Точечная диаграмма":
                            fig = px.scatter(plot_df, x=x_axis, y=y_axis,
                                             title=f"Диаграмма рассеяния: {x_axis} vs {y_axis}")
                            st.plotly_chart(fig, use_container_width=True)

                            img_bytes = fig.to_image(format="png", width=800, height=500)
                            st.download_button("Скачать график (PNG)", data=img_bytes,
                                               file_name="scatter_chart.png", mime="image/png")

                        elif chart_type == "Столбчатая диаграмма":
                            fig = px.bar(plot_df, x=x_axis, y=y_axis,
                                         title=f"Столбчатая диаграмма: {y_axis} по {x_axis}")
                            st.plotly_chart(fig, use_container_width=True)

                            img_bytes = fig.to_image(format="png", width=800, height=500)
                            st.download_button("Скачать график (PNG)", data=img_bytes,
                                               file_name="bar_chart.png", mime="image/png")
                    else:
                        st.warning("Нет данных после фильтрации")

                except Exception as e:
                    st.error(f"Ошибка: {str(e)}")
        else:
            st.warning("Нет числовых столбцов для построения графиков")

    # Вкладка 4: Скачать
    with tab4:
        st.header("Экспорт данных")

        col1, col2 = st.columns(2)

        with col1:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button("Скачать как CSV", data=csv_data,
                               file_name="exported_data.csv", mime="text/csv")

        with col2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
            excel_data = output.getvalue()
            st.download_button("Скачать как Excel", data=excel_data,
                               file_name="exported_data.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        st.subheader("Сводная статистика")

        numeric_for_stats = [col for col, typ in column_types.items() if typ == "numeric"]

        if numeric_for_stats:
            stats_df = df[numeric_for_stats].apply(safe_numeric)
            summary_stats = stats_df.describe().round(2)
            st.dataframe(summary_stats, use_container_width=True)
        else:
            st.info("Нет числовых столбцов для сводной статистики")

else:
    st.info("<- Загрузите CSV-файл с помощью боковой панели")
