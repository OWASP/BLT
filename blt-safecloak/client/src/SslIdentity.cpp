#include "SslIdentity.h"

#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QProcess>
#include <QSslSocket>
#include <QStandardPaths>

bool SslIdentity::load()
{
    const QString dir =
        QStandardPaths::writableLocation(QStandardPaths::AppDataLocation) + "/tls";
    if (!QDir().mkpath(dir)) {
        m_error = "Could not create TLS key directory: " + dir;
        return false;
    }

    const QString certPath = dir + "/cert.pem";
    const QString keyPath = dir + "/key.pem";

    if (!QFile::exists(certPath) || !QFile::exists(keyPath)) {
        if (!generate(certPath, keyPath))
            return false;
    }

    QFile certFile(certPath);
    QFile keyFile(keyPath);
    if (!certFile.open(QIODevice::ReadOnly) || !keyFile.open(QIODevice::ReadOnly)) {
        m_error = "Could not read TLS certificate or key from " + dir;
        return false;
    }

    m_cert = QSslCertificate(certFile.readAll(), QSsl::Pem);
    m_key = QSslKey(keyFile.readAll(), QSsl::Rsa, QSsl::Pem);
    if (m_cert.isNull() || m_key.isNull()) {
        m_error = "Stored TLS certificate or key is invalid. "
                  "Delete " + dir + " and restart to regenerate.";
        return false;
    }
    return true;
}

bool SslIdentity::generate(const QString &certPath, const QString &keyPath)
{
    QProcess openssl;
    openssl.start("openssl",
                  {"req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes",
                   "-days", "3650", "-subj", "/CN=SafeCloak Chat Node",
                   "-keyout", keyPath, "-out", certPath});
    if (!openssl.waitForStarted(5000)) {
        m_error = "Could not run 'openssl' to generate a TLS certificate. "
                  "Please install OpenSSL.";
        return false;
    }
    if (!openssl.waitForFinished(30000) || openssl.exitCode() != 0) {
        m_error = "Certificate generation failed: " +
                  QString::fromUtf8(openssl.readAllStandardError());
        return false;
    }
    QFile::setPermissions(keyPath, QFile::ReadOwner | QFile::WriteOwner);
    return true;
}

QSslConfiguration SslIdentity::serverConfiguration() const
{
    QSslConfiguration cfg = QSslConfiguration::defaultConfiguration();
    cfg.setLocalCertificate(m_cert);
    cfg.setPrivateKey(m_key);
    cfg.setPeerVerifyMode(QSslSocket::VerifyNone);
    cfg.setProtocol(QSsl::TlsV1_2OrLater);
    return cfg;
}

QSslConfiguration SslIdentity::clientConfiguration()
{
    QSslConfiguration cfg = QSslConfiguration::defaultConfiguration();
    cfg.setPeerVerifyMode(QSslSocket::VerifyNone);
    cfg.setProtocol(QSsl::TlsV1_2OrLater);
    return cfg;
}

QString SslIdentity::fingerprint() const
{
    const QByteArray digest = m_cert.digest(QCryptographicHash::Sha256);
    QString out;
    for (int i = 0; i < digest.size(); ++i) {
        if (i)
            out += ':';
        out += QString("%1").arg(quint8(digest[i]), 2, 16, QChar('0')).toUpper();
    }
    return out;
}
