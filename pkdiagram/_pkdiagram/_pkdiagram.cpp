#include "_pkdiagram.h"
#include <cmath>
#if TARGET_OS_IOS
#elif TARGET_OS_OSX
#else
#endif
#include <QtCore/QtCore>
#include <QtGui/QtGui>
#include <QtWidgets/QtWidgets>
#include <unsafearea.h>

#if TARGET_OS_OSX
#include <execinfo.h>
#include <iostream>
#endif

// #include <QPainterPathStroker>
// #include <QGuiApplication>
// #include <QtWidgets/QApplication>
// #include <QtWidgets/QDesktopWidget>

#if TARGET_OS_OSX
void print_stack_trace() {
    const int maxFrames = 100;
    void *frames[maxFrames];
    int frameCount = backtrace(frames, maxFrames);
    char **symbols = backtrace_symbols(frames, frameCount);

    std::cerr << "C/C++ Stack trace:" << std::endl;
    for (int i = 0; i < frameCount; ++i) {
        std::cerr << symbols[i] << std::endl;
    }

    free(symbols);
}

void print_python_stack_trace() {
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();    

    // Get the current thread state
    PyThreadState *tstate = PyThreadState_Get();

    if (tstate && tstate->frame) {
        // Get the traceback module and format_stack function
        PyObject *traceback_module = PyImport_ImportModule("traceback");
        if (traceback_module) {
            PyObject *format_stack = PyObject_GetAttrString(traceback_module, "format_stack");
            if (format_stack) {
                // Call format_stack with the current frame
                PyObject *stack_list = PyObject_CallFunctionObjArgs(format_stack, tstate->frame, NULL);
                if (stack_list) {
                    PyObject *stack_str = PyUnicode_Join(PyUnicode_FromString(""), stack_list);
                    if (stack_str) {
                        // Convert Python string to C string and print it
                        const char *stack_cstr = PyUnicode_AsUTF8(stack_str);
                        printf("Python stack trace:\n%s\n", stack_cstr);
                        Py_DECREF(stack_str);
                    }
                    Py_DECREF(stack_list);
                }
                Py_DECREF(format_stack);
            }
            Py_DECREF(traceback_module);
        }
    }


    PyGILState_Release(gstate);
}
#endif

AppFilter::AppFilter(QObject *parent)
    : QObject(parent) {
//    QGuiApplication::instance()->installEventFilter(this);
}

// Done in C++ instead of Python to keep all other events fast
bool AppFilter::eventFilter(QObject *o, QEvent *e) {

    if(o == QGuiApplication::instance()) {
        if(e->type() == QEvent::FileOpen) {
            // Qt only supports on MacOS
            QString file = static_cast<QFileOpenEvent *>(e)->file();
            emit fileOpen(file);
            return true;
        } else if (e->type() == QEvent::Quit) {
           QApplication::quit();
           return true;
        } else if (e->type() == QEvent::Close) {
            qDebug() << "e->type() == QEvent::Close";
#if TARGET_OS_OSX
            print_stack_trace();
#endif
        }
    }
    return false;
}

///////////////////////////////////////


CUtil *CUtil::_instance = NULL;
const char *CUtil::FileExtension = "fd";
const char *CUtil::PickleFileName = "diagram.pickle";
const char *CUtil::PeopleDirName = "People";
const char *CUtil::EventsDirName = "Events";


#ifdef PYQTDEPLOY_OPTIMIZED
#ifndef QT_DEBUG
bool CUtil::m_isDev = false;
#else
bool CUtil::m_isDev = true;
#endif
#else
bool CUtil::m_isDev = true;
#endif

CUtil::CUtil(QObject *parent) :
QObject(parent),
m_bInitStarted(false) {
    m_unsafeArea = new UnsafeArea(this);
    m_fsWatcher = new QFileSystemWatcher(this);
    QObject::connect(m_fsWatcher, SIGNAL(directoryChanged(const QString &)), this, SLOT(updateLocalFileList()));    
    // PyObject *pdytools = PyImport_ImportModule("pdytools");
    // printf("%p\n", pdytools);
    // qDebug() << pdytools;
    // if(pdytools) {
    //     m_isDev = false;
    //     Py_DECREF(pdytools);
    // } else { // release builds of qt and python modules but stil in dev
    //     PyErr_Clear();
    //     m_isDev = true;
    // }
}

CUtil *CUtil::instance() {
    return _instance;
}

CUtil::~CUtil() {
    delete m_unsafeArea;
    delete m_fsWatcher;
    m_fsWatcher = NULL;
}

void CUtil::startup() {
    Q_ASSERT(_instance == NULL);
	qSetMessagePattern("%{file}(%{line}): %{message}");
    _instance = CUtil_create(QApplication::instance());
}

void CUtil::shutdown() {
    Q_ASSERT(_instance != NULL);
    delete _instance;
    _instance = NULL;
}

bool CUtil::isReleaseBuild() {
#ifndef QT_DEBUG
    return false;
#else
    return true;
#endif
}

bool CUtil::isDev() {
    return m_isDev;
}

QString CUtil::qrc(const QString &relativePath) {
    QString ret;
    if(isDev()) {
        ret = CUtil::joinPath("pkdiagram", "resources", relativePath);
    } else {
        ret = QString(":/pkdiagram/resources/") + relativePath;
    }
    return ret;
}


//////////////////////////////////////

qreal CUtil::distance(const QPointF &p1, const QPointF &p2) {
    qreal a = p1.x() - p2.x();
    qreal b = p1.y() - p2.y();
    return sqrt(a*a + b*b);
}


/* Calculate a point on ray (orig, dest) <distance> from orig */
QPointF CUtil::pointOnRay(const QPointF &orig, const QPointF &dest, float distance) {
    qreal a = dest.x() - orig.x();
    qreal b = dest.y() - orig.y();
    qreal c = sqrt(pow(a, 2) + pow(b, 2)); // pythagorean
    qreal p;
    if(c > 0)
        p = distance / c;
    else
        p = 0;
    return QPointF(orig.x() + p * a, orig.y() + p * b);
}

/* Return a stroked path for QGraphicsItem shape.
 */
QPainterPath CUtil::strokedPath(const QPainterPath &path, const QPen &pen) {
    // We unfortunately need this hack as QPainterPathStroker will set a width of 1.0
    // if we pass a value of 0.0 to QPainterPathStroker::setWidth()
    qreal penWidthZero = 0.00000001;
    if(path == QPainterPath() || pen == Qt::NoPen)
        return path;
    QPainterPathStroker ps;
    ps.setCapStyle(pen.capStyle());
    if(pen.widthF() <= 0.0)
        ps.setWidth(penWidthZero);
    else
        ps.setWidth(pen.widthF() * 2);// *2 b/c nudge out
    ps.setJoinStyle(pen.joinStyle());
    ps.setMiterLimit(pen.miterLimit());
    QPainterPath ret = ps.createStroke(path);
    return ret;
}



/* Return pointC such that ray
   (pointC, pointB) is perpendicular to ray (pointA, pointB).
*/

QPointF CUtil::perpendicular(const QPointF &pointA, const QPointF &pointB, float width, bool reverse) {
    QPointF A, B;
    if(reverse) {
        A = pointB;
        B = pointA;
    } else {
        A = pointA;
        B = pointB;
    }
    qreal x1 = A.x();
    qreal x2 = B.x();
    qreal y1 = A.y();
    qreal y2 = B.y();
    qreal x3, y3;
    qreal a = x1 - x2;
    qreal b = y1 - y2;
    if(reverse) {
        x3 = x2 - b;
        y3 = y2 + a;
    } else {
        x3 = x2 + b;
        y3 = y2 - a;
    }
    if(width == -1.0)
        return QPointF(x3, y3);
    else
        return QPointF(pointOnRay(B, QPointF(x3, y3), width));
}

static QVector<qreal> firstControlPoints(const QVector<qreal>& vector)
{
    QVector<qreal> result;

    int count = vector.count();
    result.resize(count);
    result[0] = vector[0] / 2.0;

    QVector<qreal> temp;
    temp.resize(count);
    temp[0] = 0;

    qreal b = 2.0;

    for (int i = 1; i < count; i++) {
        temp[i] = 1 / b;
        b = (i < count - 1 ? 4.0 : 3.5) - temp[i];
        result[i] = (vector[i] - result[i - 1]) / b;
    }

    for (int i = 1; i < count; i++)
        result[count - i - 1] -= temp[count - i] * result[count - i];

    return result;
}
    
/*!
  Calculates control points which are needed by QPainterPath.cubicTo function to draw the cubic Bezier cureve between two points.
*/
static QVector<QPointF> calculateControlPoints(const QVector<QPointF> &points)
{
    QVector<QPointF> controlPoints;
    controlPoints.resize(points.count() * 2 - 2);

    int n = points.count() - 1;

    if (n == 1) {
        //for n==1
        controlPoints[0].setX((2 * points[0].x() + points[1].x()) / 3);
        controlPoints[0].setY((2 * points[0].y() + points[1].y()) / 3);
        controlPoints[1].setX(2 * controlPoints[0].x() - points[0].x());
        controlPoints[1].setY(2 * controlPoints[0].y() - points[0].y());
        return controlPoints;
    }

    // Calculate first Bezier control points
    // Set of equations for P0 to Pn points.
    //
    //  |   2   1   0   0   ... 0   0   0   ... 0   0   0   |   |   P1_1    |   |   P0 + 2 * P1             |
    //  |   1   4   1   0   ... 0   0   0   ... 0   0   0   |   |   P1_2    |   |   4 * P1 + 2 * P2         |
    //  |   0   1   4   1   ... 0   0   0   ... 0   0   0   |   |   P1_3    |   |   4 * P2 + 2 * P3         |
    //  |   .   .   .   .   .   .   .   .   .   .   .   .   |   |   ...     |   |   ...                     |
    //  |   0   0   0   0   ... 1   4   1   ... 0   0   0   | * |   P1_i    | = |   4 * P(i-1) + 2 * Pi     |
    //  |   .   .   .   .   .   .   .   .   .   .   .   .   |   |   ...     |   |   ...                     |
    //  |   0   0   0   0   0   0   0   0   ... 1   4   1   |   |   P1_(n-1)|   |   4 * P(n-2) + 2 * P(n-1) |
    //  |   0   0   0   0   0   0   0   0   ... 0   2   7   |   |   P1_n    |   |   8 * P(n-1) + Pn         |
    //
    QVector<qreal> vector;
    vector.resize(n);

    vector[0] = points[0].x() + 2 * points[1].x();


    for (int i = 1; i < n - 1; ++i)
        vector[i] = 4 * points[i].x() + 2 * points[i + 1].x();

    vector[n - 1] = (8 * points[n - 1].x() + points[n].x()) / 2.0;

    QVector<qreal> xControl = firstControlPoints(vector);

    vector[0] = points[0].y() + 2 * points[1].y();

    for (int i = 1; i < n - 1; ++i)
        vector[i] = 4 * points[i].y() + 2 * points[i + 1].y();

    vector[n - 1] = (8 * points[n - 1].y() + points[n].y()) / 2.0;

    QVector<qreal> yControl = firstControlPoints(vector);

    for (int i = 0, j = 0; i < n; ++i, ++j) {

        controlPoints[j].setX(xControl[i]);
        controlPoints[j].setY(yControl[i]);

        j++;

        if (i < n - 1) {
            controlPoints[j].setX(2 * points[i + 1].x() - xControl[i + 1]);
            controlPoints[j].setY(2 * points[i + 1].y() - yControl[i + 1]);
        } else {
            controlPoints[j].setX((points[n].x() + xControl[n - 1]) / 2);
            controlPoints[j].setY((points[n].y() + yControl[n - 1]) / 2);
        }
    }
    return controlPoints;
}



QPainterPath CUtil::splineFromPoints(const QVector<QPointF> &points)
{
    QPainterPath splinePath;
    QVector<QPointF> controlPoints;
    if (points.count() >= 2)
        controlPoints = calculateControlPoints(points);

    if ((points.size() < 2) || (controlPoints.size() < 2)) {
        return splinePath;
    }

    Q_ASSERT(points.count() * 2 - 2 == controlPoints.count());

    splinePath.moveTo(points.at(0));
    for (int i = 0; i < points.size() - 1; i++) {
        const QPointF &point = points.at(i + 1);
        splinePath.cubicTo(controlPoints[2 * i], controlPoints[2 * i + 1], point);
    }
    return splinePath;
}



static std::vector<double> getFirstControlPoints(const std::vector<double> &rhs)
{
    int n = (int) rhs.size();
    std::vector<double> x(n, 0);
    std::vector<double> tmp(n, 0);

    double b = 2.0;
    x[0] = rhs[0] / b;
    for (int i=1; i<n; ++i) {
        tmp[i] = 1 / b;
        b = (i < n - 1 ? 4.0 : 3.5) - tmp[i];
        x[i] = (rhs[i] - x[i - 1]) / b;
    }

    for (int i = 1; i < n; i++)
        x[n - i - 1] -= tmp[n - i] * x[n - i]; // Backsubstitution.

    return x;
}

static void getCurveControlPoints(const QVector<QPointF> &knots,
                                  QVector<QPointF> &firstControlPoints,
                                  QVector<QPointF> &secondControlPoints)
{
    const int n = knots.size()-1;
    Q_ASSERT(n >= 1);
    firstControlPoints.clear();
    secondControlPoints.clear();

    if (n==1) {
        firstControlPoints.resize(1);
        firstControlPoints[0].setX( (2 * knots[0].x() + knots[1].x()) / 3 );
        firstControlPoints[0].setY( (2 * knots[0].y() + knots[1].y()) / 3 );

        secondControlPoints.resize(1);
        secondControlPoints[0].setX( 2 * firstControlPoints[0].x() - knots[0].x() );
        secondControlPoints[0].setY( 2 * firstControlPoints[0].y() - knots[0].y() );
        return;
    }

    std::vector<double> rhs(n);

    for (int i=1; i < n-1; ++i)
        rhs[i] = 4 * knots[i].x() + 2 * knots[i+1].x();
    rhs[0] = knots[0].x() + 2 * knots[1].x();
    rhs[n-1] = (8 * knots[n-1].x() + knots[n].x()) / 2.0;
    std::vector<double> x = getFirstControlPoints(rhs);

    for (int i=1; i < n-1; ++i)
        rhs[i] = 4 * knots[i].y() + 2 * knots[i+1].y();
    rhs[0] = knots[0].y() + 2 * knots[1].y();
    rhs[n-1] = (8 * knots[n-1].y() + knots[n].y()) / 2.0;
    std::vector<double> y = getFirstControlPoints(rhs);

    firstControlPoints.resize(n);
    secondControlPoints.resize(n);
    for (int i=0; i<n; ++i) {
        firstControlPoints[i] = QPointF(x[i], y[i]);
        if (i < n-1) {
            secondControlPoints[i] = QPointF(2 * knots[i+1].x() - x[i+1], 2 * knots[i+1].y() - y[i + 1]);
        } else {
            secondControlPoints[i] = QPointF((knots[n].x() + x[n-1]) / 2, (knots[n].y() + y[n-1]) / 2);
        }
    }
}


QPainterPath CUtil::splineFromPoints2(const QVector<QPointF> &points) {

    QPainterPath path;
    int nSegments = points.size();
    if (nSegments >= 2) {
    
        QVector<QPointF> ctrl0;
        QVector<QPointF> ctrl1;
        getCurveControlPoints(points, ctrl0, ctrl1);
        
        QPointF startPoint = points.at(0);
        for (int i=0; i < nSegments-1; ++i) {
            path.moveTo(startPoint);
            path.cubicTo(ctrl0.at(i), ctrl1.at(i), points.at(i+1));
            startPoint = points.at(i+1);
        }
    }
    return path;
}


void CUtil::paintSpline(QPainter &painter, const QVector<QPointF> &points) {
    
    int nSegments = points.size();
    if (points.size() < 2)
        return;
    
    QVector<QPointF> ctrl0;
    QVector<QPointF> ctrl1;
    getCurveControlPoints(points, ctrl0, ctrl1);

    QPen pen;
    pen.setColor("lime");
    pen.setStyle(Qt::SolidLine);
    pen.setWidth(1);
    painter.setPen(pen);
    painter.setBrush(Qt::NoBrush);
    QPointF startPoint = points.at(0);
    for (int i=0; i < nSegments; ++i) {
        QPainterPath path;
        path.moveTo(startPoint);
        path.cubicTo(ctrl0.at(i), ctrl1.at(i), points.at(i+1));
        painter.drawPath(path);
        startPoint = points.at(i+1);
    }    
}

bool CUtil::QRect_contains_QRect(const QRect &rect1, const QRect &rect2, bool proper) {
    if (rect1.isNull() || rect2.isNull())
        return false;

    int x1 = rect1.x();
    int y1 = rect1.y();
    int x2 = rect1.bottomRight().x();
    int y2 = rect1.bottomRight().y();
    int _x1 = rect2.x();
    int _y1 = rect2.y();
    int _x2 = rect2.bottomRight().x();
    int _y2 = rect2.bottomRight().y();

    int l1 = x1;
    int r1 = x1;
    if (x2 - x1 + 1 < 0)
        l1 = x2;
    else
        r1 = x2;

    int l2 = _x1;
    int r2 = _x1;
    if (_x2 - _x1 + 1 < 0)
        l2 = _x2;
    else
        r2 = _x2;

    if (proper) {
        if (l2 <= l1 || r2 >= r1)
            return false;
    } else {
        if (l2 < l1 || r2 > r1)
            return false;
    }

    int t1 = y1;
    int b1 = y1;
    if (y2 - y1 + 1 < 0)
        t1 = y2;
    else
        b1 = y2;

    int t2 = _y1;
    int b2 = _y1;
    if (_y2 - _y1 + 1 < 0)
        t2 = _y2;
    else
        b2 = _y2;

    if (proper) {
        if (t2 <= t1 || b2 >= b1)
            return false;
    } else {
        if (t2 < t1 || b2 > b1)
            return false;
    }

    return true;

}


QString CUtil::joinPath(const QString& path1, const QString& path2, const QString& path3, const QString& path4, const QString& path5, const QString& path6)
{
    if (!path3.isNull() && !path4.isNull() && !path5.isNull() && !path5.isNull()) {
        return QDir::cleanPath(path1 + QDir::separator() + path2 + QDir::separator() + path3 + QDir::separator() + path4 + QDir::separator() + path5 + QDir::separator() + path6);
    } else if (!path3.isNull() && !path4.isNull() && !path5.isNull()) {
        return QDir::cleanPath(path1 + QDir::separator() + path2 + QDir::separator() + path3 + QDir::separator() + path4 + QDir::separator() + path5);
    } else if (!path3.isNull() && !path4.isNull()) {
        return QDir::cleanPath(path1 + QDir::separator() + path2 + QDir::separator() + path3 + QDir::separator() + path4);
    } else if(!path3.isNull()) {
        return QDir::cleanPath(path1 + QDir::separator() + path2 + QDir::separator() + path3);
    } else {
        return QDir::cleanPath(path1 + QDir::separator() + path2);
    }
}

    
bool CUtil::copyRecursively(QString sourceFolder, QString destFolder)
{
    bool success = false;
    QDir sourceDir(sourceFolder);

    if(!sourceDir.exists())
        return false;

    QDir destDir(destFolder);
    if(!destDir.exists())
        destDir.mkdir(destFolder);

    QStringList files = sourceDir.entryList(QDir::Files);
    for(int i = 0; i< files.count(); i++) {
        QString srcName = sourceFolder + QDir::separator() + files[i];
        QString destName = destFolder + QDir::separator() + files[i];
        success = QFile::copy(srcName, destName);
        if(!success)
            return false;
    }

    files.clear();
    files = sourceDir.entryList(QDir::AllDirs | QDir::NoDotAndDotDot);
    for(int i = 0; i< files.count(); i++)
    {
        QString srcName = sourceFolder + QDir::separator() + files[i];
        QString destName = destFolder + QDir::separator() + files[i];
        success = copyRecursively(srcName, destName);
        if(!success)
            return false;
    }

    return true;
}



//#include <QtGui/5.12.0/QtGui/qpa/qplatformwindow.h>
// https://github.com/ekke/c2gQtWS_x/blob/master/qml/main.qml
void CUtil::onScreenOrientationChanged() {
    if(_instance == NULL) {
        qDebug() << "onScreenOrientationChanged() _instance is NULL!!!";
        return;
    }
    QRect rect = screenSize();
//    qDebug() << "orientationChanged:" << rect;
    m_unsafeArea->configureDevice(rect.width(), rect.height(), devicePixelRatio());
    m_unsafeArea->orientationChanged(screenOrientation());
    QMargins margins = QMargins(m_unsafeArea->unsafeLeftMargin(),
                                m_unsafeArea->unsafeTopMargin(),
                                m_unsafeArea->unsafeRightMargin(),
                                m_unsafeArea->unsafeBottomMargin());
    if(margins != m_unsafeAreaMargins) {
        m_unsafeAreaMargins = margins;
        emit safeAreaMarginsChanged(margins);
    } 
    Qt::ScreenOrientation orientation = CUtil::screenOrientation();
    emit CUtil::instance()->screenOrientationChanged(orientation);
}


void CUtil::showCriticalMessageBox(QString message) {
    QMessageBox::critical(QApplication::activeWindow(), "", message);
}


// TimelineDelegateBase::TimelineDelegateBase(QObject *parent)
//     : QStyledItemDelegate(parent),
//       m_drawGrid(true) {
// }

// void TimelineDelegateBase::paint(QPainter *painter,
//                                  const QStyleOptionViewItem &option,
//                                  const QModelIndex &index) const {
//     QStyledItemDelegate::paint(painter, option, index);
//     if(m_drawGrid && index.column() > 0) { // buddies column
//         painter->save();
//         painter->setPen(m_gridPen);
//         painter->drawLine(option.rect.bottomLeft(), option.rect.bottomRight());
//         painter->drawLine(option.rect.bottomLeft(), option.rect.topLeft());
//         painter->restore();
//     }
// }






PathItemBase::PathItemBase(QGraphicsItem *parent) :
    QGraphicsObject(parent),
    m_delegate(0),
    m_usingDefaultDelegate(true),
    m_shapeIsBoundingRect(false),
    m_shapeIncludesChildrenRect(false),
    m_shapeMargin(5.0),
    m_shapePathIsClosed(true),
    m_showPathItemShapes(false)
{
    m_delegate = new PathItemDelegate(this);
    m_usingDefaultDelegate = true;
    // qDebug() << "PathItemBase()" << this->objectName();
}

// PathItemBase::~PathItemBase() {

//     // print_stack_trace();
//     // // print_python_stack_trace();

//     // qDebug() << "~PathItemBase() objectName: " << this->objectName() << " className: " << this->metaObject()->className() << " parentItem: " << this->parentItem() << " parent: " << this->parent();

//     // emit deleting(this);
    

// }

void PathItemBase::dev_printCStackTrace() {
#if TARGET_OS_OSX
    print_stack_trace();
#endif
}

void PathItemBase::setPathItemDelegate(PathItemDelegate *d)
{
    if(d != m_delegate) {
        if(m_usingDefaultDelegate && m_delegate) {
            delete m_delegate;
        }
        m_delegate = d;
        m_usingDefaultDelegate = false;
    }
}

void PathItemBase::updatePathItemData()
{
    if(m_shapeIsBoundingRect) {
        m_shape = QPainterPath();
        m_shape.addRect(m_path.controlPointRect());
        if(m_shapeIncludesChildrenRect) {
            m_shape.addRect(childrenBoundingRect());
        }
    } else if(!m_shapePathIsClosed) {
        m_shape = QPainterPath(m_path);
        m_shape.connectPath(m_path.toReversed());
    } else {
        m_shape = QPainterPath(m_path);
    }
    if(m_shapeMargin > 0) {
        QPen pen(m_pen);
        pen.setWidthF(pen.width() * m_shapeMargin);
        m_shape = CUtil::strokedPath(m_shape, pen);
    }
    m_boundingRect = m_shape.controlPointRect();
}

void PathItemBase::setPath(const QPainterPath &path)
{
    if(path != m_path) {
        m_path = path;
        updatePathItemData();
    }
}

void PathItemBase::setPen(const QPen &pen)
{
    if(pen != m_pen) {
        m_pen = pen;
        updatePathItemData();
    }
}

void PathItemBase::setBrush(const QBrush &brush)
{
    if(brush != m_brush) {
        m_brush = brush;
        updatePathItemData();
    }
}

void PathItemBase::paint(QPainter *painter, const QStyleOptionGraphicsItem *option, QWidget *widget)
{
    if(m_delegate) {
        m_delegate->paint(painter, option, widget);
    }
}

PathItemDelegate::PathItemDelegate(PathItemBase *pathItem) :
    m_pathItem(pathItem)
{
    pathItem->setPathItemDelegate(this);
}

void PathItemDelegate::paint(QPainter *painter, const QStyleOptionGraphicsItem *, QWidget *)
{
    if(!pathItem()->m_showPathItemShapes) {
        painter->save();
        QColor selectionColor;
        if(CUtil::instance()) {
            selectionColor = CUtil::instance()->appleControlAccentColor();
        } else {
            selectionColor = QColor(255, 0, 0, 150);
        }
        if(pathItem()->isSelected()) {
            selectionColor.setAlphaF(.6);
            QPen pen(selectionColor);
            pen.setWidth(pen.width() * 10);
            painter->setPen(pen);
            painter->setBrush(Qt::transparent);
            QPainterPathStroker stroker(pen);
            stroker.setCapStyle(Qt::RoundCap);
            QPainterPath stroke = stroker.createStroke(pathItem()->path());
            painter->drawPath(stroke);
        }
        painter->setPen(pathItem()->pen());
        painter->setBrush(pathItem()->brush());
        painter->drawPath(pathItem()->path());
        painter->restore();
    } else {
        painter->save();
        // paint bounding rect
        QPen pen;
        if(pathItem()->isSelected()) {
            pen.setColor(Qt::green);
        } else {
            pen.setColor(Qt::red);
        }
        pen.setStyle(Qt::DotLine);
        painter->setPen(pen);
        painter->drawPath(pathItem()->shape());
        painter->restore();
        
        // paint bounding rect
        painter->save();
        pen.setColor(Qt::blue);
        painter->setPen(pen);
        painter->drawRect(pathItem()->boundingRect());
        painter->restore();
    }
}

PersonDelegate::PersonDelegate(PathItemBase *pathItemBase) :
    PathItemDelegate(pathItemBase),
    m_primary(false),
    m_forceNoPaintBackground(false)
{
}

void PersonDelegate::paint(QPainter *painter, const QStyleOptionGraphicsItem *option, QWidget *widget)
{
    if(!pathItem()->dev_showPathItemShapes()) {
        // paint background before base class
        if(m_primary && (m_gender == "male" || m_gender == "female") && !m_forceNoPaintBackground) { // hack
            painter->save();
            painter->setBrush(pathItem()->brush());
            if(m_gender == "male") {
                painter->drawRect(pathItem()->path().controlPointRect());
            } else {
                painter->drawEllipse(pathItem()->path().controlPointRect());
            }
            painter->restore();
        }
    }

    PathItemDelegate::paint(painter, option, widget);
}
