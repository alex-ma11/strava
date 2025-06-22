import streamlit as st
import gpxpy
import pandas as pd
import numpy as np
from io import StringIO

st.set_page_config(page_title="Strava GPX Анализ", layout="centered")
st.title("📊 Анализ пробежки из Strava GPX")

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
    df["seconds"] = (df["time"] - df["time"].iloc[0]).dt.total_seconds()

    st.success("✅ Файл загружен и обработан. Укажите интервалы сегментов:")

    total_time = int(df["seconds"].iloc[-1])
    warmup_range = st.slider("Разминка (сек)", 0, total_time, (0, min(1200, total_time)))
    interval_range = st.slider("Интервалы (сек)", 0, total_time, (warmup_range[1], min(warmup_range[1]+600, total_time)))
    cooldown_range = st.slider("Заминка (сек)", 0, total_time, (interval_range[1], total_time))

    def summarize_segment(start, end):
        seg = df[(df["seconds"] >= start) & (df["seconds"] < end)]
        duration = end - start
        return {
            "Длительность (мин)": round(duration / 60, 1),
            "Средний пульс": round(seg["hr"].mean(), 1) if not seg["hr"].isna().all() else None,
            "Макс. пульс": round(seg["hr"].max(), 1) if not seg["hr"].isna().all() else None,
            "Средний каденс": round(seg["cadence"].mean(), 1) if not seg["cadence"].notna().sum() > 0 else None,
            "Длина сегмента (точек)": len(seg)
        }

    summary = {
        "Разминка": summarize_segment(*warmup_range),
        "Интервалы": summarize_segment(*interval_range),
        "Заминка": summarize_segment(*cooldown_range)
    }

    st.subheader("📋 Результаты по сегментам")
    st.dataframe(pd.DataFrame(summary).T.style.format("{:.1f}"))

    st.caption("💡 Вы можете подстроить интервалы выше, чтобы получить более точную аналитику по вашей тренировке.")
