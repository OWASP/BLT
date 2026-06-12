#include "MeshNode.h"

#include "FramedConnection.h"

#include <QDateTime>
#include <QJsonArray>
#include <QJsonDocument>
#include <QNetworkDatagram>
#include <QNetworkInterface>
#include <QProcess>
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
constexpr int kUdpRetryDelaysMs[] = {180, 650, 1400, 2600};
constexpr int kMessageRetryDelaysMs[] = {250, 900};
constexpr int kMaxDisplayNameChars = 32;
constexpr int kMaxTextChars = 16000;
constexpr int kMaxFileNameChars = 180;
constexpr int kMaxMimeChars = 100;
constexpr qsizetype kMaxFileBytes = 64ll * 1024 * 1024;
constexpr qsizetype kMaxBase64FileChars = 90ll * 1024 * 1024;
constexpr qsizetype kMaxAvatarBytes = 256 * 1024;
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

QString boundedText(const QJsonObject &object, const char *key, int maxChars)
{
    QString value = object.value(key).toString();
    if (value.size() > maxChars)
        value = value.left(maxChars);
    return value;
}

QString safeFileName(const QString &name)
{
    QString cleaned = name;
    cleaned.replace('\\', '/');
    cleaned = cleaned.section('/', -1).trimmed();
    cleaned.remove('\0');
    if (cleaned.isEmpty())
        cleaned = "file";
    return cleaned.left(kMaxFileNameChars);
}

QByteArray boundedBase64(const QJsonObject &object, const char *key,
                         qsizetype maxBase64Chars, qsizetype maxDecodedBytes)
{
    const QString encoded = object.value(key).toString();
    if (encoded.isEmpty() || encoded.size() > maxBase64Chars)
        return {};
    const QByteArray decoded = QByteArray::fromBase64(encoded.toLatin1());
    if (decoded.size() > maxDecodedBytes)
        return {};
    return decoded;
}

bool messageHasSafePayload(const QJsonObject &message)
{
    if (message.value("text").toString().size() > kMaxTextChars ||
        message.value("sender").toString().size() > kMaxDisplayNameChars ||
        message.value("fileName").toString().size() > kMaxFileNameChars ||
        message.value("fileMime").toString().size() > kMaxMimeChars ||
        message.value("file").toString().size() > kMaxBase64FileChars ||
        message.value("png").toString().size() > 4 * kMaxAvatarBytes / 3 + 8)
        return false;
    return true;
}

// How to open SafeCloak's inbound ports on a host firewall:
//   display    — what the user would type in a terminal (with sudo)
//   privileged — the same commands without sudo, to run via pkexec from the
//                "Allow through firewall" button (pkexec does the elevation)
// Note the range syntax differs by tool: ufw wants colons (45453:45463),
// firewalld wants hyphens (45453-45463). Using the wrong one is the cause of
// ufw's "ERROR: Bad port".
struct FirewallFix {
    QString display;
    QString privileged;
    bool valid() const { return !display.isEmpty(); }
};

// Best effort and root-free: only checks whether a firewall service is running.
// Returns an empty fix when none is detected (or not on Linux).
FirewallFix detectFirewallFix()
{
    auto serviceActive = [](const QString &service) {
        QProcess probe;
        probe.start("systemctl", {"is-active", service});
        if (!probe.waitForFinished(1500))
            return false;
        return probe.readAllStandardOutput().trimmed() == "active";
    };

    if (serviceActive("ufw")) {
        const QString body =
            "ufw allow 45453:45463/udp && ufw allow 45464:45473/tcp";
        return {"sudo ufw allow 45453:45463/udp && sudo ufw allow 45464:45473/tcp",
                body};
    }
    if (serviceActive("firewalld")) {
        const QString ports =
            "--add-port=45453-45463/udp --add-port=45464-45473/tcp";
        return {"sudo firewall-cmd --permanent " + ports +
                    " && sudo firewall-cmd --reload",
                "firewall-cmd --permanent " + ports + " && firewall-cmd --reload"};
    }
    return {};
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
    connect(&m_lanBus, &QUdpSocket::readyRead, this, &MeshNode::onLanDatagram);
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
    if (!m_lanBus.bind(bindAddress, kLanBusPort,
                       QUdpSocket::ShareAddress | QUdpSocket::ReuseAddressHint)) {
        emit fatalError("Could not bind the LAN chat port " +
                        QString::number(kLanBusPort) + ": " +
                        m_lanBus.errorString());
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
    m_lanBus.joinMulticastGroup(kMulticastGroup);
    for (const QNetworkInterface &iface : interfaces) {
        if ((iface.flags() & QNetworkInterface::IsUp) &&
            (iface.flags() & QNetworkInterface::IsRunning) &&
            (iface.flags() & QNetworkInterface::CanMulticast))
            m_lanBus.joinMulticastGroup(kMulticastGroup, iface);
    }
    m_lanBus.setSocketOption(QAbstractSocket::MulticastLoopbackOption, 1);

    emit channelsChanged(m_channels);
    updateRosterAndStatus();
    emit systemMessage("Ready. Local IP " + localAddressSummary() +
                       "; UDP " + QString::number(m_udp.localPort()) +
                       "; LAN " + QString::number(kLanBusPort) +
                       "; TCP " + QString::number(m_listener.serverPort()) + ".");
    warnIfLocalFirewall();

    sendAnnounce();
    sendLanBusPacket();
    m_announceTimer.start(kAnnounceIntervalMs);
    m_pruneTimer.start(kNodeTimeoutMs / 2);
    return true;
}

QByteArray MeshNode::announcePayload() const
{
    QJsonObject announce = selfPacketMetadata();
    announce.insert("kind", "announce");
    return QJsonDocument(announce).toJson(QJsonDocument::Compact);
}

QJsonObject MeshNode::selfPacketMetadata() const
{
    QJsonArray addresses;
    for (const QHostAddress &address : localIPv4Addresses())
        addresses.append(address.toString());
    return {{"app", m_appTag},
            {"v", 1},
            {"nodeId", m_nodeId},
            {"name", m_userName},
            {"addresses", addresses},
            {"port", m_listener.serverPort()}};
}

QList<QHostAddress> MeshNode::broadcastAddresses() const
{
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
    return broadcasts;
}

void MeshNode::writeDiscoveryDatagrams(const QByteArray &payload,
                                       const QList<QHostAddress> &extraTargets)
{
    if (m_udp.state() != QAbstractSocket::BoundState)
        return;

    const QList<QHostAddress> broadcasts = broadcastAddresses();
    QList<QNetworkInterface> multicastIfaces;
    const auto interfaces = QNetworkInterface::allInterfaces();
    for (const QNetworkInterface &iface : interfaces) {
        if ((iface.flags() & QNetworkInterface::IsUp) &&
            (iface.flags() & QNetworkInterface::IsRunning) &&
            !(iface.flags() & QNetworkInterface::IsLoopBack) &&
            (iface.flags() & QNetworkInterface::CanMulticast))
            multicastIfaces.append(iface);
    }
    for (quint16 port = kDiscoveryPortBase;
         port < kDiscoveryPortBase + kDiscoveryPortRange; ++port) {
        for (const QNetworkInterface &iface : std::as_const(multicastIfaces)) {
            if (m_udp.state() != QAbstractSocket::BoundState)
                return;
            m_udp.setMulticastInterface(iface);
            m_udp.writeDatagram(payload, kMulticastGroup, port);
        }
        for (const QHostAddress &broadcast : std::as_const(broadcasts))
            m_udp.writeDatagram(payload, broadcast, port);
        // Loopback unicast reaches other instances on this machine even where
        // the OS does not loop multicast/broadcast back to local sockets.
        if (port != m_udp.localPort())
            m_udp.writeDatagram(payload, QHostAddress::LocalHost, port);
        for (const QHostAddress &target : std::as_const(extraTargets))
            m_udp.writeDatagram(payload, target, port);
        for (const QHostAddress &target : std::as_const(m_announceTargets))
            m_udp.writeDatagram(payload, target, port);
    }
}

void MeshNode::sendLanBusPacket(const QJsonObject &message)
{
    if (m_lanBus.state() != QAbstractSocket::BoundState)
        return;

    QJsonObject packet = selfPacketMetadata();
    packet.insert("kind", message.isEmpty() ? "lan-announce" : "lan-message");
    if (!message.isEmpty())
        packet.insert("message", message);
    const QByteArray payload = QJsonDocument(packet).toJson(QJsonDocument::Compact);

    QList<QHostAddress> targets = broadcastAddresses();
    for (const KnownNode &node : std::as_const(m_known)) {
        if (!targets.contains(node.address))
            targets.append(node.address);
        for (const QHostAddress &address : node.addresses) {
            if (!targets.contains(address))
                targets.append(address);
        }
    }
    for (const QHostAddress &target : std::as_const(m_announceTargets)) {
        if (!targets.contains(target))
            targets.append(target);
    }

    auto sendOnce = [this, payload, targets] {
        if (m_lanBus.state() != QAbstractSocket::BoundState)
            return;

        QList<QNetworkInterface> multicastIfaces;
        const auto interfaces = QNetworkInterface::allInterfaces();
        for (const QNetworkInterface &iface : interfaces) {
            if ((iface.flags() & QNetworkInterface::IsUp) &&
                (iface.flags() & QNetworkInterface::IsRunning) &&
                !(iface.flags() & QNetworkInterface::IsLoopBack) &&
                (iface.flags() & QNetworkInterface::CanMulticast))
                multicastIfaces.append(iface);
        }
        for (const QNetworkInterface &iface : std::as_const(multicastIfaces)) {
            m_lanBus.setMulticastInterface(iface);
            m_lanBus.writeDatagram(payload, kMulticastGroup, kLanBusPort);
        }
        m_lanBus.writeDatagram(payload, QHostAddress::LocalHost, kLanBusPort);
        for (const QHostAddress &target : std::as_const(targets))
            m_lanBus.writeDatagram(payload, target, kLanBusPort);
    };

    sendOnce();
    for (int delay : kMessageRetryDelaysMs)
        QTimer::singleShot(delay, this, sendOnce);
}

void MeshNode::onLanDatagram()
{
    while (m_lanBus.hasPendingDatagrams()) {
        const QNetworkDatagram datagram = m_lanBus.receiveDatagram();
        const QJsonDocument doc = QJsonDocument::fromJson(datagram.data());
        if (!doc.isObject())
            continue;
        const QJsonObject packet = doc.object();
        if (packet.value("app").toString() != m_appTag)
            continue;
        const QString kind = packet.value("kind").toString();
        if (kind != "lan-announce" && kind != "lan-message")
            continue;
        const bool changed =
            learnNodeFromPacket(packet, datagram.senderAddress(), kLanBusPort);
        if (changed) {
            QTimer::singleShot(80, this, [this] {
                sendLanBusPacket();
            });
        }
        if (kind == "lan-message") {
            const QJsonObject message = packet.value("message").toObject();
            if (!message.isEmpty()) {
                emit systemMessage("Network: received LAN message from " +
                                   packet.value("name").toString() + ".");
                onPeerMessage(nullptr, message);
            }
        }
    }
}

void MeshNode::replyWithAnnounce(const QHostAddress &target, quint16 targetPort)
{
    const QByteArray payload = announcePayload();
    QList<QHostAddress> targets{target};
    writeDiscoveryDatagrams(payload, targets);
    m_udp.writeDatagram(payload, target, targetPort);
    for (int delay : kUdpRetryDelaysMs) {
        QTimer::singleShot(delay, this, [this, payload, target, targetPort] {
            QList<QHostAddress> targets{target};
            writeDiscoveryDatagrams(payload, targets);
            m_udp.writeDatagram(payload, target, targetPort);
        });
    }
    sendLanBusPacket();
}

void MeshNode::forgetStaleEndpointUsers(const QString &nodeId,
                                        const QList<QHostAddress> &addresses,
                                        quint16 tcpPort, quint16 udpPort)
{
    bool changed = false;
    for (auto it = m_known.begin(); it != m_known.end();) {
        if (it.key() == nodeId) {
            ++it;
            continue;
        }
        bool sameEndpoint = tcpPort > 0 && it->tcpPort == tcpPort;
        sameEndpoint = sameEndpoint || (udpPort > 0 && it->udpPort == udpPort);
        for (const QHostAddress &address : addresses) {
            if (it->addresses.contains(address)) {
                sameEndpoint = true;
                break;
            }
        }
        if (sameEndpoint && !m_peers.contains(it.key())) {
            m_pendingDials.remove(it.key());
            it = m_known.erase(it);
            changed = true;
            continue;
        }
        ++it;
    }
    if (changed)
        updateRosterAndStatus();
}

void MeshNode::warnIfLocalFirewall()
{
    const FirewallFix fix = detectFirewallFix();
    if (!fix.valid())
        return;
    m_firewallFixCommand = fix.display;
    m_firewallPrivilegedCommand = fix.privileged;
}

// Called when a dial fails or times out. If this node has discovered peers but
// every dial fails and it has never accepted an inbound connection, its own
// inbound is almost certainly being dropped — surface the fix once.
void MeshNode::noteDialFailure()
{
    ++m_failedDials;
    const int failureThreshold = qMax(4, qMax(1, m_known.size()) * 2);
    if (m_firewallHintShown || m_inboundEverAccepted || m_peerTrafficSeen ||
        !m_peers.isEmpty() || m_failedDials < failureThreshold || m_known.isEmpty())
        return;
    m_firewallHintShown = true;
    if (!m_firewallPrivilegedCommand.isEmpty()) {
        // This machine has a local firewall — offer the one-click fix too.
        emit systemMessage(
            "\xE2\x9A\xA0 Could not open a direct link to any peer, and no one "
            "has connected in. Your firewall is likely blocking SafeCloak — "
            "click \"Allow through firewall\" above, or run:  " + m_firewallFixCommand);
        emit firewallBlocking(m_firewallFixCommand, m_firewallPrivilegedCommand);
    } else {
        // No local firewall service detected: the block is on the peer's side.
        emit systemMessage(
            "\xE2\x9A\xA0 Could not open a direct link to any peer, and no one "
            "has connected in. A firewall is blocking SafeCloak on the computer "
            "others can't reach — on that machine run:  "
            "sudo ufw allow 45453:45463/udp && sudo ufw allow 45464:45473/tcp");
    }
}

void MeshNode::sendAnnounce()
{
    writeDiscoveryDatagrams(announcePayload());
    // Keep the LAN fallback as a first-class presence channel, not just a
    // message path. This lets later-starting clients show already-open peers
    // even when ordinary UDP discovery is filtered by the network.
    sendLanBusPacket();
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
            learnNodeFromPacket(announce, datagram.senderAddress(),
                                quint16(datagram.senderPort()));
            replyWithAnnounce(datagram.senderAddress(), quint16(datagram.senderPort()));
            if (!message.isEmpty()) {
                emit systemMessage("Network: received UDP message from " +
                                   announce.value("name").toString() + ".");
                onPeerMessage(nullptr, message);
            }
            continue;
        }

        const QString nodeId = announce.value("nodeId").toString();
        if (nodeId.isEmpty() || nodeId == m_nodeId)
            continue;
        if (m_departedNodes.contains(nodeId))
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
        forgetStaleEndpointUsers(nodeId, candidates,
                                 quint16(announce.value("port").toInt()),
                                 quint16(datagram.senderPort()));
        const QString name = announce.value("name").toString();
        const bool endpointChanged =
            !isNew && (node.addresses != candidates ||
                       node.tcpPort != quint16(announce.value("port").toInt()));
        const bool nameChanged = !isNew && node.name != name;
        node.name = name;
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
            for (const QHostAddress &target : std::as_const(introTargets)) {
                replyWithAnnounce(target, quint16(datagram.senderPort()));
            }
        }
        if (isNew || endpointChanged || nameChanged)
            updateRosterAndStatus();
    }
}

bool MeshNode::learnNodeFromPacket(const QJsonObject &packet,
                                   const QHostAddress &senderAddress,
                                   quint16 senderPort)
{
    const QString nodeId = packet.value("nodeId").toString();
    if (nodeId.isEmpty() || nodeId == m_nodeId)
        return false;
    if (m_departedNodes.contains(nodeId))
        return false;

    QList<QHostAddress> candidates;
    if (senderAddress.protocol() == QAbstractSocket::IPv4Protocol)
        candidates.append(senderAddress);
    for (const auto &value : packet.value("addresses").toArray()) {
        const QHostAddress address(value.toString());
        if (address.protocol() == QAbstractSocket::IPv4Protocol &&
            !candidates.contains(address))
            candidates.append(address);
    }
    if (candidates.isEmpty())
        candidates.append(senderAddress);

    forgetStaleEndpointUsers(nodeId, candidates, quint16(packet.value("port").toInt()),
                             senderPort);
    KnownNode &node = m_known[nodeId];
    const bool isNew = node.lastSeenMs == 0;
    const QString name = packet.value("name").toString();
    const quint16 tcpPort = quint16(packet.value("port").toInt());
    const bool changed = isNew || node.name != name ||
                         node.addresses != candidates ||
                         node.tcpPort != tcpPort ||
                         node.udpPort != senderPort;
    node.name = name;
    node.address = candidates.first();
    node.addresses = candidates;
    node.tcpPort = tcpPort;
    node.udpPort = senderPort;
    node.lastSeenMs = QDateTime::currentMSecsSinceEpoch();
    if (isNew)
        node.firstSeenMs = node.lastSeenMs;

    if (!m_peers.contains(nodeId) && !m_pendingDials.contains(nodeId) &&
        node.tcpPort > 0) {
        connectToPeer(nodeId, node);
    }
    if (isNew) {
        QStringList addressStrings;
        for (const QHostAddress &address : std::as_const(node.addresses))
            addressStrings.append(address.toString());
        emit systemMessage("Discovered " + node.name + " at " +
                           addressStrings.join(", ") + ":" +
                           QString::number(node.tcpPort) + " (LAN).");
    }
    if (changed)
        updateRosterAndStatus();
    return changed;
}

void MeshNode::rememberMessageSender(const QString &nodeId, const QString &name)
{
    if (nodeId.isEmpty() || nodeId == m_nodeId)
        return;

    KnownNode &node = m_known[nodeId];
    const bool isNew = node.lastSeenMs == 0;
    const bool changed = isNew || (!name.isEmpty() && node.name != name);
    if (!name.isEmpty())
        node.name = name;
    const qint64 now = QDateTime::currentMSecsSinceEpoch();
    if (isNew)
        node.firstSeenMs = now;
    node.lastSeenMs = now;
    if (changed)
        updateRosterAndStatus();
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
                noteDialFailure();
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
            noteDialFailure();
            connection->socket()->abort(); // emits closed via errorOccurred
        }
    });

    socket->connectToHostEncrypted(dialAddress.toString(), node.tcpPort);
}

void MeshNode::onIncomingConnection()
{
    if (!m_listener.isListening())
        return;
    while (QTcpSocket *pending = m_listener.nextPendingConnection()) {
        auto *ssl = qobject_cast<QSslSocket *>(pending);
        if (!ssl) {
            pending->deleteLater();
            continue;
        }
        // An inbound connection proves this host's firewall is not blocking us.
        m_inboundEverAccepted = true;
        emit firewallHealthy();
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
    emit firewallHealthy();

    connection->sendMessage(
        {{"type", "hello"}, {"nodeId", m_nodeId}, {"name", m_userName}});
    QJsonArray channels;
    for (const QString &channel : std::as_const(m_channels))
        channels.append(channel);
    connection->sendMessage({{"type", "channels-sync"}, {"list", channels}});

    // Give the newly linked peer our shared-channel backlog and avatar so a
    // late joiner sees prior history and everyone's picture.
    sendHistoryTo(connection);
    sendAvatarTo(connection);

    emit systemMessage(connection->remoteName + " is now reachable");
    updateRosterAndStatus();
}

void MeshNode::onPeerMessage(FramedConnection *connection, const QJsonObject &message)
{
    const QString type = message.value("type").toString();
    if (!messageHasSafePayload(message)) {
        emit systemMessage("Dropped oversized or unsafe peer payload.");
        return;
    }
    if (type != "hello" && type != "channels-sync") {
        if (!m_peerTrafficSeen) {
            m_peerTrafficSeen = true;
            emit firewallHealthy();
        }
    }

    if (type == "hello") {
        if (!connection)
            return;
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
        rememberMessageSender(message.value("senderId").toString(),
                              message.value("sender").toString());
        mergeChannel(message.value("channel").toString(), false);
        storeChannelHistory(message);
        flood(message, connection);
        emitIncomingChat(message);
    } else if (type == "dm") {
        if (!markSeen(message.value("id").toString()))
            return;
        rememberMessageSender(message.value("senderId").toString(),
                              message.value("sender").toString());
        const QString to = message.value("to").toString();
        if (to == m_nodeId) {
            emitIncomingDm(message, message.value("senderId").toString());
        } else {
            // Not for us: forward so DMs reach peers we have no direct link to.
            flood(message, connection);
        }
    } else if (type == "reaction") {
        if (!markSeen(message.value("id").toString()))
            return;
        flood(message, connection);
        applyReaction(message.value("conversation").toString(),
                      message.value("target").toString(),
                      message.value("emoji").toString(),
                      message.value("reactorId").toString(),
                      message.value("reactorName").toString(),
                      message.value("added").toBool());
    } else if (type == "edit") {
        if (!markSeen(message.value("id").toString()))
            return;
        const QString target = message.value("target").toString();
        const QString senderId = message.value("senderId").toString();
        if (!messageIsAuthoredBy(target, senderId))
            return;
        flood(message, connection);
        applyEdit(message.value("conversation").toString(), target, senderId,
                  boundedText(message, "text", kMaxTextChars));
    } else if (type == "delete") {
        if (!markSeen(message.value("id").toString()))
            return;
        const QString target = message.value("target").toString();
        const QString senderId = message.value("senderId").toString();
        if (!messageIsAuthoredBy(target, senderId))
            return;
        flood(message, connection);
        applyDelete(message.value("conversation").toString(), target, senderId);
    } else if (type == "avatar") {
        if (!markSeen(message.value("id").toString()))
            return;
        flood(message, connection);
        const QByteArray avatar =
            boundedBase64(message, "png", 4 * kMaxAvatarBytes / 3 + 8,
                          kMaxAvatarBytes);
        if (!avatar.isEmpty())
            emit avatarChanged(message.value("senderId").toString(), avatar);
    } else if (type == "history") {
        // Targeted backlog from a peer we just linked to: replay anything new.
        for (const auto &value : message.value("entries").toArray()) {
            const QJsonObject entry = value.toObject();
            if (!messageHasSafePayload(entry))
                continue;
            if (!markSeen(entry.value("id").toString()))
                continue;
            mergeChannel(entry.value("channel").toString(), false);
            storeChannelHistory(entry);
            emitIncomingChat(entry);
        }
        for (const auto &value : message.value("reactions").toArray()) {
            const QJsonObject r = value.toObject();
            applyReaction(r.value("conversation").toString(),
                          r.value("target").toString(), r.value("emoji").toString(),
                          r.value("reactorId").toString(),
                          r.value("reactorName").toString(), true);
        }
    } else if (type == "typing") {
        if (!markSeen(message.value("id").toString()))
            return;
        flood(message, connection);
        emit typingChanged(message.value("conversation").toString(),
                           message.value("senderId").toString(),
                           message.value("sender").toString(),
                           message.value("active").toBool());
    } else if (type == "bye") {
        if (!markSeen(message.value("id").toString()))
            return;
        flood(message, connection);
        removeNode(message.value("senderId").toString(), "left");
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

// Drops a node from the member list right away (clean exit via "bye", or a
// dead link with no fresh announcements).
void MeshNode::removeNode(const QString &nodeId, const QString &reason)
{
    if (nodeId.isEmpty() || nodeId == m_nodeId)
        return;
    const QString name = m_peers.contains(nodeId)
                             ? m_peers.value(nodeId)->remoteName
                             : m_known.value(nodeId).name;
    if (FramedConnection *peer = m_peers.take(nodeId)) {
        peer->disconnect(this);
        peer->close();
        peer->deleteLater();
    }
    m_pendingDials.remove(nodeId);
    const bool existed = m_known.remove(nodeId) > 0;
    m_departedNodes.insert(nodeId);
    if (existed || !name.isEmpty())
        emit systemMessage(name + " " + reason);
    updateRosterAndStatus();
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
            removeNode(nodeId, "left");
        }
    }
    connection->disconnect(this);
    connection->deleteLater();
    updateRosterAndStatus();
}

void MeshNode::sendChat(const QString &channel, const QString &text)
{
    if (!text.trimmed().isEmpty())
        broadcastChat(channel, text, {}, {}, {});
}

void MeshNode::sendDirect(const QString &targetId, const QString &text)
{
    if (!text.trimmed().isEmpty())
        sendDm(targetId, text, {}, {}, {});
}

void MeshNode::sendFile(const QString &conversation, const QString &fileName,
                        const QString &mimeType, const QByteArray &data)
{
    if (fileName.isEmpty() || data.isEmpty() || data.size() > kMaxFileBytes)
        return;
    if (conversation.startsWith('@'))
        sendDm(conversation.mid(1), QString(), safeFileName(fileName),
               mimeType.left(kMaxMimeChars), data);
    else
        broadcastChat(conversation, QString(), safeFileName(fileName),
                      mimeType.left(kMaxMimeChars), data);
}

void MeshNode::broadcastChat(const QString &channel, const QString &text,
                             const QString &fileName, const QString &mime,
                             const QByteArray &data)
{
    const qint64 ts = QDateTime::currentMSecsSinceEpoch();
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    QJsonObject message{{"type", "chat"}, {"id", id},       {"channel", channel},
                        {"sender", m_userName.left(kMaxDisplayNameChars)},
                        {"senderId", m_nodeId},
                        {"text", text.left(kMaxTextChars)},   {"ts", double(ts)}};
    if (!fileName.isEmpty()) {
        message.insert("fileName", safeFileName(fileName));
        message.insert("fileMime", mime.left(kMaxMimeChars));
        message.insert("file", QString::fromLatin1(data.toBase64()));
    }
    storeChannelHistory(message);
    flood(message, nullptr, true);
    emitIncomingChat(message);
}

void MeshNode::sendDm(const QString &targetId, const QString &text,
                      const QString &fileName, const QString &mime,
                      const QByteArray &data)
{
    if (targetId == m_nodeId)
        return;
    const qint64 ts = QDateTime::currentMSecsSinceEpoch();
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    QJsonObject message{{"type", "dm"},        {"id", id},
                        {"senderId", m_nodeId},
                        {"sender", m_userName.left(kMaxDisplayNameChars)},
                        {"to", targetId},      {"text", text.left(kMaxTextChars)},
                        {"ts", double(ts)}};
    if (!fileName.isEmpty()) {
        message.insert("fileName", safeFileName(fileName));
        message.insert("fileMime", mime.left(kMaxMimeChars));
        message.insert("file", QString::fromLatin1(data.toBase64()));
    }
    // Deliver on the direct link when there is one; otherwise route through
    // the mesh (intermediate nodes forward, only the target displays it).
    if (FramedConnection *peer = m_peers.value(targetId))
        peer->sendMessage(message);
    else
        flood(message, nullptr, true);
    // Our own copy of the conversation is keyed by the other party (target).
    QJsonObject mine = message;
    emitIncomingDm(mine, targetId);
}

void MeshNode::sendReaction(const QString &conversation, const QString &messageId,
                            const QString &emoji)
{
    if (messageId.isEmpty() || emoji.isEmpty())
        return;
    // Toggle: if we've already reacted with this emoji, remove it.
    const bool added =
        !m_reactions.value(messageId).value(emoji).contains(m_nodeId);
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    const QJsonObject message{{"type", "reaction"}, {"id", id},
                              {"conversation", conversation},
                              {"target", messageId}, {"emoji", emoji},
                              {"reactorId", m_nodeId}, {"reactorName", m_userName},
                              {"added", added}};
    flood(message, nullptr, false);
    applyReaction(conversation, messageId, emoji, m_nodeId, m_userName, added);
}

void MeshNode::editMessage(const QString &conversation, const QString &messageId,
                           const QString &newText)
{
    const QString text = newText.trimmed().left(kMaxTextChars);
    if (messageId.isEmpty() || text.isEmpty() ||
        !messageIsAuthoredBy(messageId, m_nodeId))
        return;
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    const QJsonObject message{{"type", "edit"}, {"id", id},
                              {"conversation", conversation},
                              {"target", messageId},
                              {"senderId", m_nodeId}, {"sender", m_userName},
                              {"text", text}};
    flood(message, nullptr, false);
    applyEdit(conversation, messageId, m_nodeId, text);
}

void MeshNode::deleteMessage(const QString &conversation, const QString &messageId)
{
    if (messageId.isEmpty() || !messageIsAuthoredBy(messageId, m_nodeId))
        return;
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    const QJsonObject message{{"type", "delete"}, {"id", id},
                              {"conversation", conversation},
                              {"target", messageId},
                              {"senderId", m_nodeId}, {"sender", m_userName}};
    flood(message, nullptr, false);
    applyDelete(conversation, messageId, m_nodeId);
}

void MeshNode::applyReaction(const QString &conversation, const QString &target,
                             const QString &emoji, const QString &reactorId,
                             const QString &reactorName, bool added)
{
    if (target.isEmpty() || emoji.isEmpty())
        return;
    auto &byEmoji = m_reactions[target][emoji];
    if (added)
        byEmoji.insert(reactorId, reactorName);
    else
        byEmoji.remove(reactorId);
    if (byEmoji.isEmpty())
        m_reactions[target].remove(emoji);
    const QString conv =
        conversation.isEmpty() ? m_messageConversation.value(target) : conversation;
    emit reactionChanged(conv, target, emoji, reactorName, added);
}

bool MeshNode::messageIsAuthoredBy(const QString &messageId, const QString &senderId) const
{
    return !messageId.isEmpty() && !senderId.isEmpty() &&
           m_messageSender.value(messageId) == senderId;
}

void MeshNode::updateStoredMessage(const QString &messageId, const QString &text,
                                   bool deleted)
{
    for (auto it = m_channelHistory.begin(); it != m_channelHistory.end(); ++it) {
        QList<QJsonObject> &messages = it.value();
        for (QJsonObject &message : messages) {
            if (message.value("id").toString() != messageId)
                continue;
            if (deleted) {
                message.insert("deleted", true);
                message.insert("edited", false);
                message.insert("text", QString());
                message.remove("fileName");
                message.remove("fileMime");
                message.remove("file");
            } else {
                message.insert("text", text.left(kMaxTextChars));
                message.insert("edited", true);
            }
            return;
        }
    }
}

void MeshNode::applyEdit(const QString &conversation, const QString &target,
                         const QString &senderId, const QString &text)
{
    if (!messageIsAuthoredBy(target, senderId) || text.trimmed().isEmpty())
        return;
    const QString conv =
        conversation.isEmpty() ? m_messageConversation.value(target) : conversation;
    updateStoredMessage(target, text, false);
    emit messageEdited(conv, target, text.left(kMaxTextChars));
}

void MeshNode::applyDelete(const QString &conversation, const QString &target,
                           const QString &senderId)
{
    if (!messageIsAuthoredBy(target, senderId))
        return;
    const QString conv =
        conversation.isEmpty() ? m_messageConversation.value(target) : conversation;
    updateStoredMessage(target, QString(), true);
    m_reactions.remove(target);
    emit messageDeleted(conv, target);
}

void MeshNode::setAvatar(const QByteArray &pngData)
{
    if (pngData.size() > kMaxAvatarBytes)
        return;
    m_avatarPng = pngData;
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    const QJsonObject message{{"type", "avatar"}, {"id", id},
                              {"senderId", m_nodeId}, {"name", m_userName},
                              {"png", QString::fromLatin1(pngData.toBase64())}};
    flood(message, nullptr, false);
    emit avatarChanged(m_nodeId, pngData);
}

void MeshNode::emitIncomingChat(const QJsonObject &m)
{
    ChatMessage cm;
    cm.id = m.value("id").toString();
    cm.conversation = m.value("channel").toString();
    cm.senderId = m.value("senderId").toString();
    cm.senderName = boundedText(m, "sender", kMaxDisplayNameChars);
    cm.text = boundedText(m, "text", kMaxTextChars);
    cm.timestampMs = qint64(m.value("ts").toDouble());
    cm.fileName = safeFileName(m.value("fileName").toString());
    if (cm.fileName == "file" && !m.contains("fileName"))
        cm.fileName.clear();
    cm.fileMime = boundedText(m, "fileMime", kMaxMimeChars);
    if (m.contains("file"))
        cm.fileData = boundedBase64(m, "file", kMaxBase64FileChars, kMaxFileBytes);
    cm.self = cm.senderId == m_nodeId;
    cm.edited = m.value("edited").toBool();
    cm.deleted = m.value("deleted").toBool();
    m_messageConversation.insert(cm.id, cm.conversation);
    m_messageSender.insert(cm.id, cm.senderId);
    emit messageArrived(cm);
}

void MeshNode::emitIncomingDm(const QJsonObject &m, const QString &conversationPeer)
{
    ChatMessage cm;
    cm.id = m.value("id").toString();
    cm.conversation = "@" + conversationPeer;
    cm.senderId = m.value("senderId").toString();
    cm.senderName = boundedText(m, "sender", kMaxDisplayNameChars);
    cm.text = boundedText(m, "text", kMaxTextChars);
    cm.timestampMs = qint64(m.value("ts").toDouble());
    cm.fileName = safeFileName(m.value("fileName").toString());
    if (cm.fileName == "file" && !m.contains("fileName"))
        cm.fileName.clear();
    cm.fileMime = boundedText(m, "fileMime", kMaxMimeChars);
    if (m.contains("file"))
        cm.fileData = boundedBase64(m, "file", kMaxBase64FileChars, kMaxFileBytes);
    cm.self = cm.senderId == m_nodeId;
    cm.edited = m.value("edited").toBool();
    cm.deleted = m.value("deleted").toBool();
    m_messageConversation.insert(cm.id, cm.conversation);
    m_messageSender.insert(cm.id, cm.senderId);
    emit messageArrived(cm);
}

void MeshNode::storeChannelHistory(const QJsonObject &m)
{
    const QString channel = m.value("channel").toString();
    if (channel.isEmpty())
        return;
    // Unlimited: the full backlog is kept and replayed to late joiners.
    m_channelHistory[channel].append(m);
}

void MeshNode::sendHistoryTo(FramedConnection *connection)
{
    // The full backlog, chunked so a single frame stays well under the wire
    // limit even when the history contains shared files.
    QList<QJsonObject> all;
    for (const QList<QJsonObject> &log : std::as_const(m_channelHistory))
        all.append(log);
    std::sort(all.begin(), all.end(), [](const QJsonObject &a, const QJsonObject &b) {
        return a.value("ts").toDouble() < b.value("ts").toDouble();
    });

    constexpr qint64 kChunkBudget = 8ll * 1024 * 1024;
    QJsonArray entries;
    qint64 budget = 0;
    auto flush = [&] {
        if (entries.isEmpty())
            return;
        connection->sendMessage({{"type", "history"}, {"entries", entries}});
        entries = QJsonArray();
        budget = 0;
    };
    for (const QJsonObject &m : std::as_const(all)) {
        const qint64 cost = m.value("file").toString().size() +
                            m.value("text").toString().size() + 256;
        if (budget + cost > kChunkBudget)
            flush();
        entries.append(m);
        budget += cost;
    }
    flush();

    QJsonArray reactions;
    for (auto it = m_reactions.constBegin(); it != m_reactions.constEnd(); ++it) {
        for (auto e = it.value().constBegin(); e != it.value().constEnd(); ++e) {
            for (auto r = e.value().constBegin(); r != e.value().constEnd(); ++r) {
                reactions.append(QJsonObject{
                    {"target", it.key()}, {"emoji", e.key()},
                    {"reactorId", r.key()}, {"reactorName", r.value()},
                    {"conversation", m_messageConversation.value(it.key())}});
            }
        }
    }
    if (!reactions.isEmpty())
        connection->sendMessage({{"type", "history"},
                                 {"entries", QJsonArray()},
                                 {"reactions", reactions}});
}

void MeshNode::sendAvatarTo(FramedConnection *connection)
{
    if (m_avatarPng.isEmpty())
        return;
    connection->sendMessage(
        {{"type", "avatar"},
         {"id", QUuid::createUuid().toString(QUuid::WithoutBraces)},
         {"senderId", m_nodeId}, {"name", m_userName},
         {"png", QString::fromLatin1(m_avatarPng.toBase64())}});
}

void MeshNode::sendTyping(const QString &conversation, bool active)
{
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    markSeen(id);
    // Ephemeral: flooded but never stored in history.
    const QJsonObject message{{"type", "typing"}, {"id", id},
                              {"conversation", conversation},
                              {"senderId", m_nodeId}, {"sender", m_userName},
                              {"active", active}};
    flood(message, nullptr, false);
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
        const QJsonObject message{{"type", "channel"}, {"id", id}, {"name", name}};
        flood(message, nullptr, true);
    }
}

void MeshNode::flood(const QJsonObject &message, FramedConnection *exclude,
                     bool showActivity)
{
    int tlsCount = 0;
    for (FramedConnection *peer : std::as_const(m_peers)) {
        if (peer != exclude) {
            peer->sendMessage(message);
            ++tlsCount;
        }
    }
    floodUdp(message);
    if (showActivity) {
        emit systemMessage("Network: sent " + message.value("type").toString() +
                           " to " + QString::number(tlsCount) +
                           " TLS link(s) and " + QString::number(m_known.size()) +
                           " known peer(s) by targeted LAN/UDP.");
    }
}

void MeshNode::sendMessageDatagrams(const QJsonObject &message,
                                    const QList<QHostAddress> &targets,
                                    quint16 peerUdpPort)
{
    if (targets.isEmpty())
        return;

    QJsonObject packet = selfPacketMetadata();
    packet.insert("kind", "message");
    packet.insert("message", message);
    const QByteArray payload = QJsonDocument(packet).toJson(QJsonDocument::Compact);

    auto sendOnce = [this, payload, targets, peerUdpPort] {
        for (const QHostAddress &target : targets) {
            if (m_udp.state() == QAbstractSocket::BoundState) {
                for (quint16 port = kDiscoveryPortBase;
                     port < kDiscoveryPortBase + kDiscoveryPortRange; ++port)
                    m_udp.writeDatagram(payload, target, port);
                if (peerUdpPort > 0)
                    m_udp.writeDatagram(payload, target, peerUdpPort);
            }
            if (m_lanBus.state() == QAbstractSocket::BoundState)
                m_lanBus.writeDatagram(payload, target, kLanBusPort);
        }
    };

    sendOnce();
    for (int delay : kMessageRetryDelaysMs)
        QTimer::singleShot(delay, this, sendOnce);
}

void MeshNode::floodUdp(const QJsonObject &message)
{
    for (const KnownNode &node : std::as_const(m_known)) {
        QList<QHostAddress> targets;
        if (!node.address.isNull())
            targets.append(node.address);
        for (const QHostAddress &address : node.addresses) {
            if (!targets.contains(address))
                targets.append(address);
        }
        sendMessageDatagrams(message, targets, node.udpPort);
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
            m_pendingDials.remove(it.key());
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
    QList<MemberInfo> members{{m_nodeId, m_userName, QString(), true, true}};
    for (auto it = m_peers.constBegin(); it != m_peers.constEnd(); ++it)
        members.append({it.key(), it.value()->remoteName, QString(), false, true});
    // Nodes we can see via discovery but have no link to yet.
    for (auto it = m_known.constBegin(); it != m_known.constEnd(); ++it) {
        if (!m_peers.contains(it.key()))
            members.append({it.key(), it->name,
                            it->udpPort == 0 ? QStringLiteral("(discovered)")
                                             : QString(),
                            false, false});
    }
    emit rosterChanged(members);
    int reachableCount = m_peers.size();
    for (auto it = m_known.constBegin(); it != m_known.constEnd(); ++it) {
        if (!m_peers.contains(it.key()))
            ++reachableCount;
    }
    emit statusChanged(QString::number(reachableCount) +
                       " reachable · IP " + localAddressSummary() + " · UDP " +
                       QString::number(m_udp.localPort()) + " · LAN " +
                       QString::number(kLanBusPort) + " · TCP " +
                       QString::number(m_listener.serverPort()));
}

void MeshNode::shutdown()
{
    // Clean exit: tell everyone we're leaving so they drop us immediately
    // instead of waiting for the discovery timeout.
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QJsonObject bye{{"type", "bye"}, {"id", id},
                          {"senderId", m_nodeId}, {"sender", m_userName}};
    for (FramedConnection *peer : std::as_const(m_peers))
        peer->sendMessage(bye);
    floodUdp(bye);

    m_announceTimer.stop();
    m_pruneTimer.stop();
    m_udp.close();
    m_lanBus.close();
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
