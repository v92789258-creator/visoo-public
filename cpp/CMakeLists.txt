cmake_minimum_required(VERSION 3.16)
project(VISOCppLibraries)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# ====== Cargador JSON Ultra-Rápido (SIN dependencias) ======
add_library(FastJSONLoader SHARED
    FastJSONLoader.cpp
)

set_target_properties(FastJSONLoader PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

if(WIN32)
    set_target_properties(FastJSONLoader PROPERTIES SUFFIX ".dll")
elseif(APPLE)
    set_target_properties(FastJSONLoader PROPERTIES SUFFIX ".dylib")
else()
    set_target_properties(FastJSONLoader PROPERTIES SUFFIX ".so")
endif()

# ====== Optimizador de Inventario (Búsqueda, Filtrado, Ordenamiento) ======
add_library(InventoryOptimizer SHARED
    InventoryOptimizer.cpp
)

set_target_properties(InventoryOptimizer PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

if(WIN32)
    set_target_properties(InventoryOptimizer PROPERTIES SUFFIX ".dll")
elseif(APPLE)
    set_target_properties(InventoryOptimizer PROPERTIES SUFFIX ".dylib")
else()
    set_target_properties(InventoryOptimizer PROPERTIES SUFFIX ".so")
endif()

# ====== Gráfico de Ventas con Qt5 (opcional) ======
find_package(Qt5 COMPONENTS Core Gui Widgets REQUIRED)

add_library(SalesChartWidget SHARED
    SalesChartWidget.cpp
    SalesChartWidget.h
)

target_link_libraries(SalesChartWidget PUBLIC Qt5::Core Qt5::Gui Qt5::Widgets)

set_target_properties(SalesChartWidget PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
