#pragma once

#include "ChatBackend.h"
#include "SslIdentity.h"

#include <QHash>
#include <QMainWindow>
#include <QMap>
#include <QPixmap>
#include <QSet>

#include <functional>

class MessageRow;
class SettingsDialog;
class QLabel;
class QLineEdit;
class QListWidget;
class QPushButton;
class QRadioButton;
class QScrollArea;
class QStackedWidget;
class QSystemTrayIcon;
class QVBoxLayout;

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

    void onMessage(const ChatMessage &message);
    void onReaction(const QString &conversation, const QString &messageId,
                    const QString &emoji, const QString &reactorName, bool added);
    void onAvatar(const QString &peerId, const QByteArray &pngData);
    void onTypingChanged(const QString &conversation, const QString &peerId,
                         const QString &peerName, bool active);
    void logSystem(const QString &text);
    MessageRow *addMessageRow(const ChatMessage &message);
    void rebuildConversationView();
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
    void onComposerEdited(const QString &text);
    void sendTypingState(bool active);
    void refreshTypingLabel();
    void attachFile();
    void saveIncomingFile(const QString &fileName, const QByteArray &data);
    void openSettings();
    void onDisplayNameChanged(const QString &name);
    void onAvatarChosen(const QByteArray &pngData);
    void showFirewallBanner(const QString &displayCommand,
                            const QString &privilegedCommand);
    void allowFirewall();
    void notifyIfInactive(const QString &title, const QString &body);
    QString senderColor(const QString &sender) const;

    SslIdentity m_identity;
    ChatBackend *m_backend = nullptr;

    QStackedWidget *m_stack;
    QSystemTrayIcon *m_trayIcon;

    // Setup widgets
    QLineEdit *m_nameEdit;
    QRadioButton *m_meshModeRadio;
    QRadioButton *m_serverModeRadio;
    QLineEdit *m_serverUrlEdit;
    QLineEdit *m_roomNameEdit;
    QLineEdit *m_passphraseEdit;
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
    QScrollArea *m_messageScroll;
    QWidget *m_messageContainer;
    QVBoxLayout *m_messageLayout; // message rows + a trailing stretch
    QLabel *m_typingLabel;
    QLineEdit *m_messageInput;

    SettingsDialog *m_settingsDialog = nullptr;

    QStringList m_channels;
    QString m_currentConversation;
    // Per-conversation message log and the live rows for the open conversation.
    QHash<QString, QList<ChatMessage>> m_history;
    QHash<QString, MessageRow *> m_visibleRows; // messageId -> row (current conv)
    // messageId -> emoji -> reactor display names.
    QHash<QString, QMap<QString, QStringList>> m_reactions;
    QHash<QString, QPixmap> m_avatars;          // senderId -> avatar
    QHash<QString, QString> m_dmNames;          // peerId -> display name
    QHash<QString, QHash<QString, QString>> m_typing; // conversation -> peerId -> name
    QStringList m_openDms;                      // peerIds in sidebar order
    QSet<QString> m_unread;
    QString m_userName;
    QByteArray m_userAvatar;
    QString m_typingConversation;
    QTimer *m_typingStopTimer;
};
