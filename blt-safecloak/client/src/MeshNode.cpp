#include "MeshNode.h"

#include "FramedConnection.h"

#include <QDateTime>
#include <QJsonArray>
#include <QJsonDocument>
#include <QNetworkDatagram>
#include <QUuid>

namespace {

constexpr int kAnnounceIntervalMs = 2000;
constexpr int kNodeTimeoutMs = 8000;
constexpr int kSeenCacheLimit = 4096;
const QString kAppTag = QStringLiteral("safecloak-chat");
// Discovery goes out via multicast (looped back locally, so instances on the
// same machine find each other) and via broadcast as a fallback for networks
// that filter multicast. Duplicate announcements are harmless.
const QHostAddress kMulticastGroup(QStringLiteral("239.255.43.21"));

} // namespace

MeshNode::MeshNode(const SslIdentity &identity, const QString &userName,
                   QObject *parent)
    : ChatBackend(parent),
      m_identity(identity),
      m_userName(userName),
      m_nodeId(QUuid::createUuid().toString(QUuid::WithoutBraces))
{
    m_listener.setSslConfiguration(m_identity.serverConfiguration());
    connect(&m_listener, &QSslServer::pendingConnectionAvailable, this,
            &MeshNode::onIncomingConnection);
    connect(&m_udp, &QUdpSocket::readyRead, this, &MeshNode::onDatagram);
    connect(&m_announceTimer, &QTimer::timeout, this, &MeshNode::sendAnnounce);
    connect(&m_pruneTimer, &QTimer::timeout, this, &MeshNode::prune);
}

bool MeshNode::start()
{
    if (!m_listener.listen(QHostAddress::Any, 0)) {
        emit fatalError("Could not open a TLS listener: " + m_listener.errorString());
        return false;
    }
    bool bound = false;
    for (quint16 port = kDiscoveryPortBase;
         port < kDiscoveryPortBase + kDiscoveryPortRange && !bound; ++port) {
        bound = m_udp.bind(QHostAddress::AnyIPv4, port);
    }
    if (!bound) {
        emit fatalError("Could not bind a UDP discovery port (" +
                        QString::number(kDiscoveryPortBase) + "-" +
                        QString::number(kDiscoveryPortBase + kDiscoveryPortRange - 1) +
                        " all in use): " + m_udp.errorString());
        return false;
    }
    m_udp.joinMulticastGroup(kMulticastGroup);
    m_udp.setSocketOption(QAbstractSocket::MulticastLoopbackOption, 1);

    emit channelsChanged(m_channels);
    updateRosterAndStatus();
    emit systemMessage("Mesh mode active. Looking for peers on the local network...");

    sendAnnounce();
    m_announceTimer.start(kAnnounceIntervalMs);
    m_pruneTimer.start(kNodeTimeoutMs / 2);
    return true;
}

QByteArray MeshNode::announcePayload() const
{
    const QJsonObject announce{{"app", kAppTag},
                               {"v", 1},
                               {"nodeId", m_nodeId},
                               {"name", m_userName},
                               {"port", m_listener.serverPort()}};
    return QJsonDocument(announce).toJson(QJsonDocument::Compact);
}

void MeshNode::sendAnnounce()
{
    const QByteArray payload = announcePayload();
    for (quint16 port = kDiscoveryPortBase;
         port < kDiscoveryPortBase + kDiscoveryPortRange; ++port) {
        m_udp.writeDatagram(payload, kMulticastGroup, port);
        m_udp.writeDatagram(payload, QHostAddress::Broadcast, port);
        // Loopback unicast reaches other instances on this machine even where
        // the OS does not loop multicast/broadcast back to local sockets.
        if (port != m_udp.localPort())
            m_udp.writeDatagram(payload, QHostAddress::LocalHost, port);
    }
}

void MeshNode::onDatagram()
{
    while (m_udp.hasPendingDatagrams()) {
        const QNetworkDatagram datagram = m_udp.receiveDatagram();
        const QJsonDocument doc = QJsonDocument::fromJson(datagram.data());
        if (!doc.isObject())
            continue;
        const QJsonObject announce = doc.object();
        if (announce.value("app").toString() != kAppTag)
            continue;

        const QString nodeId = announce.value("nodeId").toString();
        if (nodeId.isEmpty() || nodeId == m_nodeId)
            continue;

        KnownNode &node = m_known[nodeId];
        const bool isNew = node.lastSeenMs == 0;
        node.name = announce.value("name").toString();
        node.address = datagram.senderAddress();
        node.tcpPort = quint16(announce.value("port").toInt());
        node.lastSeenMs = QDateTime::currentMSecsSinceEpoch();

        // Exactly one side dials so each pair gets a single link; the node
        // with the lexicographically smaller id initiates.
        if (!m_peers.contains(nodeId) && !m_pendingDials.contains(nodeId) &&
            m_nodeId < nodeId) {
            connectToPeer(nodeId, node);
        }
        if (isNew) {
            // Introduce ourselves directly so the other side learns about us
            // even if our multicast/broadcast does not reach it.
            m_udp.writeDatagram(announcePayload(), datagram.senderAddress(),
                                datagram.senderPort());
            updateRosterAndStatus();
        }
    }
}

void MeshNode::connectToPeer(const QString &nodeId, const KnownNode &node)
{
    m_pendingDials.insert(nodeId);

    auto *socket = new QSslSocket;
    socket->setSslConfiguration(SslIdentity::clientConfiguration());
    auto *connection = new FramedConnection(socket, this);
    connection->remoteId = nodeId;
    connection->remoteName = node.name;

    connect(socket, &QSslSocket::encrypted, this, [this, connection] {
        adoptConnection(connection);
    });
    connect(connection, &FramedConnection::messageReceived, this,
            [this, connection](const QJsonObject &m) { onPeerMessage(connection, m); });
    connect(connection, &FramedConnection::closed, this, [this, connection] {
        onPeerClosed(connection);
    });

    socket->connectToHostEncrypted(node.address.toString(), node.tcpPort);
}

void MeshNode::onIncomingConnection()
{
    while (QTcpSocket *pending = m_listener.nextPendingConnection()) {
        auto *ssl = qobject_cast<QSslSocket *>(pending);
        if (!ssl) {
            pending->deleteLater();
            continue;
        }
        auto *connection = new FramedConnection(ssl, this);
        m_handshaking.append(connection);
        connect(connection, &FramedConnection::messageReceived, this,
                [this, connection](const QJsonObject &m) { onPeerMessage(connection, m); });
        connect(connection, &FramedConnection::closed, this,
                [this, connection] { onPeerClosed(connection); });
    }
}

// Called once a link is ready on the dialing side (TLS established) or on the
// accepting side (hello received). Sends our hello + channel sync.
void MeshNode::adoptConnection(FramedConnection *connection)
{
    const QString nodeId = connection->remoteId;
    m_pendingDials.remove(nodeId);
    m_handshaking.removeAll(connection);

    if (FramedConnection *existing = m_peers.value(nodeId)) {
        if (existing != connection) {
            // Duplicate link (e.g. both sides raced); keep the existing one.
            connection->disconnect(this);
            connection->close();
            connection->deleteLater();
            return;
        }
    } else {
        m_peers.insert(nodeId, connection);
    }

    connection->sendMessage(
        {{"type", "hello"}, {"nodeId", m_nodeId}, {"name", m_userName}});
    QJsonArray channels;
    for (const QString &channel : std::as_const(m_channels))
        channels.append(channel);
    connection->sendMessage({{"type", "channels-sync"}, {"list", channels}});

    emit systemMessage(connection->remoteName + " is now reachable");
    updateRosterAndStatus();
}

void MeshNode::onPeerMessage(FramedConnection *connection, const QJsonObject &message)
{
    const QString type = message.value("type").toString();

    if (type == "hello") {
        const bool firstHello = connection->remoteId.isEmpty();
        connection->remoteId = message.value("nodeId").toString();
        connection->remoteName = message.value("name").toString();
        if (connection->remoteId.isEmpty() || connection->remoteId == m_nodeId) {
            onPeerClosed(connection);
            return;
        }
        // Accepting side: the hello identifies the peer, finish setup.
        if (firstHello)
            adoptConnection(connection);
        return;
    }

    if (type == "chat") {
        if (!markSeen(message.value("id").toString()))
            return;
        mergeChannel(message.value("channel").toString(), false);
        flood(message, connection);
        emit chatMessage(message.value("channel").toString(),
                         message.value("sender").toString(),
                         message.value("text").toString(),
                         qint64(message.value("ts").toDouble()));
    } else if (type == "channel") {
        if (!markSeen(message.value("id").toString()))
            return;
        flood(message, connection);
        mergeChannel(message.value("name").toString(), false);
    } else if (type == "channels-sync") {
        for (const auto &value : message.value("list").toArray())
            mergeChannel(value.toString(), false);
    }
}

void MeshNode::onPeerClosed(FramedConnection *connection)
{
    m_handshaking.removeAll(connection);
    const QString nodeId = connection->remoteId;
    if (!nodeId.isEmpty()) {
        m_pendingDials.remove(nodeId);
        if (m_peers.value(nodeId) == connection) {
            m_peers.remove(nodeId);
            emit systemMessage(connection->remoteName + " disconnected");
        }
    }
    connection->disconnect(this);
    connection->deleteLater();
    updateRosterAndStatus();
}

void MeshNode::sendChat(const QString &channel, const QString &text)
{
    if (text.trimmed().isEmpty())
        return;
    const qint64 ts = QDateTime::currentMSecsSinceEpoch();
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    const QJsonObject message{{"type", "chat"}, {"id", id},      {"channel", channel},
                              {"sender", m_userName}, {"senderId", m_nodeId},
                              {"text", text},  {"ts", double(ts)}};
    flood(message);
    emit chatMessage(channel, m_userName, text, ts);
}

void MeshNode::addChannel(const QString &channel)
{
    mergeChannel(channel, true);
}

void MeshNode::mergeChannel(const QString &channel, bool announce)
{
    QString name = channel.trimmed();
    if (name.isEmpty())
        return;
    if (!name.startsWith('#'))
        name.prepend('#');
    if (!m_channels.contains(name)) {
        m_channels.append(name);
        emit channelsChanged(m_channels);
    }
    if (announce) {
        const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
        markSeen(id);
        flood({{"type", "channel"}, {"id", id}, {"name", name}});
    }
}

void MeshNode::flood(const QJsonObject &message, FramedConnection *exclude)
{
    for (FramedConnection *peer : std::as_const(m_peers)) {
        if (peer != exclude)
            peer->sendMessage(message);
    }
}

bool MeshNode::markSeen(const QString &messageId)
{
    if (messageId.isEmpty() || m_seenIds.contains(messageId))
        return false;
    m_seenIds.insert(messageId);
    m_seenOrder.enqueue(messageId);
    while (m_seenOrder.size() > kSeenCacheLimit)
        m_seenIds.remove(m_seenOrder.dequeue());
    return true;
}

void MeshNode::prune()
{
    const qint64 now = QDateTime::currentMSecsSinceEpoch();
    bool changed = false;
    for (auto it = m_known.begin(); it != m_known.end();) {
        if (now - it->lastSeenMs > kNodeTimeoutMs && !m_peers.contains(it.key())) {
            it = m_known.erase(it);
            changed = true;
        } else {
            ++it;
        }
    }
    if (changed)
        updateRosterAndStatus();
}

void MeshNode::updateRosterAndStatus()
{
    QStringList members{m_userName + " (you)"};
    for (auto it = m_peers.constBegin(); it != m_peers.constEnd(); ++it)
        members.append(it.value()->remoteName);
    // Nodes we can see via discovery but have no link to yet.
    for (auto it = m_known.constBegin(); it != m_known.constEnd(); ++it) {
        if (!m_peers.contains(it.key()))
            members.append(it->name + " (discovered)");
    }
    emit rosterChanged(members);
    emit statusChanged("Mesh · " + QString::number(m_peers.size()) + " peer(s) · TLS");
}

void MeshNode::shutdown()
{
    m_announceTimer.stop();
    m_pruneTimer.stop();
    m_udp.close();
    m_listener.close();
    const auto peers = m_peers.values() + m_handshaking;
    m_peers.clear();
    m_handshaking.clear();
    for (FramedConnection *peer : peers) {
        peer->disconnect(this);
        peer->close();
        peer->deleteLater();
    }
}
