import streamlit as st
import gpxpy
import pandas as pd
import numpy as np
from io import StringIO
from geopy.distance import geodesic

st.set_page_config(page_title="Strava GPX Анализ", layout="centered")
st.title("📊 Анализ пробежки из Strava GPX по расстоянию")

uploaded_file = st.file_uploader("Загрузите GPX-файл вашей тренировки", type="gpx")

if uploaded_file:
    gpx = gpxpy.parse(uploaded_file.read().decode("utf-8"))
    points = []

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                hr = None
                cadence = None
                if point.extensions:
                    for ext in point.extensions[0]:
                        tag = ext.tag.lower()
                        if 'hr' in tag:
                            hr = ext.text
                        elif 'cad' in tag:
                            cadence = ext.text
                points.append({
                    "time": point.time,
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "elevation": point.elevation,
                    "hr": pd.to_numeric(hr, errors='coerce'),
                    "cadence": pd.to_numeric(cadence, errors='coerce')
                })

    df = pd.DataFrame(points)
    df.dropna(subset=['time'], inplace=True)
    df["time"] = pd.to_datetime(df["time"])

    # Расчёт расстояния в метрах между точками
    dists = [0.0]
    for i in range(1, len(df)):
        coord1 = (df.loc[i - 1, "lat"], df.loc[i - 1, "lon"])
        coord2 = (df.loc[i, "lat"], df.loc[i, "lon"])
        dist = geodesic(coord1, coord2).meters
        dists.append(dist)
    df["delta_dist"] = dists
    df["distance"] = df["delta_dist"].cumsum()

    st.success("✅ Файл загружен и обработан. Укажите интервалы сегментов по расстоянию:")

    total_distance = int(df["distance"].iloc[-1])
    warmup_range = st.slider("Разминка (м)", 0, total_distance, (0, min(2000, total_distance)))
    interval_range = st.slider("Интервалы (м)", 0, total_distance, (warmup_range[1], min(warmup_range[1] + 1000, total_distance)))
    cooldown_range = st.slider("Заминка (м)", 0, total_distance, (interval_range[1], total_distance))

    def summarize_segment(start_dist, end_dist):
        seg = df[(df["distance"] >= start_dist) & (df["distance"] < end_dist)]
        duration = (seg["time"].iloc[-1] - seg["time"].iloc[0]).total_seconds()
        return {
            "Длительность (мин)": round(duration / 60, 1),
            "Средний пульс": round(seg["hr"].mean(), 1) if not seg["hr"].isna().all() else None,
            "Макс. пульс": round(seg["hr"].max(), 1) if not seg["hr"].isna().all() else None,
            "Средний каденс": round(seg["cadence"].mean(), 1) if not seg["cadence"].notna().sum() > 0 else None,
            "Дистанция (м)": round(end_dist - start_dist, 1)
        }

    summary = {
        "Разминка": summarize_segment(*warmup_range),
        "Интервалы": summarize_segment(*interval_range),
        "Заминка": summarize_segment(*cooldown_range)
    }

    st.subheader("📋 Результаты по сегментам")
    st.dataframe(pd.DataFrame(summary).T.style.format("{:.1f}"))

    st.caption("💡 Вы можете подстроить интервалы выше, чтобы получить более точную аналитику по вашей тренировке.")
