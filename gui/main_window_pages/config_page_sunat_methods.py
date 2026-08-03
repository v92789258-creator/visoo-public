"""
Módulo de extensión de métodos SUNAT para config_page.py
Estos métodos deben agregarse a la clase ConfigPage manualmente
"""

# Copiar e insertar estos métodos al final de la clase ConfigPage en config_page.py

def toggle_emision_electronica(self):
    """Alterna el estado de emisión electrónica"""
    from utils.configurador_sunat import ConfiguradorSUNAT
    
    configurador = ConfiguradorSUNAT(self.username, VISO_DIR)
    
    if self.btn_habilitar_emision.isChecked():
        # Validar que esté todo configurado
        if not self.entry_usuario_sol.text().strip():
            QMessageBox.warning(self, "Validación", "Configura el Usuario SOL primero")
            self.btn_habilitar_emision.setChecked(False)
            return
        
        if not self.entry_password_sol.text().strip():
            QMessageBox.warning(self, "Validación", "Configura la Contraseña SOL primero")
            self.btn_habilitar_emision.setChecked(False)
            return
        
        if not self.label_cert_estado.text().startswith("✓"):
            QMessageBox.warning(self, "Validación", "Carga un certificado válido primero")
            self.btn_habilitar_emision.setChecked(False)
            return
        
        # Habilitar
        success, msg = configurador.habilitar_emision_electronica(True)
        if success:
            self.btn_habilitar_emision.setText("🟢 Habilitada")
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.critical(self, "Error", msg)
            self.btn_habilitar_emision.setChecked(False)
    else:
        # Deshabilitar
        success, msg = configurador.habilitar_emision_electronica(False)
        if success:
            self.btn_habilitar_emision.setText("🔴 Deshabilitada")

def cargar_certificado_digital(self):
    """Carga archivo de certificado digital"""
    archivo, _ = QFileDialog.getOpenFileName(
        self,
        "Seleccionar Certificado",
        os.path.expanduser("~"),
        "Certificados (*.pem *.cer *.crt);;Todos (*)"
    )
    
    if archivo:
        try:
            from utils.sunat_digital_signer import SUNATDigitalSigner
            signer = SUNATDigitalSigner()
            is_valid, info = signer.verify_certificate(archivo)
            
            if is_valid:
                self.label_cert_estado.setText(f"✓ Válido hasta {info.get('not_valid_after', 'N/A')}")
                self.label_cert_estado.setStyleSheet("color: #4caf50; font-weight: bold;")
                QMessageBox.information(self, "Éxito", "Certificado válido cargado")
            else:
                QMessageBox.critical(self, "Error", f"Certificado inválido: {info.get('error', 'Desconocido')}")
                self.label_cert_estado.setText("❌ Inválido")
                self.label_cert_estado.setStyleSheet("color: #d32f2f; font-weight: bold;")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar certificado:\n{str(e)}")

def cargar_clave_privada(self):
    """Carga archivo de clave privada"""
    archivo, _ = QFileDialog.getOpenFileName(
        self,
        "Seleccionar Clave Privada",
        os.path.expanduser("~"),
        "Claves Privadas (*.key *.pem *.pfx);;Todos (*)"
    )
    
    if archivo:
        try:
            if not os.path.exists(archivo):
                raise FileNotFoundError("Archivo no encontrado")
            
            self.label_key_estado.setText(f"✓ Cargada ({os.path.basename(archivo)})")
            self.label_key_estado.setStyleSheet("color: #4caf50; font-weight: bold;")
            QMessageBox.information(self, "Éxito", "Clave privada cargada")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar clave:\n{str(e)}")

def probar_conexion_sunat(self):
    """Prueba la conexión con SUNAT"""
    from utils.sunat_client import SUNATClient
    
    usuario_sol = self.entry_usuario_sol.text().strip()
    contraseña = self.entry_password_sol.text().strip()
    
    if not usuario_sol or not contraseña:
        QMessageBox.warning(self, "Validación", "Configura Usuario y Contraseña SOL")
        return
    
    try:
        ambiente = "testing" if self.combo_ambiente.currentIndex() == 0 else "produccion"
        client = SUNATClient(usuario_sol, contraseña, ambiente)
        
        is_valid, msg = client.validar_credenciales()
        if is_valid:
            QMessageBox.information(self, "Éxito", f"Conexión SUNAT: {msg}")
        else:
            QMessageBox.warning(self, "Error", f"No se pudo conectar: {msg}")
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Error al probar conexión:\n{str(e)}")

def guardar_config_emision_electronica(self):
    """Guarda la configuración de emisión electrónica"""
    from utils.configurador_sunat import ConfiguradorSUNAT
    
    try:
        configurador = ConfiguradorSUNAT(self.username, VISO_DIR)
        
        # Guardar credenciales
        usuario = self.entry_usuario_sol.text().strip()
        contraseña = self.entry_password_sol.text().strip()
        
        if usuario and contraseña:
            success, msg = configurador.set_credenciales_sunat(usuario, contraseña)
            if not success:
                QMessageBox.warning(self, "Aviso", msg)
        
        # Guardar datos empresa
        ruc = self.entry_ruc.text().strip()
        razon_social = self.entry_razon_social.text().strip()
        
        if ruc and razon_social:
            success, msg = configurador.set_datos_empresa(
                ruc=ruc,
                razon_social=razon_social,
                direccion=self.entry_direccion.text().strip(),
                departamento=self.entry_departamento.text().strip(),
                provincia=self.entry_provincia.text().strip(),
                distrito=self.entry_distrito.text().strip()
            )
            if not success:
                QMessageBox.warning(self, "Aviso", msg)
        
        # Guardar opciones
        configurador.config['enviar_automaticamente'] = self.check_enviar_auto.isChecked()
        configurador.config['guardar_cdr'] = self.check_guardar_cdr.isChecked()
        configurador.config['ambiente'] = "testing" if self.combo_ambiente.currentIndex() == 0 else "produccion"
        
        success, msg = configurador.guardar_config()
        
        if success:
            QMessageBox.information(self, "Éxito", "Configuración SUNAT guardada correctamente")
        else:
            QMessageBox.critical(self, "Error", f"Error al guardar: {msg}")
            
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Error al guardar configuración:\n{str(e)}")
