"""Additive account/channel/library window; existing generation controls stay intact."""

from __future__ import annotations
import json
import sys
from pathlib import Path
from PySide6.QtCore import QProcess, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QAbstractItemView,
    QHeaderView,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from tools.ytbot import browser_install, channels, config, library
from tools.ytbot.accounts_store import AccountStore


class OAuthJob(QThread):
    connected = Signal(object)
    rejected = Signal(str)

    def __init__(self, store, account, client):
        super().__init__()
        self.store = store
        self.account = account
        self.client = client

    def run(self):
        from tools.ytbot.oauth import connect

        try:
            self.connected.emit(connect(self.store, self.account, Path(self.client)))
        except Exception:
            self.rejected.emit(
                "A conexão Google não foi concluída. Verifique o consentimento e o cliente OAuth Desktop (0600)."
            )


class AccountsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YoutubeBot · Contas, canais e vídeos")
        self.resize(1020, 720)
        self.store = AccountStore()
        self.browser = None
        self.verification = None
        self.readiness = None
        self.oauth_job = None
        self.oauth_channels = []
        layout = QVBoxLayout(self)
        title = QLabel("Contas e canais do YouTube")
        title.setStyleSheet("font-size:22px;font-weight:600;")
        layout.addWidget(title)
        layout.addWidget(
            QLabel(
                "Conecte cada conta em seu próprio navegador. A geração e o upload continuam usando o fluxo existente."
            )
        )
        form = QFormLayout()
        self.account = QComboBox()
        form.addRow("Conta do navegador", self.account)
        self.channel = QComboBox()
        for channel in channels.CHANNELS.values():
            self.channel.addItem(channel.name, channel.slug)
        self.channel.setPlaceholderText("Escolha o perfil do canal")
        bindings = self.store.load()["bindings"]
        preferred = next(iter(bindings)) if len(bindings) == 1 else None
        self.channel.setCurrentIndex(self.channel.findData(preferred))
        self.channel.currentIndexChanged.connect(self.refresh_library)
        form.addRow("Perfil do canal", self.channel)
        layout.addLayout(form)
        add = QHBoxLayout()
        self.identifier = QLineEdit()
        self.identifier.setPlaceholderText("ID da conta: trabalho, pessoal...")
        self.label = QLineEdit()
        self.label.setPlaceholderText("Nome para mostrar")
        button = QPushButton("Adicionar conta")
        button.clicked.connect(self.add_account)
        add.addWidget(self.identifier)
        add.addWidget(self.label)
        add.addWidget(button)
        layout.addLayout(add)
        actions = QHBoxLayout()
        self.signin = QPushButton("Conectar Google / YouTube e ChatGPT")
        self.signin.clicked.connect(self.connect_browser)
        actions.addWidget(self.signin)
        self.finish_signin = QPushButton("Concluir login")
        self.finish_signin.setEnabled(False)
        self.finish_signin.clicked.connect(self.finish_browser_login)
        actions.addWidget(self.finish_signin)
        self.oauth = QPushButton("Conectar API Google (opcional)")
        self.oauth.clicked.connect(self.connect_oauth)
        actions.addWidget(self.oauth)
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(refresh)
        layout.addLayout(actions)
        guide = QHBoxLayout()
        self.check = QPushButton("Verificar conexão completa")
        self.check.clicked.connect(self.check_connection)
        guide.addWidget(self.check)
        help_button = QPushButton("Ajuda para instalar e conectar")
        help_button.clicked.connect(self.show_setup_help)
        guide.addWidget(help_button)
        layout.addLayout(guide)
        self.verified = QComboBox()
        form2 = QFormLayout()
        form2.addRow("Canal verificado pela API", self.verified)
        layout.addLayout(form2)
        bind = QPushButton("Usar esta conta no perfil escolhido")
        bind.clicked.connect(self.bind)
        layout.addWidget(bind)
        self.binding = QLabel()
        self.binding.setWordWrap(True)
        layout.addWidget(self.binding)
        layout.addWidget(
            QLabel("Vídeos e títulos · histórico local do perfil selecionado")
        )
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Pesquisar títulos, assunto ou vídeo neste histórico"
        )
        self.search.textChanged.connect(self.render_library)
        layout.addWidget(self.search)
        self.records = []
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Título", "Estado", "Agendamento", "Vídeo"]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in [1, 2, 3]:
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )
        layout.addWidget(self.table, 1)
        self.status = QLabel(
            "A conexão precisa ser feita por você. Nenhum vídeo é gerado ou publicado ao abrir esta janela."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.account.currentIndexChanged.connect(self.refresh_verified)
        self.refresh()

    def selected_account(self):
        return self.account.currentData() or "legacy"

    def refresh(self):
        previous = self.account.currentData()
        if previous is None:
            previous = self.store.load()["bindings"].get(self.channel.currentData(), {}).get("account_id")
            if previous is None:
                previous = next(iter(self.store.load()["accounts"]), "legacy")
        self.account.blockSignals(True)
        self.account.clear()
        for item in self.store.public_accounts():
            suffix = (
                " · perfil existente"
                if item["browser_configured"]
                else " · precisa conectar"
            )
            self.account.addItem(item["label"] + suffix, item["id"])
        index = self.account.findData(previous)
        self.account.setCurrentIndex(max(0, index))
        self.account.blockSignals(False)
        self.refresh_verified()
        self.refresh_library()

    def add_account(self):
        try:
            self.store.create(self.identifier.text().strip(), self.label.text().strip())
            self.refresh()
            self.identifier.clear()
            self.label.clear()
        except ValueError as error:
            QMessageBox.warning(self, "Conta", str(error))

    def connect_browser(self):
        if self.browser and self.browser.state() != QProcess.NotRunning:
            return
        self.browser = QProcess(self)
        self.browser.setWorkingDirectory(str(config.ROOT))
        self.browser.setProcessChannelMode(QProcess.SeparateChannels)
        self.browser.finished.connect(self.browser_finished)
        arguments = [
                "-m",
                "tools.ytbot",
                "accounts",
                "connect",
                "--account",
                self.selected_account(),
            ]
        if self.selected_account() != "legacy" and browser_install.managed_executable():
            arguments.append("--managed")
        self.browser.start(sys.executable, arguments)
        self.signin.setEnabled(False)
        self.finish_signin.setEnabled(True)
        self.status.setText(
            "Conecte Google/YouTube e ChatGPT e feche o navegador. A primeira ativação do navegador automático pede novos logins; o perfil anterior fica preservado."
        )

    def browser_finished(self, exit_code, _status):
        self.signin.setEnabled(True)
        self.finish_signin.setEnabled(False)
        self.refresh()
        self.status.setText(
            "Login encerrado. Escolha o perfil do canal, vincule a conta e clique em Verificar conexão completa."
            if exit_code == 0
            else "Não foi possível abrir a sessão. Verifique o Chrome, o ambiente gráfico e se há lote ativo nessa conta."
        )

    def finish_browser_login(self):
        if self.browser and self.browser.state() != QProcess.NotRunning:
            self.browser.terminate()
            self.finish_signin.setEnabled(False)
            self.status.setText("Salvando a sessão e encerrando o navegador desta conta...")

    def show_setup_help(self):
        QMessageBox.information(
            self, "Instalação e conexão",
            "Em outro computador Ubuntu/Debian, baixe o projeto e execute, dentro da pasta dele:\n"
            "bash scripts/install-linux.sh\n\n"
            "1. Escolha ou adicione sua conta nesta janela.\n"
            "2. Clique em Conectar Google / YouTube e ChatGPT. As duas abas serão abertas.\n"
            "3. Entre pessoalmente nas contas e escolha o canal correto no YouTube.\n"
            "4. Clique em Concluir login ou feche a janela do navegador para salvar a sessão.\n"
            "5. Escolha o perfil do canal e clique em Usar esta conta no perfil escolhido.\n"
            "6. Clique em Verificar conexão completa.\n\n"
            "O instalador prepara a extensão automaticamente: não é necessário selecionar pastas. "
            "Se houver duas cópias da extensão, use a que fica em dist/chrome.\n\n"
            "Os logins ficam no perfil privado deste PC. Em outro PC ou após expirar a sessão, "
            "o Google e o ChatGPT podem pedir um novo login. Reinstalar não apaga as contas. "
            "Guia completo: docs/INSTALL-LINUX.md.",
        )

    def check_connection(self):
        if not self.channel.currentData():
            self.status.setText("Escolha o perfil do canal antes de verificar a conexão.")
            return
        if self.browser and self.browser.state() != QProcess.NotRunning:
            self.status.setText("Feche a janela de login antes de verificar a conexão.")
            return
        if self.readiness and self.readiness.state() != QProcess.NotRunning:
            return
        self.readiness = QProcess(self)
        self.readiness.setWorkingDirectory(str(config.ROOT))
        self.readiness.finished.connect(self.readiness_finished)
        self.readiness.start(sys.executable, [
            "-m", "tools.ytbot", "accounts", "check", "--account", self.selected_account(),
            "--channel", self.channel.currentData(),
        ])
        self.check.setEnabled(False)
        self.status.setText("Conferindo canal, extensão e sessão ChatGPT. Aguarde; nenhum vídeo será enviado.")

    def readiness_finished(self, code, _status):
        self.check.setEnabled(True)
        try:
            result = json.loads(bytes(self.readiness.readAllStandardOutput()).decode())
        except (ValueError, UnicodeError):
            self.status.setText("Não foi possível verificar. Feche o login e aguarde qualquer lote ativo antes de tentar novamente.")
            return
        labels = [("Canal correto", "channel_verified"), ("Extensão", "extension_ready"), ("ChatGPT conectado", "chatgpt_authenticated")]
        self.status.setText(" · ".join(f"{label}: {'OK' if result.get(key) else 'precisa verificar'}" for label, key in labels)
                            + (". Conexões prontas." if code == 0 and result.get("ready") else ". Use Conectar ou consulte a ajuda."))

    def connect_oauth(self):
        if self.oauth_job and self.oauth_job.isRunning():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Cliente Google OAuth Desktop (arquivo privado 0600)",
            "",
            "JSON (*.json)",
        )
        if not path:
            return
        self.oauth_job = OAuthJob(self.store, self.selected_account(), path)
        self.oauth_job.connected.connect(self.oauth_finished)
        self.oauth_job.rejected.connect(self.oauth_failed)
        self.oauth.setEnabled(False)
        self.status.setText(
            "Conclua o consentimento no navegador. Apenas leitura do canal é solicitada."
        )
        self.oauth_job.start()

    def oauth_finished(self, _channels):
        self.oauth.setEnabled(True)
        self.refresh_verified()
        self.status.setText(
            "Google conectado. Escolha o canal correto e vincule o perfil."
        )

    def oauth_failed(self, message):
        self.oauth.setEnabled(True)
        self.status.setText(message)

    def refresh_verified(self):
        from tools.ytbot.oauth import verified_channels

        self.verified.clear()
        for channel in verified_channels(self.store, self.selected_account()):
            self.verified.addItem(
                channel["title"] + " · " + channel["id"], channel["id"]
            )

    def bind(self):
        if not self.channel.currentData():
            self.status.setText("Escolha o perfil do canal antes de vincular a conta.")
            return
        channel_id = self.verified.currentData()
        if not channel_id:
            if self.browser and self.browser.state() != QProcess.NotRunning:
                self.status.setText(
                    "Conclua e feche a janela de login antes de verificar o canal."
                )
                return
            if self.verification and self.verification.state() != QProcess.NotRunning:
                return
            self.verification = QProcess(self)
            self.verification.setWorkingDirectory(str(config.ROOT))
            self.verification.finished.connect(self.verification_finished)
            self.verification.start(
                sys.executable,
                [
                    "-m",
                    "tools.ytbot",
                    "accounts",
                    "bind",
                    "--channel",
                    self.channel.currentData(),
                    "--account",
                    self.selected_account(),
                    "--verify-browser",
                ],
            )
            self.status.setText(
                "Verificando a identidade do canal no navegador do bot, sem enviar vídeos..."
            )
            return
        try:
            self.store.bind(
                self.channel.currentData(), self.selected_account(), channel_id
            )
            self.refresh_library()
        except ValueError as error:
            QMessageBox.warning(self, "Canal", str(error))

    def verification_finished(self, code, _status):
        self.refresh_library()
        self.status.setText(
            "Conta vinculada após conferir o ID real do canal."
            if code == 0
            else "Não foi possível verificar o canal. Conecte a conta correta e tente novamente; o vínculo anterior foi preservado."
        )

    def refresh_library(self):
        slug = self.channel.currentData()
        if not slug:
            self.binding.setText("Escolha o perfil do canal para conferir a conta vinculada.")
            self.records = []
            self.render_library()
            return
        binding = self.store.load()["bindings"].get(slug, {"account_id": "legacy"})
        expected = channels.get(slug).channel_id
        self.binding.setText(
            f"Perfil: {slug}  ·  Conta vinculada: {binding['account_id']}  ·  ID obrigatório: {expected}"
        )
        self.records = library.runs(slug, 50)
        self.render_library()

    def render_library(self):
        query = self.search.text().strip().casefold()
        records = [
            item
            for item in self.records
            if not query
            or query
            in " ".join(
                str(item.get(key, "")) for key in ["title", "topic", "video_id"]
            ).casefold()
        ]
        self.table.setRowCount(len(records))
        for row, item in enumerate(records):
            for column, key in enumerate(["title", "state", "slot", "video_id"]):
                self.table.setItem(row, column, QTableWidgetItem(str(item[key])))

    def closeEvent(self, event):
        if (
            (self.oauth_job and self.oauth_job.isRunning())
            or (self.browser and self.browser.state() != QProcess.NotRunning)
            or (self.verification and self.verification.state() != QProcess.NotRunning)
            or (self.readiness and self.readiness.state() != QProcess.NotRunning)
        ):
            self.status.setText(
                "Conclua ou aguarde o encerramento da conexão Google antes de fechar."
            )
            event.ignore()
            return
        super().closeEvent(event)


def run_accounts():
    app = QApplication.instance() or QApplication(sys.argv)
    window = AccountsWindow()
    window.show()
    app.exec()
