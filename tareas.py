import sys
import sqlite3
from datetime import datetime, timedelta
import json
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QComboBox, QLabel, QSplitter, 
                             QTextEdit, QMessageBox, QDialog, QLineEdit, QDateEdit, QFormLayout,
                             QCalendarWidget, QTabWidget, QProgressBar, QColorDialog, QFileDialog,
                             QInputDialog, QTimeEdit, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QDate, QTime, QUrl
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWebEngineWidgets import QWebEngineView

import pytesseract
from PIL import Image
import cv2
import numpy as np

class CloudSync:
    def __init__(self):
        self.api_url = "https://api.example.com/sync"  # aca api si quieren 

    def sync_tasks(self, tasks):
        response = requests.post(self.api_url, json=tasks)
        return response.json()

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('tasks.db')
        self.create_table()
        self.update_table_schema()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                project TEXT,
                title TEXT,
                description TEXT,
                priority INTEGER,
                due_date TEXT,
                category TEXT,
                completed INTEGER DEFAULT 0,
                tags TEXT,
                subtasks TEXT,
                time_spent INTEGER DEFAULT 0,
                collaborators TEXT,
                voice_note TEXT,
                image_text TEXT
            )
        ''')
        self.conn.commit()

    def update_table_schema(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        new_columns = ['tags', 'subtasks', 'time_spent', 'collaborators', 'voice_note', 'image_text']
        for column in new_columns:
            if column not in columns:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column} TEXT")
        self.conn.commit()

    def add_task(self, project, title, description, priority, due_date, category, tags, subtasks, collaborators):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (project, title, description, priority, due_date, category, tags, subtasks, collaborators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project, title, description, priority, due_date, category, json.dumps(tags), json.dumps(subtasks), json.dumps(collaborators)))
        self.conn.commit()
        return cursor.lastrowid

    def get_tasks(self, project=None, category=None):
        cursor = self.conn.cursor()
        if project and project != "Todos los proyectos":
            cursor.execute('SELECT * FROM tasks WHERE project = ?', (project,))
        elif category and category != "Todas las categorías":
            cursor.execute('SELECT * FROM tasks WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT * FROM tasks')
        return cursor.fetchall()

    def update_task(self, task_id, project, title, description, priority, due_date, category, tags, subtasks, collaborators):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tasks
            SET project = ?, title = ?, description = ?, priority = ?, due_date = ?, category = ?, tags = ?, subtasks = ?, collaborators = ?
            WHERE id = ?
        ''', (project, title, description, priority, due_date, category, json.dumps(tags), json.dumps(subtasks), json.dumps(collaborators), task_id))
        self.conn.commit()
        return cursor.rowcount

    def delete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.conn.commit()
        return cursor.rowcount

    def get_projects(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT project FROM tasks')
        return [row[0] for row in cursor.fetchall()]

    def get_categories(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM tasks')
        return [row[0] for row in cursor.fetchall()]

    def complete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tasks SET completed = 1 WHERE id = ?', (task_id,))
        self.conn.commit()
        return cursor.rowcount

    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM tasks')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE completed = 1')
        completed = cursor.fetchone()[0]
        return total, completed

    def update_time_spent(self, task_id, time_spent):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tasks SET time_spent = time_spent + ? WHERE id = ?', (time_spent, task_id))
        self.conn.commit()
        return cursor.rowcount

    def add_voice_note(self, task_id, voice_note_path):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tasks SET voice_note = ? WHERE id = ?', (voice_note_path, task_id))
        self.conn.commit()
        return cursor.rowcount

    def add_image_text(self, task_id, image_text):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tasks SET image_text = ? WHERE id = ?', (image_text, task_id))
        self.conn.commit()
        return cursor.rowcount

class TaskManager:
    def __init__(self):
        self.db = Database()
        self.cloud_sync = CloudSync()

    def add_task(self, project, title, description, priority, due_date, category, tags, subtasks, collaborators):
        task_id = self.db.add_task(project, title, description, priority, due_date, category, tags, subtasks, collaborators)
        self.sync_tasks()
        return task_id

    def get_tasks(self, project=None, category=None):
        return self.db.get_tasks(project, category)

    def update_task(self, task_id, project, title, description, priority, due_date, category, tags, subtasks, collaborators):
        result = self.db.update_task(task_id, project, title, description, priority, due_date, category, tags, subtasks, collaborators)
        self.sync_tasks()
        return result

    def delete_task(self, task_id):
        result = self.db.delete_task(task_id)
        self.sync_tasks()
        return result

    def get_projects(self):
        return self.db.get_projects()

    def get_categories(self):
        return self.db.get_categories()

    def complete_task(self, task_id):
        result = self.db.complete_task(task_id)
        self.sync_tasks()
        return result

    def get_stats(self):
        return self.db.get_stats()

    def sync_tasks(self):
        tasks = self.db.get_tasks()
        self.cloud_sync.sync_tasks(tasks)

    def update_time_spent(self, task_id, time_spent):
        return self.db.update_time_spent(task_id, time_spent)

    def add_voice_note(self, task_id, voice_note_path):
        return self.db.add_voice_note(task_id, voice_note_path)

    def add_image_text(self, task_id, image_text):
        return self.db.add_image_text(task_id, image_text)

class TaskDialog(QDialog):
    def __init__(self, parent=None, task_id=None):
        super().__init__(parent)
        self.task_id = task_id
        self.task_manager = parent.task_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Agregar/Editar Tarea")
        layout = QFormLayout()

        self.project_input = QComboBox()
        self.project_input.setEditable(True)
        projects = self.task_manager.get_projects()
        self.project_input.addItems(projects)
        layout.addRow("Proyecto:", self.project_input)

        self.title_input = QLineEdit()
        layout.addRow("Título:", self.title_input)

        self.description_input = QTextEdit()
        layout.addRow("Descripción:", self.description_input)

        self.priority_input = QComboBox()
        self.priority_input.addItems(["Baja", "Media", "Alta"])
        layout.addRow("Prioridad:", self.priority_input)

        self.due_date_input = QDateEdit()
        self.due_date_input.setDate(QDate.currentDate())
        self.due_date_input.setCalendarPopup(True)
        layout.addRow("Fecha límite:", self.due_date_input)

        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        categories = self.task_manager.get_categories()
        self.category_input.addItems(categories)
        layout.addRow("Categoría:", self.category_input)

        self.tags_input = QLineEdit()
        layout.addRow("Etiquetas (separadas por comas):", self.tags_input)

        self.subtasks_input = QTextEdit()
        layout.addRow("Subtareas (una por línea):", self.subtasks_input)

        self.collaborators_input = QLineEdit()
        layout.addRow("Colaboradores (separados por comas):", self.collaborators_input)

        save_button = QPushButton("Guardar")
        save_button.clicked.connect(self.accept)
        layout.addRow(save_button)

        self.setLayout(layout)

        if self.task_id:
            self.load_task_data()

    def load_task_data(self):
        tasks = self.task_manager.get_tasks()
        task = next((t for t in tasks if t[0] == self.task_id), None)
        if task:
            self.project_input.setCurrentText(task[1])
            self.title_input.setText(task[2])
            self.description_input.setText(task[3])
            self.priority_input.setCurrentIndex(task[4])
            self.due_date_input.setDate(QDate.fromString(task[5], "yyyy-MM-dd"))
            self.category_input.setCurrentText(task[6])
            self.tags_input.setText(", ".join(json.loads(task[8])))
            self.subtasks_input.setText("\n".join(json.loads(task[9])))
            self.collaborators_input.setText(", ".join(json.loads(task[11])))

    def get_task_data(self):
        return (
            self.project_input.currentText(),
            self.title_input.text(),
            self.description_input.toPlainText(),
            self.priority_input.currentIndex(),
            self.due_date_input.date().toString("yyyy-MM-dd"),
            self.category_input.currentText(),
            [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()],
            [subtask.strip() for subtask in self.subtasks_input.toPlainText().split("\n") if subtask.strip()],
            [collaborator.strip() for collaborator in self.collaborators_input.text().split(",") if collaborator.strip()]
        )

class PomodoroTimer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
     
        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 48px; font-weight: bold;")
        layout.addWidget(self.time_label)

     
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Iniciar")
        self.start_button.clicked.connect(self.toggle_timer)
        button_layout.addWidget(self.start_button)

        self.reset_button = QPushButton("Reiniciar")
        self.reset_button.clicked.connect(self.reset_timer)
        button_layout.addWidget(self.reset_button)

        layout.addLayout(button_layout)

  
        adjust_layout = QHBoxLayout()
        
        self.decrease_button = QPushButton("-")
        self.decrease_button.clicked.connect(self.decrease_time)
        adjust_layout.addWidget(self.decrease_button)

        self.increase_button = QPushButton("+")
        self.increase_button.clicked.connect(self.increase_time)
        adjust_layout.addWidget(self.increase_button)

        layout.addLayout(adjust_layout)

       
        self.mode_label = QLabel("Modo: Trabajo")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.time_left = 25 * 60
        self.is_break = False

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.start_button.setText("Reanudar")
        else:
            self.timer.start(1000)
            self.start_button.setText("Pausar")

    def reset_timer(self):
        self.timer.stop()
        self.time_left = 25 * 60 if not self.is_break else 5 * 60
        self.update_display()
        self.start_button.setText("Iniciar")

    def update_timer(self):
        self.time_left -= 1
        if self.time_left <= 0:
            self.timer.stop()
            self.toggle_mode()
        self.update_display()

    def update_display(self):
        minutes, seconds = divmod(self.time_left, 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

    def increase_time(self):
        self.time_left += 60
        self.update_display()

    def decrease_time(self):
        if self.time_left > 60:
            self.time_left -= 60
            self.update_display()

    def toggle_mode(self):
        self.is_break = not self.is_break
        if self.is_break:
            self.time_left = 5 * 60
            self.mode_label.setText("Modo: Descanso")
            QMessageBox.information(self, "Pomodoro", "¡Tiempo de descanso!")
        else:
            self.time_left = 25 * 60
            self.mode_label.setText("Modo: Trabajo")
            QMessageBox.information(self, "Pomodoro", "¡Tiempo de volver al trabajo!")
        self.update_display()
        self.start_button.setText("Iniciar")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_manager = TaskManager()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Gestor de Tareas Avanzado')
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

     
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

      
        self.project_selector = QComboBox()
        self.project_selector.addItem("Todos los proyectos")
        self.project_selector.currentTextChanged.connect(self.load_tasks)
        left_layout.addWidget(QLabel("Proyecto:"))
        left_layout.addWidget(self.project_selector)

        self.category_selector = QComboBox()
        self.category_selector.addItem("Todas las categorías")
        self.category_selector.currentTextChanged.connect(self.load_tasks)
        left_layout.addWidget(QLabel("Categoría:"))
        left_layout.addWidget(self.category_selector)

        # Lista de tareas
        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self.show_task_details)
        left_layout.addWidget(QLabel("Tareas:"))
        left_layout.addWidget(self.task_list)

   
        button_layout = QHBoxLayout()
        add_button = QPushButton('Agregar Tarea')
        add_button.clicked.connect(self.add_task)
        edit_button = QPushButton('Editar Tarea')
        edit_button.clicked.connect(self.edit_task)
        delete_button = QPushButton('Eliminar Tarea')
        delete_button.clicked.connect(self.delete_task)
        complete_button = QPushButton('Completar Tarea')
        complete_button.clicked.connect(self.complete_task)
        generate_report_button = QPushButton('Generar Reporte')
        generate_report_button.clicked.connect(self.generate_report)
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(complete_button)
        button_layout.addWidget(generate_report_button)
        left_layout.addLayout(button_layout)

    
        right_panel = QTabWidget()

       
        details_tab = QWidget()
        details_layout = QVBoxLayout()
        details_tab.setLayout(details_layout)

        self.task_details = QTextEdit()
        self.task_details.setReadOnly(True)
        details_layout.addWidget(QLabel("Detalles de la tarea:"))
        details_layout.addWidget(self.task_details)

        right_panel.addTab(details_tab, "Detalles")

      
        calendar_tab = QWidget()
        calendar_layout = QVBoxLayout()
        calendar_tab.setLayout(calendar_layout)

        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self.show_tasks_for_date)
        calendar_layout.addWidget(self.calendar)

        self.date_tasks = QListWidget()
        calendar_layout.addWidget(self.date_tasks)

        right_panel.addTab(calendar_tab, "Calendario")

       
        stats_tab = QWidget()
        stats_layout = QVBoxLayout()
        stats_tab.setLayout(stats_layout)

        self.stats_label = QLabel()
        stats_layout.addWidget(self.stats_label)

        self.progress_bar = QProgressBar()
        stats_layout.addWidget(self.progress_bar)

     

        right_panel.addTab(stats_tab, "Estadísticas")

      
        pomodoro_tab = QWidget()
        pomodoro_layout = QVBoxLayout()
        pomodoro_tab.setLayout(pomodoro_layout)

        self.pomodoro_timer = PomodoroTimer()
        pomodoro_layout.addWidget(self.pomodoro_timer)

        pomodoro_description = QLabel("La técnica Pomodoro consiste en trabajar en intervalos de 25 minutos seguidos de descansos de 5 minutos. Usa los botones + y - para ajustar el tiempo según tus necesidades.")
        pomodoro_description.setWordWrap(True)
        pomodoro_layout.addWidget(pomodoro_description)

        right_panel.addTab(pomodoro_tab, "Pomodoro")

     
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        main_layout.addWidget(splitter)

        self.load_projects()
        self.load_categories()
        self.load_tasks()
        self.update_stats()

       
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_due_dates)
        self.timer.start(60000)  

        
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)

    def load_projects(self):
        projects = self.task_manager.get_projects()
        self.project_selector.clear()
        self.project_selector.addItem("Todos los proyectos")
        self.project_selector.addItems(projects)

    def load_categories(self):
        categories = self.task_manager.get_categories()
        self.category_selector.clear()
        self.category_selector.addItem("Todas las categorías")
        self.category_selector.addItems(categories)

    def load_tasks(self):
        self.task_list.clear()
        project = self.project_selector.currentText()
        category = self.category_selector.currentText()
        tasks = self.task_manager.get_tasks(project if project != "Todos los proyectos" else None,
                                            category if category != "Todas las categorías" else None)
        for task in tasks:
            self.task_list.addItem(f"{task[0]}: {task[2]} - {task[1]} - Prioridad: {task[4]} - Categoría: {task[6]}")

    def show_task_details(self, item):
        task_id = int(item.text().split(':')[0])
        tasks = self.task_manager.get_tasks()
        task = next((t for t in tasks if t[0] == task_id), None)
        if task:
            details = f"Título: {task[2]}\n\n"
            details += f"Proyecto: {task[1]}\n\n"
            details += f"Descripción: {task[3]}\n\n"
            details += f"Prioridad: {['Baja', 'Media', 'Alta'][task[4]]}\n\n"
            details += f"Fecha límite: {task[5]}\n\n"
            details += f"Categoría: {task[6]}\n\n"
            details += f"Etiquetas: {', '.join(json.loads(task[8]))}\n\n"
            details += f"Subtareas:\n{chr(10).join(json.loads(task[9]))}\n\n"
            details += f"Tiempo dedicado: {task[10]} minutos\n\n"
            details += f"Colaboradores: {', '.join(json.loads(task[11]))}\n\n"
            details += f"Estado: {'Completada' if task[7] else 'Pendiente'}"
            self.task_details.setText(details)


    def add_task(self):
        dialog = TaskDialog(self)
        if dialog.exec():
            project, title, description, priority, due_date, category, tags, subtasks, collaborators = dialog.get_task_data()
            self.task_manager.add_task(project, title, description, priority, due_date, category, tags, subtasks, collaborators)
            self.load_projects()
            self.load_categories()
            self.load_tasks()
            self.update_stats()

    def edit_task(self):
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = int(current_item.text().split(':')[0])
            dialog = TaskDialog(self, task_id)
            if dialog.exec():
                project, title, description, priority, due_date, category, tags, subtasks, collaborators = dialog.get_task_data()
                self.task_manager.update_task(task_id, project, title, description, priority, due_date, category, tags, subtasks, collaborators)
                self.load_projects()
                self.load_categories()
                self.load_tasks()
                self.update_stats()

    def delete_task(self):
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = int(current_item.text().split(':')[0])
            confirm = QMessageBox.question(self, 'Confirmar eliminación', 
                                           '¿Estás seguro de que quieres eliminar esta tarea?',
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.task_manager.delete_task(task_id)
                self.load_projects()
                self.load_categories()
                self.load_tasks()
                self.update_stats()

    def complete_task(self):
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = int(current_item.text().split(':')[0])
            self.task_manager.complete_task(task_id)
            self.load_tasks()
            self.update_stats()

    def check_due_dates(self):
        tasks = self.task_manager.get_tasks()
        now = datetime.now()
        for task in tasks:
            due_date = datetime.strptime(task[5], "%Y-%m-%d")
            if due_date.date() == now.date():
                self.show_notification(f"La tarea '{task[2]}' vence hoy!")
            elif due_date.date() == (now + timedelta(days=1)).date():
                self.show_notification(f"La tarea '{task[2]}' vence mañana!")

    def show_notification(self, message):
        QMessageBox.information(self, "Recordatorio de tarea", message)

    def show_tasks_for_date(self):
        selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        tasks = self.task_manager.get_tasks()
        self.date_tasks.clear()
        for task in tasks:
            if task[5] == selected_date:
                self.date_tasks.addItem(f"{task[2]} - {task[1]}")

    def update_stats(self):
        total, completed = self.task_manager.get_stats()
        self.stats_label.setText(f"Total de tareas: {total}\nTareas completadas: {completed}")
        if total > 0:
            completion_rate = (completed / total) * 100
            self.progress_bar.setValue(int(completion_rate))
            self.stats_label.setText(self.stats_label.text() + f"\nPorcentaje completado: {completion_rate:.2f}%")
        else:
            self.progress_bar.setValue(0)
            self.stats_label.setText(self.stats_label.text() + "\nNo hay tareas aún")


    def add_image_text(self):
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = int(current_item.text().split(':')[0])
            file_name, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen", "", "Image Files (*.png *.jpg *.bmp)")
            if file_name:
                image = Image.open(file_name)
                text = pytesseract.image_to_string(image)
                self.task_manager.add_image_text(task_id, text)
                QMessageBox.information(self, "Texto extraído", f"Texto extraído de la imagen: {text}")

    def generate_report(self):
        tasks = self.task_manager.get_tasks()
        report = "Reporte de Tareas\n\n"

        for task in tasks:
            report += f"ID: {task[0]}\n"
            report += f"Título: {task[2]}\n"
            report += f"Proyecto: {task[1]}\n"
            report += f"Descripción: {task[3]}\n"
            report += f"Prioridad: {['Baja', 'Media', 'Alta'][task[4]]}\n"
            report += f"Fecha límite: {task[5]}\n"
            report += f"Categoría: {task[6]}\n"
            report += f"Estado: {'Completada' if task[7] else 'Pendiente'}\n"
            report += f"Etiquetas: {', '.join(json.loads(task[8]))}\n"
            report += f"Subtareas: {', '.join(json.loads(task[9]))}\n"
            report += f"Tiempo dedicado: {task[10]} minutos\n"
            report += f"Colaboradores: {', '.join(json.loads(task[11]))}\n\n"

        file_name, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", "", "Archivos de Texto (*.txt)")
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(report)
            QMessageBox.information(self, "Reporte Generado", f"El reporte ha sido guardado en {file_name}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion') 
    app.setWindowIcon(QIcon('icon.png'))  
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

