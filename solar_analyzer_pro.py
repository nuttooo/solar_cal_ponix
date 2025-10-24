#!/usr/bin/env python3
"""
Solar Analyzer Pro
==================

Interactive end-to-end analysis tool for hybrid solar + battery systems.
The program loads quarter-hour energy consumption data, synthesises a solar
generation profile that preserves the configured array peak, and runs a
per-day battery dispatch simulation. Visual outputs are written to the
`output/` directory alongside textual summaries printed to stdout.

The original project was accidentally deleted. This file recreates the full
application based on the latest specification, including the corrected
evening-battery logic that discharges in real time against the 16:00-22:00
load window.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configure matplotlib defaults (Thai font friendly where available)
plt.rcParams["font.family"] = "Tahoma"
plt.rcParams["font.size"] = 10


class SolarAnalyzerPro:
    """
    Full-featured solar/battery analysis pipeline with interactive prompts.
    """

    def __init__(self) -> None:
        self.df: Optional[pd.DataFrame] = None
        self.solar_generation: Optional[np.ndarray] = None
        self.battery_analysis: Optional[List[Dict]] = None

        self.solar_capacity_mw: float = 3.0
        self.sun_hours: float = 4.0
        self.battery_threshold_w: float = 1500.0
        self.battery_size_kwh: float = 0.0  # 0 means auto-calculate

        self.output_dir = "output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"📁 สร้างโฟลเดอร์ {self.output_dir}/ สำหรับเก็บผลลัพธ์")

    # --------------------------------------------------------------------- #
    # Interactive configuration                                             #
    # --------------------------------------------------------------------- #
    def get_user_input(self) -> str:
        """
        Collect interactive settings from the user.
        """
        line = "=" * 64
        print(line)
        print("🌞 เครื่องมือวิเคราะห์ระบบโซลาร์เซลล์แบบโต้ตอบ 🌞")
        print("   Interactive Solar Cell System Analysis Tool")
        print(line)

        # Solar capacity (MWp)
        while True:
            text = input("📏 ขนาดระบบโซลาร์ (MWp) [Default: 3.0]: ").strip()
            if not text:
                self.solar_capacity_mw = 3.0
                break
            try:
                value = float(text)
                if value <= 0:
                    raise ValueError
                self.solar_capacity_mw = value
                break
            except ValueError:
                print("❌ กรุณาใส่ตัวเลขที่ถูกต้อง (เช่น 3.0, 5.5, 10)")
        print(f"✅ ขนาดระบบโซลาร์: {self.solar_capacity_mw:.2f} MWp")

        # Avg sunlight hours
        while True:
            text = input("☀️ ชั่วโมงแดดเฉลี่ย/วัน [Default: 4.0]: ").strip()
            if not text:
                self.sun_hours = 4.0
                break
            try:
                value = float(text)
                if value <= 0 or value > 12:
                    raise ValueError
                self.sun_hours = value
                break
            except ValueError:
                print("❌ ชั่วโมงแดดต้องอยู่ระหว่าง 0-12 ชั่วโมง")
        print(f"✅ ชั่วโมงแดดเฉลี่ย: {self.sun_hours:.1f} ชม./วัน")

        # Battery threshold
        while True:
            text = input("⚡ เกณฑ์เริ่มจ่ายแบต (W) [Default: 1500]: ").strip()
            if not text:
                self.battery_threshold_w = 1500.0
                break
            try:
                value = float(text)
                if value <= 0:
                    raise ValueError
                self.battery_threshold_w = value
                break
            except ValueError:
                print("❌ กรุณาใส่ตัวเลขที่ถูกต้อง (เช่น 1200, 1500, 2200)")
        print(f"✅ เกณฑ์เริ่มจ่ายแบต: {self.battery_threshold_w:.0f} W")

        # Battery size
        while True:
            text = input("🔋 ขนาดแบตเตอรี่ (kWh) [0=คำนวณอัตโนมัติ, Default: 0]: ").strip()
            if not text:
                self.battery_size_kwh = 0.0
                break
            try:
                value = float(text)
                if value < 0:
                    raise ValueError
                self.battery_size_kwh = value
                break
            except ValueError:
                print("❌ กรุณาใส่ตัวเลขที่ถูกต้อง (เช่น 10, 20.5, 50) หรือ 0 สำหรับคำนวณอัตโนมัติ")
        if self.battery_size_kwh > 0:
            print(f"✅ ขนาดแบตเตอรี่: {self.battery_size_kwh:.1f} kWh (กำหนดเอง)")
        else:
            print("✅ ขนาดแบตเตอรี่: คำนวณอัตโนมัติตามความต้องการ")

        print()
        print("📊 เลือกประเภทการวิเคราะห์:")
        print("1. กราฟรายวันพร้อมการวิเคราะห์แบตเตอรี่ (Daily + Battery)")
        print("2. กราฟรวม 7 วัน (Weekly Summary)")
        print("3. วิเคราะห์แบบสมบูรณ์ (Complete Analysis)")
        print()

        while True:
            choice = input("เลือก (1/2/3) [Default: 3]: ").strip() or "3"
            if choice in {"1", "2", "3"}:
                return choice
            print("❌ กรุณาเลือก 1, 2 หรือ 3")

    # --------------------------------------------------------------------- #
    # Data ingestion                                                        #
    # --------------------------------------------------------------------- #
    def load_and_parse_data(self, file_path: str = "data/kw.csv") -> bool:
        """
        Load the raw CSV and prepare time-series structure.
        """
        print(f"📂 กำลังโหลดข้อมูลจาก: {file_path}")
        if not os.path.exists(file_path):
            print(f"❌ ไม่พบไฟล์: {file_path}")
            return False

        # Try different encodings that might handle CSV files better
        encodings = ["utf-8-sig", "utf-8", "windows-1252", "iso-8859-1", "tis-620"]
        df = None
        
        for encoding in encodings:
            try:
                print(f"   กำลังลองใช้ encoding: {encoding}")
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"   ✅ อ่านไฟล์สำเร็จด้วย encoding: {encoding}")
                break
            except UnicodeDecodeError:
                print(f"   ❌ ไม่สามารถอ่านด้วย encoding: {encoding}")
                continue
            except Exception as exc:
                print(f"   ❌ ข้อผิดพลาดอื่นๆ กับ encoding {encoding}: {exc}")
                continue
        
        if df is None:
            print(f"❌ ไม่สามารถอ่านไฟล์ด้วย encoding ที่รองรับทั้งหมดได้: {encodings}")
            return False

        expected_cols = [
            "datetime",
            "rate_a",
            "empty1",
            "rate_b",
            "empty2",
            "rate_c",
            "empty3",
        ]
        df.columns = expected_cols[: len(df.columns)]

        datetime_str = df["datetime"].astype(str).str.strip()
        datetime_str = datetime_str.str.replace(" 24.00", " 00.00", regex=False)
        
        # Handle different date formats and add better error handling
        # First, convert Thai Buddhist years to Gregorian years
        def convert_thai_to_gregorian(date_str):
            if isinstance(date_str, str):
                # Split date and time
                parts = date_str.strip().split()
                if len(parts) >= 1:
                    date_part = parts[0]
                    time_part = parts[1] if len(parts) > 1 else "00.00"
                    
                    # Split date components
                    date_components = date_part.split('/')
                    if len(date_components) == 3:
                        try:
                            year = int(date_components[2])
                            # Convert Thai Buddhist year to Gregorian year
                            if year > 2500:  # Likely Thai Buddhist year
                                year = year - 543
                                date_components[2] = str(year)
                                new_date = '/'.join(date_components)
                                return f"{new_date} {time_part}"
                        except ValueError:
                            pass
            return date_str
        
        # Apply Thai year conversion
        converted_datetime_str = datetime_str.apply(convert_thai_to_gregorian)
        
        # Try different date formats
        try:
            df["datetime"] = pd.to_datetime(
                converted_datetime_str, format="%d/%m/%Y %H.%M", errors="coerce"
            )
        except:
            try:
                # Try alternative format
                df["datetime"] = pd.to_datetime(
                    converted_datetime_str, format="%d/%m/%Y %H:%M", errors="coerce"
                )
            except:
                try:
                    # Try parsing with dayfirst=True as fallback
                    df["datetime"] = pd.to_datetime(
                        converted_datetime_str, dayfirst=True, errors="coerce"
                    )
                except:
                    print("❌ ไม่สามารถแปลงวันที่ได้ด้วยวิธีใดๆ")
                    return False
        
        # Remove rows with invalid dates
        invalid_dates = df["datetime"].isna()
        if invalid_dates.any():
            print(f"⚠️ พบวันที่ไม่ถูกต้อง {invalid_dates.sum()} แถว กำลังลบออก...")
            df = df[~invalid_dates].copy()
            if df.empty:
                print("❌ ไม่มีข้อมูลที่ถูกต้องหลังจากการกรองวันที่ไม่ถูกต้อง")
                return False

        # Adjust rows that rolled over past midnight (originally 24:00)
        mask_midnight = datetime_str.str.contains("24.00", na=False)
        df.loc[mask_midnight, "datetime"] += pd.Timedelta(days=1)

        for col in ["rate_a", "rate_b", "rate_c"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df = df.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
        df["consumption"] = df["rate_a"] + df["rate_b"] + df["rate_c"]
        df["date"] = df["datetime"].dt.date

        self.df = df
        print(f"✅ โหลดข้อมูลสำเร็จ: {len(df)} แถว")
        print(
            f"📅 ช่วงเวลาในข้อมูล: {df['date'].min()} ถึง {df['date'].max()} "
            f"({df['date'].nunique()} วัน)"
        )
        return True

    # --------------------------------------------------------------------- #
    # Solar curve synthesis                                                 #
    # --------------------------------------------------------------------- #
    def create_solar_generation(self) -> None:
        """
        Build an idealised solar production profile (quarter-hourly) per day.
        Peak is preserved while sigma is tuned so that the daily energy matches
        the configured sun-hour energy budget.
        """
        if self.df is None or self.df.empty:
            raise RuntimeError("ต้องโหลดข้อมูลก่อนสร้างกราฟ Solar")

        print("🌞 กำลังสร้างข้อมูลการผลิตไฟฟ้าจากโซลาร์ (Peak Preserved)")
        solar_capacity_kw = self.solar_capacity_mw * 1000.0
        target_energy = solar_capacity_kw * float(self.sun_hours)

        sunrise, sunset = 6.0, 18.0
        t0 = 0.5 * (sunrise + sunset)

        hours = np.arange(0.0, 24.0, 0.25)

        def daily_energy_for_sigma(sig: float) -> float:
            mask = (hours >= sunrise) & (hours <= sunset)
            power = np.zeros_like(hours)
            z = (hours[mask] - t0) / sig
            power[mask] = solar_capacity_kw * 0.9 * np.exp(-0.5 * z**2)
            return float(np.trapz(power, dx=0.25))

        max_possible_energy = solar_capacity_kw * (sunset - sunrise)
        if target_energy > max_possible_energy:
            print(
                f"⚠️ พลังงานเป้าหมาย {target_energy:.1f} kWh สูงสุดไม่เกิน "
                f"{max_possible_energy:.1f} kWh ภายใต้พีค {solar_capacity_kw:.0f} kW"
            )
            target_energy = max_possible_energy

        lo, hi = 0.2, 20.0
        while daily_energy_for_sigma(hi) < target_energy and hi < 200:
            hi *= 2.0

        for _ in range(60):
            mid = 0.5 * (lo + hi)
            energy_mid = daily_energy_for_sigma(mid)
            if energy_mid < target_energy:
                lo = mid
            else:
                hi = mid
        sigma = 0.5 * (lo + hi)
        print(
            f"   → sigma ≈ {sigma:.3f} ชม., พลังงานต่อวัน {daily_energy_for_sigma(sigma):.1f} kWh"
        )

        unique_dates = self.df["date"].unique()
        template = np.zeros_like(hours)
        mask_template = (hours >= sunrise) & (hours <= sunset)
        z_template = (hours[mask_template] - t0) / sigma
        template[mask_template] = solar_capacity_kw * 0.9 * np.exp(-0.5 * z_template**2)

        all_days: List[np.ndarray] = []
        for date in unique_dates:
            all_days.append(template.copy())
            print(f"   ✅ {date}: พีค {np.max(template):.0f} kW")

        solar_series = np.concatenate(all_days)

        # Align with measurement length
        limit = min(len(self.df), len(solar_series))
        self.df = self.df.iloc[:limit].reset_index(drop=True)
        self.solar_generation = solar_series[:limit]
        print(f"✅ สร้างข้อมูลโซลาร์สำเร็จ: {limit} จุดเวลา")

    # --------------------------------------------------------------------- #
    # Battery analytics                                                     #
    # --------------------------------------------------------------------- #
    def calculate_daily_battery_requirements(self) -> None:
        """
        Compute per-day battery envelopes and supporting metrics.
        """
        if self.df is None or self.df.empty or self.solar_generation is None:
            raise RuntimeError("กรุณาโหลดข้อมูลและสร้างโซลาร์ก่อน")

        print("🔋 กำลังคำนวณความต้องการแบตเตอรี่...")
        unique_dates = self.df["date"].unique()
        analysis: List[Dict] = []

        for date in unique_dates:
            mask = self.df["date"] == date
            daily_consumption = self.df.loc[mask, "consumption"].to_numpy()
            daily_solar = self.solar_generation[mask]
            daily_datetime = self.df.loc[mask, "datetime"].reset_index(drop=True)

            power_difference = daily_solar - daily_consumption
            cumulative_balance = np.cumsum(power_difference) * 0.25

            max_excess = float(np.max(cumulative_balance))
            max_deficit = float(np.min(cumulative_balance))
            battery_size_needed = max(abs(max_excess), abs(max_deficit))

            total_excess_energy = float(
                np.trapz(np.maximum(0, power_difference), dx=0.25)
            )
            total_deficit_energy = float(
                np.trapz(np.maximum(0, -power_difference), dx=0.25)
            )
            net_energy_balance = total_excess_energy - total_deficit_energy
            
            # Use user-specified battery size if provided, otherwise calculate optimal size
            if self.battery_size_kwh > 0:
                optimal_battery_size = self.battery_size_kwh
            else:
                optimal_battery_size = battery_size_needed * 0.8

            consumption_area = float(np.trapz(daily_consumption, dx=0.25))
            solar_area = float(np.trapz(daily_solar, dx=0.25))

            solar_metrics = self.calculate_solar_metrics(
                daily_consumption,
                daily_solar,
                daily_datetime,
                power_difference,
            )

            analysis.append(
                {
                    "date": date,
                    "power_difference": power_difference,
                    "cumulative_balance": cumulative_balance,
                    "max_excess": max_excess,
                    "max_deficit": max_deficit,
                    "battery_size_needed": battery_size_needed,
                    "optimal_battery_size": optimal_battery_size,
                    "total_excess_energy": total_excess_energy,
                    "total_deficit_energy": total_deficit_energy,
                    "net_energy_balance": net_energy_balance,
                    "consumption_area": consumption_area,
                    "solar_area": solar_area,
                    **solar_metrics,
                }
            )

        self.battery_analysis = analysis
        print(f"✅ วิเคราะห์แบตเตอรี่เสร็จสิ้น: {len(analysis)} วัน")

    def calculate_solar_metrics(
        self,
        daily_consumption: np.ndarray,
        daily_solar: np.ndarray,
        daily_datetime: pd.Series,
        power_difference: np.ndarray,
    ) -> Dict[str, float]:
        """
        Extended solar/battery metrics for report annotations.
        """
        solar_produced_per_day = float(np.trapz(daily_solar, dx=0.25))

        # Direct solar consumption
        direct_use = 0.0
        for solar_kw, load_kw in zip(daily_solar, daily_consumption):
            direct_use += min(solar_kw, load_kw) * 0.25

        solar_to_battery = float(np.trapz(np.maximum(0.0, power_difference), dx=0.25))

        load_16_22 = 0.0
        threshold_kw = self.battery_threshold_w / 1000.0

        load_16_22_with_threshold = 0.0
        excess_above_threshold_area = 0.0
        battery_discharge_area = 0.0
        load_above_threshold_area = 0.0

        # Cap the available battery energy at the specified battery size
        if self.battery_size_kwh > 0:
            remaining_battery_energy = min(solar_to_battery, self.battery_size_kwh)
        else:
            remaining_battery_energy = solar_to_battery  # 100% round-trip efficiency

        for idx, (dt, load_kw, solar_kw) in enumerate(
            zip(daily_datetime, daily_consumption, daily_solar)
        ):
            hour = int(dt.hour)
            if 16 <= hour < 22:
                load_16_22 += load_kw * 0.25

            if solar_kw > threshold_kw:
                excess_above_threshold_area += (solar_kw - threshold_kw) * 0.25

            if 16 <= hour < 22:
                if load_kw > threshold_kw:
                    load_excess = load_kw - threshold_kw
                    load_above_threshold_area += load_excess * 0.25
                    energy_needed = load_excess * 0.25
                    discharge_energy = min(remaining_battery_energy, energy_needed)
                    battery_discharge_area += discharge_energy
                    remaining_battery_energy -= discharge_energy
                    uncovered_power = load_excess - discharge_energy / 0.25
                    effective_load = threshold_kw + max(0.0, uncovered_power)
                else:
                    effective_load = load_kw
                load_16_22_with_threshold += effective_load * 0.25

        return {
            "solar_produced_per_day": solar_produced_per_day,
            "solar_consumed_directly": float(direct_use),
            "solar_to_battery": solar_to_battery,
            "load_16_22": float(load_16_22),
            "load_16_22_with_battery_threshold": float(load_16_22_with_threshold),
            "excess_above_1500_area": float(excess_above_threshold_area),
            "battery_discharge_16_22_area": float(battery_discharge_area),
            "load_above_1500_area_16_22": float(load_above_threshold_area),
        }

    # --------------------------------------------------------------------- #
    # Visualisations                                                        #
    # --------------------------------------------------------------------- #
    def create_daily_graphs_with_battery(self) -> None:
        """
        For each day create a 4-panel plot summarising production, load,
        battery use, and cumulative energy balance.
        """
        if not self.battery_analysis:
            print("⚠️ ไม่มีข้อมูลแบตเตอรี่สำหรับสร้างกราฟรายวัน")
            return

        for day_data in self.battery_analysis:
            date = day_data["date"]
            mask = self.df["date"] == date
            daily_consumption = self.df.loc[mask, "consumption"]
            daily_solar = self.solar_generation[mask]
            daily_datetime = self.df.loc[mask, "datetime"]

            fig, axes = plt.subplots(4, 1, figsize=(16, 16))
            # Determine battery size description for title
            if self.battery_size_kwh > 0:
                battery_desc = f"ขนาดแบตเตอรี่ที่กำหนด: {self.battery_size_kwh:.0f} kWh"
            else:
                battery_desc = f"ขนาดแบตเตอรี่แนะนำ: {day_data['optimal_battery_size']:.0f} kWh"
            
            fig.suptitle(
                f"การวิเคราะห์กำลังไฟรายวันที่ {date}\n"
                f"โซลาร์ {self.solar_capacity_mw:.1f} MWp, แดด {self.sun_hours:.1f} ชม./วัน\n"
                f"{battery_desc}",
                fontsize=16,
                fontweight="bold",
            )

            threshold_kw = self.battery_threshold_w / 1000.0

            # Panel 1: Load vs Solar
            ax1 = axes[0]
            ax1.fill_between(
                daily_datetime, 0, daily_consumption, alpha=0.3, color="red", label="โหลด (kW)"
            )
            ax1.fill_between(
                daily_datetime,
                0,
                daily_solar,
                alpha=0.3,
                color="orange",
                label="โซลาร์ (kW)",
            )
            ax1.plot(daily_datetime, daily_consumption, color="red", linewidth=2)
            ax1.plot(daily_datetime, daily_solar, color="orange", linewidth=2)
            ax1.axhline(
                threshold_kw,
                color="purple",
                linestyle="--",
                linewidth=2,
                label=f"เกณฑ์ {self.battery_threshold_w:.0f} W",
            )

            exceed_solar = np.maximum(0, daily_solar - threshold_kw)
            ax1.fill_between(
                daily_datetime,
                threshold_kw,
                daily_solar,
                where=(daily_solar > threshold_kw),
                color="yellow",
                alpha=0.4,
                label=f"พลังงานเกิน: {day_data['excess_above_1500_area']:.0f} kWh",
            )
            ax1.axhline(y=0, color="black", linestyle="-", alpha=0.3)
            ax1.set_title("เปรียบเทียบกำลังไฟ (Power)")
            ax1.set_ylabel("กำลังไฟ (kW)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

            # Panel 2: Power difference (charging vs discharging)
            ax2 = axes[1]
            diff = day_data["power_difference"]
            positive_diff = np.maximum(0, diff)
            negative_diff = np.minimum(0, diff)
            ax2.fill_between(
                daily_datetime,
                0,
                positive_diff,
                where=positive_diff > 0,
                alpha=0.7,
                color="green",
                label="พลังงานเกิน (ชาร์จแบต)",
            )
            ax2.fill_between(
                daily_datetime,
                0,
                negative_diff,
                where=negative_diff < 0,
                alpha=0.7,
                color="blue",
                label="พลังงานขาด (จ่ายจากแบต/กริด)",
            )
            ax2.axhline(y=0, color="black", linewidth=1, alpha=0.5)
            ax2.set_title(
                f"สมดุลพลังงาน: เกิน {day_data['total_excess_energy']:.0f} kWh, "
                f"ขาด {day_data['total_deficit_energy']:.0f} kWh"
            )
            ax2.set_ylabel("กำลังไฟ (kW)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

            # Panel 3: Battery dispatch 16:00-22:00
            ax3 = axes[2]
            evening_mask = (daily_datetime.dt.hour >= 16) & (daily_datetime.dt.hour < 22)
            evening_datetime = daily_datetime[evening_mask]
            evening_consumption = daily_consumption[evening_mask].to_numpy()

            load_above_threshold = np.maximum(0, evening_consumption - threshold_kw)
            area_above_threshold = float(load_above_threshold.sum()) * 0.25

            battery_discharge = np.zeros_like(evening_consumption)
            # Cap the available battery energy at the specified battery size
            if self.battery_size_kwh > 0:
                remaining_energy = min(float(day_data["solar_to_battery"]), self.battery_size_kwh)
            else:
                remaining_energy = float(day_data["solar_to_battery"])
            battery_discharge_energy_total = 0.0

            for idx, excess in enumerate(load_above_threshold):
                if excess <= 0 or remaining_energy <= 0:
                    continue
                energy_needed = excess * 0.25
                discharge_energy = min(remaining_energy, energy_needed)
                battery_discharge[idx] = discharge_energy / 0.25
                remaining_energy -= discharge_energy
                battery_discharge_energy_total += discharge_energy

            effective_load = np.maximum(0, evening_consumption - battery_discharge)

            ax3.fill_between(
                evening_datetime, 0, evening_consumption, alpha=0.3, color="red", label="โหลด (kW)"
            )
            ax3.plot(evening_datetime, evening_consumption, color="red", linewidth=2)
            ax3.fill_between(
                evening_datetime,
                0,
                battery_discharge,
                alpha=0.7,
                color="cyan",
                label=f"แบตจ่ายไฟ: {battery_discharge_energy_total:.0f} kWh",
            )
            ax3.plot(evening_datetime, battery_discharge, color="cyan", linewidth=2)
            ax3.plot(
                evening_datetime,
                effective_load,
                color="green",
                linewidth=2,
                label=f"โหลดหลังใช้แบต: {float(np.trapz(effective_load, dx=0.25)):.0f} kWh",
            )
            ax3.fill_between(
                evening_datetime,
                threshold_kw,
                evening_consumption,
                where=(evening_consumption > threshold_kw),
                color="yellow",
                alpha=0.5,
                label=f"โหลดเกิน {self.battery_threshold_w:.0f}W: {area_above_threshold:.0f} kWh",
            )
            ax3.axhline(
                threshold_kw,
                color="purple",
                linestyle="--",
                linewidth=2,
                label=f"เกณฑ์ {self.battery_threshold_w:.0f} W",
            )
            ax3.set_title("การจ่ายไฟจากแบตช่วง 16:00-22:00 น.")
            ax3.set_ylabel("กำลังไฟ (kW)")
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

            # Panel 4: Cumulative battery state
            ax4 = axes[3]
            cumulative_balance = day_data["cumulative_balance"]
            ax4.fill_between(
                daily_datetime,
                0,
                cumulative_balance,
                alpha=0.3,
                color="purple",
                label="สถานะแบตเตอรี่ (kWh)",
            )
            ax4.plot(daily_datetime, cumulative_balance, color="purple", linewidth=2)
            ax4.axhline(y=0, color="black", linestyle="-", alpha=0.5)
            ax4.axhline(
                day_data["max_excess"],
                color="green",
                linestyle="--",
                label=f"สูงสุด: {day_data['max_excess']:.0f} kWh",
            )
            ax4.axhline(
                day_data["max_deficit"],
                color="red",
                linestyle="--",
                label=f"ต่ำสุด: {day_data['max_deficit']:.0f} kWh",
            )
            # Determine battery size description for legend
            if self.battery_size_kwh > 0:
                battery_label = f"แบตที่กำหนด: {self.battery_size_kwh:.0f} kWh"
                battery_value = self.battery_size_kwh
            else:
                battery_label = f"แบตแนะนำ: {day_data['optimal_battery_size']:.0f} kWh"
                battery_value = day_data["optimal_battery_size"]
            
            ax4.axhline(
                battery_value,
                color="blue",
                linestyle=":",
                label=battery_label,
            )
            ax4.axhline(
                -battery_value,
                color="blue",
                linestyle=":",
                alpha=0.5,
            )
            ax4.set_title(
                f"สถานะสะสมแบตเตอรี่ (สุทธิ {day_data['net_energy_balance']:.0f} kWh)"
            )
            ax4.set_xlabel("เวลา")
            ax4.set_ylabel("พลังงานสะสม (kWh)")
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            ax4.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()
            filename = f"solar_daily_analysis_{date}.png"
            path = os.path.join(self.output_dir, filename)
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"   📈 บันทึกกราฟ {filename}")

    def create_weekly_summary(self) -> None:
        """
        Generate a 3-panel weekly summary covering the most recent 7 days.
        """
        if self.df is None or self.df.empty or self.solar_generation is None:
            print("⚠️ ไม่มีข้อมูลเพียงพอสำหรับกราฟสรุปรายสัปดาห์")
            return

        unique_dates = sorted(self.df["date"].unique())
        if not unique_dates:
            print("⚠️ ไม่มีวันที่ในข้อมูล")
            return

        if len(unique_dates) > 7:
            unique_dates = unique_dates[-7:]

        mask = self.df["date"].isin(unique_dates)
        df_filtered = self.df.loc[mask].copy()

        start_idx = df_filtered.index.min()
        end_idx = df_filtered.index.max()
        solar_filtered = self.solar_generation[start_idx : end_idx + 1]

        power_difference = solar_filtered - df_filtered["consumption"].to_numpy()
        excess_power = np.maximum(0, power_difference)
        deficit_power = np.maximum(0, -power_difference)

        total_consumption_area = float(np.trapz(df_filtered["consumption"], dx=0.25))
        total_solar_area = float(np.trapz(solar_filtered, dx=0.25))
        total_excess_area = float(np.trapz(excess_power, dx=0.25))
        total_deficit_area = float(np.trapz(deficit_power, dx=0.25))

        fig, axes = plt.subplots(3, 1, figsize=(20, 16))
        fig.suptitle(
            f"กราฟวิเคราะห์กำลังไฟ {len(unique_dates)} วัน\n"
            f"โซลาร์ {self.solar_capacity_mw:.1f} MWp, แดด {self.sun_hours:.1f} ชม./วัน",
            fontsize=18,
            fontweight="bold",
        )

        ax1 = axes[0]
        ax1.fill_between(
            df_filtered["datetime"],
            0,
            df_filtered["consumption"],
            alpha=0.3,
            color="red",
            label="โหลด (kW)",
        )
        ax1.fill_between(
            df_filtered["datetime"],
            0,
            solar_filtered,
            alpha=0.3,
            color="orange",
            label="โซลาร์ (kW)",
        )
        ax1.plot(df_filtered["datetime"], df_filtered["consumption"], color="red")
        ax1.plot(df_filtered["datetime"], solar_filtered, color="orange")
        ax1.axhline(
            df_filtered["consumption"].mean(),
            color="darkred",
            linestyle="--",
            linewidth=2,
            label=f"เฉลี่ยโหลด: {df_filtered['consumption'].mean():.0f} kW",
        )
        ax1.axhline(
            solar_filtered.mean(),
            color="darkorange",
            linestyle="--",
            linewidth=2,
            label=f"เฉลี่ยโซลาร์: {solar_filtered.mean():.0f} kW",
        )
        ax1.set_title("เปรียบเทียบกำลังไฟ (7 วันล่าสุด)")
        ax1.set_ylabel("กำลังไฟ (kW)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%H:%M"))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        ax2 = axes[1]
        ax2.fill_between(
            df_filtered["datetime"],
            0,
            excess_power,
            alpha=0.7,
            color="green",
            label="พลังงานเกิน (ชาร์จแบต)",
        )
        ax2.fill_between(
            df_filtered["datetime"],
            0,
            -deficit_power,
            alpha=0.7,
            color="blue",
            label="พลังงานขาด (ใช้จากแบต/กริด)",
        )
        ax2.axhline(y=0, color="black", linewidth=1, alpha=0.5)
        ax2.set_title(
            f"สมดุลพลังงานรวม: เกิน {total_excess_area:.0f} kWh, "
            f"ขาด {total_deficit_area:.0f} kWh"
        )
        ax2.set_ylabel("กำลังไฟ (kW)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%H:%M"))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        ax3 = axes[2]
        grouped = (
            df_filtered.groupby("date")["consumption"]
            .apply(lambda s: float(np.trapz(s, dx=0.25)))
            .reset_index(name="consumption_area")
        )
        grouped["solar_area"] = [
            float(np.trapz(solar_filtered[df_filtered["date"] == date], dx=0.25))
            for date in grouped["date"]
        ]

        x = np.arange(len(grouped))
        width = 0.35
        bars1 = ax3.bar(
            x - width / 2,
            grouped["consumption_area"],
            width,
            label="โหลดรวมต่อวัน (kWh)",
            color="red",
            alpha=0.7,
        )
        bars2 = ax3.bar(
            x + width / 2,
            grouped["solar_area"],
            width,
            label="โซลาร์รวมต่อวัน (kWh)",
            color="orange",
            alpha=0.7,
        )
        ax3.set_xticks(x)
        ax3.set_xticklabels([date.strftime("%d/%m") for date in grouped["date"]], rotation=0)
        ax3.set_ylabel("พลังงาน (kWh)")
        ax3.set_title("สรุปพลังงานรายวัน")
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis="y")

        for bar in bars1:
            ax3.annotate(
                f"{bar.get_height():.0f}",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                textcoords="offset points",
                xytext=(0, 3),
                ha="center",
                color="darkred",
            )
        for bar in bars2:
            ax3.annotate(
                f"{bar.get_height():.0f}",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                textcoords="offset points",
                xytext=(0, 3),
                ha="center",
                color="darkorange",
            )

        plt.tight_layout()
        filename = "solar_weekly_summary.png"
        path = os.path.join(self.output_dir, filename)
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)

        print(
            "✅ บันทึกกราฟสรุปรายสัปดาห์: "
            f"{filename} | โหลดรวม {total_consumption_area:.0f} kWh, "
            f"โซลาร์รวม {total_solar_area:.0f} kWh"
        )

    # --------------------------------------------------------------------- #
    # Textual summaries                                                     #
    # --------------------------------------------------------------------- #
    def print_daily_summary(self) -> None:
        """
        Print concise per-day battery summary to stdout.
        """
        if not self.battery_analysis:
            return

        print("\n📝 สรุปผลรายวัน")
        
        # Determine battery column header based on user input
        if self.battery_size_kwh > 0:
            battery_header = "แบตที่กำหนด(kWh)"
        else:
            battery_header = "แบตแนะนำ(kWh)"
            
        headers = (
            "วันที่",
            "โหลด(kWh)",
            "โซลาร์(kWh)",
            "เกิน(kWh)",
            "ขาด(kWh)",
            battery_header,
            "ใช้แบตช่วงเย็น(kWh)",
        )
        print("{:<12} {:>12} {:>12} {:>10} {:>10} {:>16} {:>18}".format(*headers))
        for day in self.battery_analysis:
            print(
                "{:<12} {:>12.0f} {:>12.0f} {:>10.0f} {:>10.0f} {:>16.0f} {:>18.0f}".format(
                    str(day["date"]),
                    day["consumption_area"],
                    day["solar_area"],
                    day["total_excess_energy"],
                    day["total_deficit_energy"],
                    day["optimal_battery_size"],
                    day["battery_discharge_16_22_area"],
                )
            )

    # --------------------------------------------------------------------- #
    # Main flow                                                             #
    # --------------------------------------------------------------------- #
    def run(self) -> None:
        """
        Orchestrate the full workflow.
        """
        choice = self.get_user_input()

        if not self.load_and_parse_data():
            return
        if self.df is None or self.df.empty:
            print("⚠️ ไม่มีข้อมูลสำหรับวิเคราะห์")
            return

        self.create_solar_generation()
        self.calculate_daily_battery_requirements()
        self.print_daily_summary()

        if choice == "1":
            self.create_daily_graphs_with_battery()
        elif choice == "2":
            self.create_weekly_summary()
        else:
            self.create_daily_graphs_with_battery()
            self.create_weekly_summary()

        print("\n🎉 วิเคราะห์เสร็จสิ้น")


def main() -> None:
    try:
        analyzer = SolarAnalyzerPro()
        analyzer.run()
    except KeyboardInterrupt:
        print("\n⛔️ ยกเลิกการทำงานโดยผู้ใช้")
    except Exception as exc:  # pragma: no cover - top-level guard
        print(f"\n❌ เกิดข้อผิดพลาด: {exc}")
        if os.environ.get("SOLAR_ANALYZER_DEBUG"):
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
