#include "HomePageWidget.h"
#include <QGraphicsDropShadowEffect>
#include <QDateTime>
#include <algorithm>
#include <QLinearGradient>

// ==================== SalesCard Implementación ====================

SalesCard::SalesCard(const QString& title, const QString& value, 
                     const QString& color, QWidget *parent)
    : QWidget(parent)
    , m_title(title)
    , m_value(value)
    , m_color(color)
{
    // Tamaño fijo para uniformidad
    setFixedHeight(110);
    setupUI();
}

void SalesCard::setValue(const QString& value) {
    if (m_valueLabel) m_valueLabel->setText(value);
}

void SalesCard::setupUI()
{
    QVBoxLayout *layout = new QVBoxLayout(this);
    layout->setContentsMargins(20, 15, 20, 15);
    layout->setSpacing(5);
    
    // Título pequeño y gris
    QLabel *titleLabel = new QLabel(m_title);
    titleLabel->setStyleSheet("color: #78909C; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;");
    layout->addWidget(titleLabel);
    
    // Valor grande
    m_valueLabel = new QLabel(m_value);
    // Usamos el color pasado para darle identidad a la cifra
    m_valueLabel->setStyleSheet(QString("color: #263238; font-size: 28px; font-weight: 800;"));
    layout->addWidget(m_valueLabel);
    
    // Barra decorativa inferior del color temático
    QWidget* bar = new QWidget();
    bar->setFixedHeight(4);
    bar->setStyleSheet(QString("background-color: %1; border-radius: 2px;").arg(m_color));
    bar->setFixedWidth(40); // Pequeña línea de acento
    layout->addWidget(bar);
    
    layout->addStretch();
    
    // Fondo blanco sutil con borde casi invisible
    setStyleSheet(R"(
        SalesCard {
            background-color: #FFFFFF;
            border: 1px solid #EEF2F5;
            border-radius: 12px;
        }
    )");
}

// ==================== ChartWidget Implementación (Gráfico Real) ====================

ChartWidget::ChartWidget(QWidget *parent) : QWidget(parent) {
    setMinimumHeight(250);
    setStyleSheet("background: transparent;");
}

void ChartWidget::setData(const std::vector<double>& values, const std::vector<QString>& labels) {
    m_values = values;
    m_labels = labels;
    update(); // Repintar
}

void ChartWidget::paintEvent(QPaintEvent *event) {
    Q_UNUSED(event);
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);

    if (m_values.empty()) return;

    double maxVal = 1.0;
    for (double v : m_values) if (v > maxVal) maxVal = v;
    
    // Márgenes internos para dibujar
    QRect r = rect().adjusted(20, 20, -20, -40);
    double stepX = (double)r.width() / (m_values.size() > 1 ? (m_values.size() - 1) : 1);
    
    // Crear el camino de la línea (Path)
    QPainterPath path;
    QPainterPath fillPath; // Para el degradado debajo
    
    // Punto inicial
    double startY = r.bottom() - (m_values[0] / maxVal) * r.height();
    path.moveTo(r.left(), startY);
    fillPath.moveTo(r.left(), r.bottom()); // Empezar abajo
    fillPath.lineTo(r.left(), startY);

    // Dibujar curvas (Cubic Bezier para suavidad)
    for (size_t i = 1; i < m_values.size(); ++i) {
        double prevX = r.left() + (i - 1) * stepX;
        double prevY = r.bottom() - (m_values[i - 1] / maxVal) * r.height();
        
        double currentX = r.left() + i * stepX;
        double currentY = r.bottom() - (m_values[i] / maxVal) * r.height();
        
        // Puntos de control para la curva
        double c1x = (prevX + currentX) / 2.0;
        double c1y = prevY;
        double c2x = (prevX + currentX) / 2.0;
        double c2y = currentY;
        
        path.cubicTo(c1x, c1y, c2x, c2y, currentX, currentY);
        fillPath.cubicTo(c1x, c1y, c2x, c2y, currentX, currentY);
    }
    
    // Cerrar el fillPath
    fillPath.lineTo(r.left() + (m_values.size()-1)*stepX, r.bottom());
    fillPath.closeSubpath();

    // 1. Dibujar el relleno (Degradado)
    QLinearGradient gradient(0, r.top(), 0, r.bottom());
    gradient.setColorAt(0, QColor(63, 81, 181, 50));   // Azul semitransparente arriba
    gradient.setColorAt(1, QColor(63, 81, 181, 0));    // Transparente abajo
    painter.fillPath(fillPath, gradient);

    // 2. Dibujar la línea
    QPen pen(QColor(63, 81, 181)); // Azul índigo
    pen.setWidth(3);
    pen.setCapStyle(Qt::RoundCap);
    painter.strokePath(path, pen);
    
    // 3. Dibujar puntos
    painter.setBrush(Qt::white);
    painter.setPen(QColor(63, 81, 181));
    for (size_t i = 0; i < m_values.size(); ++i) {
        double x = r.left() + i * stepX;
        double y = r.bottom() - (m_values[i] / maxVal) * r.height();
        painter.drawEllipse(QPointF(x, y), 4, 4);
    }

    // 4. Dibujar etiquetas Eje X (simplificadas)
    painter.setPen(QColor("#90A4AE"));
    painter.setFont(QFont("Arial", 8));
    for (size_t i = 0; i < m_labels.size(); ++i) {
        // Dibujar solo algunas etiquetas si son muchas
        if (m_values.size() > 10 && i % 2 != 0) continue; 
        
        double x = r.left() + i * stepX;
        painter.drawText(QRectF(x - 20, r.bottom() + 5, 40, 20), Qt::AlignCenter, m_labels[i]);
    }
}


// ==================== HomePageWidget Implementación ====================

HomePageWidget::HomePageWidget(const QString& opticaName, const QString& username, QWidget *parent)
    : QWidget(parent)
    , m_opticaName(opticaName)
    , m_username(username)
{
    // CRUCIAL: Permitir que el fondo sea transparente para que el diseño Python se vea
    setAttribute(Qt::WA_TranslucentBackground); 
    setupUI();
}

void HomePageWidget::setupUI()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);
    mainLayout->setAlignment(Qt::AlignTop);
    mainLayout->setSpacing(25);
    mainLayout->setContentsMargins(30, 30, 30, 30);
    
    // 1. Header (Saludo)
    QWidget *headerContainer = new QWidget();
    headerContainer->setStyleSheet("background: transparent;");
    QVBoxLayout *headerLayout = new QVBoxLayout(headerContainer);
    headerLayout->setContentsMargins(0, 0, 0, 0);
    headerLayout->setSpacing(4);
    
    // Título dinámico
    QLabel *titleLabel = new QLabel("Hola, " + (m_username.isEmpty() ? "Admin" : m_username));
    titleLabel->setStyleSheet("color: #263238; font-size: 32px; font-weight: 800; font-family: 'Segoe UI', sans-serif;");
    headerLayout->addWidget(titleLabel);
    
    QLabel *subtitleLabel = new QLabel("Resumen de actividad para " + m_opticaName);
    subtitleLabel->setStyleSheet("color: #78909C; font-size: 16px; font-weight: 500;");
    headerLayout->addWidget(subtitleLabel);
    
    mainLayout->addWidget(headerContainer);
    
    // 2. Tarjetas (Grid)
    setupCards();
    mainLayout->addWidget(m_cardsContainer);
    
    // 3. Sección del Gráfico
    QLabel *chartTitle = new QLabel("Rendimiento de Ventas (Últimos 15 días)");
    chartTitle->setStyleSheet("color: #455A64; font-size: 16px; font-weight: 700; margin-top: 10px; margin-bottom: 5px;");
    mainLayout->addWidget(chartTitle);

    m_chartWidget = new ChartWidget();
    mainLayout->addWidget(m_chartWidget, 1); // Factor de expansión 1 para ocupar espacio
}

void HomePageWidget::setupCards()
{
    m_cardsContainer = new QWidget();
    m_cardsContainer->setStyleSheet("background: transparent;");
    m_cardsLayout = new QGridLayout(m_cardsContainer);
    m_cardsLayout->setSpacing(20);
    m_cardsLayout->setContentsMargins(0, 0, 0, 0);
    
    // Instanciar tarjetas con colores Material Design
    m_patientsCard = new SalesCard("Total Pacientes", "0", "#5C6BC0"); // Indigo
    m_productsCard = new SalesCard("Inventario", "0", "#FFA726");      // Orange
    m_monthlyPatientsCard = new SalesCard("Nuevos (Mes)", "0", "#66BB6A"); // Green
    m_salesCard = new SalesCard("Ventas Totales", "S/ 0.00", "#EC407A");   // Pink
    
    m_cardsLayout->addWidget(m_patientsCard, 0, 0);
    m_cardsLayout->addWidget(m_productsCard, 0, 1);
    m_cardsLayout->addWidget(m_monthlyPatientsCard, 0, 2);
    m_cardsLayout->addWidget(m_salesCard, 0, 3);
}

void HomePageWidget::setPatientCount(int count) {
    if(m_patientsCard) m_patientsCard->setValue(QString::number(count));
}

void HomePageWidget::setProductCount(int count) {
    if(m_productsCard) m_productsCard->setValue(QString::number(count));
}

void HomePageWidget::setMonthlyPatients(int count) {
    if(m_monthlyPatientsCard) m_monthlyPatientsCard->setValue(QString::number(count));
}

void HomePageWidget::setTotalSales(double amount) {
    if(m_salesCard) m_salesCard->setValue(QString("S/ %1").arg(amount, 0, 'f', 2));
}

void HomePageWidget::updateSalesChart(const std::vector<double>& values, const std::vector<QString>& labels) {
    if(m_chartWidget) m_chartWidget->setData(values, labels);
}