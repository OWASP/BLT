#pragma once

#include <QObject>
#include <QStringList>

// Common interface for the three networking modes (host, client, mesh) so the
// UI does not care which one is active.
class ChatBackend : public QObject
{
    Q_OBJECT
public:
    using QObject::QObject;

    virtual void sendChat(const QString &channel, const QString &text) = 0;
    virtual void addChannel(const QString &channel) = 0;
    virtual void shutdown() = 0;
    virtual QString modeName() const = 0;

signals:
    // A chat message to display (includes our own messages).
    void chatMessage(const QString &channel, const QString &sender,
                     const QString &text, qint64 timestampMs);
    void systemMessage(const QString &text);
    void channelsChanged(const QStringList &channels);
    void rosterChanged(const QStringList &members);
    // Short status line for the UI, e.g. "Listening on port 47800".
    void statusChanged(const QString &status);
    // Unrecoverable failure; the UI returns to the setup screen.
    void fatalError(const QString &message);
};
