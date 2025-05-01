#include "_pkdiagram.h"
#include <QApplication>
#include <QDesktopWidget>
#include <QFileDialog>
#include <QDebug>
#include <QStandardPaths>
#include <QFileSystemWatcher>
#include <QProcess>
#include <QMessageBox>

#ifdef Q_OS_WINDOWS
#include <windows.h>    // For AllocConsole()
#include <fcntl.h>      // For _open_osfhandle()
#include <io.h>         // For _fdopen(), write()
#include <shlwapi.h>
#include <QMessageBox>
#include <QtGui/private/qzipreader_p.h>
#endif

#ifdef PK_USE_SPARKLE
// #include <winsparkle.h>
#endif


class FDDocumentWin : public FDDocument {
    
    QUrl m_url;
    QByteArray m_diagramData;
    QStringList m_fileList;
    bool m_dirty;

public:

	FDDocumentWin(QObject *parent, const QUrl &url) :
    FDDocument(parent),
    m_url(url),
    m_dirty(false) {
        QString picklePath = url.toLocalFile() + "\\" + CUtil::PickleFileName;
        QFile pickle(picklePath);
        pickle.open(QIODevice::ReadOnly);
        m_diagramData = pickle.readAll();
        pickle.close();
    }
	~FDDocumentWin() { }

	QUrl url() const { return m_url; }
	QByteArray diagramData() const { return m_diagramData; }
	void updateDiagramData(const QByteArray &data) {
        m_diagramData = data;
        m_dirty = true; // so save??
    }
    
    QStringList fileList() const {
        updateFileList();
        return m_fileList;
    }
    
	QStringList updateFileList() const {
        bool ok = false;
        QStringList ret;
        QDir peopleDir(CUtil::joinPath(url().toLocalFile(), "People"));
        foreach(QFileInfo info, peopleDir.entryInfoList()) {
            int personId = info.fileName().toInt(&ok);
            if(info.isDir() && ok) {
                foreach(QFileInfo info2, info.absoluteDir().entryInfoList()) {
                    if(info2.isDir() && info2.fileName() == "Events") {
                        foreach(QFileInfo info3, info2.absoluteDir().entryInfoList()) {
                            ok = false;
							int eventId = info3.fileName().toInt(&ok);
                            if(info3.isDir() && ok) {
                                foreach(QFileInfo eventFile, info3.absoluteDir().entryInfoList()) {
                                    if(eventFile.isFile()) {
                                        ret << (QString() + personId + QDir::separator() + eventId + QDir::separator() + info.fileName());
                                    }
                                }
                            }
                        }
                    } else if(info2.isFile()) {
                        ret << (QString() + personId + QDir::separator() + info2.fileName());
                    }
                }
            }
        }
        return ret;
    }
    
	void save(bool quietly = false) {
        if(m_dirty) {
            QString picklePath = CUtil::joinPath(m_url.toLocalFile(), CUtil::PickleFileName);
            QFile pickleFile(picklePath);
            pickleFile.open(QIODevice::WriteOnly);
            pickleFile.write(m_diagramData);

            // Desktop.ini
            QFile desktopIni_out(CUtil::joinPath(m_url.toLocalFile(), "Desktop.ini"));
            if(!desktopIni_out.exists()) {
                QFile desktopIni_in(CUtil::qrc("misc/Desktop.ini"));
                if (desktopIni_in.open(QIODevice::ReadOnly)) {
                    if (desktopIni_out.open(QIODevice::WriteOnly)) {
                        desktopIni_out.write(desktopIni_in.readAll());
                        desktopIni_out.close();
                    }
                    else {
                        qDebug() << "Could not open" << CUtil::joinPath(m_url.toLocalFile(), "Desktop.ini") << "for writing";
                    }
                } else {
                    qDebug() << "Could not open" << CUtil::qrc("misc/Desktop.ini") << "for reading";
                }
            }

            // PKDiagram-Filled.ico
            QString ico_out_path = CUtil::joinPath(m_url.toLocalFile(), "PKDiagram-Filled.ico");
            QFile ico_out(ico_out_path);
            if(!ico_out.exists()) {
                QFile ico_in(CUtil::qrc("misc/PKDiagram-Filled.ico"));
                if (ico_in.open(QIODevice::ReadOnly)) {
                    if (ico_out.open(QIODevice::WriteOnly)) {
                        ico_out.write(ico_in.readAll());
                        ico_out.close();                        
#ifdef Q_OS_WINDOWS
                        SetFileAttributesW((LPCWSTR) ico_out_path.utf16(), FILE_ATTRIBUTE_HIDDEN);
#endif
                    } else {
                        qDebug() << "Could not open" << CUtil::joinPath(m_url.toLocalFile(), "PKDiagram-Filled.ico") << "for writing";
                    }
                } else {
                    qDebug() << "Could not open" << CUtil::qrc("misc/PKDiagram-Filled.ico") << "for reading";
                }
            }

#ifdef Q_OS_WINDOWS
            const LPCWSTR bundlePath = (LPCWSTR) m_url.toLocalFile().utf16();
            if(!PathMakeSystemFolderW(bundlePath)) {
                qDebug() << "PathMakeSystemFolderW() failed for" << m_url.toLocalFile();
            }
#endif

            m_dirty = false;
            if(!quietly) {
                emit saved();
            }
        }
    }
    
	void saveAs(const QUrl &url) {
        QFileInfo targetInfo(url.toLocalFile());
        if(targetInfo.exists() && QDir(url.toLocalFile()).rmpath(".") == false) {
            qDebug() << "Could not overwrite file " << url.toLocalFile();
            return;
        }
        QString bundleName = QDir(url.toLocalFile()).dirName();
        QDir bundleDir(url.toLocalFile());
        bundleDir.cdUp();
        bundleDir.mkpath(bundleName);
        bundleDir.cd(bundleName);
        QString picklePath = CUtil::joinPath(m_url.toLocalFile(), CUtil::PickleFileName);
        QFile pickleFile(picklePath);
        pickleFile.open(QIODevice::WriteOnly);
        pickleFile.write(m_diagramData);
        m_dirty = false;
        emit savedAs(url);
    }
    
	void close() { }
    
	void addFile(const QString &src, const QString &relativePath) {
        if(m_fileList.contains(relativePath)) {
            qDebug() << "File already exists:" << relativePath;
        }
        QFile iFile(src);
        if(iFile.open(QIODevice::ReadOnly) == false) {
            qDebug() << "Could not read from file:" << src;
        }
        QByteArray data = iFile.readAll();
        iFile.close();
        QString oPath = CUtil::joinPath(m_url.toLocalFile(), relativePath);
		QFile oFile(oPath);
        if(oFile.open(QIODevice::WriteOnly)) {
            oFile.write(data);
            oFile.close();
            m_fileList << relativePath;
            m_dirty = true;
            emit fileAdded(relativePath);
        } else {
            qDebug() << "Could not open file for writing:" << relativePath;
        }
    }
	void removeFile(const QString &relativePath) {
        if(!m_fileList.contains(relativePath)) {
            qDebug() << "File entry not found for:" << relativePath;
            return;
        }
        QFile f(relativePath);
        if(f.remove() == false) {
            qDebug() << "Could not delete file:" << relativePath;
            return;
        }
        m_fileList.removeAll(relativePath);
        emit fileRemoved(relativePath);
    }
	void renameFile(const QString &oldPath, const QString &newPath) {
        if(!m_fileList.contains(oldPath)) {
            qDebug() << "File entry not found for:" << oldPath;
            return;
        }
        if(QFile(oldPath).rename(newPath) == false) {
            qDebug() << "Could not rename file" << oldPath << "to" << newPath;
        }
    }
};


// -------------------------------------------------------------------------------
//  CUtil
//
//  Windows implementation
// -------------------------------------------------------------------------------

#if PK_USE_SPARKLE
#ifdef Q_OS_WINDOWS
static void(*win_sparkle_set_appcast_url)(const char*) = NULL;
static void(*win_sparkle_init)() = NULL;
static void(*win_sparkle_check_update_without_ui)() = NULL;
static void(*win_sparkle_cleanup)() = NULL;
typedef int (*win_sparkle_user_run_installer_callback_t)(const wchar_t *);
static void (*win_sparkle_set_user_run_installer_callback)(win_sparkle_user_run_installer_callback_t) = NULL;
#endif
#endif


class CUtilWin : public CUtil {
    
    bool m_bInitialized;
    QString m_forcedDocRoot;
    QString m_documentsFolderPath;
    QList<QUrl> m_fileList;
    QTimer* m_updateQuitTimer;

public:

    static void logAndNotifyUser(QString msg) {
        qDebug() << msg;
        QMessageBox::critical(NULL, "Failed to install update.", msg);
    }

#ifdef Q_OS_WINDOWS
    static int OnWinsparkleZipFileDownloaded(const wchar_t *_updateFilePath) {        
        qint64 pid = 0;
        QProcess process;
        QProcess newProcess;
        QString newExePath;
        QFile downloadedExe;
        QStringList errorString;

        QString updateFilePath = QString::fromWCharArray(_updateFilePath);
        QString curExePath = QCoreApplication::applicationFilePath();
        QString curExeDir = QFileInfo(curExePath).absolutePath();
        QString curExeFileName = QFileInfo(curExePath).fileName();
        QString zipDlPath = QFileInfo(updateFilePath).absolutePath();
        QString curExeDest = zipDlPath + "\\" + curExeFileName + ".old";
        qDebug() << "updateFilePath:" << updateFilePath;
        qDebug() << "curExePath:" << curExePath << "curExeFileName:" << curExeFileName;
        qDebug() << "zipDlPath:" << zipDlPath << "curExeDest:" << curExeDest;
        qDebug() << "Moving current exe into temporary folder. CURRENT" << curExePath << "DESTINATION:" << curExeDest;
        if (!QFile::rename(curExePath, curExeDest)) {
            errorString << "Could not move current app exe to temp folder. CURRENT" << curExePath << "DESTINATION:" << curExeDest;
            goto updateError;
        }
        qDebug() << "Decompressing:" << updateFilePath;
        process.setWorkingDirectory(zipDlPath);
        process.setProcessChannelMode(QProcess::MergedChannels);
        process.start("unzip", QStringList() << updateFilePath);
        process.waitForFinished();
        process.close();
        // wasn't returning correctly
        if (process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0) {
           errorString << "error unzipping exe download: exitStatus():" << QString::number(process.exitStatus()) << "error():" << QString::number(process.error()) << "exitCode:" << QString::number(process.exitCode());
           goto updateError;
        }
        else {
            qDebug() << "Unzip finished without error:" << process.readAllStandardOutput();
        }

        if(!QZipReader(updateFilePath).extractAll(zipDlPath)) {
            errorString << "Error unzipping" <<  updateFilePath << "to folder" << zipDlPath;
            goto updateError;
        }

        qDebug() << "Listing download folder:" << zipDlPath;
        foreach(QFileInfo fileInfo, QDir(zipDlPath).entryInfoList()) {
            qDebug() << "    " << fileInfo;
        }

        newExePath = zipDlPath + "\\Family Diagram.exe";
        if (!QFileInfo(newExePath).exists()) {
            errorString << "Downloaded zip file was not unzipped successfully.";
            goto updateError;
        }

        qDebug() << "Moving downloaded exe into current exe's old location. NEW:" << newExePath << " CURRENT:" << curExePath;
        qDebug() << "Source exists?" << QFileInfo(newExePath).exists();
        downloadedExe.setFileName(newExePath);
        if (!downloadedExe.rename(curExePath)) {
            errorString << "Could not move downloaded exe to it's final destination. NEW:" << newExePath << " CURRENT:" << curExePath << "ERROR:" << downloadedExe.errorString();
            goto updateError;
        }

        qDebug() << "Starting new exe:" << curExePath;
        if (!newProcess.startDetached(curExePath, QStringList(), curExeDir, &pid)) {
#ifdef Q_OS_WINDOWS
            errorString << "Could not start updated exe:" << curExePath;
#endif
            goto updateError;
        }

#ifdef Q_OS_WINDOWS
        qDebug() << "Exiting current exe.";
        ExitProcess(0);
#endif
//        ((CUtilWin*) instance())->m_updateQuitTimer->start();
            //QTimer::singleShot(500, QApplication::quit);

    updateError:
        QString message = QString("There was an problem updating the app. Please contact support here: https://alaskafamilysystems.com/family-diagram/support/\n\nERROR MESSAGE: ") + errorString.join(" ");
        emit CUtil::instance()->errorMessageReceived(message);
        return 1;
    }

#endif

    CUtilWin(QObject *parent) :
    CUtil(parent),
    m_bInitialized(false) {
    }
    
    bool isInitialized() const {
        return m_bInitialized;
    }
    
    void init() {
        if (!m_bInitStarted) {
            qSetMessagePattern("%{file}(%{line}): %{message}");

            connect(this, SIGNAL(errorMessageReceived(QString)), this, SLOT(showCriticalMessageBox(QString)));
            
			m_documentsFolderPath = QStandardPaths::standardLocations(QStandardPaths::DocumentsLocation)[0];
			m_fsWatcher->addPath(documentsFolderPath());
            updateLocalFileList();

#ifdef PK_USE_SPARKLE
#ifdef Q_OS_WINDOWS

            m_updateQuitTimer = new QTimer(this);
            m_updateQuitTimer->setInterval(500);
            m_updateQuitTimer->callOnTimeout(QApplication::instance(), &QApplication::quit, Qt::QueuedConnection);


            QString curExePath = QCoreApplication::applicationFilePath();
            QString curExeDir = QFileInfo(curExePath).absolutePath();

            // QStringList extraFiles = {
            //     "misc/WinSparkle.dll",
            // };
            // foreach(QString qrc_filePath, extraFiles) {

            //     qrc_filePath = CUtil::qrc(qrc_filePath);
            //     QFile qrc_file(qrc_filePath);
            //     QString dest_filePath = QDir::cleanPath(curExeDir + "/" + QFileInfo(qrc_filePath).fileName());
            //     QString dest_fileName = QFileInfo(dest_filePath).fileName();
            //     QFile dest_file(dest_filePath);

            //     if (!qrc_file.exists()) {
            //         qDebug() << "Expected to find:" << qrc_filePath;
            //         continue;
            //     }

            //     if (!qrc_file.open(QIODevice::ReadOnly)) {
            //         qDebug() << "Could not open" << qrc_filePath << "for reading";
            //         continue;
            //     }

            //     QByteArray qrc_data = qrc_file.readAll();

            //     // Delete if updating
            //     bool allGood = false;
            //     if (dest_file.exists()) {
            //         qDebug() << "Found" << dest_fileName << ", checking contents..";
            //         if (!dest_file.open(QIODevice::ReadOnly)) {
            //             qDebug() << "Could not open" << dest_filePath << "for reading.";
            //         }
            //         QByteArray dest_data = dest_file.readAll();
            //         dest_file.close();
            //         if (qrc_data != dest_data) {
            //             qDebug() << dest_fileName << " is out of date, updating...";
            //             if (!QFile::rename(dest_filePath, dest_filePath + ".bak")) {
            //                 qDebug() << "Error renaming" << dest_filePath << "to" << dest_filePath + ".bak";
            //             }
            //         } else {
            //             allGood = true;
            //         }
            //     }

            //     if (!dest_file.open(QIODevice::WriteOnly)) {
            //         qDebug() << "Could not open" << dest_filePath << "for writing.";
            //         continue;
            //     }

            //     if (!allGood) {
            //         qDebug() << "Writing " << dest_filePath;
            //         dest_file.write(qrc_data);
            //         dest_file.close();
            //         qDebug() << "Wrote" << dest_filePath;
            //     }
            // }

            // Load WinSparkle.dll
            QString appDataDir = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
            QString winSparkleDllPath = appDataDir + "/misc/WinSparkle.dll";
            if (QFile(winSparkleDllPath).exists()) {
                qDebug() << "Loading" << winSparkleDllPath;
                const char* dllPath = QDir::toNativeSeparators(winSparkleDllPath).toLatin1().constData();
                HMODULE lib = LoadLibrary(dllPath);
                if (lib == NULL) {
                    wchar_t buf[256];
                    FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                        NULL, GetLastError(), MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
                        buf, (sizeof(buf) / sizeof(wchar_t)), NULL);
                    QString ee = QString::fromWCharArray(buf);
                    qDebug() << ee;
                }

                win_sparkle_set_appcast_url = (void(*)(const char*)) GetProcAddress(lib, "win_sparkle_set_appcast_url");
                win_sparkle_init = (void(*)()) GetProcAddress(lib, "win_sparkle_init");
                win_sparkle_check_update_without_ui = (void(*)()) GetProcAddress(lib, "win_sparkle_check_update_without_ui");
                win_sparkle_cleanup = (void(*)()) GetProcAddress(lib, "win_sparkle_cleanup");
                
                win_sparkle_set_user_run_installer_callback = (void(*)(win_sparkle_user_run_installer_callback_t)) GetProcAddress(lib, "win_sparkle_set_user_run_installer_callback");
                if (!win_sparkle_set_user_run_installer_callback) {
                    qDebug() << "WinSparkle dll api does not match that expected.";
                } else {
                    win_sparkle_set_user_run_installer_callback(CUtilWin::OnWinsparkleZipFileDownloaded);
                }
            }

            // Initialize WinSparkle as soon as the app itself is initialized, right
            // before entering the event loop:
#if PK_ALPHA_BUILD
            qDebug() << "PK_ALPHA_BUILD";
            if (win_sparkle_set_appcast_url) {
                // win_sparkle_set_appcast_url("https://api.appcenter.ms/v0.1/public/sparkle/apps/a7be6c1a-599c-4341-923c-18441ca8a92e");
                win_sparkle_set_appcast_url("https://familydiagram.com/appcast_windows_alpha.xml");
            } else {
                qDebug() << "Could not load win_sparkle_set_appcast_url";
            }
#elif PK_BETA_BUILD
            qDebug() << "PK_BETA_BUILD";
            if (win_sparkle_set_appcast_url) {
                // win_sparkle_set_appcast_url("https://api.appcenter.ms/v0.1/public/sparkle/apps/24bc1e7d-4f27-4172-a6fe-ed65ca74f5f9");
                win_sparkle_set_appcast_url("https://familydiagram.com/appcast_windows_beta.xml");
            } else {
                qDebug() << "Could not load win_sparkle_set_appcast_url";
            }
#else
            if (win_sparkle_set_appcast_url) {
                // win_sparkle_set_appcast_url("https://api.appcenter.ms/v0.1/public/sparkle/apps/dc5b20e4-6c8a-434f-9000-69eb18b2b61e");
                win_sparkle_set_appcast_url("https://familydiagram.com/appcast_windows.xml");
            } else {
                qDebug() << "Could not load win_sparkle_set_appcast_url";
            }
#endif
            if (win_sparkle_init) {
                win_sparkle_init();
            } else {
                qDebug() << "Could not load win_sparkle_init";
            }
	    
#endif
#endif // PK_USE_SPARKLE

            m_bInitStarted = true;
            m_bInitialized = true;
        }
    }
    
    void deinit() {
#ifdef PK_USE_SPARKLE
#ifdef Q_OS_WINDOWS
        delete m_updateQuitTimer;

        if(win_sparkle_cleanup) {
            win_sparkle_cleanup();
        }
        else {
            qDebug() << "Could not load win_sparkle_cleanup";
        }
#endif
#endif

        m_bInitialized = false;
    }

    void checkForUpdates() const {
#ifdef PK_USE_SPARKLE
#ifdef Q_OS_WINDOWS
        qDebug() << "checkForUpdates()";
        if (win_sparkle_check_update_without_ui) {
            qDebug() << "win_sparkle_check_update_without_ui()";
            win_sparkle_check_update_without_ui();
        }
        else {
            qDebug() << "Could not load win_sparkle_check_update_with_ui";
        }
#endif
#else
	qDebug() << "No update framework configured";
#endif
    }

    void forceDocsPath(const QString &path) {
        if(!documentsFolderPath().isEmpty()) {
            m_fsWatcher->removePath(documentsFolderPath());
        }
        m_forcedDocRoot = path;
        if(!documentsFolderPath().isEmpty()) {
            m_fsWatcher->addPath(documentsFolderPath());
        }
        updateLocalFileList();
    }   

    QString documentsFolderPath() const {
        if(!m_forcedDocRoot.isEmpty()) {
            return m_forcedDocRoot;
        } else {
            return m_documentsFolderPath;
        }
    }
    
    void openExistingFile(const QUrl &url) {
        //if(!QFileInfo(url.toLocalFile()).isFile()) {
        //    qDebug() << "File does not exist:" << url.toLocalFile();
        //}
        FDDocument *fdDoc = new FDDocumentWin(instance(), url);
        emit fileOpened(fdDoc);
    }
    
    void updateLocalFileList() { // called by QFileSystemWatcher
        QList<QUrl> newEntries;
        foreach(QFileInfo info, QDir(documentsFolderPath()).entryInfoList()) {
            if(info.isDir() && info.suffix() == CUtil::FileExtension) {
                newEntries << QUrl::fromLocalFile(info.filePath());
            }
        }

        QList<QUrl> oldEntries = m_fileList;
        bool found = false;
        foreach(QUrl oldEntry, oldEntries) {
            found = false;
            foreach(QUrl updatedEntry, newEntries) {
                if(oldEntry.toLocalFile() == updatedEntry.toLocalFile()) {
                    found = true;
                    break;
                }
            }
            if(!found) {
                //            NSLog(@"fileRemoved(%@)", oldEntry.relativePath);
                // qDebug() << "fileRemoved(" << oldEntry.toLocalFile() << ")";
                emit CUtil::instance()->fileRemoved(oldEntry);
            }
        }
        
        foreach(QUrl updatedEntry, newEntries) {
            found = false;
            foreach(QUrl oldEntry, oldEntries) {
                if(oldEntry.toLocalFile() == updatedEntry.toLocalFile()) {
                    found = true;
                    break;
                }
            }
            if(!found) {
                emit CUtil::instance()->fileAdded(updatedEntry, CUtil::FileIsCurrent);
            }
        }
        
        m_fileList = newEntries;
    }
    
    void dev_crash() const {
		volatile int* a = reinterpret_cast<volatile int*>(NULL);
		*a = 1;
    }
    
    QList<QUrl> fileList() const {
        return m_fileList;
    }
    
    FileStatus fileStatusForUrl(const QUrl &url) const {
        (void) url;
        return FileIsCurrent;
    }
    
    // deprecated
    void trackAnalyticsEvent(const QString eventName) {
        qDebug() << "TODO:" << eventName;
    }
    
    QString getOpenFileName() const {
//        return QFileDialog::getOpenFileName(QApplication::activeWindow());
        qDebug() << "TODO";
        return QString();
    }

    QString system(const QString &cmd) {
        QProcess process;
        process.start(cmd, QStringList());
        process.waitForFinished(-1); // will wait forever until finished
        QString out(process.readAllStandardOutput());
        QString err(process.readAllStandardError());
        qDebug() << err;
        return out;
    }
    
    bool isUIDarkMode() const {
    	return false;
    }
    QColor appleControlAccentColor(void) const {
        return Qt::red;
    }

    
};

QString CUtil::getMachineModel() {
#if PK_WIN32_BUILD
    QString make = system("wmic computersystem get model");
    QString model = system("wmic computersystem get manufacturer");
    return make + ", " + model;
#else
    return "<unknown>";
#endif
}

float CUtil::devicePixelRatio() {
    return 1.0;
}


CUtil::OperatingSystem CUtil::operatingSystem() {
    return OS_Windows;
}


QRect CUtil::screenSize() {
    QSize size = QApplication::desktop()->size();
    return QRect(0, 0, size.width(), size.height());
}

Qt::ScreenOrientation CUtil::screenOrientation() {
    return Qt::PrimaryOrientation;
}



CUtil *CUtil_create(QObject *parent) {
    return new CUtilWin(parent);
}

void CUtil::dev_printBacktrace() {
}

bool CUtil::dev_amIBeingDebugged() {
    return false;
}


void CUtil::dev_showDebugConsole() {
    qDebug() << "dev_showDebugConsole 1";
#ifdef PK_WIN32_BUILD
    qDebug() << "dev_showDebugConsole PK_WIN32_BUILD";
    if (AllocConsole()) {
        // Redirect stdout/stderr to the new console
        FILE* fp;
        freopen_s(&fp, "CONOUT$", "w", stdout);
        freopen_s(&fp, "CONOUT$", "w", stderr);
        
        // Also redirect Qt's debug output
        qInstallMessageHandler([](QtMsgType type, const QMessageLogContext& context, const QString& msg) {
            QByteArray localMsg = msg.toLocal8Bit();
            fprintf(stderr, "%s\n", localMsg.constData());
            fflush(stderr);
        });
        
        qDebug() << "Debug console attached!";
    } else {
        OutputDebugStringW(L"Failed to attach debug console!\n");
    }
#endif
}
