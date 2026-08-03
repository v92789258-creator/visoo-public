"""
Components - Submódulos de HomePageWidget

Estructura modular:
- stat_card.py: ModernStatCard, ClickableLabel
- charts.py: SalesBarChart, ComparisonLineChart
- rankings.py: TopCustomersRanking, TopProductsRanking
- dialogs.py: Todos los diálogos
"""

from .stat_card import ModernStatCard, ClickableLabel
from .charts import SalesBarChart, ComparisonLineChart
from .rankings import TopCustomersRanking, TopProductsRanking
from .dialogs import CustomerDetailDialog, ProductDetailDialog, DayPurchasesDialog

__all__ = [
    'ModernStatCard',
    'ClickableLabel',
    'SalesBarChart',
    'ComparisonLineChart',
    'TopCustomersRanking',
    'TopProductsRanking',
    'CustomerDetailDialog',
    'ProductDetailDialog',
    'DayPurchasesDialog',
]
