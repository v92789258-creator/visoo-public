        # --- SECCIÓN DE BOTONES DE ACCIÓN RÁPIDA (DERECHA) ---
        icons_dir_ctrl = os.path.join(os.path.dirname(__file__), 'icons')
        
        # 1. Buscador como icono (Nuevo)
        self.search_btn_icon = QPushButton()
        self.search_btn_icon.setObjectName("searchButtonIcon")
        search_icon_path = os.path.join(icons_dir_ctrl, 'search.svg')
        if os.path.exists(search_icon_path):
            self.search_btn_icon.setIcon(QIcon(search_icon_path))
            self.search_btn_icon.setIconSize(QtCore.QSize(20, 20))
        else:
            self.search_btn_icon.setText("🔍")
        self.search_btn_icon.setFixedSize(44, 44)
        self.search_btn_icon.setFlat(True)
        self.search_btn_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn_icon.setToolTip("Buscar...")
        self.search_btn_icon.setStyleSheet('''
            QPushButton { background: transparent; border: none; padding: 10px; border-radius: 12px; }
            QPushButton:hover { background: rgba(13, 110, 253, 0.08); }
        ''')
        left_controls_layout.addWidget(self.search_btn_icon)

        # 2. Notificaciones
        from gui.notifications_popup import NotificationsPopup
        self.notifications_popup = NotificationsPopup(self)
        self.notifications_popup.load_notifications_from_history()
        self.notifications_popup.hide()
        
        btn_notifications = QPushButton()
        self.btn_notifications = btn_notifications
        notifications_icon_path = os.path.join(icons_dir_ctrl, 'bell.svg')
        self.notification_badge = QLabel("0")
        self.notification_badge.setStyleSheet("background: #E11D48; color: white; border-radius: 10px; font-weight: bold; font-size: 10px; padding: 2px 5px; min-width: 16px;")
        self.notification_badge.setAlignment(Qt.AlignCenter)
        self.notification_badge.hide()
        
        notif_container = QWidget()
        notif_layout = QHBoxLayout(notif_container)
        notif_layout.setContentsMargins(0, 0, 0, 0)
        notif_layout.setSpacing(-15)
        notif_layout.addWidget(btn_notifications)
        notif_layout.addWidget(self.notification_badge, alignment=Qt.AlignTop | Qt.AlignRight)
        notif_container.setFixedSize(44, 44)
        
        self.notifications_popup.unread_count_changed.connect(self.update_notification_badge)
        if os.path.exists(notifications_icon_path):
            btn_notifications.setIcon(QIcon(notifications_icon_path))
            btn_notifications.setIconSize(QtCore.QSize(22, 22))
        btn_notifications.setFixedSize(44, 44)
        btn_notifications.setFlat(True)
        btn_notifications.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_notifications.setStyleSheet('''
            QPushButton { background: transparent; border: none; padding: 10px; border-radius: 12px; font-size: 20px; }
            QPushButton:hover { background: rgba(13, 110, 253, 0.08); }
        ''')
        btn_notifications.clicked.connect(lambda: self.toggle_notifications_popup())
        left_controls_layout.addWidget(notif_container)

        # 3. Guardar/Backup Manual
        self._backup_button = QPushButton()
        save_icon_path = os.path.join(icons_dir_ctrl, 'save.svg')
        if os.path.exists(save_icon_path):
            self._backup_button.setIcon(QIcon(save_icon_path))
            self._backup_button.setIconSize(QtCore.QSize(16, 16))
        self._backup_button.setFixedSize(44, 44)
        self._backup_button.setFlat(True)
        self._backup_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._backup_button.setToolTip("Guardar respaldo manual")
        self._backup_button.setStyleSheet('''
            QPushButton { background: transparent; border: none; padding: 10px; border-radius: 12px; font-size: 18px; }
            QPushButton:hover { background: rgba(13, 110, 253, 0.08); }
        ''')
        self._backup_button.setVisible(self.es_dispositivo_madre())
        self._backup_button.clicked.connect(self.manual_backup)
        left_controls_layout.addWidget(self._backup_button)

        # 4. Botón Sincronización (Oculto)
        self._sync_center_button = QPushButton()
        self._sync_center_button.setVisible(False)
        self._sync_center_button.clicked.connect(self.open_sync_center)
        left_controls_layout.addWidget(self._sync_center_button)

        # 5. Perfil
        profile_top_btn = QPushButton()
        profile_top_btn.setFixedSize(44, 44)
        profile_top_icon = os.path.join(icons_dir_ctrl, 'profile.svg')
        if os.path.exists(profile_top_icon):
            profile_top_btn.setIcon(QIcon(profile_top_icon))
            profile_top_btn.setIconSize(QtCore.QSize(22, 22))
        profile_top_btn.setToolTip("Mi perfil")
        profile_top_btn.clicked.connect(lambda: self.mostrar_frame(12))
        profile_top_btn.setStyleSheet('''
            QPushButton { background: transparent; border: none; padding: 6px; margin-right: 5px; border-radius: 12px; }
            QPushButton:hover { background: rgba(13, 110, 253, 0.08); }
        ''')
        left_controls_layout.addWidget(profile_top_btn)

        # --- SECCIÓN CENTRAL (BUSCADOR OCULTO) ---
        tools_frame = QFrame()
        tools_frame.setObjectName("toolsFrame")
        tools_layout = QHBoxLayout(tools_frame)
        tools_layout.setContentsMargins(10, 0, 10, 0)
        tools_layout.setSpacing(10)
        tools_frame.setVisible(False) # Ocultar frame central
        self._topbar_tools_frame = tools_frame

        search_container = QFrame()
        search_container.setObjectName("searchContainer")
        search_container_layout = QHBoxLayout(search_container)
        search_container_layout.setContentsMargins(0, 0, 0, 0)
        search_container_layout.setSpacing(0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar...")
        self.search_input.setFixedWidth(320)
        self.search_input.setObjectName("searchInput")
        
        search_btn = QPushButton()
        search_btn.setObjectName("searchButton")
        if os.path.exists(search_icon_path):
            search_btn.setIcon(QIcon(search_icon_path))
            search_btn.setIconSize(QtCore.QSize(18, 18))
        
        search_container_layout.addWidget(self.search_input)
        search_container_layout.addWidget(search_btn)
        tools_layout.addWidget(search_container)
        self._topbar_search_container = search_container
        
        # --- LÓGICA DE BÚSQUEDA ---
        self._search_results_menu = None
        def cerrar_resultados_busqueda():
            menu_actual = getattr(self, "_search_results_menu", None)
            if menu_actual is not None and menu_actual.isVisible():
                menu_actual.close()

        def realizar_busqueda():
            texto = self.search_input.text().strip()
            if not texto:
                cerrar_resultados_busqueda()
                return
            pacientes = self.cache.get_pacientes(self.username)
            productos = self.cache.get_productos(self.username)
            resultados = []
            for p in pacientes:
                if texto.lower() in str(p.get('nombre', '')).lower() or texto.lower() in str(p.get('dni', '')).lower():
                    resultados.append(('Paciente', p))
            for p in productos:
                if texto.lower() in str(p.get('nombre', '')).lower() or texto.lower() in str(p.get('codigo', '')).lower():
                    resultados.append(('Producto', p))
            
            if not resultados:
                QtWidgets.QMessageBox.information(self, "Búsqueda", "No se encontraron resultados.")
                return

            cerrar_resultados_busqueda()
            popup = QtWidgets.QFrame(self, QtCore.Qt.Popup)
            popup.setObjectName("globalSearchPopup")
            popup.setStyleSheet("background: white; border: 1px solid #DADADA; border-radius: 8px;")
            popup_layout = QtWidgets.QVBoxLayout(popup)
            lbl_title = QtWidgets.QLabel(f"Resultados: {len(resultados)}")
            popup_layout.addWidget(lbl_title)
            list_widget = QtWidgets.QListWidget(popup)
            list_widget.setMinimumWidth(420)
            popup_layout.addWidget(list_widget)

            for tipo, item in resultados:
                txt = f"{tipo}: {item.get('nombre', '')}"
                fila = QtWidgets.QListWidgetItem(txt)
                fila.setData(QtCore.Qt.UserRole, {'tipo': tipo, 'item': item})
                list_widget.addItem(fila)

            def abrir_resultado(fila):
                if not fila: return
                data = fila.data(QtCore.Qt.UserRole)
                cerrar_resultados_busqueda()
                if data['tipo'] == 'Paciente': self.mostrar_paciente(data['item'])
                else: self.mostrar_producto(data['item'])

            list_widget.itemClicked.connect(abrir_resultado)
            self._search_results_menu = popup
            anchor = self.search_btn_icon # Anclar al nuevo icono
            popup.move(anchor.mapToGlobal(QtCore.QPoint(0, anchor.height() + 2)))
            popup.show()

        search_btn.clicked.connect(realizar_busqueda)
        self.search_btn_icon.clicked.connect(realizar_busqueda)
        self.search_input.returnPressed.connect(realizar_busqueda)
        
        # --- ENSAMBLAJE FINAL DE TOPBAR ---
        menu_layout.addStretch()
        menu_layout.addWidget(tools_frame)
        menu_layout.addStretch()
        menu_layout.addWidget(left_controls)
        outer_layout.addWidget(menu_bar)
