// Headless end-to-end check of the networking backends: starts a server with
// two clients and relays a message, then brings up two mesh nodes that must
// discover each other over UDP broadcast and exchange a flooded message.
// Exits 0 on success.

#include "../src/ChatClient.h"
#include "../src/ChatServer.h"
#include "../src/MeshNode.h"
#include "../src/SslIdentity.h"

#include <QCoreApplication>
#include <QTimer>

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

    // --- Server mode: host + two clients ---
    ChatServer server(identity, "host");
    check(server.start(48321), "server listens on TLS port 48321");

    ChatClient alice("alice");
    ChatClient bob("bob");

    QList<MemberInfo> aliceRoster;
    QString bobReceivedText, bobReceivedChannel, hostReceivedSender;
    QObject::connect(&alice, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { aliceRoster = m; });
    QObject::connect(&bob, &ChatBackend::chatMessage,
                     [&](const QString &channel, const QString &, const QString &text,
                         qint64) { bobReceivedChannel = channel; bobReceivedText = text; });
    QObject::connect(&server, &ChatBackend::chatMessage,
                     [&](const QString &, const QString &sender, const QString &,
                         qint64) { hostReceivedSender = sender; });

    alice.connectToServer("127.0.0.1", 48321);
    bob.connectToServer("127.0.0.1", 48321);

    check(waitFor([&] { return aliceRoster.size() == 3; }, 5000),
          "roster reaches 3 members (host, alice, bob)");

    alice.sendChat("#general", "hello over TLS");
    check(waitFor([&] { return !bobReceivedText.isEmpty(); }, 5000),
          "bob receives alice's message via server relay");
    check(bobReceivedText == "hello over TLS" && bobReceivedChannel == "#general",
          "relayed message content and channel are intact");
    check(waitFor([&] { return hostReceivedSender == "alice"; }, 2000),
          "host sees the message with the right sender");

    QStringList bobChannels;
    QObject::connect(&bob, &ChatBackend::channelsChanged,
                     [&](const QStringList &c) { bobChannels = c; });
    alice.addChannel("#dev");
    check(waitFor([&] { return bobChannels.contains("#dev"); }, 5000),
          "channel created by alice propagates to bob");

    // --- Direct messages through the server ---
    QString bobId, hostId;
    for (const MemberInfo &member : std::as_const(aliceRoster)) {
        if (member.name == "bob")
            bobId = member.id;
        if (member.note == "(host)")
            hostId = member.id;
    }
    check(!bobId.isEmpty() && !hostId.isEmpty(), "roster carries member ids");

    QString bobDmText, bobDmPeer, aliceDmEcho, hostDmText;
    int hostChatCount = 0;
    QObject::connect(&bob, &ChatBackend::directMessage,
                     [&](const QString &peerId, const QString &, const QString &,
                         const QString &text, qint64) {
                         bobDmPeer = peerId;
                         bobDmText = text;
                     });
    QObject::connect(&alice, &ChatBackend::directMessage,
                     [&](const QString &, const QString &peerName, const QString &,
                         const QString &text, qint64) {
                         if (text == "psst bob") aliceDmEcho = peerName;
                     });
    QObject::connect(&server, &ChatBackend::directMessage,
                     [&](const QString &, const QString &, const QString &,
                         const QString &text, qint64) { hostDmText = text; });
    QObject::connect(&server, &ChatBackend::chatMessage,
                     [&](const QString &, const QString &, const QString &, qint64) {
                         ++hostChatCount;
                     });

    alice.sendDirect(bobId, "psst bob");
    check(waitFor([&] { return bobDmText == "psst bob"; }, 5000),
          "bob receives alice's direct message");
    check(waitFor([&] { return aliceDmEcho == "bob"; }, 5000),
          "alice's DM is echoed back with the right conversation partner");
    check(hostDmText.isEmpty(), "host does not see a client-to-client DM");

    alice.sendDirect(hostId, "psst host");
    check(waitFor([&] { return hostDmText == "psst host"; }, 5000),
          "host receives a DM addressed to it");
    check(hostChatCount == 0, "DMs never surface as channel messages");

    alice.shutdown();
    bob.shutdown();
    server.shutdown();

    // --- Mesh mode: two nodes discover each other and flood a message ---
    MeshNode nodeA(identity, "node-a");
    MeshNode nodeB(identity, "node-b");

    QString meshReceived;
    int meshPeersA = 0;
    QList<MemberInfo> rosterA, rosterB;
    QObject::connect(&nodeB, &ChatBackend::chatMessage,
                     [&](const QString &, const QString &sender, const QString &text,
                         qint64) {
                         if (sender == "node-a")
                             meshReceived = text;
                     });
    QObject::connect(&nodeA, &ChatBackend::statusChanged, [&](const QString &status) {
        meshPeersA = status.contains("1 peer") ? 1 : meshPeersA;
    });
    QObject::connect(&nodeA, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterA = m; });
    QObject::connect(&nodeB, &ChatBackend::rosterChanged,
                     [&](const QList<MemberInfo> &m) { rosterB = m; });

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

    nodeA.sendChat("#general", "mesh hello");
    check(waitFor([&] { return meshReceived == "mesh hello"; }, 5000),
          "mesh message floods from node A to node B");

    // --- Direct message across the mesh ---
    QString meshBId;
    for (const MemberInfo &member : std::as_const(rosterA)) {
        if (member.name == "node-b")
            meshBId = member.id;
    }
    QString meshDmText;
    QObject::connect(&nodeB, &ChatBackend::directMessage,
                     [&](const QString &, const QString &, const QString &sender,
                         const QString &text, qint64) {
                         if (sender == "node-a")
                             meshDmText = text;
                     });
    nodeA.sendDirect(meshBId, "mesh dm");
    check(waitFor([&] { return meshDmText == "mesh dm"; }, 5000),
          "direct message reaches the mesh peer");

    nodeA.shutdown();
    nodeB.shutdown();

    qInfo(failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED");
    return failures == 0 ? 0 : 1;
}
