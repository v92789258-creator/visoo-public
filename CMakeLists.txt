cmake_minimum_required(VERSION 3.10)
project(SplashLoader)

# Configurar C++ estándar
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Agregar ejecutable
add_executable(SplashLoader SplashLoader.cpp)

# Vinculación de librerías de Windows
target_link_libraries(SplashLoader 
    user32 
    kernel32 
    comctl32 
    gdi32
)

# Configurar como aplicación de Windows (sin consola)
if(MSVC)
    set_target_properties(SplashLoader PROPERTIES
        LINK_FLAGS "/SUBSYSTEM:WINDOWS"
    )
endif()

# Recursos (icono, etc)
# Opcional: agregar archivo .rc
