#pragma once

#include <QSslCertificate>
#include <QSslConfiguration>
#include <QSslKey>
#include <QString>

// Per-installation TLS identity. A self-signed certificate is generated on
// first run (via the openssl CLI) and stored in the app data directory, so a
// node keeps a stable identity across restarts.
class SslIdentity
{
public:
    // Loads the identity, generating it first if needed. Returns false and
    // sets errorString() on failure.
    bool load();

    bool isValid() const { return !m_cert.isNull() && !m_key.isNull(); }
    QString errorString() const { return m_error; }

    // Server-side configuration: presents our certificate, does not require
    // one from the peer.
    QSslConfiguration serverConfiguration() const;

    // Client-side configuration: encrypts the channel but skips CA
    // verification, since peers on a LAN use self-signed certificates.
    static QSslConfiguration clientConfiguration();

    // SHA-256 fingerprint of our certificate, e.g. "AB12:CD34:...".
    QString fingerprint() const;

private:
    bool generate(const QString &certPath, const QString &keyPath);

    QSslCertificate m_cert;
    QSslKey m_key;
    QString m_error;
};
