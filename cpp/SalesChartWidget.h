#ifndef SALESCHARTWIDGET_H
#define SALESCHARTWIDGET_H

#include <QWidget>
#include <QPainter>
#include <vector>

class SalesChartWidget : public QWidget {
    Q_OBJECT
    
public:
    explicit SalesChartWidget(QWidget *parent = nullptr);
    
    // Métodos para actualizar datos
    void setData(const std::vector<double>& values, const std::vector<QString>& labels);
    void setTitle(const QString& title);
    void setLineColor(const QColor& color);
    void clearData();
    
protected:
    void paintEvent(QPaintEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;
    
private:
    void drawChart(QPainter &painter);
    void drawGrid(QPainter &painter);
    void drawLine(QPainter &painter);
    void drawAxes(QPainter &painter);
    void drawLabels(QPainter &painter);
    void drawLegend(QPainter &painter);
    
    std::vector<double> m_values;
    std::vector<QString> m_labels;
    QString m_title;
    QColor m_lineColor;
    
    // Dimensiones del gráfico
    int m_marginLeft;
    int m_marginRight;
    int m_marginTop;
    int m_marginBottom;
    
    // Caché para evitar recálculos
    QPixmap m_chartCache;
    bool m_needsRedraw;
};

#endif // SALESCHARTWIDGET_H
