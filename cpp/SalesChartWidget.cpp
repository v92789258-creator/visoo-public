#include "SalesChartWidget.h"
#include <QPainter>
#include <QResizeEvent>
#include <QPaintEvent>
#include <cmath>
#include <algorithm>

SalesChartWidget::SalesChartWidget(QWidget *parent)
    : QWidget(parent)
    , m_title("Sales Chart")
    , m_lineColor(25, 118, 210)  // Color azul (#1976d2)
    , m_marginLeft(60)
    , m_marginRight(40)
    , m_marginTop(60)
    , m_marginBottom(80)
    , m_needsRedraw(true)
{
    setMinimumHeight(300);
    setStyleSheet("background-color: white;");
    setAttribute(Qt::WA_StyledBackground, true);
}

void SalesChartWidget::setData(const std::vector<double>& values, const std::vector<QString>& labels)
{
    m_values = values;
    m_labels = labels;
    m_needsRedraw = true;
    update();
}

void SalesChartWidget::setTitle(const QString& title)
{
    m_title = title;
    m_needsRedraw = true;
    update();
}

void SalesChartWidget::setLineColor(const QColor& color)
{
    m_lineColor = color;
    m_needsRedraw = true;
    update();
}

void SalesChartWidget::clearData()
{
    m_values.clear();
    m_labels.clear();
    m_needsRedraw = true;
    update();
}

void SalesChartWidget::paintEvent(QPaintEvent *event)
{
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing, true);
    painter.setRenderHint(QPainter::SmoothPixmapTransform, true);
    
    // Fondo blanco
    painter.fillRect(rect(), Qt::white);
    
    drawChart(painter);
}

void SalesChartWidget::resizeEvent(QResizeEvent *event)
{
    m_needsRedraw = true;
    QWidget::resizeEvent(event);
}

void SalesChartWidget::drawChart(QPainter &painter)
{
    if (m_values.empty()) {
        // Dibujar mensaje si no hay datos
        painter.setPen(Qt::gray);
        painter.setFont(QFont("Arial", 12));
        painter.drawText(rect(), Qt::AlignCenter, "No hay datos disponibles");
        return;
    }
    
    drawGrid(painter);
    drawAxes(painter);
    drawLine(painter);
    drawLabels(painter);
    drawLegend(painter);
}

void SalesChartWidget::drawGrid(QPainter &painter)
{
    // Área útil del gráfico
    int chartWidth = width() - m_marginLeft - m_marginRight;
    int chartHeight = height() - m_marginTop - m_marginBottom;
    
    // Dibujar líneas de cuadrícula
    painter.setPen(QPen(QColor(200, 200, 200), 1, Qt::DashLine));
    
    // Líneas horizontales
    int gridLines = 5;
    for (int i = 0; i <= gridLines; ++i) {
        int y = m_marginTop + (chartHeight * i / gridLines);
        painter.drawLine(m_marginLeft, y, width() - m_marginRight, y);
    }
}

void SalesChartWidget::drawAxes(QPainter &painter)
{
    int chartWidth = width() - m_marginLeft - m_marginRight;
    int chartHeight = height() - m_marginTop - m_marginBottom;
    
    // Ejes
    painter.setPen(QPen(Qt::black, 2));
    painter.drawLine(m_marginLeft, m_marginTop, m_marginLeft, height() - m_marginBottom);
    painter.drawLine(m_marginLeft, height() - m_marginBottom, width() - m_marginRight, height() - m_marginBottom);
    
    // Etiquetas de eje Y
    painter.setPen(Qt::black);
    painter.setFont(QFont("Arial", 9));
    
    if (!m_values.empty()) {
        double maxValue = *std::max_element(m_values.begin(), m_values.end());
        if (maxValue == 0) maxValue = 1;
        
        for (int i = 0; i <= 5; ++i) {
            int y = height() - m_marginBottom - (chartHeight * i / 5);
            double value = (maxValue * i) / 5;
            painter.drawText(QRect(5, y - 10, m_marginLeft - 10, 20), 
                           Qt::AlignRight | Qt::AlignVCenter, 
                           QString::number(static_cast<int>(value)));
        }
    }
}

void SalesChartWidget::drawLine(QPainter &painter)
{
    if (m_values.empty()) return;
    
    int chartWidth = width() - m_marginLeft - m_marginRight;
    int chartHeight = height() - m_marginTop - m_marginBottom;
    
    double maxValue = *std::max_element(m_values.begin(), m_values.end());
    if (maxValue == 0) maxValue = 1;
    
    painter.setPen(QPen(m_lineColor, 2.4));
    
    // Dibujar línea
    for (size_t i = 0; i < m_values.size() - 1; ++i) {
        double x1 = m_marginLeft + (chartWidth * i) / (m_values.size() - 1);
        double y1 = height() - m_marginBottom - (chartHeight * m_values[i]) / maxValue;
        
        double x2 = m_marginLeft + (chartWidth * (i + 1)) / (m_values.size() - 1);
        double y2 = height() - m_marginBottom - (chartHeight * m_values[i + 1]) / maxValue;
        
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2));
    }
    
    // Dibujar puntos
    painter.setBrush(m_lineColor);
    painter.setPen(Qt::NoPen);
    for (size_t i = 0; i < m_values.size(); ++i) {
        double x = m_marginLeft + (chartWidth * i) / (m_values.size() - 1);
        double y = height() - m_marginBottom - (chartHeight * m_values[i]) / maxValue;
        painter.drawEllipse(QPointF(x, y), 4, 4);
    }
}

void SalesChartWidget::drawLabels(QPainter &painter)
{
    if (m_values.empty()) return;
    
    int chartWidth = width() - m_marginLeft - m_marginRight;
    
    painter.setPen(Qt::black);
    painter.setFont(QFont("Arial", 9));
    
    // Etiquetas del eje X
    for (size_t i = 0; i < m_labels.size(); ++i) {
        double x = m_marginLeft + (chartWidth * i) / (m_values.size() - 1);
        int y = height() - m_marginBottom + 20;
        
        painter.save();
        painter.translate(x, y);
        painter.rotate(-45);
        painter.drawText(QRect(0, 0, 100, 30), Qt::AlignLeft, m_labels[i]);
        painter.restore();
    }
    
    // Título
    painter.setPen(Qt::black);
    painter.setFont(QFont("Arial", 14, QFont::Bold));
    painter.drawText(QRect(m_marginLeft, 10, width() - m_marginLeft - m_marginRight, 40), 
                    Qt::AlignCenter, m_title);
}

void SalesChartWidget::drawLegend(QPainter &painter)
{
    // Rectángulo de leyenda
    int legX = width() - m_marginRight - 150;
    int legY = m_marginTop + 20;
    int legWidth = 130;
    int legHeight = 50;
    
    painter.setPen(QPen(Qt::gray, 1));
    painter.setBrush(QColor(255, 255, 255, 240));
    painter.drawRect(legX, legY, legWidth, legHeight);
    
    // Línea de ejemplo
    painter.setPen(QPen(m_lineColor, 2.4));
    painter.drawLine(legX + 10, legY + 15, legX + 30, legY + 15);
    painter.setBrush(m_lineColor);
    painter.setPen(Qt::NoPen);
    painter.drawEllipse(QPointF(legX + 20, legY + 15), 3, 3);
    
    // Texto de leyenda
    painter.setPen(Qt::black);
    painter.setFont(QFont("Arial", 10));
    painter.drawText(QRect(legX + 40, legY + 8, legWidth - 50, 25), 
                    Qt::AlignLeft | Qt::AlignVCenter, "Ventas");
}
