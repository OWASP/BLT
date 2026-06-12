#include "MainWindow.h"

#include "ChatClient.h"
#include "ChatServer.h"
#include "MeshNode.h"
#include "Theme.h"

#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QHBoxLayout>
#include <QInputDialog>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMessageBox>
#include <QProcess>
#include <QPushButton>
#include <QRadioButton>
#include <QScrollBar>
#include <QSpinBox>
#include <QStackedWidget>
#include <QTextBrowser>
#include <QThread>
#include <QVBoxLayout>

#ifndef SAFECLOAK_VERSION
#define SAFECLOAK_VERSION "dev"
#endif
#ifndef SAFECLOAK_SOURCE_DIR
#define SAFECLOAK_SOURCE_DIR ""
#endif

namespace {

// The quick-update button only works when the binary was built from a local
// checkout that still exists on this machine.
bool updateSupported()
{
    return QDir(QStringLiteral(SAFECLOAK_SOURCE_DIR)).exists("CMakeLists.txt");
}

const QString kDmPrefix = QStringLiteral("@");

bool isDirectConversation(const QString &conversation)
{
    return conversation.startsWith(kDmPrefix);
}

QString dmKey(const QString &peerId)
{
    return kDmPrefix + peerId;
}

QString dmPeerId(const QString &conversation)
{
    return conversation.mid(1);
}

} // namespace

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
    auto *versionLabel = new QLabel("v" SAFECLOAK_VERSION);
    versionLabel->setObjectName("versionLabel");
    versionLabel->setAlignment(Qt::AlignHCenter);

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

    m_updateButton = new QPushButton("\xE2\x9F\xB3 Quick update");
    m_updateButton->setObjectName("ghostButton");
    m_updateButton->setCursor(Qt::PointingHandCursor);
    m_updateButton->setToolTip("Pull the latest version, rebuild, and relaunch");
    m_updateButton->setVisible(updateSupported());
    m_updateStatus = new QLabel;
    m_updateStatus->setObjectName("modeHint");
    m_updateStatus->setWordWrap(true);
    m_updateStatus->setAlignment(Qt::AlignHCenter);
    m_updateStatus->hide();

    auto *cardLayout = new QVBoxLayout(card);
    cardLayout->setContentsMargins(28, 28, 28, 28);
    cardLayout->setSpacing(10);
    cardLayout->addWidget(title);
    cardLayout->addWidget(subtitle);
    cardLayout->addWidget(versionLabel);
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
    cardLayout->addWidget(m_updateButton, 0, Qt::AlignHCenter);
    cardLayout->addWidget(m_updateStatus);

    auto *layout = new QVBoxLayout(page);
    layout->addStretch();
    layout->addWidget(card, 0, Qt::AlignHCenter);
    layout->addStretch();

    for (QRadioButton *radio : {m_hostRadio, m_joinRadio, m_meshRadio})
        connect(radio, &QRadioButton::toggled, this, &MainWindow::updateSetupFields);
    connect(startButton, &QPushButton::clicked, this, &MainWindow::startSession);
    connect(m_nameEdit, &QLineEdit::returnPressed, this, &MainWindow::startSession);
    connect(m_updateButton, &QPushButton::clicked, this, &MainWindow::runQuickUpdate);
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
    m_currentConversation.clear();
    m_conversationHtml.clear();
    m_dmNames.clear();
    m_openDms.clear();
    m_unread.clear();
    m_channelList->clear();
    m_dmList->clear();
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

// --------------------------------------------------------------- quick update

void MainWindow::setUpdateStatus(const QString &status, bool isError)
{
    m_updateStatus->setStyleSheet(isError ? "color:#ff6b6b; background:transparent;"
                                          : "color:#9ca3af; background:transparent;");
    m_updateStatus->setText(status);
    m_updateStatus->show();
}

void MainWindow::runUpdateStep(const QString &program, const QStringList &arguments,
                               const QString &workingDir,
                               std::function<void()> onSuccess)
{
    auto *process = new QProcess(this);
    process->setWorkingDirectory(workingDir);
    connect(process, &QProcess::finished, this,
            [this, process, onSuccess](int exitCode, QProcess::ExitStatus) {
                const QString errors =
                    QString::fromUtf8(process->readAllStandardError()).trimmed();
                process->deleteLater();
                if (exitCode != 0) {
                    setUpdateStatus("Update failed: " + errors.right(300), true);
                    m_updateButton->setEnabled(true);
                    return;
                }
                onSuccess();
            });
    connect(process, &QProcess::errorOccurred, this, [this, process] {
        setUpdateStatus("Update failed: could not run " + process->program(), true);
        process->deleteLater();
        m_updateButton->setEnabled(true);
    });
    process->start(program, arguments);
}

void MainWindow::runQuickUpdate()
{
    const QString sourceDir = QStringLiteral(SAFECLOAK_SOURCE_DIR);
    const QString buildDir = sourceDir + "/build";
    m_updateButton->setEnabled(false);

    setUpdateStatus("Pulling the latest version...");
    runUpdateStep("git", {"pull", "--ff-only"}, sourceDir, [this, sourceDir, buildDir] {
        setUpdateStatus("Configuring...");
        runUpdateStep("cmake",
                      {"-S", sourceDir, "-B", buildDir, "-DCMAKE_BUILD_TYPE=Release"},
                      sourceDir, [this, buildDir] {
            setUpdateStatus("Rebuilding...");
            runUpdateStep("cmake",
                          {"--build", buildDir, "-j",
                           QString::number(QThread::idealThreadCount())},
                          buildDir, [this] {
                setUpdateStatus("Relaunching...");
                QProcess::startDetached(QCoreApplication::applicationFilePath(), {});
                QCoreApplication::quit();
            });
        });
    });
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
    auto *addChannelButton = new QPushButton("+ Add channel");
    addChannelButton->setObjectName("ghostButton");
    addChannelButton->setCursor(Qt::PointingHandCursor);

    auto *dmsLabel = new QLabel("DIRECT MESSAGES");
    dmsLabel->setObjectName("sectionLabel");
    m_dmList = new QListWidget;

    auto *membersLabel = new QLabel("MEMBERS");
    membersLabel->setObjectName("sectionLabel");
    membersLabel->setToolTip("Click a member to start a direct chat");
    m_memberList = new QListWidget;
    m_memberList->setSelectionMode(QAbstractItemView::NoSelection);
    m_memberList->setFocusPolicy(Qt::NoFocus);
    m_memberList->setCursor(Qt::PointingHandCursor);
    m_memberList->setToolTip("Click a member to start a direct chat");

    auto *leaveButton = new QPushButton("\xE2\x86\x90 Leave session");
    leaveButton->setObjectName("ghostButton");
    leaveButton->setCursor(Qt::PointingHandCursor);
    auto *chatVersionLabel = new QLabel("v" SAFECLOAK_VERSION);
    chatVersionLabel->setObjectName("versionLabel");

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
    sidebarLayout->addWidget(dmsLabel);
    sidebarLayout->addWidget(m_dmList, 2);
    sidebarLayout->addWidget(membersLabel);
    sidebarLayout->addWidget(m_memberList, 2);
    auto *footerRow = new QHBoxLayout;
    footerRow->setContentsMargins(0, 0, 0, 0);
    footerRow->addWidget(leaveButton);
    footerRow->addStretch();
    footerRow->addWidget(chatVersionLabel);
    sidebarLayout->addLayout(footerRow);

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
                    switchConversation(item->data(Qt::UserRole).toString());
            });
    connect(m_dmList, &QListWidget::currentItemChanged, this,
            [this](QListWidgetItem *item, QListWidgetItem *) {
                if (item)
                    switchConversation(item->data(Qt::UserRole).toString());
            });
    connect(m_memberList, &QListWidget::itemClicked, this,
            [this](QListWidgetItem *item) {
                const QString id = item->data(Qt::UserRole).toString();
                const bool self = item->data(Qt::UserRole + 2).toBool();
                if (!id.isEmpty() && !self)
                    openDirectChat(id, item->data(Qt::UserRole + 1).toString());
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
    connect(backend, &ChatBackend::directMessage, this, &MainWindow::onDirectMessage);
    connect(backend, &ChatBackend::systemMessage, this, &MainWindow::appendSystem);
    connect(backend, &ChatBackend::channelsChanged, this, &MainWindow::setChannels);
    connect(backend, &ChatBackend::rosterChanged, this, &MainWindow::setRoster);
    connect(backend, &ChatBackend::statusChanged, m_statusLine, &QLabel::setText);
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

// One line per message, Slack-style with the username in front:
//   12:04  alice  the message text
QString MainWindow::messageHtml(const QString &sender, const QString &text,
                                qint64 timestampMs) const
{
    const QString time =
        QDateTime::fromMSecsSinceEpoch(timestampMs).toString("hh:mm");
    return "<div style='margin:5px 0'>"
           "<span style='color:#6b7280; font-size:11px'>" + time + "</span>"
           "&nbsp;&nbsp;"
           "<span style='color:" + senderColor(sender) + "; font-weight:700'>" +
           sender.toHtmlEscaped() + "</span>"
           "&nbsp;&nbsp;"
           "<span style='color:#f1f5f9'>" + text.toHtmlEscaped() + "</span></div>";
}

void MainWindow::appendChat(const QString &channel, const QString &sender,
                            const QString &text, qint64 timestampMs)
{
    appendHtml(channel, messageHtml(sender, text, timestampMs));
}

void MainWindow::onDirectMessage(const QString &peerId, const QString &peerName,
                                 const QString &sender, const QString &text,
                                 qint64 timestampMs)
{
    if (!m_dmNames.contains(peerId) || (!peerName.isEmpty() &&
                                        m_dmNames.value(peerId) != peerName)) {
        m_dmNames.insert(peerId, peerName.isEmpty() ? QStringLiteral("unknown")
                                                    : peerName);
    }
    if (!m_openDms.contains(peerId)) {
        m_openDms.append(peerId);
        refreshDmList();
    }
    appendHtml(dmKey(peerId), messageHtml(sender, text, timestampMs));
}

void MainWindow::appendSystem(const QString &text)
{
    const QString html =
        "<div style='margin:4px 0; color:#9ca3af'><i>· " + text.toHtmlEscaped() +
        "</i></div>";
    appendHtml(m_currentConversation.isEmpty() ? QStringLiteral("#general")
                                               : m_currentConversation,
               html);
}

void MainWindow::appendHtml(const QString &conversation, const QString &html)
{
    if (conversation.isEmpty())
        return;
    m_conversationHtml[conversation] += html;
    if (conversation == m_currentConversation) {
        m_messageView->insertHtml(html);
        m_messageView->verticalScrollBar()->setValue(
            m_messageView->verticalScrollBar()->maximum());
    } else if (m_channels.contains(conversation) ||
               (isDirectConversation(conversation) &&
                m_openDms.contains(dmPeerId(conversation)))) {
        m_unread.insert(conversation);
        refreshChannelList();
        refreshDmList();
    }
}

void MainWindow::setChannels(const QStringList &channels)
{
    m_channels = channels;
    if (m_currentConversation.startsWith('#') &&
        !m_channels.contains(m_currentConversation))
        m_currentConversation.clear();
    refreshChannelList();
    if (m_currentConversation.isEmpty() && !m_channels.isEmpty())
        m_channelList->setCurrentRow(0); // triggers switchConversation
}

void MainWindow::setRoster(const QList<MemberInfo> &members)
{
    m_memberList->clear();
    for (const MemberInfo &member : members) {
        QString label = "\xE2\x97\x8F " + member.name;
        if (!member.note.isEmpty())
            label += " " + member.note;
        if (member.self)
            label += " (you)";
        auto *item = new QListWidgetItem(label);
        item->setData(Qt::UserRole, member.id);
        item->setData(Qt::UserRole + 1, member.name);
        item->setData(Qt::UserRole + 2, member.self);
        m_memberList->addItem(item);
        // Keep DM tab titles in sync with renamed/rediscovered members.
        if (m_dmNames.contains(member.id) && m_dmNames.value(member.id) != member.name) {
            m_dmNames.insert(member.id, member.name);
            refreshDmList();
            if (m_currentConversation == dmKey(member.id))
                m_channelTitle->setText(kDmPrefix + member.name);
        }
    }
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
        if (channel == m_currentConversation)
            m_channelList->setCurrentItem(item);
    }
}

void MainWindow::refreshDmList()
{
    QSignalBlocker blocker(m_dmList);
    m_dmList->clear();
    for (const QString &peerId : std::as_const(m_openDms)) {
        const QString key = dmKey(peerId);
        auto *item = new QListWidgetItem(
            (m_unread.contains(key) ? "\xE2\x97\x8F " : "") + kDmPrefix +
            m_dmNames.value(peerId, QStringLiteral("unknown")));
        item->setData(Qt::UserRole, key);
        m_dmList->addItem(item);
        if (key == m_currentConversation)
            m_dmList->setCurrentItem(item);
    }
}

void MainWindow::switchConversation(const QString &conversation)
{
    if (conversation.isEmpty() || conversation == m_currentConversation)
        return;
    m_currentConversation = conversation;
    m_unread.remove(conversation);

    QString title = conversation;
    if (isDirectConversation(conversation))
        title = kDmPrefix + m_dmNames.value(dmPeerId(conversation),
                                            QStringLiteral("unknown"));
    m_channelTitle->setText(title);
    m_messageInput->setPlaceholderText("Message " + title);
    m_messageView->setHtml(m_conversationHtml.value(conversation));
    m_messageView->verticalScrollBar()->setValue(
        m_messageView->verticalScrollBar()->maximum());

    // Selection lives in exactly one sidebar list at a time.
    if (isDirectConversation(conversation)) {
        QSignalBlocker blocker(m_channelList);
        m_channelList->clearSelection();
        m_channelList->setCurrentItem(nullptr);
    } else {
        QSignalBlocker blocker(m_dmList);
        m_dmList->clearSelection();
        m_dmList->setCurrentItem(nullptr);
    }
    refreshChannelList();
    refreshDmList();
}

void MainWindow::openDirectChat(const QString &peerId, const QString &peerName)
{
    m_dmNames.insert(peerId, peerName);
    if (!m_openDms.contains(peerId)) {
        m_openDms.append(peerId);
        refreshDmList();
    }
    switchConversation(dmKey(peerId));
    m_messageInput->setFocus();
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
    if (text.isEmpty() || !m_backend || m_currentConversation.isEmpty())
        return;
    if (isDirectConversation(m_currentConversation))
        m_backend->sendDirect(dmPeerId(m_currentConversation), text);
    else
        m_backend->sendChat(m_currentConversation, text);
    m_messageInput->clear();
}
