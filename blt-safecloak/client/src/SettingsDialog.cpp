#include "SettingsDialog.h"

#include <QBuffer>
#include <QFileDialog>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QImage>
#include <QLabel>
#include <QLineEdit>
#include <QPainter>
#include <QPainterPath>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QVBoxLayout>

namespace {
constexpr int kAvatarStored = 128;
constexpr int kAvatarPreview = 64;
} // namespace

SettingsDialog::SettingsDialog(const QString &version, QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("SafeCloak Settings");
    setMinimumSize(480, 520);

    auto *title = new QLabel("Settings");
    title->setObjectName("settingsTitle");

    // --- Profile ---
    m_nameEdit = new QLineEdit;
    m_nameEdit->setMaxLength(32);
    connect(m_nameEdit, &QLineEdit::editingFinished, this, [this] {
        const QString name = m_nameEdit->text().trimmed();
        if (!name.isEmpty())
            emit displayNameChanged(name);
    });

    m_avatarPreview = new QLabel;
    m_avatarPreview->setFixedSize(kAvatarPreview, kAvatarPreview);
    m_avatarPreview->setObjectName("avatarPreview");
    m_avatarPreview->setAlignment(Qt::AlignCenter);
    m_avatarPreview->setText("No\navatar");
    auto *chooseButton = new QPushButton("Upload avatar…");
    chooseButton->setObjectName("ghostButton");
    chooseButton->setCursor(Qt::PointingHandCursor);
    connect(chooseButton, &QPushButton::clicked, this, &SettingsDialog::chooseAvatar);
    auto *avatarRow = new QHBoxLayout;
    avatarRow->setSpacing(12);
    avatarRow->addWidget(m_avatarPreview);
    avatarRow->addWidget(chooseButton);
    avatarRow->addStretch();

    auto *form = new QFormLayout;
    form->setLabelAlignment(Qt::AlignLeft);
    form->setSpacing(8);
    form->addRow("Display name", m_nameEdit);
    form->addRow("Avatar", avatarRow);

    auto *profileLabel = new QLabel("PROFILE");
    profileLabel->setObjectName("sectionLabel");

    // --- Network log ---
    auto *logLabel = new QLabel("NETWORK LOG");
    logLabel->setObjectName("sectionLabel");
    m_log = new QPlainTextEdit;
    m_log->setReadOnly(true);
    m_log->setObjectName("networkLog");
    m_log->setMaximumBlockCount(2000);

    auto *versionLabel = new QLabel("SafeCloak v" + version);
    versionLabel->setObjectName("versionLabel");

    auto *closeButton = new QPushButton("Close");
    closeButton->setObjectName("primaryButton");
    connect(closeButton, &QPushButton::clicked, this, &QDialog::accept);
    auto *footer = new QHBoxLayout;
    footer->addWidget(versionLabel);
    footer->addStretch();
    footer->addWidget(closeButton);

    auto *layout = new QVBoxLayout(this);
    layout->setContentsMargins(20, 18, 20, 18);
    layout->setSpacing(10);
    layout->addWidget(title);
    layout->addWidget(profileLabel);
    layout->addLayout(form);
    layout->addSpacing(6);
    layout->addWidget(logLabel);
    layout->addWidget(m_log, 1);
    layout->addLayout(footer);
}

void SettingsDialog::setDisplayName(const QString &name)
{
    m_nameEdit->setText(name);
}

void SettingsDialog::setAvatar(const QByteArray &pngData)
{
    if (pngData.isEmpty())
        return;
    QPixmap pixmap;
    if (!pixmap.loadFromData(pngData))
        return;
    QPixmap rounded(kAvatarPreview, kAvatarPreview);
    rounded.fill(Qt::transparent);
    QPainter painter(&rounded);
    painter.setRenderHint(QPainter::Antialiasing);
    QPainterPath clip;
    clip.addRoundedRect(0, 0, kAvatarPreview, kAvatarPreview, 14, 14);
    painter.setClipPath(clip);
    painter.drawPixmap(0, 0,
                       pixmap.scaled(kAvatarPreview, kAvatarPreview,
                                     Qt::KeepAspectRatioByExpanding,
                                     Qt::SmoothTransformation));
    m_avatarPreview->setPixmap(rounded);
}

void SettingsDialog::appendLog(const QString &line)
{
    m_log->appendPlainText(line);
}

void SettingsDialog::chooseAvatar()
{
    const QString path = QFileDialog::getOpenFileName(
        this, "Choose avatar image", QString(),
        "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)");
    if (path.isEmpty())
        return;

    QImage image(path);
    if (image.isNull())
        return;

    // Center-crop to a square, scale down, and re-encode as PNG so every peer
    // receives a small, consistent avatar regardless of the source format.
    const int side = qMin(image.width(), image.height());
    image = image.copy((image.width() - side) / 2, (image.height() - side) / 2,
                       side, side)
                .scaled(kAvatarStored, kAvatarStored, Qt::IgnoreAspectRatio,
                        Qt::SmoothTransformation);

    QByteArray png;
    QBuffer buffer(&png);
    buffer.open(QIODevice::WriteOnly);
    image.save(&buffer, "PNG");

    setAvatar(png);
    emit avatarChosen(png);
}
