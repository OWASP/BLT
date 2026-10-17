#pragma once

#include <QByteArray>
#include <QDialog>

class QLabel;
class QLineEdit;
class QPlainTextEdit;

// Settings + diagnostics, kept out of the main chat for a clean interface:
// display name, avatar upload, and the network/debug log.
class SettingsDialog : public QDialog
{
    Q_OBJECT
public:
    SettingsDialog(const QString &version, QWidget *parent = nullptr);

    void setDisplayName(const QString &name);
    void setAvatar(const QByteArray &pngData);
    void appendLog(const QString &line);

signals:
    void displayNameChanged(const QString &name);
    void avatarChosen(const QByteArray &pngData);

private:
    void chooseAvatar();

    QLineEdit *m_nameEdit;
    QLabel *m_avatarPreview;
    QPlainTextEdit *m_log;
};
