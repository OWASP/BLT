#include "ChatClient.h"

#include "FramedConnection.h"
#include "SslIdentity.h"

#include <QJsonArray>
#include <QUuid>

ChatClient::ChatClient(const QString &userName, QObject *parent)
    : ChatBackend(parent),
      m_userName(userName),
      m_nodeId(QUuid::createUuid().toString(QUuid::WithoutBraces))
{
}

void ChatClient::connectToServer(const QString &host, quint16 port)
{
    auto *socket = new QSslSocket;
    socket->setSslConfiguration(SslIdentity::clientConfiguration());
    m_connection = new FramedConnection(socket, this);

    connect(socket, &QSslSocket::encrypted, this, [this, host, port] {
        m_connected = true;
        m_connection->sendMessage(
            {{"type", "hello"}, {"nodeId", m_nodeId}, {"name", m_userName}});
        emit statusChanged("Connected to " + host + ":" + QString::number(port) +
                           " · TLS");
    });
    connect(m_connection, &FramedConnection::messageReceived, this,
            &ChatClient::onServerMessage);
    connect(m_connection, &FramedConnection::closed, this, [this, socket] {
        const QString detail = socket->errorString();
        emit fatalError(m_connected
                            ? "Connection to the server was lost. " + detail
                            : "Could not connect to the server. " + detail);
    });

    emit statusChanged("Connecting to " + host + "...");
    socket->connectToHostEncrypted(host, port);
}

void ChatClient::onServerMessage(const QJsonObject &message)
{
    const QString type = message.value("type").toString();
    if (type == "chat") {
        emit chatMessage(message.value("channel").toString(),
                         message.value("sender").toString(),
                         message.value("text").toString(),
                         qint64(message.value("ts").toDouble()));
    } else if (type == "channels") {
        QStringList channels;
        for (const auto &value : message.value("list").toArray())
            channels.append(value.toString());
        emit channelsChanged(channels);
    } else if (type == "roster") {
        QStringList members;
        for (const auto &value : message.value("members").toArray())
            members.append(value.toString());
        emit rosterChanged(members);
    } else if (type == "system") {
        emit systemMessage(message.value("text").toString());
    }
}

void ChatClient::sendChat(const QString &channel, const QString &text)
{
    if (m_connection && !text.trimmed().isEmpty())
        m_connection->sendMessage(
            {{"type", "chat"}, {"channel", channel}, {"text", text}});
}

void ChatClient::addChannel(const QString &channel)
{
    if (m_connection && !channel.trimmed().isEmpty())
        m_connection->sendMessage({{"type", "join"}, {"channel", channel}});
}

void ChatClient::shutdown()
{
    if (m_connection) {
        m_connection->disconnect(this);
        m_connection->close();
        m_connection->deleteLater();
        m_connection = nullptr;
    }
}
