"""
D05 — Аналитический дашборд для интернет-магазина
Streamlit + Pandas + Plotly
Метрики, графики, фильтры — всё для владельца бизнеса.

Запуск локально: streamlit run dashboard.py
Деплой: Streamlit Cloud (бесплатно)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# ── Настройки страницы ─────────────────────────────────────
st.set_page_config(
    page_title="AI-Аналитика — Интернет-магазин",
    page_icon="📊",
    layout="wide",
)

# ── Генерация демо-данных ──────────────────────────────────
@st.cache_data
def generate_data():
    """Генерирует реалистичные данные продаж за 90 дней"""
    random.seed(42)

    categories = {
        "Электроника": ["Наушники", "Зарядка USB-C", "Чехол для телефона", "Повербанк", "Кабель Lightning"],
        "Одежда": ["Футболка", "Худи", "Носки (3 пары)", "Кепка", "Шоппер"],
        "Дом и сад": ["Кашпо керамика", "Свеча ароматическая", "Плед", "Подставка для ноутбука", "Органайзер"],
        "Спорт": ["Бутылка для воды", "Фитнес-резинки", "Коврик для йоги", "Скакалка", "Полотенце спортивное"],
    }

    prices = {
        "Наушники": 2490, "Зарядка USB-C": 890, "Чехол для телефона": 590,
        "Повербанк": 1990, "Кабель Lightning": 490,
        "Футболка": 1290, "Худи": 2990, "Носки (3 пары)": 490,
        "Кепка": 890, "Шоппер": 690,
        "Кашпо керамика": 1490, "Свеча ароматическая": 790, "Плед": 2490,
        "Подставка для ноутбука": 1890, "Органайзер": 990,
        "Бутылка для воды": 690, "Фитнес-резинки": 890, "Коврик для йоги": 1590,
        "Скакалка": 490, "Полотенце спортивное": 590,
    }

    sources = ["Яндекс Директ", "Органический поиск", "Соцсети", "Прямой заход", "Реферал"]

    orders = []
    base_date = datetime.now() - timedelta(days=90)

    for day_offset in range(90):
        date = base_date + timedelta(days=day_offset)
        weekday = date.weekday()

        # Больше заказов в будни и в конце месяца
        base_orders = random.randint(8, 18)
        if weekday >= 5:  # выходные — чуть меньше
            base_orders = random.randint(5, 12)
        if date.day > 25:  # конец месяца — больше
            base_orders += random.randint(2, 5)

        for _ in range(base_orders):
            category = random.choice(list(categories.keys()))
            product = random.choice(categories[category])
            qty = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
            price = prices[product]
            source = random.choices(sources, weights=[30, 25, 20, 15, 10])[0]

            orders.append({
                "date": date.strftime("%Y-%m-%d"),
                "order_id": f"ORD-{random.randint(10000, 99999)}",
                "product": product,
                "category": category,
                "quantity": qty,
                "price": price,
                "revenue": price * qty,
                "source": source,
            })

    return pd.DataFrame(orders)


# ── Загрузка данных ────────────────────────────────────────
df = generate_data()
df["date"] = pd.to_datetime(df["date"])


# ── Заголовок ──────────────────────────────────────────────
st.markdown("## 📊 Аналитика интернет-магазина")
st.markdown("Дашборд для владельца бизнеса: выручка, заказы, товары, источники трафика.")
st.divider()


# ── Фильтры (сайдбар) ─────────────────────────────────────
st.sidebar.header("🔎 Фильтры")

# Период
min_date = df["date"].min().date()
max_date = df["date"].max().date()
date_range = st.sidebar.date_input(
    "Период",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Категория
all_categories = ["Все"] + sorted(df["category"].unique().tolist())
selected_category = st.sidebar.selectbox("Категория", all_categories)

# Источник трафика
all_sources = ["Все"] + sorted(df["source"].unique().tolist())
selected_source = st.sidebar.selectbox("Источник трафика", all_sources)


# ── Применение фильтров ───────────────────────────────────
filtered = df.copy()

if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["date"].dt.date >= start) & (filtered["date"].dt.date <= end)]

if selected_category != "Все":
    filtered = filtered[filtered["category"] == selected_category]

if selected_source != "Все":
    filtered = filtered[filtered["source"] == selected_source]


# ── Метрики (KPI) ─────────────────────────────────────────
total_revenue = filtered["revenue"].sum()
total_orders = filtered["order_id"].nunique()
avg_check = total_revenue / total_orders if total_orders > 0 else 0
total_items = filtered["quantity"].sum()

# Дельта — сравнение с предыдущим периодом
if len(date_range) == 2:
    period_days = (end - start).days
    prev_start = start - timedelta(days=period_days)
    prev_end = start - timedelta(days=1)
    prev = df[(df["date"].dt.date >= prev_start) & (df["date"].dt.date <= prev_end)]

    if selected_category != "Все":
        prev = prev[prev["category"] == selected_category]
    if selected_source != "Все":
        prev = prev[prev["source"] == selected_source]

    prev_revenue = prev["revenue"].sum()
    prev_orders = prev["order_id"].nunique()
    prev_avg = prev_revenue / prev_orders if prev_orders > 0 else 0

    rev_delta = f"{((total_revenue - prev_revenue) / prev_revenue * 100):+.1f}%" if prev_revenue else None
    ord_delta = f"{((total_orders - prev_orders) / prev_orders * 100):+.1f}%" if prev_orders else None
    avg_delta = f"{((avg_check - prev_avg) / prev_avg * 100):+.1f}%" if prev_avg else None
else:
    rev_delta = ord_delta = avg_delta = None

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Выручка", f"{total_revenue:,.0f} ₽".replace(",", " "), rev_delta)
col2.metric("📦 Заказов", f"{total_orders:,}".replace(",", " "), ord_delta)
col3.metric("🧾 Средний чек", f"{avg_check:,.0f} ₽".replace(",", " "), avg_delta)
col4.metric("📋 Товаров продано", f"{total_items:,}".replace(",", " "))

st.divider()


# ── Графики ────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

# 1. Выручка по дням (линейный)
with chart_col1:
    st.markdown("### 📈 Выручка по дням")
    daily = filtered.groupby(filtered["date"].dt.date)["revenue"].sum().reset_index()
    daily.columns = ["Дата", "Выручка"]

    fig1 = px.line(
        daily, x="Дата", y="Выручка",
        labels={"Выручка": "Выручка, ₽"},
    )
    fig1.update_traces(line_color="#6C5CE7", line_width=2)
    fig1.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig1, use_container_width=True)


# 2. Топ-5 товаров по продажам (бар-чарт)
with chart_col2:
    st.markdown("### 🏆 Топ-5 товаров по выручке")
    top_products = (
        filtered.groupby("product")["revenue"]
        .sum()
        .sort_values(ascending=True)
        .tail(5)
        .reset_index()
    )
    top_products.columns = ["Товар", "Выручка"]

    fig2 = px.bar(
        top_products, x="Выручка", y="Товар",
        orientation="h",
        labels={"Выручка": "Выручка, ₽"},
        color_discrete_sequence=["#00B894"],
    )
    fig2.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(categoryorder="total ascending"),
    )
    st.plotly_chart(fig2, use_container_width=True)


# ── Второй ряд графиков ───────────────────────────────────
chart_col3, chart_col4 = st.columns(2)

# 3. Выручка по категориям (пай-чарт)
with chart_col3:
    st.markdown("### 🗂 Выручка по категориям")
    cat_rev = filtered.groupby("category")["revenue"].sum().reset_index()
    cat_rev.columns = ["Категория", "Выручка"]

    fig3 = px.pie(
        cat_rev, values="Выручка", names="Категория",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hole=0.4,
    )
    fig3.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)


# 4. Источники трафика
with chart_col4:
    st.markdown("### 🌐 Заказы по источникам трафика")
    source_orders = (
        filtered.groupby("source")["order_id"]
        .nunique()
        .sort_values(ascending=True)
        .reset_index()
    )
    source_orders.columns = ["Источник", "Заказов"]

    fig4 = px.bar(
        source_orders, x="Заказов", y="Источник",
        orientation="h",
        color_discrete_sequence=["#FDCB6E"],
    )
    fig4.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig4, use_container_width=True)


# ── Таблица данных ─────────────────────────────────────────
st.divider()

with st.expander("📋 Данные (таблица)", expanded=False):
    display_df = filtered[["date", "order_id", "product", "category", "quantity", "price", "revenue", "source"]].copy()
    display_df.columns = ["Дата", "Заказ", "Товар", "Категория", "Кол-во", "Цена", "Выручка", "Источник"]
    display_df = display_df.sort_values("Дата", ascending=False)
    st.dataframe(display_df, use_container_width=True, height=400)


# ── Футер ──────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center; color:#888; font-size:13px;'>"
    "AI-Агентство · Аналитический дашборд · Демо-данные"
    "</div>",
    unsafe_allow_html=True,
)
