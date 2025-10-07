from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QListWidget, QMessageBox, QLabel, QHBoxLayout
from login import get_users, add_user, delete_user, init_db
from db_connection import get_db, dict_cursor

class BenutzerVerwaltenDialog(QDialog):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        
        init_db(self.db_path)
        self.setWindowTitle("Benutzer verwalten")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.user_list = QListWidget()
        layout.addWidget(QLabel("Benutzerkonten:"))
        layout.addWidget(self.user_list)

        # Benutzer hinzufügen
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Neuer Benutzername")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Passwort")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.add_btn = QPushButton("Benutzer hinzufügen")


        self.add_btn.clicked.connect(self.benutzer_hinzufuegen)

        layout.addWidget(QLabel("Neuen Benutzer hinzufügen:"))
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.add_btn)

        # Benutzer löschen
        self.delete_btn = QPushButton("Markierten Benutzer löschen")


        self.delete_btn.clicked.connect(self.benutzer_loeschen)
        layout.addWidget(self.delete_btn)

        self.setLayout(layout)
        self.liste_aktualisieren()

    def liste_aktualisieren(self):
        self.user_list.clear()
        users = get_users(self.db_path)  # Hier db_path übergeben
        self.user_list.addItems(users)

    def benutzer_hinzufuegen(self):
        name = self.username_input.text()
        pw = self.password_input.text()

        if not name or not pw:
            QMessageBox.warning(self, "Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
            return

        success = add_user(self.db_path, name, pw)  # db_path zuerst
        if success:
            self.username_input.clear()
            self.password_input.clear()
            self.liste_aktualisieren()
            self.accept()  # Dialog schließen
        else:
            QMessageBox.warning(self, "Fehler", "Benutzername existiert bereits.")

    def benutzer_loeschen(self):
        selected_items = self.user_list.selectedItems()
        if not selected_items:
            return
        name = selected_items[0].text()
        confirm = QMessageBox.question(self, "Löschen bestätigen", f"Benutzer '{name}' wirklich löschen?")
        if confirm == QMessageBox.Yes:
            if delete_user(self.db_path, name):  # db_path zuerst
                self.liste_aktualisieren()
            else:
                QMessageBox.warning(self, "Fehler", "Konnte Benutzer nicht löschen.")
