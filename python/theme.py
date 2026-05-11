def get_stylesheet():
    return """
        QMainWindow, QWidget {
            background-color: #121212;
            color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        QLabel {
            color: #e0e0e0;
            font-size: 14px;
        }
        
        QGroupBox {
            background-color: #1e1e1e;
            border: 2px solid #333;
            border-radius: 8px;
            margin-top: 24px;
            padding-top: 15px;
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 10px;
        }
        
        QPushButton {
            background-color: #0d6efd;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 15px;
            font-weight: bold;
        }
        
        QPushButton:hover { background-color: #0b5ed7; }
        QPushButton:pressed { background-color: #0a58ca; }
        QPushButton:disabled { background-color: #333333; color: #888888; }
        
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #2d2d2d;
            color: white;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 8px;
            font-size: 15px;
        }
        
        QComboBox::drop-down {
            border-left: 1px solid #444;
            width: 20px;
        }
        
        QComboBox QListView {
            background-color: #2d2d2d;
            alternate-background-color: #2d2d2d;
            color: white;
            border: none;
            selection-background-color: #0d6efd;
            outline: 0px;
        }
        
        QComboBox QListView::item {
            min-height: 30px;
            border: none;
            padding: 5px;
            background-color: #2d2d2d;
        }
        
        QComboBox QListView::item:selected {
            background-color: #0d6efd;
            color: white;
            border: none;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #444;
            height: 10px;
            background: #2d2d2d;
            margin: 2px 0;
            border-radius: 5px;
        }
        
        QSlider::handle:horizontal {
            background: #0d6efd;
            border: 1px solid #0b5ed7;
            width: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }
        
        QDial {
            background-color: #0d6efd;
        }
        
        QLCDNumber {
            background-color: #111111;
            color: #0d6efd;
            border: 1px solid #333;
            border-radius: 4px;
        }
    """
