// Headless end-to-end check of the mesh backend: nodes must discover each
// other, establish TLS links in both rosters, and exchange channel/DM messages.
// Exits 0 on success.

#include "../src/MeshNode.h"
#include "../src/RoomCrypto.h"
#include "../src/SslIdentity.h"

#include <QCoreApplication>
#include <QTimer>
#include <QUuid>

#include <functional>

namespace {

int failures = 0;

void check(bool condition, const char *what)
{
    if (condition) {
        qInfo("PASS: %s", what);
    } else {
        qCritical("FAIL: %s", what);
        ++failures;
    }
}

// Runs the event loop until predicate() is true or timeout elapses.
bool waitFor(const std::function<bool()> &predicate, int timeoutMs)
{
    QElapsedTimer timer;
    timer.start();
    while (!predicate()) {
        if (timer.elapsed() > timeoutMs)
            return false;
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
    }
    return true;
}

} // namespace

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    app.setApplicationName("SafeCloakChatTest");

    SslIdentity identity;
    check(identity.load(), "TLS identity loads (generating if needed)");
    if (!identity.isValid())
        return 1;
    check(!identity.fingerprint().isEmpty(), "certificate fingerprint available");

    RoomCrypto crypto("test-room", "correct horse battery staple");
    check(crypto.isValid(), "room crypto key derives");
    const QJsonObject secret{{"type", "chat"}, {"text", "encrypted hello"}};
    const QJsonObject encrypted = crypto.encryptObject(secret);
    check(encrypted.value("kind").toString() == "cipher" &&
              !encrypted.value("body").toString().isEmpty(),
          "room crypto encrypts to an opaque envelope");
    check(crypto.decryptObject(encrypted).value("text").toString() == "encrypted hello",
          "room crypto decrypts a valid envelope");
    RoomCrypto wrongCrypto("test-room", "wrong passphrase");
    check(wrongCrypto.decryptObject(encrypted).isEmpty(),
          "room crypto rejects the wrong passphrase");

    const QString testAppTag =
        QStringLiteral("safecloak-chat-test-") +
        QUuid::createUuid().toString(QUuid::WithoutBraces);

    // --- Two nodes discover each other and flood a message ---
    MeshNode nodeA(identity, "node-a", nullptr, testAppTag);
    MeshNode nodeB(identity, "node-b", nullptr, testAppTag);

    QString meshReceived;
    int meshPeersA = 0;
    QList<MemberInfo> rosterA, rosterB;
    QStringList channelsB;
    ChatMessage lastBChat;
    QObject::connect(&nodeB, &ChatBackend::messageArrived,
                     [&](const ChatMessage &m) {
                         if (m.senderName == "node-a" && m.conversation == "#general") {
                             meshReceived = m.text;
                             lastBChat = m;
                         }
                     });
    QObject::connect(&nodeA, &ChatBackend::statusChanged, [&](const QString &status) {
        meshPeersA = status.contains("1 reachable") ? 1 : meshPeersA;
    });
    QObject::connect(&nodeA, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterA = m; });
    QObject::connect(&nodeB, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterB = m; });
    QObject::connect(&nodeB, &ChatBackend::channelsChanged,
                     [&](const QStringList &channels) { channelsB = channels; });
    QObject::connect(&nodeA, &ChatBackend::fatalError,
                     [](const QString &message) { qCritical("node-a: %s", qPrintable(message)); });
    QObject::connect(&nodeB, &ChatBackend::fatalError,
                     [](const QString &message) { qCritical("node-b: %s", qPrintable(message)); });

    check(nodeA.start(), "mesh node A starts");
    check(nodeB.start(), "mesh node B starts");

    check(waitFor([&] { return meshPeersA == 1; }, 15000),
          "mesh nodes discover each other and establish a TLS link");

    // Both sides must see the other as a connected peer (the "first user
    // doesn't see the second" bug): present in the roster with no
    // "(discovered)" note left.
    auto seesConnectedPeer = [](const QList<MemberInfo> &roster, const QString &name) {
        for (const MemberInfo &member : roster) {
            if (member.name == name && !member.self && member.note.isEmpty())
                return true;
        }
        return false;
    };
    check(waitFor([&] { return seesConnectedPeer(rosterA, "node-b"); }, 5000),
          "node A's roster shows node B as a connected peer");
    check(waitFor([&] { return seesConnectedPeer(rosterB, "node-a"); }, 5000),
          "node B's roster shows node A as a connected peer (both directions)");
    auto peerOnline = [](const QList<MemberInfo> &roster, const QString &name) {
        for (const MemberInfo &member : roster) {
            if (member.name == name && !member.self)
                return member.online;
        }
        return false;
    };
    check(waitFor([&] {
              return peerOnline(rosterA, "node-b") && peerOnline(rosterB, "node-a");
          }, 5000),
          "connected mesh peers are marked online for green dots");

    nodeA.sendChat("#general", "mesh hello");
    check(waitFor([&] { return meshReceived == "mesh hello"; }, 5000),
          "mesh message floods from node A to node B");

    QString unauthorizedEdit;
    QObject::connect(&nodeA, &ChatBackend::messageEdited,
                     [&](const QString &, const QString &messageId,
                         const QString &text) {
                         if (messageId == lastBChat.id)
                             unauthorizedEdit = text;
                     });
    nodeB.editMessage("#general", lastBChat.id, "peer takeover");
    QElapsedTimer unauthorizedTimer;
    unauthorizedTimer.start();
    while (unauthorizedTimer.elapsed() < 500)
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
    check(unauthorizedEdit.isEmpty(),
          "mesh rejects edits from a node that did not author the message");

    QString editedText;
    QObject::connect(&nodeB, &ChatBackend::messageEdited,
                     [&](const QString &, const QString &messageId,
                         const QString &text) {
                         if (messageId == lastBChat.id)
                             editedText = text;
                     });
    nodeA.editMessage("#general", lastBChat.id, "mesh hello edited");
    check(waitFor([&] { return editedText == "mesh hello edited"; }, 5000),
          "mesh message edit reaches the peer");

    QString deletedMessageId;
    QObject::connect(&nodeB, &ChatBackend::messageDeleted,
                     [&](const QString &, const QString &messageId) {
                         deletedMessageId = messageId;
                     });
    nodeA.deleteMessage("#general", lastBChat.id);
    check(waitFor([&] { return deletedMessageId == lastBChat.id; }, 5000),
          "mesh message delete reaches the peer");

    nodeA.addChannel("#dev");
    check(waitFor([&] { return channelsB.contains("#dev"); }, 5000),
          "channel created by node A propagates to node B");

    // --- Direct message across the mesh ---
    QString meshBId;
    for (const MemberInfo &member : std::as_const(rosterA)) {
        if (member.name == "node-b")
            meshBId = member.id;
    }
    QString meshDmText;
    QObject::connect(&nodeB, &ChatBackend::messageArrived,
                     [&](const ChatMessage &m) {
                         if (m.senderName == "node-a" && m.conversation.startsWith('@'))
                             meshDmText = m.text;
                     });
    nodeA.sendDirect(meshBId, "mesh dm");
    check(waitFor([&] { return meshDmText == "mesh dm"; }, 5000),
          "direct message reaches the mesh peer");

    QString typingConversation;
    QString typingPeer;
    bool typingActive = false;
    QObject::connect(&nodeB, &ChatBackend::typingChanged,
                     [&](const QString &conversation, const QString &peerId,
                         const QString &, bool active) {
                         typingConversation = conversation;
                         typingPeer = peerId;
                         typingActive = active;
                     });
    nodeA.sendTyping("#general", true);
    check(waitFor([&] {
              return typingConversation == "#general" && !typingPeer.isEmpty() &&
                     typingActive;
          }, 5000),
          "typing indicator reaches the mesh peer");
    nodeA.sendTyping("#general", false);
    check(waitFor([&] { return !typingActive; }, 5000),
          "typing stopped indicator reaches the mesh peer");

    // --- File sharing ---
    ChatMessage fileMsg;
    QObject::connect(&nodeB, &ChatBackend::messageArrived, [&](const ChatMessage &m) {
        if (m.hasFile())
            fileMsg = m;
    });
    const QByteArray gifBytes = QByteArray::fromHex(
        "47494638396101000100800000000000ffffff21f90400000000002c00000000"
        "0100010000020144003b");
    nodeA.sendFile("#general", "tiny.gif", "image/gif", gifBytes);
    check(waitFor([&] { return fileMsg.hasFile(); }, 5000),
          "file attachment reaches the mesh peer");
    check(fileMsg.fileName == "tiny.gif" && fileMsg.fileMime == "image/gif" &&
              fileMsg.fileData == gifBytes,
          "file name, mime, and bytes survive the transfer intact");

    // --- Reactions ---
    QString reactEmoji;
    int reactCount = 0;
    QObject::connect(&nodeB, &ChatBackend::reactionChanged,
                     [&](const QString &, const QString &messageId, const QString &emoji,
                         const QString &, bool added) {
                         if (messageId == lastBChat.id && added) {
                             reactEmoji = emoji;
                             ++reactCount;
                         }
                     });
    nodeA.sendReaction("#general", lastBChat.id, "\xF0\x9F\x91\x8D");
    check(waitFor([&] { return reactEmoji == "\xF0\x9F\x91\x8D"; }, 5000),
          "reaction on a message reaches the mesh peer");

    // --- Avatars ---
    QByteArray avatarSeen;
    QObject::connect(&nodeB, &ChatBackend::avatarChanged,
                     [&](const QString &, const QByteArray &png) { avatarSeen = png; });
    const QByteArray avatarPng("\x89PNG\r\n\x1a\n fake-avatar-bytes", 27);
    nodeA.setAvatar(avatarPng);
    check(waitFor([&] { return avatarSeen == avatarPng; }, 5000),
          "avatar propagates to the mesh peer");

    nodeA.shutdown();
    check(waitFor([&] { return !seesConnectedPeer(rosterB, "node-a"); }, 5000),
          "clean bye removes the leaving mesh peer from the roster");
    nodeB.shutdown();

    // --- Mesh between two distinct IP addresses ---
    // Linux routes the whole 127.0.0.0/8 range to loopback, so binding one
    // node to 127.0.0.2 and the other to 127.0.0.3 simulates two hosts: the
    // announce carries a real sender address, the dial goes to that address,
    // and the TLS handshake crosses the two endpoints. macOS only configures
    // 127.0.0.1 by default, so those aliases are not available on GitLab's
    // macOS runners unless they are added with elevated network setup.
#ifdef Q_OS_LINUX
    const QHostAddress addrC("127.0.0.2");
    const QHostAddress addrD("127.0.0.3");
    MeshNode nodeC(identity, "node-c", nullptr, testAppTag);
    MeshNode nodeD(identity, "node-d", nullptr, testAppTag);

    QList<MemberInfo> rosterC, rosterD;
    QString crossIpChat, crossIpDm;
    QObject::connect(&nodeC, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterC = m; });
    QObject::connect(&nodeD, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterD = m; });
    QObject::connect(&nodeD, &ChatBackend::messageArrived,
                     [&](const ChatMessage &m) {
                         if (m.senderName == "node-c" && m.conversation == "#general")
                             crossIpChat = m.text;
                         else if (m.senderName == "node-c" &&
                                  m.conversation.startsWith('@'))
                             crossIpDm = m.text;
                     });
    QObject::connect(&nodeC, &ChatBackend::fatalError,
                     [](const QString &message) { qCritical("node-c: %s", qPrintable(message)); });
    QObject::connect(&nodeD, &ChatBackend::fatalError,
                     [](const QString &message) { qCritical("node-d: %s", qPrintable(message)); });

    check(nodeC.start(addrC, {addrD}), "mesh node C starts on 127.0.0.2");
    check(nodeD.start(addrD, {addrC}), "mesh node D starts on 127.0.0.3");

    check(waitFor([&] { return seesConnectedPeer(rosterC, "node-d"); }, 15000),
          "node C (127.0.0.2) links to node D across IP addresses");
    check(waitFor([&] { return seesConnectedPeer(rosterD, "node-c"); }, 5000),
          "node D (127.0.0.3) links to node C across IP addresses");

    nodeC.sendChat("#general", "hello across addresses");
    check(waitFor([&] { return crossIpChat == "hello across addresses"; }, 5000),
          "channel message crosses the two IP addresses");

    QString nodeDId;
    for (const MemberInfo &member : std::as_const(rosterC)) {
        if (member.name == "node-d")
            nodeDId = member.id;
    }
    nodeC.sendDirect(nodeDId, "dm across addresses");
    check(waitFor([&] { return crossIpDm == "dm across addresses"; }, 5000),
          "direct message crosses the two IP addresses");

    nodeC.shutdown();
    nodeD.shutdown();
#else
    qInfo("SKIP: cross-IP loopback mesh test requires Linux 127.0.0.0/8 aliases");
#endif

    // --- History sync: a node that joins late gets the channel backlog ---
    MeshNode nodeG(identity, "node-g", nullptr, testAppTag);
    check(nodeG.start(), "history node G starts");
    nodeG.sendChat("#general", "said before H joined");
    nodeG.sendChat("#general", "second message before H");
    // Give G's own history a moment to settle, then bring up H.
    waitFor([] { return false; }, 300);

    MeshNode nodeH(identity, "node-h", nullptr, testAppTag);
    QStringList historyTexts;
    QObject::connect(&nodeH, &ChatBackend::messageArrived, [&](const ChatMessage &m) {
        if (m.senderName == "node-g")
            historyTexts.append(m.text);
    });
    check(nodeH.start(), "history node H starts");
    check(waitFor([&] {
              return historyTexts.contains("said before H joined") &&
                     historyTexts.contains("second message before H");
          }, 15000),
          "late joiner H receives node G's channel history on connect");

    nodeG.shutdown();
    nodeH.shutdown();

    // --- Same display name still means two distinct live members ---
    MeshNode nodeE(identity, "same-name", nullptr, testAppTag);
    MeshNode nodeF(identity, "same-name", nullptr, testAppTag);

    QList<MemberInfo> rosterE, rosterF;
    QObject::connect(&nodeE, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterE = m; });
    QObject::connect(&nodeF, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterF = m; });
    QObject::connect(&nodeE, &ChatBackend::fatalError,
                     [](const QString &message) { qCritical("node-e: %s", qPrintable(message)); });
    QObject::connect(&nodeF, &ChatBackend::fatalError,
                     [](const QString &message) { qCritical("node-f: %s", qPrintable(message)); });

    check(nodeE.start(), "same-name node E starts");
    check(nodeF.start(), "same-name node F starts");

    auto hasDistinctPeerWithSameName = [](const QList<MemberInfo> &roster) {
        QString selfId;
        bool sawPeer = false;
        for (const MemberInfo &member : roster) {
            if (member.self)
                selfId = member.id;
        }
        for (const MemberInfo &member : roster) {
            if (!member.self && member.name == "same-name" &&
                !member.id.isEmpty() && member.id != selfId)
                sawPeer = true;
        }
        return sawPeer;
    };
    check(waitFor([&] { return hasDistinctPeerWithSameName(rosterE); }, 15000),
          "node E shows the peer even when both users have the same display name");
    check(waitFor([&] { return hasDistinctPeerWithSameName(rosterF); }, 5000),
          "node F shows the peer even when both users have the same display name");

    nodeE.shutdown();
    nodeF.shutdown();

    qInfo(failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED");
    return failures == 0 ? 0 : 1;
}
