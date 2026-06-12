#include "ServerNode.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QJsonArray>
#include <QJsonDocument>
#include <QRandomGenerator>
#include <QSslSocket>
#include <QUuid>

namespace {

constexpr int kSeenCacheLimit = 4096;
constexpr quint64 kMaxWsPayload = 96ull * 1024 * 1024;
constexpr int kMaxDisplayNameChars = 32;
constexpr int kMaxTextChars = 16000;
constexpr int kMaxFileNameChars = 180;
constexpr int kMaxMimeChars = 100;
constexpr qsizetype kMaxFileBytes = 64ll * 1024 * 1024;
constexpr qsizetype kMaxBase64FileChars = 90ll * 1024 * 1024;
constexpr qsizetype kMaxAvatarBytes = 256 * 1024;

QByteArray randomKey()
{
    QByteArray key(16, Qt::Uninitialized);
    for (int i = 0; i < key.size(); ++i)
        key[i] = char(QRandomGenerator::global()->bounded(256));
    return key.toBase64();
}

QString wsPath(const QUrl &url)
{
    QString path = url.path().isEmpty() ? "/" : url.path();
    if (url.hasQuery())
        path += "?" + url.query();
    return path;
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
    return message.value("text").toString().size() <= kMaxTextChars &&
           message.value("sender").toString().size() <= kMaxDisplayNameChars &&
           message.value("fileName").toString().size() <= kMaxFileNameChars &&
           message.value("fileMime").toString().size() <= kMaxMimeChars &&
           message.value("file").toString().size() <= kMaxBase64FileChars &&
           message.value("png").toString().size() <= 4 * kMaxAvatarBytes / 3 + 8;
}

} // namespace

ServerNode::ServerNode(const QString &userName, const QUrl &serverUrl,
                       const QString &roomName, const QString &passphrase,
                       QObject *parent)
    : ChatBackend(parent),
      m_userName(userName),
      m_url(serverUrl),
      m_roomName(roomName.trimmed()),
      m_nodeId(QUuid::createUuid().toString(QUuid::WithoutBraces)),
      m_crypto(m_roomName, passphrase)
{
}

bool ServerNode::start()
{
    if (!m_crypto.isValid()) {
        emit fatalError(m_crypto.errorString());
        return false;
    }
    if (!m_url.isValid() || (m_url.scheme() != "ws" && m_url.scheme() != "wss")) {
        emit fatalError("Enter a ws:// or wss:// server URL.");
        return false;
    }
    if (m_roomName.isEmpty()) {
        emit fatalError("Enter a room name.");
        return false;
    }

    m_socket = m_url.scheme() == "wss" ? new QSslSocket(this) : new QTcpSocket(this);
    connectSocketSignals();
    const int port = m_url.port(m_url.scheme() == "wss" ? 443 : 80);
    emit statusChanged("Connecting to " + m_url.host() + "...");
    if (auto *ssl = qobject_cast<QSslSocket *>(m_socket))
        ssl->connectToHostEncrypted(m_url.host(), port);
    else
        m_socket->connectToHost(m_url.host(), port);
    return true;
}

void ServerNode::connectSocketSignals()
{
    connect(m_socket, &QTcpSocket::readyRead, this, &ServerNode::onSocketReadyRead);
    connect(m_socket, &QTcpSocket::connected, this, [this] {
        if (!qobject_cast<QSslSocket *>(m_socket))
            onConnectedTransport();
    });
    if (auto *ssl = qobject_cast<QSslSocket *>(m_socket))
        connect(ssl, &QSslSocket::encrypted, this, &ServerNode::onConnectedTransport);
    connect(m_socket, &QTcpSocket::disconnected, this, [this] {
        emit statusChanged("Disconnected from server");
        for (auto it = m_peers.begin(); it != m_peers.end(); ++it)
            it->online = false;
        updateRosterAndStatus();
    });
    connect(m_socket, &QTcpSocket::errorOccurred, this, [this] {
        emit systemMessage("Server socket error: " + m_socket->errorString());
    });
}

void ServerNode::onConnectedTransport()
{
    sendHandshake();
}

void ServerNode::sendHandshake()
{
    m_wsKey = randomKey();
    QByteArray host = m_url.host().toUtf8();
    if (m_url.port() > 0)
        host += ":" + QByteArray::number(m_url.port());
    const QByteArray request =
        "GET " + wsPath(m_url).toUtf8() + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Sec-WebSocket-Key: " + m_wsKey + "\r\n\r\n";
    m_socket->write(request);
}

void ServerNode::onSocketReadyRead()
{
    m_readBuffer += m_socket->readAll();
    if (!m_wsReady) {
        const int headerEnd = m_readBuffer.indexOf("\r\n\r\n");
        if (headerEnd < 0)
            return;
        const QByteArray header = m_readBuffer.left(headerEnd);
        m_readBuffer.remove(0, headerEnd + 4);
        if (!header.startsWith("HTTP/1.1 101") && !header.startsWith("HTTP/1.0 101")) {
            emit fatalError("Server did not accept the WebSocket upgrade.");
            return;
        }
        m_wsReady = true;
        emit channelsChanged(m_channels);
        updateRosterAndStatus();
        emit statusChanged("Connected to encrypted server room " + m_roomName);
        sendHello();
        if (!m_avatarPng.isEmpty())
            setAvatar(m_avatarPng);
    }

    while (m_readBuffer.size() >= 2) {
        const uchar b0 = uchar(m_readBuffer.at(0));
        const uchar b1 = uchar(m_readBuffer.at(1));
        const int opcode = b0 & 0x0f;
        quint64 len = b1 & 0x7f;
        int pos = 2;
        if (len == 126) {
            if (m_readBuffer.size() < pos + 2)
                return;
            len = (uchar(m_readBuffer.at(pos)) << 8) | uchar(m_readBuffer.at(pos + 1));
            pos += 2;
        } else if (len == 127) {
            if (m_readBuffer.size() < pos + 8)
                return;
            len = 0;
            for (int i = 0; i < 8; ++i)
                len = (len << 8) | uchar(m_readBuffer.at(pos + i));
            pos += 8;
        }
        if (len > kMaxWsPayload) {
            emit systemMessage("Server frame exceeded the safe size limit; disconnecting.");
            m_socket->disconnectFromHost();
            return;
        }
        const bool masked = b1 & 0x80;
        QByteArray mask;
        if (masked) {
            if (m_readBuffer.size() < pos + 4)
                return;
            mask = m_readBuffer.mid(pos, 4);
            pos += 4;
        }
        if (m_readBuffer.size() < pos + int(len))
            return;
        QByteArray payload = m_readBuffer.mid(pos, int(len));
        m_readBuffer.remove(0, pos + int(len));
        if (masked) {
            for (int i = 0; i < payload.size(); ++i)
                payload[i] = payload.at(i) ^ mask.at(i % 4);
        }
        if (opcode == 0x8) {
            m_socket->disconnectFromHost();
            return;
        }
        if (opcode == 0x1)
            processFrame(payload);
    }
}

void ServerNode::processFrame(const QByteArray &payload)
{
    if (quint64(payload.size()) > kMaxWsPayload)
        return;
    const QJsonDocument doc = QJsonDocument::fromJson(payload);
    if (!doc.isObject())
        return;
    const QJsonObject plain = m_crypto.decryptObject(doc.object());
    if (plain.isEmpty() || plain.value("senderId").toString() == m_nodeId)
        return;
    handlePlain(plain);
}

void ServerNode::sendTextFrame(const QByteArray &payload)
{
    if (!m_wsReady || !m_socket)
        return;
    if (quint64(payload.size()) > kMaxWsPayload) {
        emit systemMessage("Message exceeded the safe server frame limit and was not sent.");
        return;
    }
    QByteArray frame;
    frame.append(char(0x81));
    if (payload.size() < 126) {
        frame.append(char(0x80 | payload.size()));
    } else if (payload.size() <= 0xffff) {
        frame.append(char(0x80 | 126));
        frame.append(char((payload.size() >> 8) & 0xff));
        frame.append(char(payload.size() & 0xff));
    } else {
        frame.append(char(0x80 | 127));
        quint64 len = payload.size();
        for (int i = 7; i >= 0; --i)
            frame.append(char((len >> (8 * i)) & 0xff));
    }
    QByteArray mask(4, Qt::Uninitialized);
    for (int i = 0; i < 4; ++i)
        mask[i] = char(QRandomGenerator::global()->bounded(256));
    frame.append(mask);
    QByteArray masked = payload;
    for (int i = 0; i < masked.size(); ++i)
        masked[i] = masked.at(i) ^ mask.at(i % 4);
    frame.append(masked);
    m_socket->write(frame);
}

QJsonObject ServerNode::makeMessage(const QString &type) const
{
    return {{"type", type},
            {"id", QUuid::createUuid().toString(QUuid::WithoutBraces)},
            {"senderId", m_nodeId},
            {"sender", m_userName.left(kMaxDisplayNameChars)},
            {"ts", double(QDateTime::currentMSecsSinceEpoch())}};
}

void ServerNode::sendEncrypted(const QJsonObject &plain, bool showActivity)
{
    QJsonObject envelope = m_crypto.encryptObject(plain);
    if (envelope.isEmpty()) {
        emit systemMessage("Server encryption failed; message was not sent.");
        return;
    }
    sendTextFrame(QJsonDocument(envelope).toJson(QJsonDocument::Compact));
    if (showActivity)
        emit systemMessage("Network: sent encrypted " + plain.value("type").toString() +
                           " through server room " + m_roomName + ".");
}

void ServerNode::sendHello()
{
    QJsonArray channels;
    for (const QString &channel : std::as_const(m_channels))
        channels.append(channel);
    QJsonObject hello = makeMessage("hello");
    hello.insert("channels", channels);
    sendEncrypted(hello, true);
}

void ServerNode::sendChat(const QString &channel, const QString &text)
{
    if (text.trimmed().isEmpty())
        return;
    QJsonObject message = makeMessage("chat");
    message.insert("channel", channel);
    message.insert("text", text.left(kMaxTextChars));
    markSeen(message.value("id").toString());
    storeHistory(message);
    sendEncrypted(message, true);
    emitChat(message);
}

void ServerNode::sendDirect(const QString &targetId, const QString &text)
{
    if (text.trimmed().isEmpty() || targetId == m_nodeId)
        return;
    QJsonObject message = makeMessage("dm");
    message.insert("to", targetId);
    message.insert("text", text.left(kMaxTextChars));
    markSeen(message.value("id").toString());
    sendEncrypted(message, true);
    emitDm(message, targetId);
}

void ServerNode::sendFile(const QString &conversation, const QString &fileName,
                          const QString &mimeType, const QByteArray &data)
{
    if (fileName.isEmpty() || data.isEmpty() || data.size() > kMaxFileBytes)
        return;
    if (conversation.startsWith('@')) {
        QJsonObject message = makeMessage("dm");
        message.insert("to", conversation.mid(1));
        message.insert("fileName", safeFileName(fileName));
        message.insert("fileMime", mimeType.left(kMaxMimeChars));
        message.insert("file", QString::fromLatin1(data.toBase64()));
        markSeen(message.value("id").toString());
        sendEncrypted(message, true);
        emitDm(message, conversation.mid(1));
    } else {
        QJsonObject message = makeMessage("chat");
        message.insert("channel", conversation);
        message.insert("fileName", safeFileName(fileName));
        message.insert("fileMime", mimeType.left(kMaxMimeChars));
        message.insert("file", QString::fromLatin1(data.toBase64()));
        markSeen(message.value("id").toString());
        storeHistory(message);
        sendEncrypted(message, true);
        emitChat(message);
    }
}

void ServerNode::sendReaction(const QString &conversation, const QString &messageId,
                              const QString &emoji)
{
    if (messageId.isEmpty() || emoji.isEmpty())
        return;
    const bool added =
        !m_reactions.value(messageId).value(emoji).contains(m_nodeId);
    QJsonObject message = makeMessage("reaction");
    message.insert("conversation", conversation);
    message.insert("target", messageId);
    message.insert("emoji", emoji);
    message.insert("reactorId", m_nodeId);
    message.insert("reactorName", m_userName);
    message.insert("added", added);
    markSeen(message.value("id").toString());
    handlePlain(message);
    sendEncrypted(message, false);
}

void ServerNode::setAvatar(const QByteArray &pngData)
{
    if (pngData.size() > kMaxAvatarBytes)
        return;
    m_avatarPng = pngData;
    QJsonObject message = makeMessage("avatar");
    message.insert("png", QString::fromLatin1(pngData.toBase64()));
    markSeen(message.value("id").toString());
    emit avatarChanged(m_nodeId, pngData);
    sendEncrypted(message, false);
}

void ServerNode::sendTyping(const QString &conversation, bool active)
{
    QJsonObject message = makeMessage("typing");
    message.insert("conversation", conversation);
    message.insert("active", active);
    sendEncrypted(message, false);
}

void ServerNode::addChannel(const QString &channel)
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
    QJsonObject message = makeMessage("channel");
    message.insert("name", name);
    markSeen(message.value("id").toString());
    sendEncrypted(message, true);
}

void ServerNode::shutdown()
{
    QJsonObject bye = makeMessage("bye");
    sendEncrypted(bye, true);
    if (m_socket) {
        m_socket->disconnectFromHost();
        m_socket->deleteLater();
        m_socket = nullptr;
    }
}

void ServerNode::handlePlain(const QJsonObject &message)
{
    if (!messageHasSafePayload(message)) {
        emit systemMessage("Dropped oversized or unsafe server payload.");
        return;
    }
    const QString type = message.value("type").toString();
    if (type != "typing" && !markSeen(message.value("id").toString()))
        return;
    const QString senderId = message.value("senderId").toString();
    const QString sender = message.value("sender").toString();
    if (!senderId.isEmpty())
        rememberPeer(senderId, sender);

    if (type == "hello") {
        bool changed = false;
        for (const auto &value : message.value("channels").toArray()) {
            const QString channel = value.toString();
            if (!channel.isEmpty() && !m_channels.contains(channel)) {
                m_channels.append(channel);
                changed = true;
            }
        }
        if (changed)
            emit channelsChanged(m_channels);
        sendHistoryTo(senderId);
    } else if (type == "chat") {
        if (!m_channels.contains(message.value("channel").toString()))
            m_channels.append(message.value("channel").toString());
        storeHistory(message);
        emitChat(message);
    } else if (type == "dm") {
        const QString to = message.value("to").toString();
        if (to == m_nodeId)
            emitDm(message, senderId);
    } else if (type == "channel") {
        const QString name = message.value("name").toString();
        if (!m_channels.contains(name)) {
            m_channels.append(name);
            emit channelsChanged(m_channels);
        }
    } else if (type == "reaction") {
        const QString target = message.value("target").toString();
        const QString emoji = message.value("emoji").toString();
        const QString reactorId = message.value("reactorId").toString();
        const QString reactorName = message.value("reactorName").toString();
        if (message.value("added").toBool())
            m_reactions[target][emoji].insert(reactorId, reactorName);
        else
            m_reactions[target][emoji].remove(reactorId);
        emit reactionChanged(message.value("conversation").toString(), target,
                             emoji, reactorName, message.value("added").toBool());
    } else if (type == "avatar") {
        const QByteArray avatar =
            boundedBase64(message, "png", 4 * kMaxAvatarBytes / 3 + 8,
                          kMaxAvatarBytes);
        if (!avatar.isEmpty())
            emit avatarChanged(senderId, avatar);
    } else if (type == "typing") {
        emit typingChanged(message.value("conversation").toString(), senderId,
                           sender, message.value("active").toBool());
    } else if (type == "history") {
        if (!message.value("to").toString().isEmpty() &&
            message.value("to").toString() != m_nodeId)
            return;
        for (const auto &value : message.value("entries").toArray()) {
            const QJsonObject entry = value.toObject();
            if (!messageHasSafePayload(entry))
                continue;
            if (markSeen(entry.value("id").toString())) {
                storeHistory(entry);
                emitChat(entry);
            }
        }
    } else if (type == "bye") {
        if (m_peers.contains(senderId)) {
            m_peers[senderId].online = false;
            emit systemMessage(sender + " left");
            updateRosterAndStatus();
        }
    }
}

void ServerNode::sendHistoryTo(const QString &peerId)
{
    if (peerId.isEmpty() || m_channelHistory.isEmpty())
        return;
    QJsonArray entries;
    for (const QList<QJsonObject> &history : std::as_const(m_channelHistory)) {
        for (const QJsonObject &entry : history)
            entries.append(entry);
    }
    QJsonObject message = makeMessage("history");
    message.insert("to", peerId);
    message.insert("entries", entries);
    sendEncrypted(message, false);
}

void ServerNode::emitChat(const QJsonObject &message)
{
    ChatMessage out;
    out.id = message.value("id").toString();
    out.conversation = message.value("channel").toString();
    out.senderId = message.value("senderId").toString();
    out.senderName = boundedText(message, "sender", kMaxDisplayNameChars);
    out.text = boundedText(message, "text", kMaxTextChars);
    out.timestampMs = qint64(message.value("ts").toDouble());
    out.fileName = safeFileName(message.value("fileName").toString());
    if (out.fileName == "file" && !message.contains("fileName"))
        out.fileName.clear();
    out.fileMime = boundedText(message, "fileMime", kMaxMimeChars);
    if (message.contains("file"))
        out.fileData = boundedBase64(message, "file", kMaxBase64FileChars, kMaxFileBytes);
    m_messageConversation.insert(out.id, out.conversation);
    emit messageArrived(out);
}

void ServerNode::emitDm(const QJsonObject &message, const QString &conversationPeer)
{
    ChatMessage out;
    out.id = message.value("id").toString();
    out.conversation = "@" + conversationPeer;
    out.senderId = message.value("senderId").toString();
    out.senderName = boundedText(message, "sender", kMaxDisplayNameChars);
    out.text = boundedText(message, "text", kMaxTextChars);
    out.timestampMs = qint64(message.value("ts").toDouble());
    out.fileName = safeFileName(message.value("fileName").toString());
    if (out.fileName == "file" && !message.contains("fileName"))
        out.fileName.clear();
    out.fileMime = boundedText(message, "fileMime", kMaxMimeChars);
    if (message.contains("file"))
        out.fileData = boundedBase64(message, "file", kMaxBase64FileChars, kMaxFileBytes);
    m_messageConversation.insert(out.id, out.conversation);
    emit messageArrived(out);
}

void ServerNode::rememberPeer(const QString &peerId, const QString &name, bool online)
{
    if (peerId.isEmpty() || peerId == m_nodeId)
        return;
    Peer &peer = m_peers[peerId];
    peer.name = name.isEmpty() ? peer.name : name;
    peer.online = online;
    peer.lastSeenMs = QDateTime::currentMSecsSinceEpoch();
    updateRosterAndStatus();
}

void ServerNode::updateRosterAndStatus()
{
    QList<MemberInfo> members{{m_nodeId, m_userName, QString(), true, m_wsReady}};
    for (auto it = m_peers.constBegin(); it != m_peers.constEnd(); ++it)
        members.append({it.key(), it->name, QString(), false, it->online});
    emit rosterChanged(members);
    emit statusChanged(QString::number(m_peers.size()) +
                       " server peer(s) · encrypted room " + m_roomName);
}

void ServerNode::storeHistory(const QJsonObject &message)
{
    const QString channel = message.value("channel").toString();
    if (!channel.isEmpty())
        m_channelHistory[channel].append(message);
}

bool ServerNode::markSeen(const QString &messageId)
{
    if (messageId.isEmpty() || m_seenIds.contains(messageId))
        return false;
    m_seenIds.insert(messageId);
    m_seenOrder.enqueue(messageId);
    while (m_seenOrder.size() > kSeenCacheLimit)
        m_seenIds.remove(m_seenOrder.dequeue());
    return true;
}
