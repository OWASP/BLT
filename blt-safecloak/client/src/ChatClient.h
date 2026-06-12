#pragma once

#include "ChatBackend.h"

#include <QJsonObject>

class FramedConnection;

// Client mode: connects to a node running in server mode over TLS. The
// server echoes our own messages back, so everything we display comes from
// the server and ordering is consistent for all members.
class ChatClient : public ChatBackend
{
    Q_OBJECT
public:
    ChatClient(const QString &userName, QObject *parent = nullptr);

    void connectToServer(const QString &host, quint16 port);

    void sendChat(const QString &channel, const QString &text) override;
    void sendDirect(const QString &targetId, const QString &text) override;
    void addChannel(const QString &channel) override;
    void shutdown() override;
    QString modeName() const override { return "Client"; }

private:
    void onServerMessage(const QJsonObject &message);

    QString m_userName;
    QString m_nodeId;
    FramedConnection *m_connection = nullptr;
    bool m_connected = false;
};
