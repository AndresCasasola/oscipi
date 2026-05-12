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
        QProgressBar {
            background-color: #1a1a2e;
            border: 1px solid #333;
            border-radius: 4px;
            height: 18px;
            text-align: center;
            color: #ccc;
            font-size: 12px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d6efd, stop:1 #6610f2);
            border-radius: 3px;
        }
        
        QTabWidget::pane {
            border: none;
            border-top: 2px solid #0d6efd;
            background-color: #121212;
        }
        
        QTabBar::tab {
            background-color: #1a1a1a;
            color: #888;
            border: 1px solid #2a2a2a;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 10px 28px;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 0.5px;
            min-width: 140px;
        }
        
        QTabBar::tab:selected {
            background-color: #0d6efd;
            color: white;
            border-color: #0d6efd;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #252535;
            color: #ccc;
        }
    """
