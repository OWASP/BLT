#pragma once

#include "ChatBackend.h"
#include "SslIdentity.h"

#include <QElapsedTimer>
#include <QHash>
#include <QJsonObject>
#include <QQueue>
#include <QSet>
#include <QSslServer>
#include <QTimer>
#include <QUdpSocket>

class FramedConnection;

// Mesh mode: no central server. Every node announces itself over UDP
// broadcast, opens TLS connections to discovered peers, and floods chat
// messages through the mesh. Message IDs are deduplicated so floods
// terminate even when the connection graph has cycles.
class MeshNode : public ChatBackend
{
    Q_OBJECT
public:
    // Each instance binds the first free port in this range, so several
    // instances can run on one machine and still address each other directly.
    static constexpr quint16 kDiscoveryPortBase = 45454;
    static constexpr quint16 kDiscoveryPortRange = 10;

    MeshNode(const SslIdentity &identity, const QString &userName,
             QObject *parent = nullptr);

    bool start();

    void sendChat(const QString &channel, const QString &text) override;
    void sendDirect(const QString &targetId, const QString &text) override;
    void addChannel(const QString &channel) override;
    void shutdown() override;
    QString modeName() const override { return "Mesh"; }

private:
    struct KnownNode {
        QString name;
        QHostAddress address;
        quint16 tcpPort = 0;
        qint64 firstSeenMs = 0;
        qint64 lastSeenMs = 0;
        qint64 lastIntroSentMs = 0; // throttles unicast introductions
    };

    QByteArray announcePayload() const;
    void sendAnnounce();
    void onDatagram();
    void onIncomingConnection();
    void adoptConnection(FramedConnection *connection);
    void onPeerMessage(FramedConnection *connection, const QJsonObject &message);
    void onPeerClosed(FramedConnection *connection);
    void connectToPeer(const QString &nodeId, const KnownNode &node);
    void flood(const QJsonObject &message, FramedConnection *exclude = nullptr);
    bool markSeen(const QString &messageId);
    void prune();
    void updateRosterAndStatus();
    void mergeChannel(const QString &channel, bool announce);

    SslIdentity m_identity;
    QString m_userName;
    QString m_nodeId;

    QSslServer m_listener;
    QUdpSocket m_udp;
    QTimer m_announceTimer;
    QTimer m_pruneTimer;

    QHash<QString, KnownNode> m_known;            // nodeId -> last announcement
    QHash<QString, FramedConnection *> m_peers;   // nodeId -> live link
    QSet<QString> m_pendingDials;                 // nodeIds we are connecting to
    QList<FramedConnection *> m_handshaking;      // accepted, no hello yet

    QSet<QString> m_seenIds;
    QQueue<QString> m_seenOrder;
    QStringList m_channels{"#general", "#random"};
};
