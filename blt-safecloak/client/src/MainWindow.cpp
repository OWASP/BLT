#include "MainWindow.h"

#include "ChatClient.h"
#include "ChatServer.h"
#include "MeshNode.h"
#include "Theme.h"

#include <QDateTime>
#include <QHBoxLayout>
#include <QInputDialog>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMessageBox>
#include <QPushButton>
#include <QRadioButton>
#include <QScrollBar>
#include <QSpinBox>
#include <QStackedWidget>
#include <QTextBrowser>
#include <QVBoxLayout>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent)
{
    setWindowTitle("SafeCloak Chat");
    resize(1060, 700);

    m_stack = new QStackedWidget(this);
    m_stack->addWidget(buildSetupPage());
    m_stack->addWidget(buildChatPage());
    setCentralWidget(m_stack);

    if (!m_identity.load()) {
        m_setupError->setText(m_identity.errorString());
        m_setupError->show();
    }
}

// ---------------------------------------------------------------- setup page

QWidget *MainWindow::buildSetupPage()
{
    auto *page = new QWidget;

    auto *card = new QWidget;
    card->setObjectName("setupCard");
    card->setFixedWidth(420);

    auto *title = new QLabel("<span style='color:#ff4444'>SafeCloak</span> Chat");
    title->setObjectName("appTitle");
    title->setAlignment(Qt::AlignHCenter);
    auto *subtitle = new QLabel("Encrypted chat for your local network");
    subtitle->setObjectName("appSubtitle");
    subtitle->setAlignment(Qt::AlignHCenter);

    m_nameEdit = new QLineEdit;
    m_nameEdit->setPlaceholderText("Display name");
    m_nameEdit->setMaxLength(32);

    m_hostRadio = new QRadioButton("Host a server");
    auto *hostHint = new QLabel("Run the room on this machine; others join you.");
    hostHint->setObjectName("modeHint");
    m_joinRadio = new QRadioButton("Join a server");
    auto *joinHint = new QLabel("Connect to someone hosting on the network.");
    joinHint->setObjectName("modeHint");
    m_meshRadio = new QRadioButton("Mesh mode");
    auto *meshHint = new QLabel("No server — discover peers automatically via broadcast.");
    meshHint->setObjectName("modeHint");
    m_hostRadio->setChecked(true);

    m_hostEdit = new QLineEdit;
    m_hostEdit->setPlaceholderText("Server address (e.g. 192.168.1.20)");
    m_portSpin = new QSpinBox;
    m_portSpin->setRange(1024, 65535);
    m_portSpin->setValue(47800);
    m_portSpin->setPrefix("Port  ");

    m_setupError = new QLabel;
    m_setupError->setWordWrap(true);
    m_setupError->setStyleSheet("color:#ff6b6b; background:transparent;");
    m_setupError->hide();

    auto *startButton = new QPushButton("Start chatting");
    startButton->setObjectName("primaryButton");
    startButton->setMinimumHeight(40);

    auto *cardLayout = new QVBoxLayout(card);
    cardLayout->setContentsMargins(28, 28, 28, 28);
    cardLayout->setSpacing(10);
    cardLayout->addWidget(title);
    cardLayout->addWidget(subtitle);
    cardLayout->addSpacing(14);
    cardLayout->addWidget(m_nameEdit);
    cardLayout->addSpacing(8);
    cardLayout->addWidget(m_hostRadio);
    cardLayout->addWidget(hostHint);
    cardLayout->addWidget(m_joinRadio);
    cardLayout->addWidget(joinHint);
    cardLayout->addWidget(m_meshRadio);
    cardLayout->addWidget(meshHint);
    cardLayout->addSpacing(8);
    cardLayout->addWidget(m_hostEdit);
    cardLayout->addWidget(m_portSpin);
    cardLayout->addWidget(m_setupError);
    cardLayout->addSpacing(10);
    cardLayout->addWidget(startButton);

    auto *layout = new QVBoxLayout(page);
    layout->addStretch();
    layout->addWidget(card, 0, Qt::AlignHCenter);
    layout->addStretch();

    for (QRadioButton *radio : {m_hostRadio, m_joinRadio, m_meshRadio})
        connect(radio, &QRadioButton::toggled, this, &MainWindow::updateSetupFields);
    connect(startButton, &QPushButton::clicked, this, &MainWindow::startSession);
    connect(m_nameEdit, &QLineEdit::returnPressed, this, &MainWindow::startSession);
    updateSetupFields();

    return page;
}

void MainWindow::updateSetupFields()
{
    m_hostEdit->setVisible(m_joinRadio->isChecked());
    m_portSpin->setVisible(!m_meshRadio->isChecked());
}

void MainWindow::startSession()
{
    const QString name = m_nameEdit->text().trimmed();
    if (name.isEmpty()) {
        m_setupError->setText("Please enter a display name.");
        m_setupError->show();
        return;
    }
    if (!m_identity.isValid() && !m_identity.load()) {
        m_setupError->setText(m_identity.errorString());
        m_setupError->show();
        return;
    }
    m_setupError->hide();

    // Reset chat state.
    m_channels.clear();
    m_currentChannel.clear();
    m_channelHtml.clear();
    m_unread.clear();
    m_channelList->clear();
    m_memberList->clear();
    m_messageView->clear();

    if (m_hostRadio->isChecked()) {
        auto *server = new ChatServer(m_identity, name, this);
        attachBackend(server);
        if (!server->start(quint16(m_portSpin->value())))
            return; // fatalError already routed to the setup page
    } else if (m_joinRadio->isChecked()) {
        const QString host = m_hostEdit->text().trimmed();
        if (host.isEmpty()) {
            m_setupError->setText("Please enter the server address.");
            m_setupError->show();
            return;
        }
        auto *client = new ChatClient(name, this);
        attachBackend(client);
        client->connectToServer(host, quint16(m_portSpin->value()));
    } else {
        auto *mesh = new MeshNode(m_identity, name, this);
        attachBackend(mesh);
        if (!mesh->start())
            return;
    }

    if (m_backend) {
        m_modeBadge->setText(m_backend->modeName().toUpper());
        m_encryptionLabel->setText(
            "\xF0\x9F\x94\x92 TLS encrypted · fingerprint " +
            m_identity.fingerprint().left(23) + "…");
        m_stack->setCurrentIndex(1);
        m_messageInput->setFocus();
    }
}

// ----------------------------------------------------------------- chat page

QWidget *MainWindow::buildChatPage()
{
    auto *page = new QWidget;

    // Sidebar
    auto *sidebar = new QWidget;
    sidebar->setObjectName("sidebar");
    sidebar->setFixedWidth(230);

    auto *workspace = new QLabel("<span style='color:#ff4444'>Safe</span>Cloak Chat");
    workspace->setObjectName("workspaceName");
    m_modeBadge = new QLabel("—");
    m_modeBadge->setObjectName("modeBadge");
    m_statusLine = new QLabel;
    m_statusLine->setObjectName("statusLine");
    m_statusLine->setWordWrap(true);

    auto *channelsLabel = new QLabel("CHANNELS");
    channelsLabel->setObjectName("sectionLabel");
    m_channelList = new QListWidget;
    m_channelList->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    auto *addChannelButton = new QPushButton("+ Add channel");
    addChannelButton->setObjectName("ghostButton");
    addChannelButton->setCursor(Qt::PointingHandCursor);

    auto *membersLabel = new QLabel("MEMBERS");
    membersLabel->setObjectName("sectionLabel");
    m_memberList = new QListWidget;
    m_memberList->setSelectionMode(QAbstractItemView::NoSelection);
    m_memberList->setFocusPolicy(Qt::NoFocus);

    auto *leaveButton = new QPushButton("\xE2\x86\x90 Leave session");
    leaveButton->setObjectName("ghostButton");
    leaveButton->setCursor(Qt::PointingHandCursor);

    auto *badgeRow = new QHBoxLayout;
    badgeRow->setContentsMargins(0, 0, 0, 0);
    badgeRow->addWidget(workspace);
    badgeRow->addStretch();
    badgeRow->addWidget(m_modeBadge);

    auto *sidebarLayout = new QVBoxLayout(sidebar);
    sidebarLayout->setContentsMargins(14, 16, 14, 12);
    sidebarLayout->setSpacing(6);
    sidebarLayout->addLayout(badgeRow);
    sidebarLayout->addWidget(m_statusLine);
    sidebarLayout->addWidget(channelsLabel);
    sidebarLayout->addWidget(m_channelList, 3);
    sidebarLayout->addWidget(addChannelButton);
    sidebarLayout->addWidget(membersLabel);
    sidebarLayout->addWidget(m_memberList, 2);
    sidebarLayout->addWidget(leaveButton);

    // Main column
    auto *header = new QWidget;
    header->setObjectName("chatHeader");
    m_channelTitle = new QLabel("#general");
    m_channelTitle->setObjectName("channelTitle");
    m_encryptionLabel = new QLabel;
    m_encryptionLabel->setObjectName("encryptionLabel");
    auto *headerLayout = new QHBoxLayout(header);
    headerLayout->setContentsMargins(18, 12, 18, 12);
    headerLayout->addWidget(m_channelTitle);
    headerLayout->addStretch();
    headerLayout->addWidget(m_encryptionLabel);

    m_messageView = new QTextBrowser;
    m_messageView->setObjectName("messageView");
    m_messageView->setOpenExternalLinks(true);

    auto *composer = new QWidget;
    composer->setObjectName("composerBar");
    m_messageInput = new QLineEdit;
    m_messageInput->setObjectName("messageInput");
    m_messageInput->setPlaceholderText("Message #general");
    auto *sendButton = new QPushButton("Send");
    sendButton->setObjectName("primaryButton");
    auto *composerLayout = new QHBoxLayout(composer);
    composerLayout->setContentsMargins(14, 10, 14, 12);
    composerLayout->setSpacing(8);
    composerLayout->addWidget(m_messageInput);
    composerLayout->addWidget(sendButton);

    auto *mainColumn = new QVBoxLayout;
    mainColumn->setContentsMargins(0, 0, 0, 0);
    mainColumn->setSpacing(0);
    mainColumn->addWidget(header);
    mainColumn->addWidget(m_messageView, 1);
    mainColumn->addWidget(composer);

    auto *layout = new QHBoxLayout(page);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    layout->addWidget(sidebar);
    layout->addLayout(mainColumn, 1);

    connect(m_channelList, &QListWidget::currentItemChanged, this,
            [this](QListWidgetItem *item, QListWidgetItem *) {
                if (item)
                    switchChannel(item->data(Qt::UserRole).toString());
            });
    connect(addChannelButton, &QPushButton::clicked, this, &MainWindow::promptAddChannel);
    connect(m_messageInput, &QLineEdit::returnPressed, this, &MainWindow::sendCurrentMessage);
    connect(sendButton, &QPushButton::clicked, this, &MainWindow::sendCurrentMessage);
    connect(leaveButton, &QPushButton::clicked, this, [this] { leaveSession(); });

    return page;
}

void MainWindow::attachBackend(ChatBackend *backend)
{
    if (m_backend)
        leaveSession();
    m_backend = backend;

    connect(backend, &ChatBackend::chatMessage, this, &MainWindow::appendChat);
    connect(backend, &ChatBackend::systemMessage, this, &MainWindow::appendSystem);
    connect(backend, &ChatBackend::channelsChanged, this, &MainWindow::setChannels);
    connect(backend, &ChatBackend::statusChanged, m_statusLine, &QLabel::setText);
    connect(backend, &ChatBackend::rosterChanged, this, [this](const QStringList &members) {
        m_memberList->clear();
        for (const QString &member : members)
            m_memberList->addItem("\xE2\x97\x8F " + member);
    });
    connect(backend, &ChatBackend::fatalError, this, [this](const QString &message) {
        leaveSession();
        m_setupError->setText(message);
        m_setupError->show();
    });
}

void MainWindow::leaveSession(const QString &)
{
    if (m_backend) {
        m_backend->disconnect(this);
        m_backend->disconnect(m_statusLine);
        m_backend->shutdown();
        m_backend->deleteLater();
        m_backend = nullptr;
    }
    m_stack->setCurrentIndex(0);
}

// ------------------------------------------------------------------ messages

QString MainWindow::senderColor(const QString &sender) const
{
    const uint hash = qHash(sender);
    return Theme::kSenderPalette[hash % Theme::kSenderPaletteSize];
}

void MainWindow::appendChat(const QString &channel, const QString &sender,
                            const QString &text, qint64 timestampMs)
{
    const QString time =
        QDateTime::fromMSecsSinceEpoch(timestampMs).toString("hh:mm");
    const QString html =
        "<div style='margin:6px 0'>"
        "<span style='color:" + senderColor(sender) + "; font-weight:700'>" +
        sender.toHtmlEscaped() + "</span> "
        "<span style='color:#9ca3af; font-size:11px'>" + time + "</span><br>"
        "<span style='color:#f1f5f9'>" + text.toHtmlEscaped() + "</span></div>";
    appendHtml(channel, html);
}

void MainWindow::appendSystem(const QString &text)
{
    const QString html =
        "<div style='margin:4px 0; color:#9ca3af'><i>· " + text.toHtmlEscaped() +
        "</i></div>";
    appendHtml(m_currentChannel.isEmpty() ? QStringLiteral("#general") : m_currentChannel,
               html);
}

void MainWindow::appendHtml(const QString &channel, const QString &html)
{
    if (channel.isEmpty())
        return;
    m_channelHtml[channel] += html;
    if (channel == m_currentChannel) {
        m_messageView->insertHtml(html);
        m_messageView->verticalScrollBar()->setValue(
            m_messageView->verticalScrollBar()->maximum());
    } else if (m_channels.contains(channel)) {
        m_unread.insert(channel);
        refreshChannelList();
    }
}

void MainWindow::setChannels(const QStringList &channels)
{
    m_channels = channels;
    if (!m_channels.contains(m_currentChannel))
        m_currentChannel.clear();
    refreshChannelList();
    if (m_currentChannel.isEmpty() && !m_channels.isEmpty())
        m_channelList->setCurrentRow(0); // triggers switchChannel
}

void MainWindow::refreshChannelList()
{
    QSignalBlocker blocker(m_channelList);
    m_channelList->clear();
    for (const QString &channel : std::as_const(m_channels)) {
        auto *item = new QListWidgetItem(
            (m_unread.contains(channel) ? "\xE2\x97\x8F " : "") + channel);
        item->setData(Qt::UserRole, channel);
        m_channelList->addItem(item);
        if (channel == m_currentChannel)
            m_channelList->setCurrentItem(item);
    }
}

void MainWindow::switchChannel(const QString &channel)
{
    if (channel.isEmpty() || channel == m_currentChannel)
        return;
    m_currentChannel = channel;
    m_unread.remove(channel);
    m_channelTitle->setText(channel);
    m_messageInput->setPlaceholderText("Message " + channel);
    m_messageView->setHtml(m_channelHtml.value(channel));
    m_messageView->verticalScrollBar()->setValue(
        m_messageView->verticalScrollBar()->maximum());
    refreshChannelList();
}

void MainWindow::promptAddChannel()
{
    if (!m_backend)
        return;
    bool ok = false;
    const QString name = QInputDialog::getText(
        this, "Add channel", "Channel name:", QLineEdit::Normal, "#", &ok);
    if (ok && !name.trimmed().isEmpty() && name.trimmed() != "#")
        m_backend->addChannel(name);
}

void MainWindow::sendCurrentMessage()
{
    const QString text = m_messageInput->text().trimmed();
    if (text.isEmpty() || !m_backend || m_currentChannel.isEmpty())
        return;
    m_backend->sendChat(m_currentChannel, text);
    m_messageInput->clear();
}
