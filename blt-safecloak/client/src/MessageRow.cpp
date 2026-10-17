#include "MessageRow.h"

#include <QBuffer>
#include <QDateTime>
#include <QHBoxLayout>
#include <QLabel>
#include <QMenu>
#include <QMovie>
#include <QPainter>
#include <QPainterPath>
#include <QPixmap>
#include <QPushButton>
#include <QVBoxLayout>

namespace {

constexpr int kAvatarSize = 36;
constexpr int kMaxMediaWidth = 360;

const char *kReactionChoices[] = {"\xF0\x9F\x91\x8D", "\xE2\x9D\xA4\xEF\xB8\x8F",
                                  "\xF0\x9F\x98\x82", "\xF0\x9F\x8E\x89",
                                  "\xF0\x9F\x98\xAE", "\xF0\x9F\x98\xA2",
                                  "\xF0\x9F\x99\x8F", "\xF0\x9F\x94\xA5"};

// A rounded-rectangle fallback avatar: the sender's initial on a colored tile.
QPixmap initialsAvatar(const QString &name, const QString &color)
{
    QPixmap pixmap(kAvatarSize, kAvatarSize);
    pixmap.fill(Qt::transparent);
    QPainter painter(&pixmap);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setBrush(QColor(color));
    painter.setPen(Qt::NoPen);
    painter.drawRoundedRect(0, 0, kAvatarSize, kAvatarSize, 9, 9);
    painter.setPen(Qt::white);
    QFont font = painter.font();
    font.setBold(true);
    font.setPixelSize(16);
    painter.setFont(font);
    const QString initial = name.isEmpty() ? "?" : name.left(1).toUpper();
    painter.drawText(pixmap.rect(), Qt::AlignCenter, initial);
    return pixmap;
}

QString humanSize(qint64 bytes)
{
    if (bytes < 1024)
        return QString::number(bytes) + " B";
    if (bytes < 1024 * 1024)
        return QString::number(bytes / 1024.0, 'f', 1) + " KB";
    return QString::number(bytes / (1024.0 * 1024.0), 'f', 1) + " MB";
}

} // namespace

MessageRow::MessageRow(const ChatMessage &message, const QString &nameColor,
                       QWidget *parent)
    : QFrame(parent), m_message(message), m_nameColor(nameColor)
{
    setObjectName("messageRow");

    auto *outer = new QHBoxLayout(this);
    outer->setContentsMargins(12, 5, 12, 5);
    outer->setSpacing(10);

    m_avatarLabel = new QLabel;
    m_avatarLabel->setFixedSize(kAvatarSize, kAvatarSize);
    m_avatarLabel->setPixmap(initialsAvatar(message.senderName, nameColor));
    outer->addWidget(m_avatarLabel, 0, Qt::AlignTop);

    auto *column = new QVBoxLayout;
    column->setContentsMargins(0, 0, 0, 0);
    column->setSpacing(3);

    const QString time =
        QDateTime::fromMSecsSinceEpoch(message.timestampMs).toString("hh:mm");
    auto *header = new QLabel(
        "<span style='color:" + nameColor + "; font-weight:700'>" +
        message.senderName.toHtmlEscaped() + "</span>"
        "&nbsp;&nbsp;<span style='color:#6b7280; font-size:11px'>" + time +
        (message.edited ? " (edited)" : "") + "</span>");
    header->setTextFormat(Qt::RichText);
    auto *headerRow = new QHBoxLayout;
    headerRow->setContentsMargins(0, 0, 0, 0);
    headerRow->setSpacing(6);
    headerRow->addWidget(header);
    headerRow->addStretch();
    if (message.self && !message.deleted) {
        if (!message.text.isEmpty()) {
            auto *edit = new QPushButton("Edit");
            edit->setObjectName("messageAction");
            edit->setCursor(Qt::PointingHandCursor);
            edit->setToolTip("Edit message");
            connect(edit, &QPushButton::clicked, this, [this] {
                emit editRequested(m_message.id, m_message.text);
            });
            headerRow->addWidget(edit);
        }
        auto *del = new QPushButton("Delete");
        del->setObjectName("messageAction");
        del->setCursor(Qt::PointingHandCursor);
        del->setToolTip("Delete message");
        connect(del, &QPushButton::clicked, this, [this] {
            emit deleteRequested(m_message.id);
        });
        headerRow->addWidget(del);
    }
    column->addLayout(headerRow);

    if (message.deleted) {
        auto *body = new QLabel("<span style='color:#9ca3af'><i>Message deleted</i></span>");
        body->setObjectName("messageText");
        body->setTextFormat(Qt::RichText);
        column->addWidget(body);
    } else if (!message.text.isEmpty()) {
        auto *body = new QLabel(message.text.toHtmlEscaped());
        body->setObjectName("messageText");
        body->setWordWrap(true);
        body->setTextInteractionFlags(Qt::TextSelectableByMouse |
                                      Qt::LinksAccessibleByMouse);
        body->setOpenExternalLinks(true);
        column->addWidget(body);
    }

    if (!message.deleted && message.hasFile())
        buildAttachment(this, column);

    m_reactionsBar = nullptr;
    if (!message.deleted) {
        auto *reactionsRow = new QWidget;
        m_reactionsBar = new QHBoxLayout(reactionsRow);
        m_reactionsBar->setContentsMargins(0, 2, 0, 0);
        m_reactionsBar->setSpacing(4);
        auto *addReaction = new QPushButton("\xF0\x9F\x99\x82\x2B");
        addReaction->setObjectName("reactionAdd");
        addReaction->setCursor(Qt::PointingHandCursor);
        addReaction->setToolTip("Add reaction");
        connect(addReaction, &QPushButton::clicked, this,
                &MessageRow::showReactionPicker);
        m_reactionsBar->addWidget(addReaction);
        m_reactionsBar->addStretch();
        column->addWidget(reactionsRow);
    }

    outer->addLayout(column, 1);
}

void MessageRow::buildAttachment(QWidget *, QVBoxLayout *layout)
{
    const QString mime = m_message.fileMime;
    const QByteArray &data = m_message.fileData;

    if (mime == "image/gif") {
        auto *label = new QLabel;
        auto *buffer = new QBuffer(label);
        buffer->setData(data);
        buffer->open(QIODevice::ReadOnly);
        auto *movie = new QMovie(buffer, QByteArray(), label);
        if (movie->isValid()) {
            movie->jumpToFrame(0);
            QSize size = movie->currentImage().size();
            if (size.width() > kMaxMediaWidth)
                size.scale(kMaxMediaWidth, kMaxMediaWidth * size.height() /
                                               qMax(1, size.width()),
                           Qt::KeepAspectRatio);
            movie->setScaledSize(size);
            label->setMovie(movie);
            movie->start();
            layout->addWidget(label);
            return;
        }
    } else if (mime.startsWith("image/")) {
        QPixmap pixmap;
        if (pixmap.loadFromData(data)) {
            if (pixmap.width() > kMaxMediaWidth)
                pixmap = pixmap.scaledToWidth(kMaxMediaWidth,
                                              Qt::SmoothTransformation);
            auto *label = new QLabel;
            label->setPixmap(pixmap);
            layout->addWidget(label);
            return;
        }
    }

    // Non-image (or undecodable image): a downloadable file chip.
    auto *chip = new QWidget;
    chip->setObjectName("fileChip");
    auto *chipLayout = new QHBoxLayout(chip);
    chipLayout->setContentsMargins(10, 8, 10, 8);
    chipLayout->setSpacing(8);
    auto *icon = new QLabel("\xF0\x9F\x93\x8E");
    auto *name = new QLabel(m_message.fileName.toHtmlEscaped() + "  <span "
                            "style='color:#9ca3af'>(" +
                            humanSize(data.size()) + ")</span>");
    name->setTextFormat(Qt::RichText);
    auto *save = new QPushButton("Save");
    save->setObjectName("ghostButton");
    save->setCursor(Qt::PointingHandCursor);
    connect(save, &QPushButton::clicked, this, [this] {
        emit saveFileRequested(m_message.fileName, m_message.fileData);
    });
    chipLayout->addWidget(icon);
    chipLayout->addWidget(name, 1);
    chipLayout->addWidget(save);
    layout->addWidget(chip);
}

void MessageRow::setAvatar(const QPixmap &pixmap)
{
    if (pixmap.isNull())
        return;
    QPixmap rounded(kAvatarSize, kAvatarSize);
    rounded.fill(Qt::transparent);
    QPainter painter(&rounded);
    painter.setRenderHint(QPainter::Antialiasing);
    QPainterPath clip;
    clip.addRoundedRect(0, 0, kAvatarSize, kAvatarSize, 9, 9);
    painter.setClipPath(clip);
    painter.drawPixmap(0, 0,
                       pixmap.scaled(kAvatarSize, kAvatarSize,
                                     Qt::KeepAspectRatioByExpanding,
                                     Qt::SmoothTransformation));
    m_avatarLabel->setPixmap(rounded);
}

void MessageRow::setReactions(const QMap<QString, QStringList> &reactions)
{
    if (!m_reactionsBar)
        return;
    // Clear existing chips (keep the trailing "+" button and stretch).
    while (m_reactionsBar->count() > 2) {
        QLayoutItem *item = m_reactionsBar->takeAt(0);
        if (item->widget())
            item->widget()->deleteLater();
        delete item;
    }
    int insertAt = 0;
    for (auto it = reactions.constBegin(); it != reactions.constEnd(); ++it) {
        auto *chip = new QPushButton(it.key() + " " +
                                     QString::number(it.value().size()));
        chip->setObjectName("reactionChip");
        chip->setCursor(Qt::PointingHandCursor);
        chip->setToolTip(it.value().join(", "));
        const QString emoji = it.key();
        connect(chip, &QPushButton::clicked, this,
                [this, emoji] { emit reactionToggled(m_message.id, emoji); });
        m_reactionsBar->insertWidget(insertAt++, chip);
    }
}

void MessageRow::showReactionPicker()
{
    QMenu menu(this);
    for (const char *emoji : kReactionChoices) {
        QAction *action = menu.addAction(QString::fromUtf8(emoji));
        const QString value = QString::fromUtf8(emoji);
        connect(action, &QAction::triggered, this,
                [this, value] { emit reactionToggled(m_message.id, value); });
    }
    menu.exec(QCursor::pos());
}
