import libtorrent as lt
import time
import sys
import io
import os
import ctypes
from ctypes import wintypes
from PyQt5 import QtWidgets, QtGui, QtCore

def get_download_folder_alternative():
    user_profile = os.environ.get("USERPROFILE")
    download_folder = os.path.join(user_profile, "Downloads")
    return download_folder


class TorrentWidgetItem(QtWidgets.QWidget):
    remove_torrent = QtCore.pyqtSignal(dict)

    def __init__(self, torrent, session, parent=None):
        super(TorrentWidgetItem, self).__init__(parent)

        self.torrent = torrent
        self.session = session

    def pause_resume(self):
        if self.torrent['handle'].status().paused:
            self.torrent['handle'].resume()
        else:
            self.torrent['handle'].pause()

    def remove(self):
        self.torrent['handle'].pause()
        self.torrent['to_remove'] = True
        self.session.remove_torrent(self.torrent['handle'])
        self.remove_torrent.emit(self.torrent)


class TorrentClient(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.upload_limit = None
        self.download_limit = None

        self.torrents = []

        self.setGeometry(300, 300, 800, 600)
        self.setWindowIcon(QtGui.QIcon('img/1.ico'))
        self.setWindowTitle('KrakenPeer')

        style = '''
            QWidget {
                background-color: #333333;
                color: #ffffff;
                font-family: "Arial";
            }
            QPushButton {
                background-color: #555555;
                color: #ffffff;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #777777;
            }
            QTableWidget {
                background-color: #444444;
                color: #ffffff;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #555555;
                padding: 5px;
                border: 1px solid #444444;
                color: #ffffff;
            }
        '''
        self.setStyleSheet(style)

        menu_bar = self.menuBar()

        archivo_menu = menu_bar.addMenu('Archivo')

        agregar_torrent_action = QtWidgets.QAction('Agregar Torrent', self)
        agregar_torrent_action.triggered.connect(self.add_torrent)
        archivo_menu.addAction(agregar_torrent_action)

        seleccionar_ruta_action = QtWidgets.QAction('Seleccionar Ruta de Descarga', self)
        seleccionar_ruta_action.triggered.connect(self.select_download_path)
        archivo_menu.addAction(seleccionar_ruta_action)

        download_menu = menu_bar.addMenu('Descarga')

        download_limit_action = QtWidgets.QAction('Límite de descarga', self)
        download_limit_action.triggered.connect(self.set_download_rate_limit_dialog)
        download_menu.addAction(download_limit_action)
        self.torrent_list = QtWidgets.QTableWidget(0, 4)
        self.torrent_list.setHorizontalHeaderLabels(['Nombre', 'Progreso', 'Velocidad', 'Tamaño'])
        self.torrent_list.verticalHeader().setVisible(False)
        self.torrent_list.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setCentralWidget(self.torrent_list)
        self.torrent_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.torrent_list.customContextMenuRequested.connect(self.show_context_menu)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_torrents)
        self.timer.start(1000)


        self.download_path = get_download_folder_alternative()

        
        
        self.show()
        self.setAcceptDrops(True)


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.torrent'):
                self.add_torrent_from_file(path)
    def add_torrent_from_file(self, file_path):
        handle = self.session.add_torrent({'ti': lt.torrent_info(file_path), 'save_path': self.download_path})
        self.torrents.append({'handle': handle, 'progress': 0, 'item': None, 'to_remove': False, 'name': handle.name()})


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.torrent_list.setGeometry(10, 50, self.width() - 20, self.height() - 100)

    def select_download_path(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ShowDirsOnly
        download_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar Ruta de Descarga', self.download_path, options=options)
        if download_path:
            self.download_path = download_path

    def add_torrent(self):
        file_dialog = QtWidgets.QFileDialog.getOpenFileName(self, 'Seleccionar archivo torrent')

        if file_dialog[0]:
            torrent_file = file_dialog[0]

            handle = self.session.add_torrent({'ti': lt.torrent_info(torrent_file), 'save_path': self.download_path})

            self.torrents.append({'handle': handle, 'progress': 0, 'item': None, 'to_remove': False, 'name': handle.name()})

    def update_torrents(self):
        for t in self.torrents:
            if t['to_remove']:
                continue

            handle = t['handle']

            if handle.is_valid():
                status = handle.status()

                t['progress'] = int(status.progress * 100)
                t['download_rate'] = status.download_rate / 1000 / 1000  # MB/s

                if not t['item']:
                    t['item'] = TorrentWidgetItem(t, self.session)
                    row_position = self.torrent_list.rowCount()
                    self.torrent_list.insertRow(row_position)

                    self.torrent_list.setItem(row_position, 0, QtWidgets.QTableWidgetItem(t['name']))

                    progress_bar = QtWidgets.QProgressBar()
                    progress_bar.setValue(t['progress'])
                    progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid grey;
                        border-radius: 5px;
                        text-align: center;
                    }

                    QProgressBar::chunk {
                        background-color: #008000;
                    }
                    """)
                    self.torrent_list.setCellWidget(row_position, 1, progress_bar)

                    self.torrent_list.setItem(row_position, 2, QtWidgets.QTableWidgetItem(f"{t['download_rate']:.2f} MB/s"))
                    self.torrent_list.setCellWidget(row_position, 3, t['item'])

                    t['item'].remove_torrent.connect(self.remove_torrent)
                    t['list_item'] = row_position
                    file_size_gb = handle.status().total_wanted / (1024 * 1024 * 1024)
                    self.torrent_list.setItem(row_position, 3, QtWidgets.QTableWidgetItem(f"{file_size_gb:.2f} GB"))
                    self.torrent_list.setCellWidget(row_position, 4, t['item'])


                else:
                    self.torrent_list.item(t['list_item'], 0).setText(t['name'])
                    progress_bar = self.torrent_list.cellWidget(t['list_item'], 1)
                    progress_bar.setValue(t['progress'])

                    
                    if status.paused:
                        progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: 2px solid grey;
                            border-radius: 5px;
                            text-align: center;
                        }

                        QProgressBar::chunk {
                            background-color: #FFD700;
                        }
                        """)
                    else:
                        progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: 2px solid grey;
                            border-radius: 5px;
                            text-align: center;
                        }

                        QProgressBar::chunk {
                            background-color: #008000;
                        }
                        """)

                    file_size_gb = handle.status().total_wanted / (1024 * 1024 * 1024)
                    self.torrent_list.setItem(t['list_item'], 3, QtWidgets.QTableWidgetItem(f"{file_size_gb:.2f} GB"))
                    self.torrent_list.item(t['list_item'], 2).setText(f"{t['download_rate']:.2f} MB/s")
                    self.torrent_list.item(t['list_item'], 2).setTextAlignment(QtCore.Qt.AlignCenter)
                    self.torrent_list.item(t['list_item'], 3).setTextAlignment(QtCore.Qt.AlignCenter)

            else:
                self.torrent_list.removeRow(t['list_item'])
                self.torrents.remove(t)
                break


                
    def contextMenuEvent(self, event):
        index = self.torrent_list.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            if row < len(self.torrents):
                t = self.torrents[row]

                context_menu = QtWidgets.QMenu(self)

                pause_action = QtWidgets.QAction('Pausar' if not t['handle'].status().paused else 'Reanudar', self)
                pause_action.triggered.connect(t['item'].pause_resume)
                context_menu.addAction(pause_action)

                remove_action = QtWidgets.QAction('Eliminar', self)
                remove_action.triggered.connect(t['item'].remove)
                context_menu.addAction(remove_action)

                context_menu.exec_(event.globalPos())

    def remove_torrent(self, torrent):
        if torrent in self.torrents:
            self.torrent_list.removeRow(torrent['list_item'])
            self.torrents.remove(torrent)

    def set_download_rate_limit(self, limit):
        if self.download_limit != limit:
            self.download_limit = limit
            self.session.set_download_rate_limit(limit * 1000)

    def set_download_rate_limit_dialog(self):
        limit, ok = QtWidgets.QInputDialog.getInt(self, 'Límite de descarga', 'Velocidad de descarga (KB/s):', self.download_limit or 0, 0)
        if ok:
            self.set_download_rate_limit(limit)
    def show_context_menu(self, pos):
        index = self.torrent_list.indexAt(pos)
        if index.isValid():
            row = index.row()
            if row < len(self.torrents):
                t = self.torrents[row]

                context_menu = QtWidgets.QMenu(self)

                pause_action = QtWidgets.QAction('Pausar' if not t['handle'].status().paused else 'Reanudar', self)
                pause_action.triggered.connect(t['item'].pause_resume)
                context_menu.addAction(pause_action)

                remove_action = QtWidgets.QAction('Eliminar', self)
                remove_action.triggered.connect(t['item'].remove)
                context_menu.addAction(remove_action)

                context_menu.exec_(self.torrent_list.viewport().mapToGlobal(pos))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    client = TorrentClient()
    sys.exit(app.exec_())

