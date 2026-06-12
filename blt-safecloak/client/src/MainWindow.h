#pragma once

#include "ChatBackend.h"
#include "SslIdentity.h"

#include <QHash>
#include <QMainWindow>
#include <QSet>

#include <functional>

class QLabel;
class QLineEdit;
class QListWidget;
class QPushButton;
class QStackedWidget;
class QSystemTrayIcon;
class QTextBrowser;

class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);

private:
    // Setup page
    QWidget *buildSetupPage();
    void startSession();
    void runQuickUpdate();
    void buildAndRelaunch(const QString &clientDir);
    void runUpdateStep(const QString &program, const QStringList &arguments,
                       const QString &workingDir, std::function<void()> onSuccess);
    void setUpdateStatus(const QString &status, bool isError = false);

    // Chat page
    QWidget *buildChatPage();
    void attachBackend(ChatBackend *backend);
    void leaveSession(const QString &reason = QString());

    void appendChat(const QString &channel, const QString &sender,
                    const QString &text, qint64 timestampMs);
    void onDirectMessage(const QString &peerId, const QString &peerName,
                         const QString &sender, const QString &text,
                         qint64 timestampMs);
    void appendSystem(const QString &text);
    void appendHtml(const QString &conversation, const QString &html);
    void setChannels(const QStringList &channels);
    void setRoster(const QList<MemberInfo> &members);
    // A conversation key is either a channel ("#general") or a direct chat
    // ("@<peerId>").
    void switchConversation(const QString &conversation);
    void openDirectChat(const QString &peerId, const QString &peerName);
    void refreshChannelList();
    void refreshDmList();
    void promptAddChannel();
    void sendCurrentMessage();
    void showFirewallBanner(const QString &displayCommand,
                            const QString &privilegedCommand);
    void allowFirewall();
    void notifyIfInactive(const QString &title, const QString &body);
    QString senderColor(const QString &sender) const;
    QString messageHtml(const QString &sender, const QString &text,
                        qint64 timestampMs) const;

    SslIdentity m_identity;
    ChatBackend *m_backend = nullptr;

    QStackedWidget *m_stack;
    QSystemTrayIcon *m_trayIcon;

    // Setup widgets
    QLineEdit *m_nameEdit;
    QLabel *m_setupError;
    QPushButton *m_updateButton;
    QLabel *m_updateStatus;

    // Chat widgets
    QLabel *m_statusLine;
    QLabel *m_channelTitle;
    QLabel *m_encryptionLabel;
    QListWidget *m_channelList;
    QListWidget *m_dmList;
    QListWidget *m_memberList;
    QWidget *m_firewallBanner;
    QLabel *m_firewallBannerLabel;
    QPushButton *m_firewallAllowButton;
    QString m_firewallPrivilegedCommand;
    QTextBrowser *m_messageView;
    QLineEdit *m_messageInput;

    QStringList m_channels;
    QString m_currentConversation;
    QHash<QString, QString> m_conversationHtml; // conversation -> message html
    QHash<QString, QString> m_dmNames;          // peerId -> display name
    QStringList m_openDms;                      // peerIds in sidebar order
    QSet<QString> m_unread;
    QString m_userName;
};
