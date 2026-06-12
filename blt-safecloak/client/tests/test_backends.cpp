// Headless end-to-end check of the mesh backend: nodes must discover each
// other, establish TLS links in both rosters, and exchange channel/DM messages.
// Exits 0 on success.

#include "../src/MeshNode.h"
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

    nodeA.sendChat("#general", "mesh hello");
    check(waitFor([&] { return meshReceived == "mesh hello"; }, 5000),
          "mesh message floods from node A to node B");

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

    // --- Mesh between two distinct IP addresses ---
    // Linux routes the whole 127.0.0.0/8 range to loopback, so binding one
    // node to 127.0.0.2 and the other to 127.0.0.3 simulates two hosts: the
    // announce carries a real sender address, the dial goes to that address,
    // and the TLS handshake crosses the two endpoints.
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
    QObject::connect(&nodeD, &ChatBackend::chatMessage,
                     [&](const QString &channel, const QString &sender,
                         const QString &text, qint64) {
                         if (sender == "node-c" && channel == "#general")
                             crossIpChat = text;
                     });
    QObject::connect(&nodeD, &ChatBackend::directMessage,
                     [&](const QString &, const QString &, const QString &sender,
                         const QString &text, qint64) {
                         if (sender == "node-c")
                             crossIpDm = text;
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

    qInfo(failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED");
    return failures == 0 ? 0 : 1;
}
