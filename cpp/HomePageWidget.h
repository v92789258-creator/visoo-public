#ifndef HOMEPAGE_WIDGET_H
#define HOMEPAGE_WIDGET_H

#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QGridLayout>
#include <vector>
#include <QString>
#include <QPainter>
#include <QPainterPath>

// --- SalesCard: Tarjeta de Estadística ---
class SalesCard : public QWidget {
    Q_OBJECT
    
public:
    explicit SalesCard(const QString& title, const QString& value, 
                      const QString& color = "#1976d2", QWidget *parent = nullptr);
    void setValue(const QString& value); // Para actualizar sin recrear

private:
    void setupUI();
    QString m_title;
    QString m_value;
    QString m_color;
    QLabel* m_valueLabel; // Puntero directo para actualizar rápido
};

// --- ChartWidget: Widget dedicado al dibujo del gráfico ---
class ChartWidget : public QWidget {
    Q_OBJECT
public:
    explicit ChartWidget(QWidget *parent = nullptr);
    void setData(const std::vector<double>& values, const std::vector<QString>& labels);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    std::vector<double> m_values;
    std::vector<QString> m_labels;
};

// --- HomePageWidget: Contenedor Principal ---
class HomePageWidget : public QWidget {
    Q_OBJECT
    
public:
    explicit HomePageWidget(const QString& opticaName, const QString& username, QWidget *parent = nullptr);
    
    // Setters
    void setPatientCount(int count);
    void setProductCount(int count);
    void setMonthlyPatients(int count);
    void setTotalSales(double amount);
    
    void updateSalesChart(const std::vector<double>& values, 
                         const std::vector<QString>& labels);
    
protected:
    // Eliminamos paintEvent de fondo para permitir transparencia
    // void paintEvent(QPaintEvent *event) override; 
    
private:
    void setupUI();
    void setupCards();
    
    // UI Elements
    QString m_opticaName;
    QString m_username;
    
    QWidget *m_cardsContainer;
    QGridLayout *m_cardsLayout;
    
    SalesCard *m_patientsCard;
    SalesCard *m_productsCard;
    SalesCard *m_monthlyPatientsCard;
    SalesCard *m_salesCard;
    
    ChartWidget *m_chartWidget; // Widget personalizado para el gráfico
};

#endif // HOMEPAGE_WIDGET_H