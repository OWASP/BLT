#include "MainWindow.h"
#include "Theme.h"

#include <QApplication>
#include <QStyleFactory>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("SafeCloakChat");
    app.setOrganizationName("OWASP-BLT");
    app.setStyle(QStyleFactory::create("Fusion"));
    app.setStyleSheet(Theme::kStyleSheet);

    MainWindow window;
    window.show();
    return app.exec();
}
