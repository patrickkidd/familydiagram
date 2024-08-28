%Module _pkdiagram
%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip
%Import QtWidgets/QtWidgetsmod.sip

%ModuleHeaderCode
#include <_pkdiagram.h>
%End


class FDDocument : QObject {

%ConvertToSubClassCode
    FDDocument *doc = dynamic_cast<FDDocument *>(sipCpp);
    if(doc) {
         sipType = sipType_FDDocument;
    } else {
         sipType = NULL;
    }
%End

private:

    FDDocument();

public:

    QUrl url();
    QByteArray diagramData() const;
    void updateDiagramData(const QByteArray &data);
    QStringList fileList() const;
    void save(bool quietly=false) /KeywordArgs="Optional"/;
    void saveAs(const QUrl &);
    void close();
    void addFile(const QString &src, const QString &relativePath);
    void removeFile(const QString &relativePath);
    void renameFile(const QString &oldPath, const QString &newPath);

signals:
    void fileAdded(const QString &);
    void fileRemoved(const QString &);
    void saved();
    void disableEditing();
    void enableEditing();
    void changed();
};


class AppFilter : QObject {
public:
    AppFilter(QObject *parent=NULL);
signals:
    void fileOpen(const QString &);
};


class CUtil : QObject {

private:

    CUtil();

public:

    enum FileStatus {
        FileStatusNone,
        FileIsCurrent,
        FileNotDownloaded,
        FileIsDownloading
    };

    enum OperatingSystem {
        OS_iPad,
        OS_iPhone,
        OS_Mac,
        OS_Windows,
        OS_Unknown
    };

    static CUtil *instance();
    static void startup();
    static void shutdown();

    virtual void init();
    virtual void deinit();
    bool isInitialized() const;

    bool iCloudAvailable() const;
    QString iCloudDocsPath() const;
    bool iCloudOn() const;
    void setiCloudOn(bool);
    static CUtil::OperatingSystem operatingSystem();
    static bool isReleaseBuild();
    static bool isDev();

    void forceDocsPath(const QString &);
    QString documentsFolderPath() const;
//    void newUntitledFile();
    void openExistingFile(const QUrl &url);
    bool startDownloading(const QUrl &);
    QString getOpenFileName() const;

    void showFeedbackWindow() const;
    void checkForUpdates();
    bool isUpdateAvailable() const;

    void trackAnalyticsEvent(QString, QMap<QString, QString>);

    QList<QUrl> fileList() const;
    CUtil::FileStatus fileStatusForUrl(const QUrl &) const;
    bool isUIDarkMode() const;
    QColor appleControlAccentColor() const;

    void dev_crash() const;
    static void dev_printBacktrace();
    static bool dev_amIBeingDebugged();
    
    static QRect screenSize();
    static Qt::ScreenOrientation screenOrientation();
    QMargins safeAreaMargins();
//    static bool isiOSSimulator();
    static QString getMachineModel();

    static qreal distance(const QPointF &p1, const QPointF &p2);
    static QPointF pointOnRay(const QPointF &orig, const QPointF &dest, float distance);
    static QPointF perpendicular(const QPointF &pointA, const QPointF &pointB, float width, bool reverse=false);
    static QPainterPath strokedPath(const QPainterPath &, const QPen &);
    static QPainterPath splineFromPoints(const QVector<QPointF> &points);
    static void paintSpline(QPainter &painter, const QVector<QPointF> &points);
    static QPainterPath splineFromPoints2(const QVector<QPointF> &points);
    static bool QRect_contains_QRect(const QRect &rect1, const QRect &rect2, bool proper=false);

public slots:

    void updateLocalFileList();

signals:
    void initialized();
    void fileAdded(const QUrl &, int);
    void fileRemoved(const QUrl &);
    void fileStatusChanged(QUrl, int);
    void fileOpened(FDDocument *);
    void updateIsAvailable();
    void updateIsNotAvailable();
    void iCloudOnChanged(bool);
    void safeAreaMarginsChanged(const QMargins &);
    void screenOrientationChanged(Qt::ScreenOrientation);
    void systemPaletteChanged();    
};


/*
class TimelineDelegateBase : QStyledItemDelegate {
    
public:
    TimelineDelegateBase(QObject *parent = NULL);

    void setGridPen(const QPen &pen);
    void setDrawGrid(const bool &on);

    void paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) const;
};
*/


class PathItemDelegate {

public:

    PathItemDelegate(PathItemBase *);

    PathItemBase *pathItem() const;
    
    virtual void paint(QPainter *, const QStyleOptionGraphicsItem *, QWidget * = nullptr);
};


class PathItemBase : QGraphicsObject {

public:
    virtual void timerEvent(QTimerEvent *); // fix crash on mac?

    void dev_setShowPathItemShapes(bool);
    void dev_printCStackTrace();

    PathItemBase(QGraphicsItem *parent=nullptr);

    PathItemDelegate *delegate();
    void setPathItemDelegate(PathItemDelegate *);

    virtual void updateGeometry();
    void updatePathItemData();

    void paint(QPainter *, const QStyleOptionGraphicsItem *, QWidget * = nullptr);
    virtual QPainterPath shape() const;
    virtual QRectF boundingRect() const;

    bool shapeIsBoundingRect() const;
    void setShapeIsBoundingRect(bool);    

    bool shapeIncludesChildrenRect() const;
    void setShapeIncludesChildrenRect(bool on);

    bool shapePathIsClosed() const;
    void setShapePathIsClosed(bool);    

    void setShapeMargin(float x);
    float shapeMargin() const;
        
    const QPainterPath &path() const;
    void setPath(const QPainterPath &);
    
    const QPen &pen() const;
    void setPen(const QPen &);
    void setPenColor(const QColor &);
    
    const QBrush &brush() const;
    void setBrush(const QBrush &);
    void setBrushColor(const QColor &c);
};


class PersonDelegate : PathItemDelegate {

public:

    PersonDelegate(PathItemBase *);

    void setPrimary(bool);
    void setGender(const QString &);
    void setForceNoPaintBackground(bool on);

    void paint(QPainter *, const QStyleOptionGraphicsItem *, QWidget * = nullptr);
};
