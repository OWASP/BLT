#pragma once

#include <QJsonObject>
#include <QObject>
#include <QSslSocket>

// Wraps an encrypted socket and exchanges length-prefixed JSON messages:
// a 4-byte big-endian payload length followed by a UTF-8 JSON object.
class FramedConnection : public QObject
{
    Q_OBJECT
public:
    // Takes ownership of the socket (reparents it).
    explicit FramedConnection(QSslSocket *socket, QObject *parent = nullptr);

    void sendMessage(const QJsonObject &message);
    void close();
    QSslSocket *socket() const { return m_socket; }

    // Identity of the remote node, filled in once its "hello" arrives.
    QString remoteId;
    QString remoteName;

signals:
    void messageReceived(const QJsonObject &message);
    void closed();

private:
    void onReadyRead();

    static constexpr quint32 kMaxFrame = 1024 * 1024;

    QSslSocket *m_socket;
    QByteArray m_buffer;
};
