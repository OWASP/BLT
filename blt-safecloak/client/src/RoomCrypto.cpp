#include "RoomCrypto.h"

#include <QCryptographicHash>
#include <QJsonDocument>
#include <QRandomGenerator>

#include <openssl/evp.h>
#include <openssl/rand.h>

namespace {

constexpr int kKeyBytes = 32;
constexpr int kNonceBytes = 12;
constexpr int kTagBytes = 16;
constexpr int kPbkdfRounds = 210000;
constexpr qsizetype kMaxPlainBytes = 96ll * 1024 * 1024;

QByteArray saltForRoom(const QString &roomName)
{
    return QCryptographicHash::hash("SafeCloak room:" + roomName.toUtf8(),
                                    QCryptographicHash::Sha256)
        .left(16);
}

QByteArray randomBytes(int count)
{
    QByteArray out(count, Qt::Uninitialized);
    if (RAND_bytes(reinterpret_cast<unsigned char *>(out.data()), count) != 1) {
        for (int i = 0; i < count; ++i)
            out[i] = char(QRandomGenerator::global()->bounded(256));
    }
    return out;
}

} // namespace

RoomCrypto::RoomCrypto(const QString &roomName, const QString &passphrase)
{
    if (roomName.trimmed().isEmpty() || passphrase.isEmpty()) {
        m_error = "Room name and passphrase are required.";
        return;
    }
    m_key.resize(kKeyBytes);
    const QByteArray pass = passphrase.toUtf8();
    const QByteArray salt = saltForRoom(roomName.trimmed());
    if (PKCS5_PBKDF2_HMAC(pass.constData(), pass.size(),
                          reinterpret_cast<const unsigned char *>(salt.constData()),
                          salt.size(), kPbkdfRounds, EVP_sha256(), kKeyBytes,
                          reinterpret_cast<unsigned char *>(m_key.data())) != 1) {
        m_key.clear();
        m_error = "Could not derive the room encryption key.";
    }
}

QJsonObject RoomCrypto::encryptObject(const QJsonObject &plain) const
{
    if (m_key.isEmpty())
        return {};

    const QByteArray nonce = randomBytes(kNonceBytes);
    const QByteArray input = QJsonDocument(plain).toJson(QJsonDocument::Compact);
    if (input.size() > kMaxPlainBytes)
        return {};
    QByteArray cipher(input.size() + kTagBytes, Qt::Uninitialized);
    QByteArray tag(kTagBytes, Qt::Uninitialized);

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    int len = 0;
    int outLen = 0;
    if (!ctx ||
        EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) != 1 ||
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, nonce.size(), nullptr) != 1 ||
        EVP_EncryptInit_ex(ctx, nullptr, nullptr,
                           reinterpret_cast<const unsigned char *>(m_key.constData()),
                           reinterpret_cast<const unsigned char *>(nonce.constData())) != 1 ||
        EVP_EncryptUpdate(ctx, reinterpret_cast<unsigned char *>(cipher.data()), &len,
                          reinterpret_cast<const unsigned char *>(input.constData()),
                          input.size()) != 1) {
        if (ctx)
            EVP_CIPHER_CTX_free(ctx);
        return {};
    }
    outLen = len;
    if (EVP_EncryptFinal_ex(ctx,
                            reinterpret_cast<unsigned char *>(cipher.data()) + outLen,
                            &len) != 1 ||
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, tag.size(), tag.data()) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        return {};
    }
    outLen += len;
    EVP_CIPHER_CTX_free(ctx);
    cipher.resize(outLen);

    return {{"kind", "cipher"},
            {"v", 1},
            {"nonce", QString::fromLatin1(nonce.toBase64())},
            {"tag", QString::fromLatin1(tag.toBase64())},
            {"body", QString::fromLatin1(cipher.toBase64())}};
}

QJsonObject RoomCrypto::decryptObject(const QJsonObject &envelope) const
{
    if (m_key.isEmpty() || envelope.value("kind").toString() != "cipher")
        return {};

    const QByteArray nonce = QByteArray::fromBase64(envelope.value("nonce").toString().toLatin1());
    const QByteArray tag = QByteArray::fromBase64(envelope.value("tag").toString().toLatin1());
    const QByteArray cipher = QByteArray::fromBase64(envelope.value("body").toString().toLatin1());
    if (nonce.size() != kNonceBytes || tag.size() != kTagBytes || cipher.isEmpty() ||
        cipher.size() > kMaxPlainBytes)
        return {};

    QByteArray plain(cipher.size(), Qt::Uninitialized);
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    int len = 0;
    int outLen = 0;
    if (!ctx ||
        EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) != 1 ||
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, nonce.size(), nullptr) != 1 ||
        EVP_DecryptInit_ex(ctx, nullptr, nullptr,
                           reinterpret_cast<const unsigned char *>(m_key.constData()),
                           reinterpret_cast<const unsigned char *>(nonce.constData())) != 1 ||
        EVP_DecryptUpdate(ctx, reinterpret_cast<unsigned char *>(plain.data()), &len,
                          reinterpret_cast<const unsigned char *>(cipher.constData()),
                          cipher.size()) != 1) {
        if (ctx)
            EVP_CIPHER_CTX_free(ctx);
        return {};
    }
    outLen = len;
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, tag.size(),
                        const_cast<char *>(tag.constData()));
    const int ok = EVP_DecryptFinal_ex(ctx,
                                       reinterpret_cast<unsigned char *>(plain.data()) + outLen,
                                       &len);
    EVP_CIPHER_CTX_free(ctx);
    if (ok != 1)
        return {};
    outLen += len;
    plain.resize(outLen);
    const QJsonDocument doc = QJsonDocument::fromJson(plain);
    return doc.isObject() ? doc.object() : QJsonObject{};
}
