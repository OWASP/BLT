#pragma once

#include "ChatBackend.h"
#include "RoomCrypto.h"

#include <QHash>
#include <QJsonObject>
#include <QQueue>
#include <QSet>
#include <QTcpSocket>
#include <QUrl>

class ServerNode : public ChatBackend
{
    Q_OBJECT
public:
    ServerNode(const QString &userName, const QUrl &serverUrl,
               const QString &roomName, const QString &passphrase,
               QObject *parent = nullptr);

    bool start();

    void sendChat(const QString &channel, const QString &text) override;
    void sendDirect(const QString &targetId, const QString &text) override;
    void sendFile(const QString &conversation, const QString &fileName,
                  const QString &mimeType, const QByteArray &data) override;
    void sendReaction(const QString &conversation, const QString &messageId,
                      const QString &emoji) override;
    void editMessage(const QString &conversation, const QString &messageId,
                     const QString &newText) override;
    void deleteMessage(const QString &conversation, const QString &messageId) override;
    void setAvatar(const QByteArray &pngData) override;
    void sendTyping(const QString &conversation, bool active) override;
    void addChannel(const QString &channel) override;
    void shutdown() override;
    QString modeName() const override { return "Server"; }

private:
    struct Peer {
        QString name;
        qint64 lastSeenMs = 0;
        bool online = true;
    };

    void connectSocketSignals();
    void sendHandshake();
    void onSocketReadyRead();
    void onConnectedTransport();
    void processFrame(const QByteArray &payload);
    void sendTextFrame(const QByteArray &payload);
    void sendEncrypted(const QJsonObject &plain, bool showActivity = false);
    void sendHello();
    void sendHistoryTo(const QString &peerId);
    void handlePlain(const QJsonObject &message);
    void emitChat(const QJsonObject &message);
    void emitDm(const QJsonObject &message, const QString &conversationPeer);
    void rememberPeer(const QString &peerId, const QString &name, bool online = true);
    void updateRosterAndStatus();
    void storeHistory(const QJsonObject &message);
    void updateStoredMessage(const QString &messageId, const QString &text, bool deleted);
    bool messageIsAuthoredBy(const QString &messageId, const QString &senderId) const;
    void applyEdit(const QString &conversation, const QString &target,
                   const QString &senderId, const QString &text);
    void applyDelete(const QString &conversation, const QString &target,
                     const QString &senderId);
    bool markSeen(const QString &messageId);
    QJsonObject makeMessage(const QString &type) const;

    QString m_userName;
    QUrl m_url;
    QString m_roomName;
    QString m_nodeId;
    RoomCrypto m_crypto;
    QTcpSocket *m_socket = nullptr;
    QByteArray m_readBuffer;
    QByteArray m_wsKey;
    bool m_wsReady = false;

    QStringList m_channels{"#general", "#random"};
    QHash<QString, Peer> m_peers;
    QHash<QString, QList<QJsonObject>> m_channelHistory;
    QHash<QString, QString> m_messageConversation;
    QHash<QString, QString> m_messageSender;
    QHash<QString, QHash<QString, QHash<QString, QString>>> m_reactions;
    QByteArray m_avatarPng;
    QSet<QString> m_seenIds;
    QQueue<QString> m_seenOrder;
};
