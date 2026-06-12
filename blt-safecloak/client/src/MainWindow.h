#pragma once

#include "SslIdentity.h"

#include <QHash>
#include <QMainWindow>
#include <QSet>

class ChatBackend;
class QLabel;
class QLineEdit;
class QListWidget;
class QPushButton;
class QRadioButton;
class QSpinBox;
class QStackedWidget;
class QTextBrowser;

class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);

private:
    // Setup page
    QWidget *buildSetupPage();
    void updateSetupFields();
    void startSession();

    // Chat page
    QWidget *buildChatPage();
    void attachBackend(ChatBackend *backend);
    void leaveSession(const QString &reason = QString());

    void appendChat(const QString &channel, const QString &sender,
                    const QString &text, qint64 timestampMs);
    void appendSystem(const QString &text);
    void appendHtml(const QString &channel, const QString &html);
    void setChannels(const QStringList &channels);
    void switchChannel(const QString &channel);
    void refreshChannelList();
    void promptAddChannel();
    void sendCurrentMessage();
    QString senderColor(const QString &sender) const;

    SslIdentity m_identity;
    ChatBackend *m_backend = nullptr;

    QStackedWidget *m_stack;

    // Setup widgets
    QLineEdit *m_nameEdit;
    QRadioButton *m_hostRadio;
    QRadioButton *m_joinRadio;
    QRadioButton *m_meshRadio;
    QLineEdit *m_hostEdit;
    QSpinBox *m_portSpin;
    QLabel *m_setupError;

    // Chat widgets
    QLabel *m_modeBadge;
    QLabel *m_statusLine;
    QLabel *m_channelTitle;
    QLabel *m_encryptionLabel;
    QListWidget *m_channelList;
    QListWidget *m_memberList;
    QTextBrowser *m_messageView;
    QLineEdit *m_messageInput;

    QStringList m_channels;
    QString m_currentChannel;
    QHash<QString, QString> m_channelHtml; // channel -> accumulated message html
    QSet<QString> m_unread;
};
