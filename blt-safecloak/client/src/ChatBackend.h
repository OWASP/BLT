#pragma once

#include <QByteArray>
#include <QList>
#include <QObject>
#include <QString>
#include <QStringList>

// A chat participant as shown in the member list. `id` is the stable node id
// used to address direct messages.
struct MemberInfo {
    QString id;
    QString name;
    QString note;     // e.g. "(discovered)"
    bool self = false;
    bool online = false; // live link right now (green dot)
};

// A single chat message delivered to the UI. `conversation` is either a
// channel ("#general") or a direct chat keyed by the other party ("@<peerId>").
// A message may carry text, a file attachment, or both.
struct ChatMessage {
    QString id;
    QString conversation;
    QString senderId;
    QString senderName;
    QString text;
    qint64 timestampMs = 0;
    QString fileName;   // non-empty => has a file attachment
    QString fileMime;
    QByteArray fileData;

    bool hasFile() const { return !fileName.isEmpty(); }
};

// Common interface for chat networking. The desktop app runs as a mesh-only
// LAN node; keeping the interface small keeps the UI decoupled from it.
class ChatBackend : public QObject
{
    Q_OBJECT
public:
    using QObject::QObject;

    virtual void sendChat(const QString &channel, const QString &text) = 0;
    // Direct (one-to-one) message to the member with the given id.
    virtual void sendDirect(const QString &targetId, const QString &text) = 0;
    // Share a file in a conversation ("#channel" or "@peerId").
    virtual void sendFile(const QString &conversation, const QString &fileName,
                          const QString &mimeType, const QByteArray &data) = 0;
    // Toggle an emoji reaction on a previously seen message.
    virtual void sendReaction(const QString &conversation, const QString &messageId,
                              const QString &emoji) = 0;
    // Publish this node's avatar (PNG bytes; empty clears it).
    virtual void setAvatar(const QByteArray &pngData) = 0;
    // Tell peers we started/stopped typing in a conversation.
    virtual void sendTyping(const QString &conversation, bool active) = 0;
    virtual void addChannel(const QString &channel) = 0;
    virtual void shutdown() = 0;
    virtual QString modeName() const = 0;

signals:
    // A chat or direct message to display (includes our own messages, and
    // replayed history from peers).
    void messageArrived(const ChatMessage &message);
    // An emoji reaction was added or removed on a message.
    void reactionChanged(const QString &conversation, const QString &messageId,
                         const QString &emoji, const QString &reactorName, bool added);
    // A peer's avatar became available or changed (PNG bytes).
    void avatarChanged(const QString &peerId, const QByteArray &pngData);
    // A peer started (active=true) or stopped typing in a conversation.
    void typingChanged(const QString &conversation, const QString &peerId,
                       const QString &peerName, bool active);
    // Diagnostic/log line (discovery, dials, errors). Shown in Settings, not chat.
    void systemMessage(const QString &text);
    // A host firewall is blocking SafeCloak's inbound ports. `displayCommand`
    // is the terminal command to fix it; `privilegedCommand` is the same
    // without sudo, for the UI to run via pkexec when the user clicks "Allow".
    void firewallBlocking(const QString &displayCommand,
                          const QString &privilegedCommand);
    void channelsChanged(const QStringList &channels);
    void rosterChanged(const QList<MemberInfo> &members);
    // Short status line for the UI.
    void statusChanged(const QString &status);
    // Unrecoverable failure; the UI returns to the setup screen.
    void fatalError(const QString &message);
};
