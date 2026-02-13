
#include <Python.h>

#include <QObject>
#include <QUrl>
#include <QMap>
#include <QString>
#include <QPainterPath>
#include <QRect>
#include <QPointF>
#include <QPainter>
#include <QEvent>
//#include <QStyledItemDelegate>
#include <QGraphicsObject>


void print_python_stack_trace();


class FDDocument : public QObject {
    
    Q_OBJECT
    
public:

    FDDocument(QObject *parent=NULL) { (void) parent; }
    virtual QByteArray diagramData() const = 0;
    virtual void updateDiagramData(const QByteArray &) = 0;
    virtual QUrl url() const = 0;
    virtual QStringList fileList() const = 0;
    virtual void save(bool quietly=false) = 0;
    virtual void saveAs(const QUrl &url) = 0;
    virtual void close() = 0;
    virtual void addFile(const QString &src, const QString &relativePath) = 0;
    virtual void removeFile(const QString &relativePath) = 0;
    virtual void renameFile(const QString &oldPath, const QString &newPath) = 0;
//    virtual void deleteFile(const QString &relativePath) = 0;
    
signals:
    void fileAdded(const QString &);
    void fileRemoved(const QString &);
    void saved();
    void savedAs(const QUrl &);
    void changed();
    void disableEditing();
    void enableEditing();
};



class QFileSystemWatcher;
class UnsafeArea;

class CUtil : public QObject {

    Q_OBJECT
    
protected:
    
	static CUtil *_instance;
	QMap<QUrl, FDDocument *> m_docs;
	QFileSystemWatcher *m_fsWatcher;
	bool m_bInitStarted; // `m_bInitCompleted` is determined by d.isInitialized;
    UnsafeArea *m_unsafeArea;
    QMargins m_unsafeAreaMargins;
    static bool m_isDev;

	CUtil(QObject *parent);
    
public:
    
    static const char *FileExtension;
    static const char *PickleFileName;
    static const char *PeopleDirName;
    static const char *EventsDirName;

    enum FileStatus {
        FileStatusNone,
        FileIsCurrent,
        FileNotDownloaded,
        FileIsDownloading
    };

    enum OperatingSystem {
        OS_Unknown =         0x00,
        OS_iPad =            0x02,
        OS_iPhone =          0x04,
        OS_iPhoneSimulator = 0x08,  // also OS_iPhone
        OS_Mac =             0x10,
        OS_Windows =         0x20
    };
    
    ~CUtil();
    static void startup();
    static void shutdown();
    static CUtil *instance();

    //
    // Virtuals
    //
    
    virtual void init() {}
    virtual void deinit() {}
    virtual bool isInitialized() const = 0;

    //
    // Cloud stuff
    //

    virtual bool iCloudAvailable() const { return false; }
    virtual QString iCloudDocsPath() const { return QString(); }
    virtual bool iCloudOn() const { return false; }
    virtual void setiCloudOn(bool) { }
    virtual bool startDownloading(const QUrl &) { return false; }
    virtual FileStatus fileStatusForUrl(const QUrl &) const = 0;
    virtual bool isUIDarkMode() const = 0;
    virtual QColor appleControlAccentColor() const = 0;

    virtual void forceDocsPath(const QString &) {}
    virtual QString documentsFolderPath() const = 0;
    virtual QList<QUrl> fileList() const = 0;
//    virtual void newUntitledFile();
    virtual void openExistingFile(const QUrl &url) = 0;
    virtual QString getOpenFileName() const = 0;
    
	virtual void showFeedbackWindow() const {}
	virtual void checkForUpdates() const {}
	virtual bool isUpdateAvailable() const { return false; }
    
    // deprecated
	virtual void trackAnalyticsEvent(QString, QMap<QString, QString>) {}
    
    //
    // Static utils
    //

//    static bool isiOSSimulator(); // initializes constant so must be static
    
    static OperatingSystem operatingSystem();
    static bool isReleaseBuild();
    static QString qrc(const QString &);
	static QRect screenSize();
    static float devicePixelRatio();
    static Qt::ScreenOrientation screenOrientation();
    QMargins safeAreaMargins(); // { return m_unsafeAreaMargins; }
	static QString getMachineModel();

    static qreal distance(const QPointF &p1, const QPointF &p2);
    static QPointF pointOnRay(const QPointF &orig, const QPointF &dest, float distance);
    static QPointF perpendicular(const QPointF &pointA, const QPointF &pointB, float width, bool reverse=false);
    static QPainterPath strokedPath(const QPainterPath &, const QPen &);
    static QPainterPath splineFromPoints(const QVector<QPointF> &points);
    static void paintSpline(QPainter &painter, const QVector<QPointF> &points);
    static QPainterPath splineFromPoints2(const QVector<QPointF> &points);
    static bool QRect_contains_QRect(const QRect &rect1, const QRect &rect2, bool proper=false);
    static QString joinPath(const QString& path1, const QString& path2, const QString& path3 = QString(), const QString& path4 = QString(), const QString& path5 = QString(), const QString& path6 = QString());
    static bool copyRecursively(QString sourceFolder, QString destFolder);

    // dev only
    virtual void dev_crash() const {}
    static void dev_printBacktrace();
    static bool dev_amIBeingDebugged();
    static void dev_showDebugConsole();
    static bool isDev();
    static void openNativeUrl(const QString &url);


public Q_SLOTS: // qslots n windows
    
    virtual void updateLocalFileList() {}
    void onSafeAreaMarginsChanged();
    void onScreenOrientationChanged();
    void showCriticalMessageBox(QString);
    
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
    void errorMessageReceived(QString);
};

CUtil *CUtil_create(QObject *parent);



/***************************************************/
/**                  For Speed                    **/
/***************************************************/


class AppFilter : public QObject {

    Q_OBJECT

public:
    
    AppFilter(QObject *parent=NULL);
    
    bool eventFilter(QObject *o, QEvent *e);
    
signals:

    void fileOpen(const QString &);
    void urlOpened(const QString &);
    void escapeKey(QKeyEvent *);
};


// class TimelineDelegateBase : public QStyledItemDelegate {
    
//     Q_OBJECT
    
//     QPen m_gridPen;
//     bool m_drawGrid;

// public:
//     TimelineDelegateBase(QObject *parent = NULL);

//     void setGridPen(const QPen &pen) { m_gridPen = pen; }
//     void setDrawGrid(const bool &on) { m_drawGrid = on; }

//     void paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) const override;
// };


class PathItemBase;

class PathItemDelegate {
    
protected:
    
    PathItemBase *m_pathItem;
    
public:
    PathItemDelegate(PathItemBase *);
    virtual ~PathItemDelegate() {}

    PathItemBase *pathItem() const { return m_pathItem; }
    
    virtual void paint(QPainter *, const QStyleOptionGraphicsItem *, QWidget * = nullptr);
};


// a simpler version of QGraphicsPathItem
class PathItemBase : public QGraphicsObject {

    Q_OBJECT

    friend class PathItemDelegate;

    PathItemDelegate *m_delegate;
    bool m_usingDefaultDelegate;
    QPainterPath m_path;
    QPen m_pen;
    QBrush m_brush;
    QRectF m_boundingRect; // cache
    QPainterPath m_shape; // cache
    bool m_shapeIsBoundingRect;
    bool m_shapeIncludesChildrenRect;
    float m_shapeMargin; // additional padding around shape()
    bool m_shapePathIsClosed;
    bool m_showPathItemShapes;

public:

    virtual void timerEvent(QTimerEvent *) {}; // fix crash on mac?

    bool dev_showPathItemShapes() const { return m_showPathItemShapes; }
    void dev_setShowPathItemShapes(bool on) { m_showPathItemShapes = on; update(); }
    void dev_printCStackTrace();

    PathItemBase(QGraphicsItem *parent=nullptr);
    // ~PathItemBase();

    PathItemDelegate *delegate() { return m_delegate; }
    void setPathItemDelegate(PathItemDelegate *d);

    // so this can be called from c++
    virtual void updateGeometry() { prepareGeometryChange(); } 
    void updatePathItemData();

    virtual void paint(QPainter *, const QStyleOptionGraphicsItem *, QWidget * = nullptr);
    virtual QPainterPath shape() const { return m_shape; }
    virtual QRectF boundingRect() const { return m_boundingRect; }

    bool shapeIsBoundingRect() const { return m_shapeIncludesChildrenRect; }
    void setShapeIsBoundingRect(bool on) { m_shapeIsBoundingRect = on; updatePathItemData(); }

    bool shapeIncludesChildrenRect() const { return m_shapeIncludesChildrenRect; }
    void setShapeIncludesChildrenRect(bool on) { m_shapeIncludesChildrenRect = on; updatePathItemData(); }

    bool shapePathIsClosed() const { return m_shapePathIsClosed; }
    void setShapePathIsClosed(bool on) { m_shapePathIsClosed = on; updatePathItemData(); }

    void setShapeMargin(float x) { m_shapeMargin = x; updatePathItemData(); }
    float shapeMargin() const { return m_shapeMargin; }

    const QPainterPath &path() const { return m_path; }
    void setPath(const QPainterPath &);
    
    const QPen &pen() const { return m_pen; }
    void setPen(const QPen &);
    void setPenColor(const QColor &c) { m_pen.setColor(c); }
    
    const QBrush &brush() const { return m_brush; }
    void setBrush(const QBrush &);
    void setBrushColor(const QColor &c) { m_brush.setColor(c); }
};


class PersonDelegate : public PathItemDelegate {

    bool m_primary;
    bool m_forceNoPaintBackground;
    QString m_gender;

public:

    PersonDelegate(PathItemBase *);
    virtual ~PersonDelegate() {}

    void setPrimary(bool on) { m_primary = on; }
    void setGender(const QString &gender) { m_gender = gender; }
    void setForceNoPaintBackground(bool on) { m_forceNoPaintBackground = on; }

    virtual void paint(QPainter *, const QStyleOptionGraphicsItem *, QWidget * = nullptr);
};
