"""
Estilos consistentes para botones en la aplicación VISO
"""

PRIMARY_BUTTON = """
QPushButton {
    background-color: #0078D4;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #106EBE;
}
QPushButton:pressed {
    background-color: #005A9E;
}
QPushButton:disabled {
    background-color: #C8C8C8;
    color: #666666;
}
"""

SECONDARY_BUTTON = """
QPushButton {
    background-color: white;
    color: #0078D4;
    border: 1px solid #0078D4;
    border-radius: 4px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #E5F3FF;
}
QPushButton:pressed {
    background-color: #C7E0F4;
}
QPushButton:disabled {
    border-color: #C8C8C8;
    color: #666666;
}
"""

DELETE_BUTTON = """
QPushButton {
    background-color: white;
    color: #D83B01;
    border: 1px solid #D83B01;
    border-radius: 4px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #FDE7E9;
}
QPushButton:pressed {
    background-color: #F4C8C8;
}
"""

ACTION_BUTTON = """
QPushButton {
    background-color: #F0F0F0;
    color: #333333;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    text-align: left;
}
QPushButton:hover {
    background-color: #E5E5E5;
}
QPushButton:pressed {
    background-color: #D9D9D9;
}
"""

ICON_BUTTON = """
QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px;
}
QPushButton:hover {
    background-color: #E5E5E5;
}
QPushButton:pressed {
    background-color: #D9D9D9;
}
"""

# Estilo para botones de navegación en la barra lateral
SIDEBAR_BUTTON = """
QPushButton {
    background-color: transparent;
    color: #333333;
    border: none;
    border-radius: 0px;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
}
QPushButton:hover {
    background-color: rgba(0, 120, 212, 0.1);
}
QPushButton:checked {
    background-color: rgba(0, 120, 212, 0.2);
    color: #0078D4;
    border-left: 4px solid #0078D4;
}
"""

# Estilo para botones de submenu en la barra lateral
SUBMENU_BUTTON = """
QPushButton {
    background-color: transparent;
    color: #666666;
    border: none;
    border-radius: 0px;
    padding: 8px 16px 8px 32px;
    text-align: left;
    font-size: 13px;
}
QPushButton:hover {
    background-color: rgba(0, 120, 212, 0.05);
}
QPushButton:checked {
    background-color: rgba(0, 120, 212, 0.1);
    color: #0078D4;
}
"""

def create_action_button_group(title):
    return f"""
QGroupBox {{
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    margin-top: 16px;
}}
QGroupBox::title {{
    color: #333333;
    font-weight: bold;
    padding: 8px;
    margin-left: 8px;
}}
"""