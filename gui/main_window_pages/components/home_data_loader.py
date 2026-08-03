"""
Home data loading and business metrics for the dashboard.
"""

import datetime


class HomeDataLoader:
    """Gestor centralizado de carga y procesamiento de datos para HomePage."""

    def __init__(self, username):
        self.username = username

    def load_all(self, allow_remote_restore: bool = True, fast_start: bool = False):
        from utils.file_handler import (
            cargar_pacientes_dashboard,
            cargar_productos_dashboard,
            cargar_ventas_dashboard,
        )

        return {
            "pacientes": cargar_pacientes_dashboard(
                self.username,
                allow_remote_restore=allow_remote_restore,
                fast_start=fast_start,
            ),
            "productos": cargar_productos_dashboard(
                self.username,
                allow_remote_restore=allow_remote_restore,
                fast_start=fast_start,
            ),
            "ventas": cargar_ventas_dashboard(
                self.username,
                allow_remote_restore=allow_remote_restore,
                fast_start=fast_start,
            ),
        }

    @staticmethod
    def _parse_date(value):
        text = str(value or "").strip()
        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1]

        formatos = (
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        )
        for fmt in formatos:
            try:
                return datetime.datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _safe_sale_amount(venta):
        try:
            return float(venta.get("total") or venta.get("monto") or 0.0)
        except (ValueError, TypeError, AttributeError):
            return 0.0

    def _count_patients_in_range(self, pacientes, start_date, end_date=None):
        count = 0
        for paciente in pacientes:
            if not isinstance(paciente, dict):
                continue

            fecha_obj = self._parse_date(
                paciente.get("fecha")
                or paciente.get("fecha_registro")
                or paciente.get("created_at")
            )
            if fecha_obj is None:
                continue

            fecha_date = fecha_obj.date()
            if fecha_date < start_date:
                continue
            if end_date is not None and fecha_date > end_date:
                continue
            count += 1
        return count

    def count_patients_this_month(self, pacientes):
        today = datetime.date.today()
        current_month_start = datetime.date(today.year, today.month, 1)
        return self._count_patients_in_range(pacientes, current_month_start)

    def count_patients_last_days(self, pacientes, days=30):
        days = max(1, int(days or 1))
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=days - 1)
        return self._count_patients_in_range(pacientes, start_date, today)

    def summarize_patients(self, pacientes):
        today = datetime.date.today()
        current_month_start = datetime.date(today.year, today.month, 1)
        previous_month_end = current_month_start - datetime.timedelta(days=1)
        previous_month_start = datetime.date(previous_month_end.year, previous_month_end.month, 1)

        valid_patients = [p for p in pacientes if isinstance(p, dict)]
        return {
            "total": len(valid_patients),
            "last_30_days": self.count_patients_last_days(valid_patients, days=30),
            "current_month": self._count_patients_in_range(valid_patients, current_month_start, today),
            "previous_month": self._count_patients_in_range(valid_patients, previous_month_start, previous_month_end),
        }

    def summarize_inventory(self, productos, low_stock_threshold=5):
        valid_products = [p for p in productos if isinstance(p, dict)]
        out_of_stock = 0
        low_stock = 0

        for producto in valid_products:
            try:
                stock = float(producto.get("stock") or 0)
            except (TypeError, ValueError):
                stock = 0.0

            if stock <= 0:
                out_of_stock += 1
            elif stock <= low_stock_threshold:
                low_stock += 1

        return {
            "total": len(valid_products),
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
        }

    def calculate_total_sales(self, ventas):
        total = 0.0
        for venta in ventas:
            if not isinstance(venta, dict):
                continue
            total += self._safe_sale_amount(venta)
        return total

    def summarize_sales(self, ventas):
        today = datetime.date.today()
        current_week_start = today - datetime.timedelta(days=6)
        previous_week_end = current_week_start - datetime.timedelta(days=1)
        previous_week_start = previous_week_end - datetime.timedelta(days=6)

        total_sales = 0.0
        current_week_total = 0.0
        previous_week_total = 0.0

        for venta in ventas:
            if not isinstance(venta, dict):
                continue

            monto = self._safe_sale_amount(venta)
            total_sales += monto

            fecha_obj = self._parse_date(venta.get("fecha"))
            if fecha_obj is None:
                continue

            fecha_date = fecha_obj.date()
            if current_week_start <= fecha_date <= today:
                current_week_total += monto
            elif previous_week_start <= fecha_date <= previous_week_end:
                previous_week_total += monto

        return {
            "total": total_sales,
            "current_week": current_week_total,
            "previous_week": previous_week_total,
        }

    def prepare_sales_chart(self, ventas, days=15):
        today = datetime.date.today()
        date_range = [today - datetime.timedelta(days=i) for i in range(days - 1, -1, -1)]
        sales_by_date = {d: 0.0 for d in date_range}

        for venta in ventas:
            if not isinstance(venta, dict):
                continue

            fecha_obj = self._parse_date(venta.get("fecha"))
            if fecha_obj is None:
                continue

            fecha_date = fecha_obj.date()
            if fecha_date in sales_by_date:
                sales_by_date[fecha_date] += self._safe_sale_amount(venta)

        return {
            "amounts": [sales_by_date[d] for d in date_range],
            "labels": [d.strftime("%d/%m") for d in date_range],
        }
