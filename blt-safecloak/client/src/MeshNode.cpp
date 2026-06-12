#include "MeshNode.h"

#include "FramedConnection.h"

#include <QDateTime>
#include <QJsonArray>
#include <QJsonDocument>
#include <QNetworkDatagram>
#include <QNetworkInterface>
#include <QSslError>
#include <QTimer>
#include <QUuid>

namespace {

constexpr int kAnnounceIntervalMs = 2000;
// Generous: Wi-Fi access points drop multicast/broadcast intermittently, and
// a node should not vanish from the roster over a few lost announcements.
constexpr int kNodeTimeoutMs = 15000;
constexpr int kDialTimeoutMs = 8000;
constexpr int kSeenCacheLimit = 4096;
const QString kDefaultAppTag = QStringLiteral("safecloak-chat");
// Discovery goes out via multicast (looped back locally, so instances on the
// same machine find each other) and via broadcast as a fallback for networks
// that filter multicast. Duplicate announcements are harmless.
const QHostAddress kMulticastGroup(QStringLiteral("239.255.43.21"));

QList<QHostAddress> localIPv4Addresses()
{
    QList<QHostAddress> addresses;
    const auto interfaces = QNetworkInterface::allInterfaces();
    for (const QNetworkInterface &iface : interfaces) {
        if (!(iface.flags() & QNetworkInterface::IsUp) ||
            !(iface.flags() & QNetworkInterface::IsRunning) ||
            (iface.flags() & QNetworkInterface::IsLoopBack))
            continue;
        const auto entries = iface.addressEntries();
        for (const QNetworkAddressEntry &entry : entries) {
            const QHostAddress address = entry.ip();
            if (address.protocol() == QAbstractSocket::IPv4Protocol &&
                !addresses.contains(address))
                addresses.append(address);
        }
    }
    if (addresses.isEmpty())
        addresses.append(QHostAddress(QHostAddress::LocalHost));
    return addresses;
}

QString localAddressSummary()
{
    QStringList addresses;
    for (const QHostAddress &address : localIPv4Addresses())
        addresses.append(address.toString());
    return addresses.join(", ");
}

} // namespace

MeshNode::MeshNode(const SslIdentity &identity, const QString &userName,
                   QObject *parent, const QString &appTag)
    : ChatBackend(parent),
      m_identity(identity),
      m_userName(userName),
      m_nodeId(QUuid::createUuid().toString(QUuid::WithoutBraces)),
      m_appTag(appTag.isEmpty() ? kDefaultAppTag : appTag)
{
    m_listener.setSslConfiguration(m_identity.serverConfiguration());
    connect(&m_listener, &QSslServer::pendingConnectionAvailable, this,
            &MeshNode::onIncomingConnection);
    connect(&m_udp, &QUdpSocket::readyRead, this, &MeshNode::onDatagram);
    connect(&m_announceTimer, &QTimer::timeout, this, &MeshNode::sendAnnounce);
    connect(&m_pruneTimer, &QTimer::timeout, this, &MeshNode::prune);
}

bool MeshNode::start(const QHostAddress &bindAddress,
                     const QList<QHostAddress> &announceTargets)
{
    m_announceTargets = announceTargets;

    bool listening = false;
    for (quint16 port = kTcpPortBase;
         port < kTcpPortBase + kTcpPortRange && !listening; ++port) {
        listening = m_listener.listen(bindAddress, port);
    }
    if (!listening && !m_listener.listen(bindAddress, 0)) {
        emit fatalError("Could not open a TLS listener: " + m_listener.errorString());
        return false;
    }
    bool bound = false;
    for (quint16 port = kDiscoveryPortBase;
         port < kDiscoveryPortBase + kDiscoveryPortRange && !bound; ++port) {
        bound = m_udp.bind(bindAddress, port);
    }
    if (!bound) {
        emit fatalError("Could not bind a UDP discovery port (" +
                        QString::number(kDiscoveryPortBase) + "-" +
                        QString::number(kDiscoveryPortBase + kDiscoveryPortRange - 1) +
                        " all in use): " + m_udp.errorString());
        return false;
    }
    // Join the group on every multicast-capable interface — machines with
    // several interfaces (Wi-Fi + docker bridges + VPNs) would otherwise only
    // receive on whichever one the OS picked by default.
    m_udp.joinMulticastGroup(kMulticastGroup);
    const auto interfaces = QNetworkInterface::allInterfaces();
    for (const QNetworkInterface &iface : interfaces) {
        if ((iface.flags() & QNetworkInterface::IsUp) &&
            (iface.flags() & QNetworkInterface::IsRunning) &&
            (iface.flags() & QNetworkInterface::CanMulticast))
            m_udp.joinMulticastGroup(kMulticastGroup, iface);
    }
    m_udp.setSocketOption(QAbstractSocket::MulticastLoopbackOption, 1);

    emit channelsChanged(m_channels);
    updateRosterAndStatus();
    emit systemMessage("Ready. Local IP " + localAddressSummary() +
                       "; UDP " + QString::number(m_udp.localPort()) +
                       "; TCP " + QString::number(m_listener.serverPort()) + ".");

    sendAnnounce();
    m_announceTimer.start(kAnnounceIntervalMs);
    m_pruneTimer.start(kNodeTimeoutMs / 2);
    return true;
}

QByteArray MeshNode::announcePayload() const
{
    QJsonArray addresses;
    for (const QHostAddress &address : localIPv4Addresses())
        addresses.append(address.toString());
    const QJsonObject announce{{"app", m_appTag},
                               {"kind", "announce"},
                               {"v", 1},
                               {"nodeId", m_nodeId},
                               {"name", m_userName},
                               {"addresses", addresses},
                               {"port", m_listener.serverPort()}};
    return QJsonDocument(announce).toJson(QJsonDocument::Compact);
}

void MeshNode::sendAnnounce()
{
    const QByteArray payload = announcePayload();

    // Collect the directed broadcast address of every usable IPv4 interface.
    // Announcing per interface (instead of letting the OS pick one route for
    // 255.255.255.255 / the multicast group) is what makes discovery work on
    // machines with several interfaces — docker bridges, VPNs, etc. would
    // otherwise swallow the announcements.
    QList<QHostAddress> broadcasts{QHostAddress::Broadcast};
    QList<QNetworkInterface> multicastIfaces;
    const auto interfaces = QNetworkInterface::allInterfaces();
    for (const QNetworkInterface &iface : interfaces) {
        if (!(iface.flags() & QNetworkInterface::IsUp) ||
            !(iface.flags() & QNetworkInterface::IsRunning) ||
            (iface.flags() & QNetworkInterface::IsLoopBack))
            continue;
        if (iface.flags() & QNetworkInterface::CanMulticast)
            multicastIfaces.append(iface);
        const auto entries = iface.addressEntries();
        for (const QNetworkAddressEntry &entry : entries) {
            const QHostAddress broadcast = entry.broadcast();
            if (!broadcast.isNull() && !broadcasts.contains(broadcast))
                broadcasts.append(broadcast);
        }
    }

    for (quint16 port = kDiscoveryPortBase;
         port < kDiscoveryPortBase + kDiscoveryPortRange; ++port) {
        for (const QNetworkInterface &iface : std::as_const(multicastIfaces)) {
            m_udp.setMulticastInterface(iface);
            m_udp.writeDatagram(payload, kMulticastGroup, port);
        }
        for (const QHostAddress &broadcast : std::as_const(broadcasts))
            m_udp.writeDatagram(payload, broadcast, port);
        // Loopback unicast reaches other instances on this machine even where
        // the OS does not loop multicast/broadcast back to local sockets.
        if (port != m_udp.localPort())
            m_udp.writeDatagram(payload, QHostAddress::LocalHost, port);
        for (const QHostAddress &target : std::as_const(m_announceTargets))
            m_udp.writeDatagram(payload, target, port);
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
        if (announce.value("app").toString() != m_appTag)
            continue;

        if (announce.value("kind").toString() == "message") {
            const QJsonObject message = announce.value("message").toObject();
            if (!message.isEmpty())
                onPeerMessage(nullptr, message);
            continue;
        }

        const QString nodeId = announce.value("nodeId").toString();
        if (nodeId.isEmpty() || nodeId == m_nodeId)
            continue;

        const qint64 now = QDateTime::currentMSecsSinceEpoch();
        KnownNode &node = m_known[nodeId];
        const bool isNew = node.lastSeenMs == 0;
        QList<QHostAddress> candidates;
        if (datagram.senderAddress().protocol() == QAbstractSocket::IPv4Protocol)
            candidates.append(datagram.senderAddress());
        for (const auto &value : announce.value("addresses").toArray()) {
            const QHostAddress address(value.toString());
            if (address.protocol() == QAbstractSocket::IPv4Protocol &&
                !candidates.contains(address))
                candidates.append(address);
        }
        if (candidates.isEmpty())
            candidates.append(datagram.senderAddress());
        const bool endpointChanged =
            !isNew && (node.addresses != candidates ||
                       node.tcpPort != quint16(announce.value("port").toInt()));
        node.name = announce.value("name").toString();
        node.address = candidates.first();
        node.addresses = candidates;
        node.tcpPort = quint16(announce.value("port").toInt());
        node.udpPort = quint16(datagram.senderPort());
        node.lastSeenMs = now;
        if (isNew)
            node.firstSeenMs = now;

        if (isNew || endpointChanged) {
            QStringList addressStrings;
            for (const QHostAddress &address : std::as_const(node.addresses))
                addressStrings.append(address.toString());
            emit systemMessage("Discovered " + node.name + " at " +
                               addressStrings.join(", ") + ":" +
                               QString::number(node.tcpPort) + " (UDP from " +
                               datagram.senderAddress().toString() + ":" +
                               QString::number(datagram.senderPort()) + ").");
        }

        // Dial immediately from both sides. Duplicate links are resolved
        // deterministically in adoptConnection(), and dialing both ways avoids
        // one-way discovery/timing failures where a peer is visible but not
        // reachable in the roster.
        if (!m_peers.contains(nodeId) && !m_pendingDials.contains(nodeId) &&
            node.tcpPort > 0) {
            connectToPeer(nodeId, node);
        }
        // While there is no link, keep introducing ourselves directly to the
        // sender. This is what lets the other side learn about us when its
        // network drops our multicast/broadcast (or a previous introduction
        // was lost) — throttled so two unconnected nodes don't ping-pong.
        if (!m_peers.contains(nodeId) &&
            now - node.lastIntroSentMs > kAnnounceIntervalMs / 2) {
            node.lastIntroSentMs = now;
            QList<QHostAddress> introTargets = node.addresses;
            if (!introTargets.contains(datagram.senderAddress()))
                introTargets.prepend(datagram.senderAddress());
            const QByteArray payload = announcePayload();
            for (const QHostAddress &target : std::as_const(introTargets)) {
                m_udp.writeDatagram(payload, target, datagram.senderPort());
                for (quint16 port = kDiscoveryPortBase;
                     port < kDiscoveryPortBase + kDiscoveryPortRange; ++port) {
                    if (port != datagram.senderPort())
                        m_udp.writeDatagram(payload, target, port);
                }
            }
        }
        if (isNew)
            updateRosterAndStatus();
    }
}

void MeshNode::connectToPeer(const QString &nodeId, KnownNode &node)
{
    const QList<QHostAddress> addresses =
        node.addresses.isEmpty() ? QList<QHostAddress>{node.address} : node.addresses;
    if (addresses.isEmpty() || node.tcpPort == 0)
        return;
    const QHostAddress dialAddress =
        addresses.at(node.nextDialIndex % addresses.size());
    node.nextDialIndex = (node.nextDialIndex + 1) % addresses.size();
    m_pendingDials.insert(nodeId);
    emit systemMessage("Dialing " + node.name + " at " + dialAddress.toString() +
                       ":" + QString::number(node.tcpPort) + "...");

    auto *socket = new QSslSocket;
    connect(socket, &QSslSocket::errorOccurred, this,
            [this, nodeId, name = node.name, dialAddress, socket](QAbstractSocket::SocketError) {
                m_pendingDials.remove(nodeId);
                emit systemMessage("Direct TLS link to " + name + " at " +
                                   dialAddress.toString() + " failed: " +
                                   socket->errorString() +
                                   ". LAN fallback remains active while retrying.");
                updateRosterAndStatus();
            });
    connect(socket, &QSslSocket::sslErrors, this,
            [this, node](const QList<QSslError> &errors) {
                QStringList messages;
                for (const QSslError &error : errors)
                    messages.append(error.errorString());
                emit systemMessage("TLS warning from " + node.name + ": " +
                                   messages.join("; ") + ".");
            });
    socket->setSslConfiguration(SslIdentity::clientConfiguration());
    auto *connection = new FramedConnection(socket, this);
    connection->remoteId = nodeId;
    connection->remoteName = node.name;
    connection->outbound = true;

    connect(socket, &QSslSocket::encrypted, this, [this, connection] {
        adoptConnection(connection);
    });
    connect(connection, &FramedConnection::messageReceived, this,
            [this, connection](const QJsonObject &m) { onPeerMessage(connection, m); });
    connect(connection, &FramedConnection::closed, this, [this, connection] {
        onPeerClosed(connection);
    });
    // Abort dials that hang (filtered port, gone peer) well before the OS
    // connect timeout, so the retry loop in prune() can take another shot.
    QTimer::singleShot(kDialTimeoutMs, connection, [this, connection] {
        if (!connection->socket()->isEncrypted()) {
            emit systemMessage("Direct TLS link to " + connection->remoteName +
                               " timed out. LAN fallback remains active while retrying.");
            connection->socket()->abort(); // emits closed via errorOccurred
        }
    });

    socket->connectToHostEncrypted(dialAddress.toString(), node.tcpPort);
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
            // Duplicate link (both sides dialed). Both nodes keep the link
            // whose dialer has the smaller id, so they agree on a survivor.
            const QString newDialer = connection->outbound ? m_nodeId : nodeId;
            const QString oldDialer = existing->outbound ? m_nodeId : nodeId;
            FramedConnection *loser = newDialer < oldDialer ? existing : connection;
            loser->socket()->disconnect(this);
            loser->disconnect(this);
            loser->close();
            loser->deleteLater();
            if (loser == connection)
                return;
            m_peers.insert(nodeId, connection);
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
    } else if (type == "dm") {
        if (!markSeen(message.value("id").toString()))
            return;
        const QString to = message.value("to").toString();
        if (to == m_nodeId) {
            emit directMessage(message.value("from").toString(),
                               message.value("fromName").toString(),
                               message.value("fromName").toString(),
                               message.value("text").toString(),
                               qint64(message.value("ts").toDouble()));
        } else {
            // Not for us: forward so DMs reach peers we have no direct link to.
            flood(message, connection);
        }
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

void MeshNode::sendDirect(const QString &targetId, const QString &text)
{
    if (text.trimmed().isEmpty() || targetId == m_nodeId)
        return;
    const qint64 ts = QDateTime::currentMSecsSinceEpoch();
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    const QJsonObject message{{"type", "dm"},        {"id", id},
                              {"from", m_nodeId},    {"fromName", m_userName},
                              {"to", targetId},      {"text", text},
                              {"ts", double(ts)}};
    // Deliver on the direct link when there is one; otherwise route through
    // the mesh (intermediate nodes forward, only the target displays it).
    if (FramedConnection *peer = m_peers.value(targetId))
        peer->sendMessage(message);
    else
        flood(message);
    const QString targetName =
        m_peers.contains(targetId) ? m_peers.value(targetId)->remoteName
                                   : m_known.value(targetId).name;
    emit directMessage(targetId, targetName, m_userName, text, ts);
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
    floodUdp(message);
}

void MeshNode::sendUdpToNode(const KnownNode &node, const QJsonObject &message)
{
    if (node.udpPort == 0)
        return;
    const QJsonObject packet{{"app", m_appTag}, {"kind", "message"}, {"message", message}};
    const QByteArray payload = QJsonDocument(packet).toJson(QJsonDocument::Compact);

    QList<QHostAddress> targets = node.addresses;
    if (!targets.contains(node.address))
        targets.prepend(node.address);
    for (const QHostAddress &target : std::as_const(targets))
        m_udp.writeDatagram(payload, target, node.udpPort);
}

void MeshNode::floodUdp(const QJsonObject &message)
{
    for (auto it = m_known.constBegin(); it != m_known.constEnd(); ++it) {
        if (!m_peers.contains(it.key()))
            sendUdpToNode(it.value(), message);
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
        if (now - it->lastSeenMs > kNodeTimeoutMs && !m_peers.contains(it.key()) &&
            !m_pendingDials.contains(it.key())) {
            it = m_known.erase(it);
            changed = true;
            continue;
        }
        // Link establishment safety net: if a dial failed or timed out, retry
        // while the peer is still being announced.
        if (!m_peers.contains(it.key()) && !m_pendingDials.contains(it.key())) {
            connectToPeer(it.key(), it.value());
        }
        ++it;
    }
    if (changed)
        updateRosterAndStatus();
}

void MeshNode::updateRosterAndStatus()
{
    QList<MemberInfo> members{{m_nodeId, m_userName, QString(), true}};
    for (auto it = m_peers.constBegin(); it != m_peers.constEnd(); ++it)
        members.append({it.key(), it.value()->remoteName, QString(), false});
    // Nodes we can see via discovery but have no link to yet.
    for (auto it = m_known.constBegin(); it != m_known.constEnd(); ++it) {
        if (!m_peers.contains(it.key()))
            members.append({it.key(), it->name,
                            it->udpPort == 0 ? QStringLiteral("(discovered)")
                                             : QString(),
                            false});
    }
    emit rosterChanged(members);
    int reachableCount = m_peers.size();
    for (auto it = m_known.constBegin(); it != m_known.constEnd(); ++it) {
        if (!m_peers.contains(it.key()))
            ++reachableCount;
    }
    emit statusChanged(QString::number(reachableCount) +
                       " reachable · IP " + localAddressSummary() + " · UDP " +
                       QString::number(m_udp.localPort()) + " · TCP " +
                       QString::number(m_listener.serverPort()));
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
