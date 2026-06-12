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

    QStringList aliceRoster;
    QString bobReceivedText, bobReceivedChannel, hostReceivedSender;
    QObject::connect(&alice, &ChatBackend::rosterChanged,
                     [&](const QStringList &m) { aliceRoster = m; });
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

    alice.shutdown();
    bob.shutdown();
    server.shutdown();

    // --- Mesh mode: two nodes discover each other and flood a message ---
    MeshNode nodeA(identity, "node-a");
    MeshNode nodeB(identity, "node-b");

    QString meshReceived;
    int meshPeersA = 0;
    QObject::connect(&nodeB, &ChatBackend::chatMessage,
                     [&](const QString &, const QString &sender, const QString &text,
                         qint64) {
                         if (sender == "node-a")
                             meshReceived = text;
                     });
    QObject::connect(&nodeA, &ChatBackend::statusChanged, [&](const QString &status) {
        meshPeersA = status.contains("1 peer") ? 1 : meshPeersA;
    });

    check(nodeA.start(), "mesh node A starts");
    check(nodeB.start(), "mesh node B starts");

    check(waitFor([&] { return meshPeersA == 1; }, 15000),
          "mesh nodes discover each other and establish a TLS link");

    nodeA.sendChat("#general", "mesh hello");
    check(waitFor([&] { return meshReceived == "mesh hello"; }, 5000),
          "mesh message floods from node A to node B");

    nodeA.shutdown();
    nodeB.shutdown();

    qInfo(failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED");
    return failures == 0 ? 0 : 1;
}
