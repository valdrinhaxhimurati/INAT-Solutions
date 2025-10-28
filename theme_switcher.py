from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
import sys, os

def load_qss(relpath):
    path = os.path.join(os.path.dirname(__file__), relpath)
    try:
        with open(path, "r", encoding="utf-8") as f:
            qss = f.read()
        QApplication.instance().setStyleSheet(qss)
        print("Loaded QSS:", relpath)
    except Exception as e:
        print("Failed to load QSS:", e)

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("Theme Switcher Example")
layout = QVBoxLayout(window)

btn_dark = QPushButton("Dark Theme")
btn_light = QPushButton("Light Theme")
layout.addWidget(btn_dark)
layout.addWidget(btn_light)

btn_dark.clicked.connect(lambda: load_qss("MaterialDark.qss"))
btn_light.clicked.connect(lambda: load_qss("MaterialLight.qss"))

window.show()
sys.exit(app.exec_())
