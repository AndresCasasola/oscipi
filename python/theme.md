# Pico-OS Universal UI Theme

This document defines the official visual identity and UI specifications for the Pico-OS desktop applications built with PyQt5.

## Design Tokens

### 1. Color Palette (Dark Mode)
- **Background Base**: `#121212` (Used for main windows and empty space)
- **Background Surface**: `#1e1e1e` (Used for GroupBoxes and Panels)
- **Input Surface**: `#2d2d2d` (Used for Inputs, ComboBoxes, and secondary buttons)
- **Primary Accent**: `#0d6efd` (Bootstrap Blue, used for active buttons, sliders, knobs)
- **Primary Hover**: `#0b5ed7`
- **Primary Pressed**: `#0a58ca`
- **Text Primary**: `#e0e0e0`
- **Text Disabled/Muted**: `#aaaaaa`
- **Border Color**: `#444444` (Used for inputs) and `#333333` (Used for containers)

### 2. Typography
- **Font Family**: `'Segoe UI', Arial, sans-serif`
- **Base Size**: `14px` (Increased from 12/13px for better readability)
- **Interactive Elements Size**: `15px` (Buttons, Inputs, Selectors)
- **Headings**: `16px`, Bold (GroupBox titles)

### 3. Sizing & Spacing
- **Border Radius (Containers)**: `8px`
- **Border Radius (Inputs/Buttons)**: `4px` - `5px`
- **Padding (Buttons)**: `10px 20px` (Generous padding for clickable areas)
- **Padding (Inputs)**: `8px`

## Implementation
All PyQt5 scripts must import and apply the universal stylesheet to ensure a consistent, modern, and readable interface.

```python
from theme import get_stylesheet

app = QtWidgets.QApplication(sys.argv)
app.setStyleSheet(get_stylesheet())
```
