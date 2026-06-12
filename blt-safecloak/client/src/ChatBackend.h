#pragma once

#include <QList>
#include <QObject>
#include <QString>
#include <QStringList>

// A chat participant as shown in the member list. `id` is the stable node id
// used to address direct messages.
struct MemberInfo {
    QString id;
    QString name;
    QString note;     // e.g. "(host)" or "(discovered)"
    bool self = false;
};

// Common interface for chat networking. The desktop app currently runs as a
// mesh-only LAN node, but keeping the interface small keeps UI code decoupled.
class ChatBackend : public QObject
{
    Q_OBJECT
public:
    using QObject::QObject;

    virtual void sendChat(const QString &channel, const QString &text) = 0;
    // Direct (one-to-one) message to the member with the given id.
    virtual void sendDirect(const QString &targetId, const QString &text) = 0;
    virtual void addChannel(const QString &channel) = 0;
    virtual void shutdown() = 0;
    virtual QString modeName() const = 0;

signals:
    // A chat message to display (includes our own messages).
    void chatMessage(const QString &channel, const QString &sender,
                     const QString &text, qint64 timestampMs);
    // A direct message in the conversation with `peerId` (includes our own;
    // `sender` tells the UI who wrote it).
    void directMessage(const QString &peerId, const QString &peerName,
                       const QString &sender, const QString &text,
                       qint64 timestampMs);
    void systemMessage(const QString &text);
    void channelsChanged(const QStringList &channels);
    void rosterChanged(const QList<MemberInfo> &members);
    // Short status line for the UI, e.g. "Listening on port 47800".
    void statusChanged(const QString &status);
    // Unrecoverable failure; the UI returns to the setup screen.
    void fatalError(const QString &message);
};
