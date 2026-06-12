// Renders the two app pages to PNG files for visual inspection without a
// display. Usage: QT_QPA_PLATFORM=offscreen ./safecloak-screenshot <dir>

#include "../src/MainWindow.h"
#include "../src/Theme.h"

#include <QApplication>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QStackedWidget>
#include <QStyleFactory>
#include <QTextBrowser>
#include <QTimer>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("SafeCloakChat");
    app.setStyle(QStyleFactory::create("Fusion"));
    app.setStyleSheet(Theme::kStyleSheet);

    const QString dir = argc > 1 ? argv[1] : ".";

    MainWindow window;
    window.resize(1060, 700);
    window.show();

    QTimer::singleShot(300, [&] {
        window.grab().save(dir + "/page-setup.png");

        // Fake a populated chat page purely for the visual check.
        auto *stack = window.findChild<QStackedWidget *>();
        stack->setCurrentIndex(1);
        if (auto *badge = window.findChild<QLabel *>("modeBadge"))
            badge->setText("MESH");
        if (auto *status = window.findChild<QLabel *>("statusLine"))
            status->setText("Mesh · 2 peer(s) · TLS");
        if (auto *enc = window.findChild<QLabel *>("encryptionLabel"))
            enc->setText("\xF0\x9F\x94\x92 TLS encrypted · fingerprint 5C:1A:33:F0:9B…");
        const auto lists = window.findChildren<QListWidget *>();
        for (QListWidget *list : lists) {
            if (list->objectName().isEmpty()) // skip none; identify by parent order
                continue;
        }
        // channel + member lists are unnamed; populate both found lists.
        if (lists.size() >= 2) {
            lists[0]->addItems({"#general", "#random", "\xE2\x97\x8F #dev"});
            lists[0]->setCurrentRow(0);
            lists[1]->addItems({"\xE2\x97\x8F casey (you)", "\xE2\x97\x8F sam",
                                "\xE2\x97\x8F rio (discovered)"});
        }
        if (auto *view = window.findChild<QTextBrowser *>("messageView")) {
            view->insertHtml(
                "<div style='margin:6px 0'><span style='color:#ff6b6b;font-weight:700'>sam</span> "
                "<span style='color:#9ca3af;font-size:11px'>14:02</span><br>"
                "<span style='color:#f1f5f9'>hey team, the mesh link is up</span></div>"
                "<div style='margin:4px 0;color:#9ca3af'><i>· rio is now reachable</i></div>"
                "<div style='margin:6px 0'><span style='color:#60a5fa;font-weight:700'>casey</span> "
                "<span style='color:#9ca3af;font-size:11px'>14:03</span><br>"
                "<span style='color:#f1f5f9'>nice — everything is encrypted end to end over TLS</span></div>");
        }
        QTimer::singleShot(200, [&] {
            window.grab().save(dir + "/page-chat.png");
            app.quit();
        });
    });

    return app.exec();
}
