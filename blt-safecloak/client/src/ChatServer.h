#pragma once

#include "ChatBackend.h"
#include "SslIdentity.h"

#include <QHash>
#include <QJsonObject>
#include <QSslServer>

class FramedConnection;

// Server mode: this node hosts the room over TLS. Clients connect, the
// server relays every message to all participants and owns the channel list
// and roster. The hosting user participates like any other member.
class ChatServer : public ChatBackend
{
    Q_OBJECT
public:
    ChatServer(const SslIdentity &identity, const QString &userName,
               QObject *parent = nullptr);

    bool start(quint16 port);

    void sendChat(const QString &channel, const QString &text) override;
    void sendDirect(const QString &targetId, const QString &text) override;
    void addChannel(const QString &channel) override;
    void shutdown() override;
    QString modeName() const override { return "Server"; }

private:
    void onPendingConnection();
    void onClientMessage(FramedConnection *client, const QJsonObject &message);
    void onClientClosed(FramedConnection *client);
    void broadcast(const QJsonObject &message);
    void broadcastRoster();
    void broadcastChannels();
    void broadcastSystem(const QString &text);

    SslIdentity m_identity;
    QString m_userName;
    QString m_nodeId;
    QSslServer m_server;
    QList<FramedConnection *> m_clients; // includes not-yet-named connections
    QStringList m_channels{"#general", "#random"};
};
