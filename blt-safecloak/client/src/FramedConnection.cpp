#include "FramedConnection.h"

#include <QJsonDocument>
#include <QtEndian>

FramedConnection::FramedConnection(QSslSocket *socket, QObject *parent)
    : QObject(parent), m_socket(socket)
{
    m_socket->setParent(this);
    connect(m_socket, &QSslSocket::readyRead, this, &FramedConnection::onReadyRead);
    connect(m_socket, &QSslSocket::disconnected, this, &FramedConnection::closed);
    connect(m_socket, &QSslSocket::errorOccurred, this,
            [this](QAbstractSocket::SocketError) { emit closed(); });
}

void FramedConnection::sendMessage(const QJsonObject &message)
{
    if (m_socket->state() != QAbstractSocket::ConnectedState)
        return;
    const QByteArray payload = QJsonDocument(message).toJson(QJsonDocument::Compact);
    QByteArray frame(4, Qt::Uninitialized);
    qToBigEndian<quint32>(quint32(payload.size()), frame.data());
    frame.append(payload);
    m_socket->write(frame);
}

void FramedConnection::close()
{
    m_socket->disconnect(this);
    m_socket->abort();
}

void FramedConnection::onReadyRead()
{
    m_buffer.append(m_socket->readAll());
    while (true) {
        if (m_buffer.size() < 4)
            return;
        const quint32 length = qFromBigEndian<quint32>(m_buffer.constData());
        if (length > kMaxFrame) {
            m_socket->abort();
            return;
        }
        if (quint32(m_buffer.size()) < 4 + length)
            return;
        const QJsonDocument doc = QJsonDocument::fromJson(m_buffer.mid(4, length));
        m_buffer.remove(0, 4 + length);
        if (doc.isObject())
            emit messageReceived(doc.object());
    }
}
