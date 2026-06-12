#include "ChatServer.h"

#include "FramedConnection.h"

#include <QDateTime>
#include <QJsonArray>
#include <QUuid>

namespace {

QJsonArray toJsonArray(const QStringList &list)
{
    QJsonArray array;
    for (const QString &item : list)
        array.append(item);
    return array;
}

} // namespace

ChatServer::ChatServer(const SslIdentity &identity, const QString &userName,
                       QObject *parent)
    : ChatBackend(parent),
      m_identity(identity),
      m_userName(userName),
      m_nodeId(QUuid::createUuid().toString(QUuid::WithoutBraces))
{
    m_server.setSslConfiguration(m_identity.serverConfiguration());
    connect(&m_server, &QSslServer::pendingConnectionAvailable, this,
            &ChatServer::onPendingConnection);
}

bool ChatServer::start(quint16 port)
{
    if (!m_server.listen(QHostAddress::Any, port)) {
        emit fatalError("Could not listen on port " + QString::number(port) +
                        ": " + m_server.errorString());
        return false;
    }
    emit channelsChanged(m_channels);
    broadcastRoster();
    emit statusChanged("Hosting on port " + QString::number(m_server.serverPort()) +
                       " · TLS " + m_identity.fingerprint().left(23));
    emit systemMessage("Server started. Others can join with this machine's "
                       "address and port " + QString::number(m_server.serverPort()) + ".");
    return true;
}

void ChatServer::onPendingConnection()
{
    while (QTcpSocket *pending = m_server.nextPendingConnection()) {
        auto *ssl = qobject_cast<QSslSocket *>(pending);
        if (!ssl) {
            pending->deleteLater();
            continue;
        }
        auto *client = new FramedConnection(ssl, this);
        m_clients.append(client);
        connect(client, &FramedConnection::messageReceived, this,
                [this, client](const QJsonObject &m) { onClientMessage(client, m); });
        connect(client, &FramedConnection::closed, this,
                [this, client] { onClientClosed(client); });
    }
}

void ChatServer::onClientMessage(FramedConnection *client, const QJsonObject &message)
{
    const QString type = message.value("type").toString();

    if (type == "hello") {
        client->remoteId = message.value("nodeId").toString();
        client->remoteName = message.value("name").toString().trimmed();
        if (client->remoteName.isEmpty())
            client->remoteName = "anonymous";
        client->sendMessage({{"type", "channels"}, {"list", toJsonArray(m_channels)}});
        broadcastRoster();
        broadcastSystem(client->remoteName + " joined");
        return;
    }

    // Ignore everything else until the client has introduced itself.
    if (client->remoteName.isEmpty())
        return;

    if (type == "chat") {
        const QString text = message.value("text").toString();
        QString channel = message.value("channel").toString();
        if (text.trimmed().isEmpty() || !m_channels.contains(channel))
            return;
        const qint64 ts = QDateTime::currentMSecsSinceEpoch();
        broadcast({{"type", "chat"},
                   {"channel", channel},
                   {"sender", client->remoteName},
                   {"text", text},
                   {"ts", double(ts)}});
        emit chatMessage(channel, client->remoteName, text, ts);
    } else if (type == "join") {
        addChannel(message.value("channel").toString());
    }
}

void ChatServer::onClientClosed(FramedConnection *client)
{
    m_clients.removeAll(client);
    const QString name = client->remoteName;
    client->deleteLater();
    if (!name.isEmpty()) {
        broadcastRoster();
        broadcastSystem(name + " left");
    }
}

void ChatServer::sendChat(const QString &channel, const QString &text)
{
    if (text.trimmed().isEmpty() || !m_channels.contains(channel))
        return;
    const qint64 ts = QDateTime::currentMSecsSinceEpoch();
    broadcast({{"type", "chat"},
               {"channel", channel},
               {"sender", m_userName},
               {"text", text},
               {"ts", double(ts)}});
    emit chatMessage(channel, m_userName, text, ts);
}

void ChatServer::addChannel(const QString &channel)
{
    QString name = channel.trimmed();
    if (name.isEmpty())
        return;
    if (!name.startsWith('#'))
        name.prepend('#');
    if (m_channels.contains(name))
        return;
    m_channels.append(name);
    broadcastChannels();
    broadcastSystem("channel " + name + " created");
}

void ChatServer::shutdown()
{
    m_server.close();
    const auto clients = m_clients;
    m_clients.clear();
    for (FramedConnection *client : clients) {
        client->close();
        client->deleteLater();
    }
}

void ChatServer::broadcast(const QJsonObject &message)
{
    for (FramedConnection *client : std::as_const(m_clients)) {
        if (!client->remoteName.isEmpty())
            client->sendMessage(message);
    }
}

void ChatServer::broadcastRoster()
{
    QStringList members{m_userName + " (host)"};
    for (FramedConnection *client : std::as_const(m_clients)) {
        if (!client->remoteName.isEmpty())
            members.append(client->remoteName);
    }
    broadcast({{"type", "roster"}, {"members", toJsonArray(members)}});
    emit rosterChanged(members);
}

void ChatServer::broadcastChannels()
{
    broadcast({{"type", "channels"}, {"list", toJsonArray(m_channels)}});
    emit channelsChanged(m_channels);
}

void ChatServer::broadcastSystem(const QString &text)
{
    broadcast({{"type", "system"}, {"text", text}});
    emit systemMessage(text);
}
