-- Script SQL para crear las tablas de pacientes y graduaciones
-- Ejecutar en MySQL de Hostinger

-- ============================================================================
-- TABLA: PACIENTES
-- ============================================================================
CREATE TABLE IF NOT EXISTS `pacientes` (
  `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `id_usuario` VARCHAR(100) NOT NULL,
  `nombre` VARCHAR(255) NOT NULL,
  `dni` VARCHAR(20) NOT NULL,
  `edad` INT(11),
  `genero` VARCHAR(1),
  `fecha_nacimiento` DATE,
  `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  -- Índice único para evitar duplicados
  UNIQUE KEY `unique_usuario_dni` (`id_usuario`, `dni`),
  KEY `idx_usuario` (`id_usuario`),
  KEY `idx_dni` (`dni`),
  KEY `idx_fecha_registro` (`fecha_registro`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLA: GRADUACIONES
-- ============================================================================
CREATE TABLE IF NOT EXISTS `graduaciones` (
  `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `id_paciente` INT(11) NOT NULL,
  `fecha` DATE NOT NULL,
  `optometra` VARCHAR(255),
  
  -- Datos de graduación en JSON (para flexibilidad)
  `lejos_od` JSON,
  `lejos_oi` JSON,
  `cerca_od` JSON,
  `cerca_oi` JSON,
  
  `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  -- Índice único: un paciente no puede tener dos graduaciones el mismo día
  UNIQUE KEY `unique_paciente_fecha` (`id_paciente`, `fecha`),
  KEY `idx_paciente` (`id_paciente`),
  KEY `idx_fecha` (`fecha`),
  
  -- Relación foránea con pacientes
  CONSTRAINT `fk_paciente` FOREIGN KEY (`id_paciente`) 
    REFERENCES `pacientes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- ÍNDICES ADICIONALES PARA OPTIMIZACIÓN
-- ============================================================================
CREATE INDEX IF NOT EXISTS `idx_graduaciones_paciente_fecha` 
  ON `graduaciones` (`id_paciente`, `fecha` DESC);

-- ============================================================================
-- VERIFICAR QUE LAS TABLAS EXISTEN
-- ============================================================================
SELECT 'Tabla pacientes:' AS info, COUNT(*) as registros FROM pacientes;
SELECT 'Tabla graduaciones:' AS info, COUNT(*) as registros FROM graduaciones;

-- ============================================================================
-- MOSTRAR ESTRUCTURA
-- ============================================================================
DESCRIBE pacientes;
DESCRIBE graduaciones;
