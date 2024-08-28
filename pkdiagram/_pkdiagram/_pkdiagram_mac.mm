#import "_pkdiagram.h"

#include <TargetConditionals.h>
#if TARGET_OS_IOS
#import <UIKit/UIKit.h>
#else
#import <AppKit/AppKit.h>
#endif

#ifdef PK_USE_APPCENTER
@import AppCenter;
@import AppCenterAnalytics;
@import AppCenterCrashes;
#endif

#ifdef PK_USE_SPARKLE
#import <Sparkle/Sparkle.h>
static NSURL *SparkleFeedURL = nil;
#endif

#ifdef PK_USE_BUGSNAG
#import <Bugsnag/Bugsnag.h>
#endif

#include <QFileInfo>
#include <QDir>
#include <QFile>
#include <QFileSystemWatcher>
#include <QGuiApplication>
#include <QDebug>
#include <QtWidgets/QtWidgets>

#include <assert.h>
#include <stdbool.h>
#include <sys/types.h>
#include <unistd.h>
#include <sys/sysctl.h>

static bool AmIBeingDebugged(void)
// Returns true if the current process is being debugged (either
// running under the debugger or has a debugger attached post facto).
{
    int                 junk;
    int                 mib[4];
    struct kinfo_proc   info;
    size_t              size;
    
    // Initialize the flags so that, if sysctl fails for some bizarre
    // reason, we get a predictable result.
    
    info.kp_proc.p_flag = 0;
    
    // Initialize mib, which tells sysctl the info we want, in this case
    // we're looking for information about a specific process ID.
    
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = getpid();
    
    // Call sysctl.
    
    size = sizeof(info);
    junk = sysctl(mib, sizeof(mib) / sizeof(*mib), &info, &size, NULL, 0);
    assert(junk == 0);
    
    // We're being debugged if the P_TRACED flag is set.
    
    return ( (info.kp_proc.p_flag & P_TRACED) != 0 );
}




@class CUtilPrivate;
@class DiagramDocument;


NSURL *URLByDeletingTrailingSlash(NSURL *url) {
    if ([url.absoluteString hasSuffix:@"/"])
        return [NSURL URLWithString:[url.absoluteString substringToIndex:url.absoluteString.length - 1]];
    else
        return url;
}

@implementation NSURL (IsEqualTesting)
- (BOOL) isEqualToURL:(NSURL*)otherURL
{
    return [[self absoluteURL] isEqual:[otherURL absoluteURL]] ||
        ([self isFileURL] && [otherURL isFileURL] &&
         ([[self path] isEqual:[otherURL path]]));
}
@end


@interface FDApplication : NSApplication
@end

@implementation FDApplication

#ifdef PK_USE_BUGSNAG
- (void)reportException:(NSException *)theException {
    NSLog(@">> FDApplication::reportException: %@", theException);
    [Bugsnag notify:theException];
    [super reportException:theException];
}
#endif

@end


// -------------------------------------------------------------------------------
//  FDDocumentPrivate
//
//  Place holder
// -------------------------------------------------------------------------------
#pragma mark -
class FDDocumentMac : public FDDocument {
    
public:
    DiagramDocument *doc;
    FDDocumentMac(QObject *parent, DiagramDocument *doc);
    ~FDDocumentMac();
    
    QUrl url();
    QByteArray diagramData() const;
    void updateDiagramData(const QByteArray &data);
    QStringList fileList() const;
    QUrl url() const;
    void save(bool quietly=false);
    void saveAs(const QUrl &);
    void close();
    void addFile(const QString &src, const QString &relativePath);
    void removeFile(const QString &relativePath);
    void renameFile(const QString &oldPath, const QString &newPath);
    
    void onDocChanged();
};

static NSString * cNSString(const char *str) {
    return [NSString stringWithCString:str encoding:NSASCIIStringEncoding];
}


static NSString * const DocumentType = @"Family Diagram";
static NSString * const FileExtension = cNSString(CUtil::FileExtension);
static NSString * const PickleFileName = cNSString(CUtil::PickleFileName);
static NSString * const PeopleDirName = cNSString(CUtil::PeopleDirName);
static NSString * const EventsDirName = cNSString(CUtil::EventsDirName);


// -------------------------------------------------------------------------------
//  FileEntry
//
//  A file found on the drive
// -------------------------------------------------------------------------------
#pragma mark -
@interface FileEntry : NSObject
@property(nonatomic, strong) NSURL *fileURL;
@property(nonatomic, strong) NSString *fileStatus;
@property(nonatomic, strong) NSString *relativePath; // debug
@end

@implementation FileEntry
@end

@class PKOrientationListener;


// -------------------------------------------------------------------------------
//  CUtilPrivate
//
//  Staic back-end interface
// -------------------------------------------------------------------------------
#pragma mark -
@interface CUtilPrivate : NSObject
#ifdef PK_USE_SPARKLE
<SUUpdaterDelegate>
#endif


- (void) deinit;
- (void) stopQuery;
- (void) startQuery;
- (void) processiCloudQuery:(NSNotification *)notification;
- (NSURL *) documentsFolderPath;
- (void) forceDocRoot:(NSURL *)path;
//- (void) rescanFileSystem;
- (NSInteger)showAlert:(NSString *)title message:(NSString *)message firstButton:(NSString *)firstButton;
- (NSInteger)showAlert:(NSString *)title message:(NSString *)message firstButton:(NSString *)firstButton secondButton:(NSString *)secondButton;
- (NSInteger)showAlert:(NSString *)title message:(NSString *)message firstButton:(NSString *)firstButton secondButton:(NSString *)secondButton thirdButton:(NSString *)thirdButton;

@property(nonatomic) BOOL isInitialized;
@property(nonatomic, strong) NSURL * localRoot;
@property(nonatomic, strong) NSURL * iCloudRoot;
@property(nonatomic) BOOL iCloudAvailable; // iCloud account is logged in; airplane mode might be on
@property(nonatomic) BOOL iCloudEntriesReady; // query returned for first time
@property(nonatomic, strong) NSMetadataQuery *iCloudQuery;
@property(nonatomic, strong) NSMutableArray * iCloudEntries;
@property(nonatomic, strong) NSMutableArray * localEntries;
@property(nonatomic, strong) NSMutableArray * globalEntries;
@property(nonatomic) BOOL moveLocalToiCloud;
@property(nonatomic) BOOL copyiCloudToLocal;
@property(nonatomic) BOOL isUpdateAvailable;
@property(nonatomic, strong) NSURL *forcedDocRoot;
@property(nonatomic, strong) PKOrientationListener *m_orientationListener;

////////////////////

//@property(nonatomic) BOOL iCloudAvailable; // iCloud account is logged in; airplane mode might be on
//@property(nonatomic, strong) NSURL *iCloudRoot; // iCloud container is available
//@property(nonatomic, strong) NSURL *iCloudDocPath;
//@property(nonatomic, strong) NSMetadataQuery *iCloudQuery;
//@property(nonatomic, strong) NSMutableArray *docFolderFileEntries;


@end



// -------------------------------------------------------------------------------
//  DiagramDocument
//
//  Main document class
// -------------------------------------------------------------------------------
#pragma mark -
#if TARGET_OS_IOS
@interface DiagramDocument : UIDocument
#elif TARGET_OS_MAC
@interface DiagramDocument : NSDocument
#endif

@property(nonatomic) FDDocumentMac *fdDoc;
@property(nonatomic, strong) NSData *pickle;
@property(nonatomic, strong) NSFileWrapper *fileWrapper;
@property(nonatomic, strong) NSFileWrapper *peopleDirWrapper;
// @property(nonatomic, strong) NSDictionary *peopleDirEntries; // model; person/event/file tree held here
@property(nonatomic, strong) NSMutableArray *fileEntries;
@property(nonatomic, strong) NSMutableDictionary *importedFiles; // { NSString *relativePath : NSData *bytes }

- (void)setDirty;
- (BOOL)addFile:(NSString *)relativePath fromFile:(NSString *)src;
- (BOOL)removeFile:(NSString *)relativePath;
- (BOOL)renameFile:(NSString *)oldPath :(NSString *)newPath;
- (void)documentStateChanged:(NSNotification *)notification;

@end





// -------------------------------------------------------------------------------
//  DiagramDocument
//
//  Main document class
// -------------------------------------------------------------------------------
#pragma mark -
@implementation DiagramDocument

// -------------------------------------------------------------------------------
//  autosavesInPlace
// -------------------------------------------------------------------------------
+ (BOOL)autosavesInPlace
{
    // This gives us autosave and versioning for free in 10.7 and later.
    return YES;
}

#if ! TARGET_OS_IOS
// -------------------------------------------------------------------------------
//  canAsynchronouslyWriteToURL:url:typeName:saveOperation
//
//  Turn this on for async saving allowing saving to be asynchronous, making all our
//  save methods (dataOfType, saveToURL) to be called on a background thread.
// -------------------------------------------------------------------------------
- (BOOL)canAsynchronouslyWriteToURL:(NSURL *)url ofType:(NSString *)typeName forSaveOperation:(NSSaveOperationType)saveOperation
{
    (void) url;
    (void) typeName;
    (void) saveOperation;
    
    return NO;
}
#endif

// -------------------------------------------------------------------------------
//  init
// -------------------------------------------------------------------------------
- (instancetype)init
{
    self = [super init];
    if (self != nil)
    {
        self.fileWrapper = [[NSFileWrapper alloc] initDirectoryWithFileWrappers:@{}];
        self.fileEntries = [NSMutableArray array];
        self.importedFiles = [NSMutableDictionary dictionary];
#if TARGET_OS_IOS
        [[NSNotificationCenter defaultCenter] addObserver:self
                                                 selector:@selector(documentStateChanged:)
                                                     name:UIDocumentStateChangedNotification
                                                   object:self];
#else
        // TODO
#endif
    }
    return self;
}

- (void)documentStateChanged:(NSNotification *)notification {
    (void) notification;
    
    self.fdDoc->onDocChanged();
}


// -------------------------------------------------------------------------------
//  fileWrapperOfType:typeName:error
//
//  Called when the user saves this document or when autosave is performed.
//  Create and return a file wrapper that contains the contents of this document,
//  formatted for our specified type.
// -------------------------------------------------------------------------------
#if TARGET_OS_IOS
- (id)contentsForType:(NSString *)typeName
                error:(NSError **)outError
#elif TARGET_OS_MAC
- (NSFileWrapper *)fileWrapperOfType:(NSString *)typeName
                               error:(NSError **)outError
#endif
{
    (void) typeName;
    (void) outError;
    
    // NSString *packageName = [self.fileURL lastPathComponent];
    // NSLog(@"DiagramDocument::fileWrapperOfType: %@", packageName);

    if (self.fileWrapper == nil) {
        self.fileWrapper = [[NSFileWrapper alloc] initDirectoryWithFileWrappers:@{}];
    }
    NSDictionary *packageFileWrappers = [self.fileWrapper fileWrappers];

    NSFileWrapper *pickleWrapper = packageFileWrappers[PickleFileName];
    if((pickleWrapper == nil) && (self.pickle != nil)) {
        pickleWrapper = [[NSFileWrapper alloc] initRegularFileWithContents:self.pickle];
        // NSLog(@"writing pickle: %@\n\n", self.pickle);
        [pickleWrapper setPreferredFilename:PickleFileName];
        [self.fileWrapper addFileWrapper:pickleWrapper];
        packageFileWrappers = [self.fileWrapper fileWrappers]; // gets deleted
    }
    
    NSFileWrapper *peopleDirWrapper = packageFileWrappers[PeopleDirName];
    if(pickleWrapper == nil) {
        peopleDirWrapper = [[NSFileWrapper alloc] initDirectoryWithFileWrappers:@{}];
    }
    NSDictionary *peopleContents = [peopleDirWrapper fileWrappers];
    void (^updateFileEntry)(NSString *, NSData *, BOOL) = ^(NSString *relativePath, NSData *fileData, BOOL remove) {
        NSArray *parts = [relativePath componentsSeparatedByString:@"/"];
        int result = -1;
        if(parts.count == 3 && [[NSScanner scannerWithString:parts[1]] scanInt:&result]) { // People/xyz/abc.def
            
            NSString *personName = parts[1];
            NSString *fileName = parts[2];
            
            // People/xyz
            NSFileWrapper *personDirWrapper = peopleContents[personName];
            if(personDirWrapper == nil) {
                personDirWrapper = [[NSFileWrapper alloc] initDirectoryWithFileWrappers:@{}];
                personDirWrapper.preferredFilename = personName;
                [peopleDirWrapper addFileWrapper:personDirWrapper];
            }
            
            // People/xyz/abc.def
            NSDictionary *personContents = [personDirWrapper fileWrappers];
//            NSLog(@"        personContents: %@", personContents);
            NSFileWrapper *fileWrapper = personContents[fileName];
            if(!remove && fileWrapper == nil) {
                NSURL *fileEntryURL = [self.fileURL URLByAppendingPathComponent:relativePath];
                NSError *error = nil;
                if(fileData) {
                    fileWrapper = [[NSFileWrapper alloc] initRegularFileWithContents:fileData];
                } else {
                    fileWrapper = [[NSFileWrapper alloc] initWithURL:fileEntryURL
                                                             options:NSFileWrapperReadingImmediate
                                                               error:&error];
                }
                fileWrapper.preferredFilename = fileName;
                [personDirWrapper addFileWrapper:fileWrapper];
                NSLog(@"    Saved new file %@", relativePath);
            } else if(remove && fileWrapper != nil) {
                //[personContents removeObjectForKey:fileName];
                NSLog(@"    Deleted file %@", relativePath);
            }

        } else if(parts.count == 5 &&
                  [[NSScanner scannerWithString:parts[1]] scanInt:&result] &&
                  [[NSScanner scannerWithString:parts[3]] scanInt:&result]) { // People/xyz/Events/xyz/abc.def
            NSString *personName = parts[1];
            NSString *eventName = parts[3];
            NSString *fileName = parts[4];
            
            // People/xyz
            NSFileWrapper *personDirWrapper = peopleContents[personName];
            if(personDirWrapper == nil) {
                personDirWrapper = [[NSFileWrapper alloc] initDirectoryWithFileWrappers:@{}];
                personDirWrapper.preferredFilename = personName;
                [peopleDirWrapper addFileWrapper:personDirWrapper];
            }
            
            // People/xyz/Events
            NSDictionary *personContents = [personDirWrapper fileWrappers];
            NSFileWrapper *eventsDirWrapper = personContents[EventsDirName];
            if(eventsDirWrapper == nil) {
                eventsDirWrapper = [[NSFileWrapper alloc] initDirectoryWithFileWrappers:@{}];
                eventsDirWrapper.preferredFilename = EventsDirName;
                [personDirWrapper addFileWrapper:eventsDirWrapper];
            }
            
            // People/xyz/Events/xyz
            NSDictionary *eventsContents = [eventsDirWrapper fileWrappers];
            NSFileWrapper *eventDirWrapper = eventsContents[eventName];
            if(eventDirWrapper == nil) {
                eventDirWrapper = [[NSFileWrapper alloc] initDirectoryWithFileWrappers:@{}];
                eventDirWrapper.preferredFilename = eventName;
                [eventsDirWrapper addFileWrapper:eventDirWrapper];
            }
            
            // People/xyz/Events/xyz/abc.def
            NSDictionary *eventContents = [eventDirWrapper fileWrappers];
            // NSLog(@"        eventContents: %@", eventContents);
            NSFileWrapper *fileWrapper = eventContents[fileName];
            if(!remove && fileWrapper == nil) {
                NSURL *fileEntryURL = [self.fileURL URLByAppendingPathComponent:relativePath];
                NSError *error = nil;
                if(fileData) {
                    fileWrapper = [[NSFileWrapper alloc] initRegularFileWithContents:fileData];
                } else {
                    fileWrapper = [[NSFileWrapper alloc] initWithURL:fileEntryURL
                                                             options:NSFileWrapperReadingImmediate
                                                               error:&error];
                }
                fileWrapper.preferredFilename = fileName;
                [eventDirWrapper addFileWrapper:fileWrapper];
                NSLog(@"    Saved new file %@", relativePath);
            } else if(remove && fileWrapper != nil) {
                //[personContents removeObjectForKey:fileName];
                NSLog(@"    Deleted file %@", relativePath);
            }
        }
    };
    
    // so if files are added to the list then they will remain in the saved version.
    // If files get added from the list they will not be saved.
    if(_fileEntries.count > 0) {
        for(NSString *relativePath in _fileEntries) {
            updateFileEntry(relativePath, nil, NO);
        }
    }
    if(_importedFiles.count > 0) {
        for(NSString *relativePath in _importedFiles) {
            NSData *data = _importedFiles[relativePath];
            updateFileEntry(relativePath, data, NO);
        }
    }

    return self.fileWrapper;
}

// -------------------------------------------------------------------------------
//  readFromFileWrapper:fileWrapper:typeName:outError
//
//  Set the contents of this document by reading from a file wrapper of a specified type,
//  and return YES if successful.
// -------------------------------------------------------------------------------
#if TARGET_OS_IOS
- (BOOL)loadFromContents:(id)contents
                  ofType:(NSString *)typeName
                   error:(NSError **)outError
#elif TARGET_OS_MAC
- (BOOL)readFromFileWrapper:(NSFileWrapper *)fileWrapper
                     ofType:(NSString *)typeName
                      error:(NSError **)outError
#endif
{
    (void) typeName;
    (void) outError;
    
#if TARGET_OS_IOS
    self.fileWrapper = (NSFileWrapper *) contents;
#elif TARGET_OS_MAC
    self.fileWrapper = fileWrapper;
#endif
    
    NSDictionary *fileWrappers = [self.fileWrapper fileWrappers];
    
    NSFileWrapper *pickleWrapper = fileWrappers[PickleFileName];
    if(pickleWrapper != nil) {
        NSData *pickle = pickleWrapper.regularFileContents;
        self.pickle = pickle; // model
        // NSLog(@"reading pickle: %@\n\n", pickle);
    }
    
//    // traverse the dir structure storing dictionaries of all the dirs and arrays of all the files
//    NSString *packageName = [self.fileURL lastPathComponent];
//    NSLog(@"DiagramDocument:readFromFileWrapper: %@", packageName);
    NSFileWrapper *peopleWrapper = fileWrappers[PeopleDirName];
    //NSMutableDictionary *newPeopleDirEntries = [NSMutableDictionary dictionary];
    NSMutableArray *newFileEntries = [NSMutableArray array];
    if(peopleWrapper != nil) {
//        NSLog(@"    %@", PeopleDirName);
        NSDictionary *peopleContents = [peopleWrapper fileWrappers];
        for(NSString *personFileName in peopleContents) {
            if(personFileName) { // can be nil
                int result = -1;
                NSFileWrapper *personWrapper = peopleContents[personFileName];
                if(personWrapper.isDirectory && [[NSScanner scannerWithString:personFileName] scanInt:&result]) { // must be int(person id)
//                    NSLog(@"    %@/%@", PeopleDirName, personFileName);
                    NSDictionary *personContents = [personWrapper fileWrappers];
//                    NSLog(@"personContents: %@", personContents);
                    for(NSString *eventsDirOrFileName in personContents) {
                        NSFileWrapper *eventsDirOrFileWrapper = personContents[eventsDirOrFileName];
                        if(eventsDirOrFileWrapper.isDirectory) {
                            // Events dir
                            if([eventsDirOrFileName isEqualToString:EventsDirName]) {
//                                NSLog(@"    %@/%@/%@", PeopleDirName, personFileName, EventsDirName);
                                NSDictionary *eventsDirContents = [eventsDirOrFileWrapper fileWrappers];
                                for(NSString *eventDirName in eventsDirContents) {
//                                    NSLog(@"    %@/%@/%@/%@", PeopleDirName, personFileName, EventsDirName, eventDirName);
                                    NSFileWrapper *eventDirWrapper = eventsDirContents[eventDirName];
                                    NSDictionary *eventDirContents = [eventDirWrapper fileWrappers];
                                    for(NSString *fileName in eventDirContents) {
                                        // NSFileWrapper *fileWrapper = eventContents[fileName];
//                                        NSLog(@"    %@/%@/%@/%@/%@", PeopleDirName, personFileName, EventsDirName, eventDirName, fileName);
                                        NSString *relativeFilePath = [NSString stringWithFormat:@"%@/%@/%@/%@/%@",
                                                                      PeopleDirName, personFileName, EventsDirName, eventDirName, fileName];
                                        [newFileEntries addObject:relativeFilePath];
                                    }
                                }
                            }
                        }
                        
                        // Regular file at Person level
                        else if(eventsDirOrFileWrapper.isRegularFile) {
                            NSString *fileName = eventsDirOrFileName;
                            NSString *relativeFilePath = [NSString stringWithFormat:@"%@/%@/%@",
                                                          PeopleDirName, personFileName, fileName];
//                            NSLog(@"    %@", relativeFilePath);
                            [newFileEntries addObject:relativeFilePath];
                        }
                    }
                }
            }
        }
    }
    
//    NSLog(@"self.fileEntries: %@", self.fileEntries);
    
    for(NSString *newEntry in newFileEntries) {
        bool found = false;
        for(NSString *oldEntry in self.fileEntries) {
            if([oldEntry isEqualToString:newEntry]) {
                found = true;
                break;
            }
        }
        if(found == false && _fdDoc) {
            NSLog(@"Doc: fileAdded(%@)", newEntry);
            if(_fdDoc) {
                emit self.fdDoc->fileAdded(QString::fromNSString(newEntry));
            }
        }
    }

    for(NSString *oldEntry in self.fileEntries) {
        bool found = false;
        for(NSString *newEntry in newFileEntries) {
            if([newEntry isEqualToString:oldEntry]) {
                found = true;
                break;
            }
        }
        if(found == false && _fdDoc) {
            NSLog(@"Doc: fileRemoved(%@)", oldEntry);
            emit self.fdDoc->fileRemoved(QString::fromNSString(oldEntry));
        }
    }
    
    self.fileEntries = newFileEntries;
    
    return YES;
}


// file is updating from iCloud
- (void)disableEditing {
    emit self.fdDoc->disableEditing();
}

// file is done updating from iCloud
- (void)enableEditing {
    emit self.fdDoc->enableEditing();
}


// -------------------------------------------------------------------------------
//  updatePickle:pickle
//
//  Save the diagram data to the document.
// -------------------------------------------------------------------------------
- (void)updatePickle:(NSData *)pickle {
    self.pickle = pickle;
    // NSLog(@"updating pickle: %@\n\n", pickle);

    NSFileWrapper *pickleWrapper = self.fileWrapper.fileWrappers[PickleFileName];
    if(pickleWrapper != nil) {
        [self.fileWrapper removeFileWrapper:pickleWrapper];
    }
    
    [self setDirty];
}

- (void) setDirty {
#if TARGET_OS_IOS
    [self updateChangeCount:UIDocumentChangeDone];
#elif TARGET_OS_MAC
    [self updateChangeCount:NSChangeDone];
#endif
}

// -------------------------------------------------------------------------------
//  addFile:relativePath:fromFile
//
//  Add a file to the document
// -------------------------------------------------------------------------------
- (BOOL)addFile:(NSString *)relativePath fromFile:(NSString *)src {
    if([_fileEntries containsObject:relativePath]) {
        NSLog(@"File already exists: %@", relativePath);
        return FALSE;
    }
    if([_importedFiles objectForKey:relativePath]) {
        NSLog(@"File already imported: %@", relativePath);
        return FALSE;
    }
    NSData *data = [NSData dataWithContentsOfFile:src];
    self.importedFiles[relativePath] = data;
    [self setDirty];
    NSLog(@"Added file: %@", relativePath);
    return TRUE;
}

// -------------------------------------------------------------------------------
//  addFile:path
//
//  Remove a file from the document
// -------------------------------------------------------------------------------
- (BOOL)removeFile:(NSString *)path {
    if(_importedFiles[path]) {
        [_importedFiles removeObjectForKey:path];
        NSLog(@"Removed imported file: %@", path);
        [self setDirty];
        return TRUE;
    }
    if([_fileEntries containsObject:path]) {
        NSArray *parts = [path componentsSeparatedByString:@"/"];
        NSFileWrapper *lastWrapper = self.fileWrapper;
        NSFileWrapper *currentWrapper = nil;
        for(int i=0; i < (int) parts.count; i++) {
            NSString *part = parts[i];
            NSDictionary *contents = [lastWrapper fileWrappers];
            currentWrapper = contents[part];
            if(currentWrapper) {
                if(i == (int) parts.count - 1) {
                    [lastWrapper removeFileWrapper:currentWrapper];
                    [self setDirty];
                    [_fileEntries removeObject:path];
                    NSLog(@"Removed file: %@", path);
                    return TRUE;
                }
            } else {
                NSLog(@"File does not exist: %@", path);
                return FALSE;
            }
            lastWrapper = currentWrapper;
        }
    }
    NSLog(@"File does not exist: %@", path);
    return FALSE;
}


// -------------------------------------------------------------------------------
//  addFile:oldPath:newPath
//
//  Rename a file in place
// -------------------------------------------------------------------------------
- (BOOL)renameFile:(NSString *)oldPath :(NSString *)newPath {
    if(_importedFiles[oldPath]) {
        NSData *data = _importedFiles[oldPath];
        [_importedFiles removeObjectForKey:oldPath];
        _importedFiles[newPath] = data;
        NSLog(@"Renamed imported file: %@ => %@", oldPath, newPath);
        [self setDirty];
        return TRUE;
    }
    if([_fileEntries containsObject:oldPath]) {
        NSArray *parts = [oldPath componentsSeparatedByString:@"/"];
        NSFileWrapper *currentWrapper = self.fileWrapper;
        for(int i=0; i < (int) parts.count && parts != nil; i++) {
            NSString *part = parts[i];
            NSDictionary *contents = [currentWrapper fileWrappers];
            currentWrapper = contents[part];
            if(currentWrapper) {
                if(i == (int) parts.count - 1) {
                    currentWrapper.preferredFilename = part;
                    [self setDirty];
                    [_fileEntries removeObject:oldPath];
                    [_fileEntries removeObject:newPath];
                    NSLog(@"Renamed file: %@ => %@", oldPath, newPath);
                    return TRUE;
                }
            } else {
                NSLog(@"File does not exist: %@", oldPath);
                return FALSE;
            }
        }
    }
    NSLog(@"File does not exist: %@", oldPath);
    return FALSE;
}



// -------------------------------------------------------------------------------
//  delete:fileURL
//
//  Save the diagram data to the document.
// -------------------------------------------------------------------------------
//- (void)delete:(NSURL *) fileURL {
//
//    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^(void) {
//        NSFileCoordinator* fileCoordinator = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
//        [fileCoordinator coordinateWritingItemAtURL:fileURL options:NSFileCoordinatorWritingForDeleting
//                                              error:nil byAccessor:^(NSURL* writingURL) {
//                                                  NSFileManager* fileManager = [[NSFileManager alloc] init];
//                                                  NSError *error;
//                                                  BOOL success = [fileManager removeItemAtURL:writingURL error:&error];
//                                                  if(!success) { // this doesn't actually seem a reliable error indicator
//                                                      NSLog(@"Could not delete file: %@", error);
//                                                  }
//                                                  [d rescanFileSyste];
//                                              }];
//    });
//}

@end

#pragma mark -

@interface PKOrientationListener : NSObject
@end

@implementation PKOrientationListener
 

- (instancetype)init
{
    self = [super init];
    if (self) {
#if TARGET_OS_IOS
        [[UIDevice currentDevice] beginGeneratingDeviceOrientationNotifications];
        [[NSNotificationCenter defaultCenter]
            addObserver:self
            selector:@selector(orientationChanged:)
            name:@"UIDeviceOrientationDidChangeNotification" object:nil];
#endif
    }
    return self;
}

- (void)dealloc
{
#if TARGET_OS_IOS
    [[UIDevice currentDevice] endGeneratingDeviceOrientationNotifications];
    [[NSNotificationCenter defaultCenter]
        removeObserver:self
        name:@"UIDeviceOrientationDidChangeNotification" object:nil];
#elif TARGET_OS_MAC
#if !__has_feature(objc_arc)
    [super dealloc];
#endif
#else
    [super dealloc];
#endif
}

- (void)orientationChanged:(NSNotification *)notification
{
    Q_UNUSED(notification);
    CUtil::instance()->onScreenOrientationChanged();
}

@end




#pragma mark -

@implementation CUtilPrivate


#ifdef PK_USE_SPARKLE
- (void)updater:(SUUpdater *)updater didFindValidUpdate:(SUAppcastItem *)item {
    self.isUpdateAvailable = true;
    CUtil::instance()->updateIsAvailable();
}

- (void)updater:(SUUpdater *)updater didFinishLoadingAppcast:(SUAppcast *)appcast {
}

- (void)updaterDidNotFindUpdate:(SUUpdater *)updater {
    self.isUpdateAvailable = false;
    CUtil::instance()->updateIsNotAvailable();
}
#endif

-(void)darkModeChanged:(NSNotification *)notif
{
    (void) notif;
    // works, but no longer needed on ios b/c QApplication::paletteChanged is emitted with dark mode
    // qDebug() << "-(void)darkModeChanged:(NSNotification *)notif";
    // emit CUtil::instance()->systemPaletteChanged();
}

#if TARGET_OS_IOS
+ (UIViewController*) topMostController
{
    UIViewController *topController = [UIApplication sharedApplication].keyWindow.rootViewController;

    while (topController.presentedViewController) {
        topController = topController.presentedViewController;
    }

    return topController;
}
#endif

// called from app.py
- (id)init {
    if(self = [super init]) {

        // _forcedDocRoot = nil;

#if TARGET_OS_IOS
        _m_orientationListener = [[PKOrientationListener alloc] init];
        
        // Register the preference defaults early.
        NSDictionary *appDefaults = @{ @"iCloudOn": @(TRUE) };
        [[NSUserDefaults standardUserDefaults] registerDefaults:appDefaults];

        /*
        
        NSDictionary<NSString*, id> *dic = [[NSUserDefaults standardUserDefaults] dictionaryRepresentation];
        NSLog(@"%@", dic);
        NSObject *enableiCloud = [[NSUserDefaults standardUserDefaults] objectForKey:@"upload_research_data"];
        NSLog(@"%@", enableiCloud);
         */
        
//        UIViewController *vc = [[self class] topMostController];
        
        // [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(darkModeChanged:) name:@"traitCollectionDidChange" object:vc];
        
#else
        [[NSDistributedNotificationCenter defaultCenter] addObserver:self selector:@selector(darkModeChanged:) name:@"AppleInterfaceThemeChangedNotification" object:nil];
                
#endif

#ifdef PK_USE_APPCENTER
        if(!AmIBeingDebugged()) {
#if PK_ALPHA_BUILD
            [MSAppCenter start:@"40fb47d9-8e02-43f7-b594-bbb72c6f38e9" withServices:@[[MSAnalytics class], [MSCrashes class]]];
#elif PK_BETA_BUILD
            [MSAppCenter start:@"f8ac3812-6a64-404a-a924-87e9173a694f" withServices:@[[MSAnalytics class], [MSCrashes class]]];
#else
            [MSAppCenter start:@"1857bd26-2675-4f63-98e9-1cdb6381ef34" withServices:@[[MSAnalytics class], [MSCrashes class]]];
#endif
//            [MSDistribute setEnabled:true];
//            qDebug() << "MSDistribute.isEnabled()" << [MSDistribute isEnabled];
            [MSAnalytics setEnabled:true];
//            qDebug() << "MSAnalytics.isEnabled()" << [MSAnalytics isEnabled];
        }
#else
        (void) AmIBeingDebugged;
#endif

#ifdef PK_USE_BUGSNAG
        [Bugsnag start];
#endif
    
#ifdef PK_USE_SPARKLE
            SUUpdater *ssu =  [SUUpdater sharedUpdater];

#if PK_ALPHA_BUILD
            SparkleFeedURL = [NSURL URLWithString: @"https://api.appcenter.ms/v0.1/public/sparkle/apps/40fb47d9-8e02-43f7-b594-bbb72c6f38e9"];
            qDebug() << "PK_ALPHA_BUILD";
#elif PK_BETA_BUILD
            SparkleFeedURL = [NSURL URLWithString: @"https://api.appcenter.ms/v0.1/public/sparkle/apps/f8ac3812-6a64-404a-a924-87e9173a694f"];
            qDebug() << "PK_BETA_BUILD";
#else
            SparkleFeedURL = [NSURL URLWithString: @"https://api.appcenter.ms/v0.1/public/sparkle/apps/1857bd26-2675-4f63-98e9-1cdb6381ef34"];
#endif
            if(SparkleFeedURL != nil) {
                [ssu setFeedURL:SparkleFeedURL];
                ssu.delegate = self;
                [ssu checkForUpdatesInBackground];
            }
#endif

        _isInitialized = NO;
        [self refresh];
    }
    return self;
}

- (void) deinit {
    [self stopQuery];
#if TARGET_OS_IOS
    //[m_orientationListener release];
#else
    [[NSDocumentController sharedDocumentController] saveAllDocuments:nil];
#endif
}


#pragma mark Helpers

- (BOOL)iCloudOn {
    return [[NSUserDefaults standardUserDefaults] boolForKey:@"iCloudOn"];
}

- (void)setiCloudOn:(BOOL)on {
    [[NSUserDefaults standardUserDefaults] setBool:on forKey:@"iCloudOn"];
    [[NSUserDefaults standardUserDefaults] synchronize];
    emit CUtil::instance()->iCloudOnChanged(on);
}

- (BOOL)iCloudWasOn {
    return [[NSUserDefaults standardUserDefaults] boolForKey:@"iCloudWasOn"];
}

- (void)setiCloudWasOn:(BOOL)on {
    [[NSUserDefaults standardUserDefaults] setBool:on forKey:@"iCloudWasOn"];
    [[NSUserDefaults standardUserDefaults] synchronize];
}

- (BOOL)iCloudPrompted {
    return [[NSUserDefaults standardUserDefaults] boolForKey:@"iCloudPrompted"];
}

- (void)setiCloudPrompted:(BOOL)prompted {
    [[NSUserDefaults standardUserDefaults] setBool:prompted forKey:@"iCloudPrompted"];
    [[NSUserDefaults standardUserDefaults] synchronize];
}

- (NSURL *)localRoot {
    if (_localRoot == nil) {
        NSArray * paths = [[NSFileManager defaultManager] URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask];
        _localRoot = [paths objectAtIndex:0];
    }
    return _localRoot;
}


- (void)forceDocRoot:(NSURL *)path {
    self.forcedDocRoot = path;
    //[self startQuery]; // re-start
    [self stopQuery]; // dev only, so stop the query
    [self loadLocal];
}


- (NSURL *) documentsFolderPath {
    if(_forcedDocRoot) {
        return _forcedDocRoot;
    } else if (self.iCloudAvailable && self.iCloudOn) {
        return [self.iCloudRoot URLByAppendingPathComponent:@"Documents" isDirectory:YES];
    } else {
        return self.localRoot;
    }
}

- (NSURL *)getDocURL:(NSString *)filename {
    return [[self documentsFolderPath] URLByAppendingPathComponent:filename];
}

- (BOOL)docNameExistsInEntries:(NSString *)docName {
    BOOL nameExists = NO;
    for (FileEntry *entry in _globalEntries) {
        if ([[entry.fileURL lastPathComponent] isEqualToString:docName]) {
            nameExists = YES;
            break;
        }
    }
    return nameExists;
}

- (BOOL)docNameExistsIniCloudEntries:(NSString *)docName {
    BOOL nameExists = NO;
    for (FileEntry *entry in _iCloudEntries) {
        if ([[entry.fileURL lastPathComponent] isEqualToString:docName]) {
            nameExists = YES;
            break;
        }
    }
    return nameExists;
}

- (NSString*)getDocFilename:(NSString *)prefix uniqueInEntries:(BOOL)uniqueInEntries {
    NSInteger docCount = 0;
    NSString* newDocName = nil;
    
    // At this point, the document list should be up-to-date.
    BOOL done = NO;
    BOOL first = YES;
    while (!done) {
        if (first) {
            first = NO;
            newDocName = [NSString stringWithFormat:@"%@.%@",
                          prefix, FileExtension];
        } else {
            newDocName = [NSString stringWithFormat:@"%@ %d.%@",
                          prefix, (int) docCount, FileExtension];
        }
        
        // Look for an existing document with the same name. If one is
        // found, increment the docCount value and try again.
        BOOL nameExists;
        if (uniqueInEntries) {
            nameExists = [self docNameExistsInEntries:newDocName];
        } else {
            nameExists = [self docNameExistsIniCloudEntries:newDocName];
        }
        if (!nameExists) {
            break;
        } else {
            docCount++;
        }
        
    }
    
    return newDocName;
}

- (void)initializeiCloudAccessWithCompletion:(void (^)(BOOL available)) completion {
    if(QApplication::platformName() != "offscreen") {
        dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
            self.iCloudRoot = [[NSFileManager defaultManager] URLForUbiquityContainerIdentifier:nil];
            if (self.iCloudRoot != nil) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    // NSLog(@"iCloud available at: %@", self.iCloudRoot);
                    completion(TRUE);
                });
            }
            else {
                dispatch_async(dispatch_get_main_queue(), ^{
                    // NSLog(@"iCloud not available");
                    completion(FALSE);
                });
            }
        });
    } else {
        completion(FALSE);
    }
}


- (NSInteger)showAlert:(NSString *)title message:(NSString *)message firstButton:(NSString *)firstButton {
    return [self showAlert:title message:message firstButton:firstButton secondButton:nil thirdButton:nil];
}

- (NSInteger)showAlert:(NSString *)title message:(NSString *)message firstButton:(NSString *)firstButton secondButton:(NSString *)secondButton {
    return [self showAlert:title message:message firstButton:firstButton secondButton:secondButton thirdButton:nil];
}

- (NSInteger)showAlert:(NSString *)title
               message:(NSString *)message
           firstButton:(NSString *)firstButton
          secondButton:(NSString *)secondButton
           thirdButton:(NSString *)thirdButton {
    NSInteger ret = -1;
#if TARGET_OS_IOS
// TODO
    /*
    UIAlertAction *firstAction = nil;
    UIAlertAction *secondAction = nil;
    UIAlertAction *thirdAction = nil;
    
    UIAlertController * alert = [UIAlertController
                                 alertControllerWithTitle:@"Title"
                                 message:message
                                 preferredStyle:UIAlertControllerStyleAlert];
    firstAction = [UIAlertAction
                   actionWithTitle:firstButton
                   style:UIAlertActionStyleDefault
                   handler:^(UIAlertAction * action) {
                       ret = 0;
                   }];
    [alert addAction:firstAction];
    if(secondButton) {
        secondAction = [UIAlertAction
                        actionWithTitle:secondButton
                        style:UIAlertActionStyleDefault
                        handler:^(UIAlertAction * action) {
                            ret = 1;
                        }];
        [alert addAction:secondAction];
    }
    if(thirdButton) {
        thirdAction = [UIAlertAction
                       actionWithTitle:thirdButton
                       style:UIAlertActionStyleDefault
                       handler:^(UIAlertAction * action) {
                           ret = 2;
                       }];
        [alert addAction:thirdAction];
    }
    
    [self presentViewController:alert animated:YES completion:nil];
    */
#else
    NSAlert *alert = [[NSAlert alloc] init];
    [alert addButtonWithTitle:firstButton];
    if(secondButton) {
        [alert addButtonWithTitle:secondButton];
    }
    if(thirdButton) {
        [alert addButtonWithTitle:thirdButton];
    }
    
    [alert setMessageText:title];
    [alert setInformativeText:message];
#if __MAC_OS_X_VERSION_MIN_ALLOWED > 1011
    [alert setAlertStyle:NSAlertStyleInformational];
#endif
    NSModalResponse response = [alert runModal];
    if (response == NSAlertFirstButtonReturn) {
        ret = 0;
    } else if (response == NSAlertSecondButtonReturn) {
        ret = 1;
    } else if (response == NSAlertThirdButtonReturn) {
        ret = 2;
    }
#endif
    return ret;
}


#pragma mark File management methods

- (void)iCloudToLocalImpl {
    
    return; // Not moving files between computer and iCloud for now.
    
    NSLog(@"iCloud => local impl");
    
    for (FileEntry *entry in _iCloudEntries) {
        
        NSURL *fileURL = entry.fileURL;
        NSString * fileName = [[fileURL lastPathComponent] stringByDeletingPathExtension];
        NSURL *destURL = [self getDocURL:[self getDocFilename:fileName uniqueInEntries:YES]];
        
        // Perform copy on background thread
        dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^(void) {
            NSFileCoordinator* fileCoordinator = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
            [fileCoordinator coordinateReadingItemAtURL:fileURL options:NSFileCoordinatorReadingWithoutChanges error:nil byAccessor:^(NSURL *newURL) {
                (void) newURL;
                
                NSFileManager * fileManager = [[NSFileManager alloc] init];
                NSError * error;
                BOOL success = [fileManager copyItemAtURL:fileURL toURL:destURL error:&error];
                if (success) {
                    NSLog(@"Copied %@ to %@ (%d)", fileURL, destURL, self.iCloudOn);
                } else {
                    NSLog(@"Failed to copy %@ to %@: %@", fileURL, destURL, error.localizedDescription);
                }
            }];
        });
    }
    
}

- (void)iCloudToLocal {
//    NSLog(@"iCloud => local");
    
    NSInteger button = [self showAlert:@"You are logged into iCloud Drive but you are not using it for Family Diagram."
                               message:@"What would you like to do with the documents currently on this device?"
                           firstButton:@"Continue Using iCloud"
                          secondButton:@"Keep a Local Copy"
                           thirdButton:@"Keep on iCloud Only"];
    
    if (button == 0) {
        
        [self setiCloudOn:YES];
        [self refresh];
        
    } else if (button == 1) {
        
        if (_iCloudEntriesReady) {
            [self iCloudToLocalImpl];
        } else {
            _copyiCloudToLocal = YES;
        }
        
    } else if (button == 2) {
        
        // Do nothing
        
    }
}

- (void)localToiCloudImpl {
    
    return; // Not moving files between computer and iCloud for now.
    
    NSLog(@"local => iCloud impl");
    
    NSArray * localDocuments = [[NSFileManager defaultManager] contentsOfDirectoryAtURL:self.localRoot includingPropertiesForKeys:nil options:0 error:nil];
    for (unsigned long i=0; i < localDocuments.count; i++) {

//        NSString *filePath = [[localDocuments objectAtIndex:i] path];
//        NSString *lastChar = [filePath substringFromIndex:[filePath length] - 1];
//        if([lastChar isEqualToString:@"/"]) {
//            filePath = [filePath substringToIndex:[filePath length]-1];
//        }
        NSURL * fileURL = [localDocuments objectAtIndex:i]; // [NSURL URLWithString:filePath];
        NSString *filePath = [fileURL path];
        NSString *pathExtension = [fileURL pathExtension];
        fileURL = URLByDeletingTrailingSlash(fileURL);
//        fileURL = [NSURL fileURLWithPath:[fileURL path]];
        if ([[fileURL pathExtension] isEqualToString:FileExtension]) {
            
            NSLog(@"Trying to move: %@, %@, %@", filePath, pathExtension, fileURL);
            NSString * fileName = [[fileURL lastPathComponent] stringByDeletingPathExtension];
            NSURL *destURL = [self getDocURL:[self getDocFilename:fileName uniqueInEntries:NO]];
            
            // Perform actual move in background thread
            dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^(void) {
                NSError * error;
                BOOL success = [[NSFileManager defaultManager] setUbiquitous:self.iCloudOn itemAtURL:fileURL destinationURL:destURL error:&error];
                if (success) {
                    NSLog(@"Moved %@ to %@", fileURL, destURL);
                } else {
                    NSLog(@"Failed to move %@ to %@: %@", fileURL, destURL, error.localizedDescription);
                }
            });
            
        }
    }
    
}

- (void)localToiCloud {
//    NSLog(@"local => iCloud");
    
    // If we have a valid list of iCloud files, proceed
    if (_iCloudEntriesReady) {
        [self localToiCloudImpl];
    }
    // Have to wait for list of iCloud files to refresh
    else {
        _moveLocalToiCloud = YES;
    }
}



#pragma mark Refresh Methods

- (void)loadLocal {
    NSMutableArray *updatedEntries = [[NSMutableArray alloc] init];
    NSURL *docRoot = [self documentsFolderPath];
    if(!docRoot) {
        NSLog(@"no doc root!");
        return;
    }
    NSArray *localDocuments = [[NSFileManager defaultManager] contentsOfDirectoryAtURL:docRoot includingPropertiesForKeys:nil options:0 error:nil];
    NSString *docsPath = [docRoot path];
    for (unsigned long i=0; i < localDocuments.count; i++) {
        NSURL * fileURL = [localDocuments objectAtIndex:i];
        NSString *fileName = [fileURL lastPathComponent];
        NSString *filePath = [docsPath stringByAppendingPathComponent:fileName];
        NSString *relativePath = [filePath stringByReplacingOccurrencesOfString:[docsPath stringByAppendingString:@"/"] withString:@""];
        // Don't include hidden files.
        NSNumber *aBool = nil;
        [fileURL getResourceValue:&aBool forKey:NSURLIsHiddenKey error:nil];
        bool hidden = [aBool boolValue];
        if(hidden) {
            continue;
        }
        // Don't include backup files.
        NSString *packageName = [fileName stringByDeletingPathExtension];
        if([packageName hasSuffix:@"~"]) {
            continue;
        }
        BOOL isDir = NO;
        bool exists = [[NSFileManager defaultManager] fileExistsAtPath:filePath isDirectory:&isDir];
//        NSLog(@"%@, %@ %i, %i", relativePath, filePath, isDir, hidden);
        if([[fileURL pathExtension] isEqualToString:FileExtension] && exists && isDir) {
            FileEntry *entry = [[FileEntry alloc] init];
            entry.fileURL = URLByDeletingTrailingSlash(fileURL);
            entry.relativePath = relativePath;
            entry.fileStatus = NSURLUbiquitousItemDownloadingStatusCurrent;
            [updatedEntries addObject:entry];
        }
    }
    
    updateFileEntries(_globalEntries, updatedEntries);
    _globalEntries = _localEntries = updatedEntries;
    
}



//  -------------------------------------------------------------------------------
//  refresh
//
//  Called when the view loads or when a major prefs changes.
//  For example, must check if user logged out of iCloud or if iCloud was
//  disabled.
// -------------------------------------------------------------------------------
- (void)refresh {
    
    _iCloudEntriesReady = NO;
    for(FileEntry *entry in _globalEntries) {
        emit CUtil::instance()->fileRemoved(QUrl::fromNSURL(entry.fileURL));
    }
    [_localEntries removeAllObjects];
    [_globalEntries removeAllObjects];
    [_iCloudEntries removeAllObjects];

    [self initializeiCloudAccessWithCompletion:^(BOOL available) {
        
        _iCloudAvailable = available;
        
        if (!_iCloudAvailable) {
            
            // If iCloud isn't available, set promoted to no (so we can ask them next time it becomes available)
            [self setiCloudPrompted:NO];
            
            // If iCloud was toggled on previously, warn user that the docs will be loaded locally
            if ([self iCloudWasOn]) {
        
                [self showAlert:@"You're Not Using iCloud"
                        message:@"Your documents were removed from this device but remain stored in iCloud."
                    firstButton:@"OK" secondButton:nil thirdButton:nil];
            }
            
            // No matter what, iCloud isn't available so switch it to off.
            [self setiCloudOn:NO];
            [self setiCloudWasOn:NO];
            
        } else {
            
            // Ask user if want to turn on iCloud if it's available and we haven't asked already
            if (![self iCloudOn] && ![self iCloudPrompted]) {
                
                [self setiCloudPrompted:YES];

                NSInteger ret = [self showAlert:@"Use iCloud to store family diagrams?"
                                        message:@"Click \"Use iCloud\" to automatically store your documents in the cloud to keep them up-to-date across all your devices."
                                    firstButton:@"Later"
                                   secondButton:@"Use iCloud"
                                 ];
                if (ret == 1)
                {
                    [self setiCloudOn:YES];
                    [self refresh];
                }
            }
            
            // If iCloud newly switched off, move local docs to iCloud
            if ([self iCloudOn] && ![self iCloudWasOn]) {
                [self localToiCloud];
            }
            
            // If iCloud newly switched on, move iCloud docs to local
            if (![self iCloudOn] && [self iCloudWasOn]) {
                [self iCloudToLocal];
            }
            
            // Start querying iCloud for files, whether on or off
//            if([self iCloudOn]) {
                [self startQuery];
//            }
            
            // No matter what, refresh with current value of iCloudOn
            [self setiCloudWasOn:[self iCloudOn]];
            
        }
        
        if (![self iCloudOn]) {
            [self loadLocal];
        }
        
        if(!_isInitialized) {
            _isInitialized = YES;
//            [self startQuery];
            // qDebug() << "emit CUtil::instance()->initialized();";
            emit CUtil::instance()->initialized(); // show the app and get rolling.
        }
        
    }];
}




//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////


#pragma mark iCloud Query

- (void)startQuery {
    
    [self stopQuery];
    
    _iCloudQuery = [[NSMetadataQuery alloc] init];
    if (_iCloudQuery) {
        
        // Search documents subdir only
        [_iCloudQuery setSearchScopes:[NSArray arrayWithObject:NSMetadataQueryUbiquitousDocumentsScope]];
        [_iCloudQuery setPredicate:[NSPredicate predicateWithFormat:@"%K LIKE '*.fd'", NSMetadataItemFSNameKey]];
        [[NSNotificationCenter defaultCenter] addObserver:self
                                                 selector:@selector(processiCloudQuery:)
                                                     name:NSMetadataQueryDidFinishGatheringNotification
                                                   object:nil];
        [[NSNotificationCenter defaultCenter] addObserver:self
                                                 selector:@selector(processiCloudQuery:)
                                                     name:NSMetadataQueryDidUpdateNotification
                                                   object:nil];
        // has to happen in the main thread
        dispatch_async(dispatch_get_main_queue(), ^{
            [_iCloudQuery startQuery];
            if(!_iCloudQuery.started) {
                NSLog(@"Could not start NSMetadataQuery.");
            } else {
                // NSLog(@"Started NSMetadataQuery.");
            }
        });
    }
    
}

- (void)stopQuery {
        
    if (_iCloudQuery) {
        [[NSNotificationCenter defaultCenter] removeObserver:self name:NSMetadataQueryDidFinishGatheringNotification object:nil];
        [[NSNotificationCenter defaultCenter] removeObserver:self name:NSMetadataQueryDidUpdateNotification object:nil];
        [_iCloudQuery stopQuery];
        _iCloudQuery = nil;
        // NSLog(@"Stopped NSMetadataQuery");
    }
    
}

void updateFileEntries(NSMutableArray *oldEntries, NSMutableArray *newEntries) {
 
    bool found = false;
    for(FileEntry *oldEntry in oldEntries) {
        found = false;
        for(FileEntry *updatedEntry in newEntries) {
            if([oldEntry.fileURL isEqual:updatedEntry.fileURL]) {
                found = true;
                break;
            }
        }
        if(!found) {
            // NSLog(@"updateFileEntries - fileRemoved(%@)", oldEntry.relativePath);
            emit CUtil::instance()->fileRemoved(QUrl::fromNSURL(oldEntry.fileURL));
        }
    }
    for(FileEntry *updatedEntry in newEntries) {
        found = false;
        for(FileEntry *oldEntry in oldEntries) {
            if([oldEntry.fileURL isEqual:updatedEntry.fileURL]) {
                found = true;
                break;
            }
        }
        if(!found) {
            CUtil::FileStatus status = CUtil::FileIsCurrent;
            if([updatedEntry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusCurrent]) {
                status = CUtil::FileIsCurrent;
            } else if([updatedEntry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusNotDownloaded]) {
                status = CUtil::FileNotDownloaded;
            } else if([updatedEntry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusDownloaded]) {
                status = CUtil::FileIsDownloading;
            }
            // NSLog(@"updateFileEntries - fileAdded(%@, %@)", updatedEntry.fileURL, updatedEntry.fileStatus);
            emit CUtil::instance()->fileAdded(QUrl::fromNSURL(updatedEntry.fileURL), status);
        }
    }
    for(FileEntry *updatedEntry in newEntries) {
        if(updatedEntry.fileStatus) { // just report files, fileStaus == null for dirs
            found = false;
            for(FileEntry *oldEntry in oldEntries) {
                if([oldEntry.fileURL isEqual:updatedEntry.fileURL]) {
                    found = true;
                    if(![oldEntry.fileStatus isEqual:updatedEntry.fileStatus]) {
                        if([updatedEntry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusCurrent])
                            emit CUtil::instance()->fileStatusChanged(QUrl::fromNSURL(oldEntry.fileURL), CUtil::FileIsCurrent);
                        else if([updatedEntry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusNotDownloaded])
                            emit CUtil::instance()->fileStatusChanged(QUrl::fromNSURL(oldEntry.fileURL), CUtil::FileNotDownloaded);
                        else if([updatedEntry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusDownloaded])
                            emit CUtil::instance()->fileStatusChanged(QUrl::fromNSURL(oldEntry.fileURL),CUtil::FileIsDownloading);
                        // NSLog(@"updateFileEntries - fileStatusChanged(%@, %@) -> %@", updatedEntry.relativePath, updatedEntry.fileStatus, oldEntry.fileStatus);
                    }
                    break;
                }
            }
        }
    }
    
}

- (void)processiCloudQuery:(NSNotification *) notification {

    (void) notification;
    
    NSMutableArray *updatedEntries = [[NSMutableArray alloc] init];
    int iResults = [_iCloudQuery resultCount];
    _iCloudEntriesReady = YES;
    
    for(int i=0; i < iResults; i++) {
        NSMetadataItem *theResult = [_iCloudQuery resultAtIndex:i];
        NSURL *fileURL = [theResult valueForAttribute:NSMetadataItemURLKey];
        
        // Don't include hidden files.
        NSNumber * aBool = nil;
        [fileURL getResourceValue:&aBool forKey:NSURLIsHiddenKey error:nil];
        if (aBool && [aBool boolValue]) {
            continue;
        }

        // Don't include backup files.
        NSString *packageName = [[fileURL lastPathComponent] stringByDeletingPathExtension];
//        NSLog(@">>> %@, %hhd", packageName, [packageName hasSuffix:@"~"]);
        if([packageName hasSuffix:@"~"]) {
            continue;
        }
        
        NSString *fileStatus;
        [fileURL getResourceValue:&fileStatus forKey:NSURLUbiquitousItemDownloadingStatusKey error:nil];
        
        
        NSString *fileName = [[fileURL lastPathComponent] stringByStandardizingPath];
        NSString *fullPath = [[fileURL path] stringByStandardizingPath];
        NSString *docsPath = [[[self documentsFolderPath] path] stringByAppendingString:@"/"];
        NSString *relativePath = [fullPath stringByReplacingOccurrencesOfString:docsPath withString:@""];
        if ([fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusDownloaded]) {
            NSLog(@"[iCloud:stale] %@", relativePath);
        } else if ([fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusCurrent]) {
//            NSLog(@"[iCloud:current] %@", relativePath);
        } else if ([fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusNotDownloaded]) {
            NSLog(@"[iCloud:not-downloaded] %@", relativePath);
            if([[fileName pathExtension] isEqualToString:FileExtension] || // always download file package
               [[fileName pathExtension] isEqualToString:@"pickle"]) { // always download pickle file
                NSError *error;
                BOOL downloading = [[NSFileManager defaultManager] startDownloadingUbiquitousItemAtURL:fileURL error:&error];
                if (downloading) {
                    NSLog(@"[iCloud:downloading] %@", [relativePath lastPathComponent]);
                } else {
                    NSLog(@"[iCloud:download-failed] %@, %@", [relativePath lastPathComponent], error);
                }
            }
        }
        FileEntry *entry = [[FileEntry alloc] init];
        if([fileURL.absoluteString hasSuffix:@"/"])
            entry.fileURL = [NSURL URLWithString:[fileURL.absoluteString substringToIndex:fileURL.absoluteString.length - 1]];
        else
            entry.fileURL = fileURL;
        entry.fileStatus = fileStatus;
        entry.relativePath = relativePath;
        [updatedEntries addObject:entry];
    }
    
    if([self iCloudOn]) {
        updateFileEntries(_globalEntries, updatedEntries);
        _globalEntries = _iCloudEntries = updatedEntries;
    }

    if (_moveLocalToiCloud) {
        _moveLocalToiCloud = NO;
        [self localToiCloudImpl];
    }
    else if (_copyiCloudToLocal) {
        _copyiCloudToLocal = NO;
        [self iCloudToLocalImpl];
    }

}



- (NSString *)relativePathFor:(NSURL*) fileURL {
    NSString *fullPath = [fileURL path];
    NSString *docsPath = [[[self documentsFolderPath] path] stringByAppendingString:@"/"];
    NSString *relativePath = [fullPath stringByReplacingOccurrencesOfString:docsPath withString:@""];
    return relativePath;
}

/*
- (void) newUntitledFile {
    DiagramDocument * doc = [[DiagramDocument alloc] init];
    FDDocument *fdDoc = new FDDocumentMac(CUtil::instance(), doc);
    emit CUtil::instance()->fileOpened(fdDoc);
}
*/


- (void) openExistingFile:(NSURL *) fileURL {
    
#if TARGET_OS_IOS
    DiagramDocument * doc = [[DiagramDocument alloc] initWithFileURL:fileURL];
    [doc openWithCompletionHandler:^(BOOL success) {
        //        UIDocumentState state = doc.documentState;
        //        NSFileVersion * version = [NSFileVersion currentVersionOfItemAtURL:fileURL];
        if(!success) {
            NSLog(@"Failed to open %@", doc.fileURL);
//            NSLog(@"    %@", error);
        } else {
            QUrl url = QUrl::fromNSURL(doc.fileURL);
//            NSLog(@"Loaded File URL: %@", [doc.fileURL lastPathComponent]);
            FDDocument *fdDoc = new FDDocumentMac(CUtil::instance(), doc);
            emit CUtil::instance()->fileOpened(fdDoc);
        }
    }];
#elif TARGET_OS_MAC
    NSError *error = nil;
    DiagramDocument *doc = [[DiagramDocument alloc] initWithContentsOfURL:fileURL ofType:DocumentType error:&error];
    if(error == nil) {
        // NSLog(@"Loaded File URL: %@", [doc.fileURL lastPathComponent]);
        [[NSDocumentController sharedDocumentController] addDocument:doc];
        FDDocument *fdDoc = new FDDocumentMac(CUtil::instance(), doc);
        emit CUtil::instance()->fileOpened(fdDoc);
    } else {
        NSLog(@"Failed to open %@", fileURL);
        NSLog(@"    %@", error);
    }
//        NSDocumentController *dc = [NSDocumentController sharedDocumentController];
//        [dc openDocumentWithContentsOfURL:fileURL
//                                  display:NO
//                        completionHandler:^void (NSDocument *doc, BOOL alreadyOpen, NSError *error) {
//                            [self docOpened:(DiagramDocument *)doc alreadyOpen:alreadyOpen error:(error != nil)];
//                        }];
#endif

}

- (bool)startDownloading:(NSURL *) url {
    NSError *error;
    if([[NSFileManager defaultManager] isUbiquitousItemAtURL:url]) {
        NSString *fileStatus;
        [url getResourceValue:&fileStatus forKey:NSURLUbiquitousItemDownloadingStatusKey error:nil];
        if ([fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusNotDownloaded]) {
            BOOL downloading = [[NSFileManager defaultManager] startDownloadingUbiquitousItemAtURL:url error:&error];
            if (downloading) {
                NSLog(@"[iCloud] started downloading: %@", [url lastPathComponent]);
            } else {
                NSLog(@"[iCloud] failed to start download: %@, %@", [url lastPathComponent], error);
            }
            return downloading;
        } else {
//            NSLog(@"[iCloud] item already download[ed|ing]: %@", [url lastPathComponent]);
        }
    } else {
        NSLog(@"[iCloud] item not ubiquitous: %@", [url lastPathComponent]);
    }
    return FALSE;
}

@end


#pragma mark -
// -------------------------------------------------------------------------------
//  CUtil
//
//  Apple implementation
// -------------------------------------------------------------------------------


class CUtilApple : public CUtil {
    
    CUtilPrivate *d;

public:
    
    CUtilApple(QObject *parent) :
    CUtil(parent) {
        d = [CUtilPrivate alloc];
    }
    ~CUtilApple() {
        // [d dealloc];
    }
    
    void init() {
        if(! m_bInitStarted) {

            // qDebug() << "CUtil::init";
            
            d = [d init];
            
            if(d.forcedDocRoot) {
                m_fsWatcher->addPath(QUrl::fromNSURL(d.forcedDocRoot).toLocalFile());
            } else if(!iCloudOn()) {
                m_fsWatcher->addPath(QUrl::fromNSURL(d.localRoot).toLocalFile());
            }
            
#if TARGET_OS_IOS
#else
#if __MAC_OS_X_VERSION_MIN_ALLOWED > 1011  // note use of 1050 instead of __MAC_10_12
            NSOperatingSystemVersion v;
            v.majorVersion = 10;
            v.minorVersion = 12;
            v.patchVersion = 0;
            //[[NSProcessInfo processInfo] operatingSystemVersion]
            if([[NSProcessInfo processInfo] isOperatingSystemAtLeastVersion:v]) {
                [NSWindow setAllowsAutomaticWindowTabbing: NO];
            }
#else
#endif
#endif
            if(![d isInitialized]) {
                m_bInitStarted = true;
                QEventLoop loop; // block until initialized
                connect(this, SIGNAL(initialized()), &loop, SLOT(quit()));
                loop.exec();
            }
        }
    }
    
    void deinit() {
        [d deinit];
        
        //        [d dealloc];
        //    QMap<QUrl, FDDocument *>::iterator it = m_docs.begin();
        //    while(it != m_docs.end()) {
        //        FDDocument *doc = it.value();
        //        [doc stopQuery];
        ////        m_docs.erase(it); // causes crash
        //        it++;
        //    }
        
    }
    
    bool isInitialized() const {
        if(d && d.isInitialized) {
            return true; // so as not to wait for the signal from MainWindow
        } else {
            return false;
        }
    }

    /*
    void newUntitledFile() {
        [d newUntitledFile];
    }
    */
    
    void openExistingFile(const QUrl &url) {
        [d openExistingFile:url.toNSURL()];
    }
    
    bool startDownloading(const QUrl &url) {
        return [d startDownloading:url.toNSURL()];
    }

    void forceDocsPath(const QString &path) {
        if(path.isNull()) {
            [d forceDocRoot:nil];
            m_fsWatcher->removePath(QUrl::fromNSURL(d.localRoot).toLocalFile());
        } else {
            NSString *nspath = path.toNSString();
            NSURL *url = [NSURL fileURLWithPath:nspath];
            if(url) {
                [d forceDocRoot:url];
                if(m_fsWatcher && ! path.isEmpty() and ! m_fsWatcher->directories().contains(path)) {
                    m_fsWatcher->addPath(path);
                }
            }
        }
    }    
    
    QString documentsFolderPath() const {
        NSURL *url = [d documentsFolderPath];
        //    NSLog(@"documentsFolderPath(): %@", url);
        QString ret = QUrl::fromNSURL(url).toLocalFile();
        if(ret.endsWith("/")) {
            return ret.remove(ret.length()-1, 1);
        } else {
            return ret;
        }
    }
    bool iCloudAvailable() const {
        return d.iCloudAvailable;
    }
    
    bool iCloudOn() const {
        return d.iCloudOn;
    }
    
    QString iCloudDocsPath() const {
        QUrl url = QUrl::fromNSURL([d.iCloudRoot URLByAppendingPathComponent:@"Documents"]);
        return url.toLocalFile();
    }
    
    void setiCloudOn(bool on) {
        if(on != iCloudOn()) {
            [d setiCloudOn:on];
            [d refresh];
            foreach(QString path, m_fsWatcher->directories()) {
                m_fsWatcher->removePath(path);
            }
            if(on){
            } else {
                m_fsWatcher->addPath(documentsFolderPath());
            }
        }
    }
    void updateLocalFileList() {
        [d loadLocal];
    }

    void dev_crash() const {
#ifdef PK_USE_BUGSNAG
        [Bugsnag notifyError:[NSError errorWithDomain:@"(Crash application QAction from Debug menu)" code:408 userInfo:nil]];
#endif
        @throw NSInternalInconsistencyException;
    }

    QList<QUrl> fileList() const {
        QList<QUrl> ret;
        for(FileEntry *entry in d.globalEntries) {
            ret << QUrl::fromNSURL(entry.fileURL);
        }
        return ret;
    }
    FileStatus fileStatusForUrl(const QUrl &url) const {
        for(FileEntry *entry in d.globalEntries) {
            if([entry.fileURL isEqualToURL:url.toNSURL()]) {
                if ([entry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusDownloaded]) {
                    return CUtil::FileIsDownloading;
                } else if ([entry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusCurrent]) {
                    return CUtil::FileIsCurrent;
                } else if ([entry.fileStatus isEqualToString:NSURLUbiquitousItemDownloadingStatusNotDownloaded]) {
                    return CUtil::FileNotDownloaded;
                } else {
                    return CUtil::FileStatusNone;
                }
            }
        }
        return CUtil::FileStatusNone;
    }

    bool isUIDarkMode() const {
#if TARGET_OS_OSX
        NSString *osxMode = [[NSUserDefaults standardUserDefaults] stringForKey:@"AppleInterfaceStyle"];
        QString qMode = QString::fromNSString(osxMode);
        if(qMode == "Dark") {
            return true;
        } else {
            return false;
        }
#else
        UIUserInterfaceStyle s = [UITraitCollection currentTraitCollection].userInterfaceStyle;
        if(s == UIUserInterfaceStyleDark) {
            return true;
        } else {
            return false;
        }
#endif
    }

    #ifdef Q_OS_MACOS
QColor qt_mac_toQColor(const NSColor *color) const
{
    QColor qtColor;
    NSString *colorSpace = [color colorSpaceName];
    if (colorSpace == NSDeviceCMYKColorSpace) {
        CGFloat cyan, magenta, yellow, black, alpha;
        [color getCyan:&cyan magenta:&magenta yellow:&yellow black:&black alpha:&alpha];
        qtColor.setCmykF(cyan, magenta, yellow, black, alpha);
    } else {
        NSColor *tmpColor;
        tmpColor = [color colorUsingColorSpaceName:NSDeviceRGBColorSpace];
        CGFloat red, green, blue, alpha;
        [tmpColor getRed:&red green:&green blue:&blue alpha:&alpha];
        qtColor.setRgbF(red, green, blue, alpha);
    }
    return qtColor;
}
#endif


    QColor appleControlAccentColor() const {
#ifdef Q_OS_MACOS
        if (@available(macOS 10.14, *)) {
            // macOS 10.14 or later code path
            return qt_mac_toQColor([NSColor controlAccentColor]);
        } else {
            return QApplication::palette().color(QPalette::Active, QPalette::Highlight);
        }
#else
        return QApplication::palette().color(QPalette::Active, QPalette::Highlight);
#endif
    }

    
    QString getOpenFileName() const {
#if TARGET_OS_OSX
        NSOpenPanel *openPanel = [NSOpenPanel openPanel];
        [openPanel setAllowedFileTypes : [NSArray arrayWithObjects : ::FileExtension, nil]];
        [openPanel setAllowsMultipleSelection : NO];
        [openPanel setTreatsFilePackagesAsDirectories : NO];
        [openPanel setTitle : @"Open Diagram"];
        
        NSInteger result = [openPanel runModal];
        
        QStringList stringList;
        
        if (result == NSModalResponseOK) {
            NSArray *URLs = [openPanel URLs];
            for (NSURL *URL in URLs) {
                return QString::fromNSString(URL.path);
            }
        }
        return QString();
#else
        return QFileDialog::getOpenFileName(QApplication::activeWindow());
#endif
    }
    
    void showFeedbackWindow() const {
#ifdef PK_USE_APPCENTER
        dispatch_async(dispatch_get_main_queue(), ^{
                //
        });
#endif
    }
    
    void checkForUpdates() const {
#ifdef PK_USE_SPARKLE
        if(SparkleFeedURL != nil) {
            [[SUUpdater sharedUpdater] checkForUpdates:nil];
        }
#endif
    }

    bool isUpdateAvailable() const {
        return d.isUpdateAvailable;
    }
    
    void trackAnalyticsEvent(QString eventName, QMap<QString, QString> properties) {
        (void) eventName;
        (void) properties;
#ifdef PK_USE_APPCENTER
        if(properties.count() > 0) {
            NSMutableDictionary *nsd = [NSMutableDictionary dictionaryWithCapacity:properties.count()];
            QMapIterator<QString, QString> i(properties);
            // this crashes on toNSString()
            // while(i.hasNext()) {
            //     nsd[i.key().toNSString()] = i.value().toNSString();
            // }
            while(i.hasNext()) {
                i.next();
                NSString *key = i.key().toNSString();
                NSString *value = i.value().toNSString();
                if (key != nil && value != nil) {
                    nsd[key] = value;
                }
            }
            [MSAnalytics trackEvent:eventName.toNSString() withProperties:nsd];
        } else {
            [MSAnalytics trackEvent:eventName.toNSString()];
        }
#endif
    }

};


/*
bool CUtil::isiOSSimulator() {
#if TARGET_IPHONE_SIMULATOR
    return true;
#else
    return false;
#endif
}
*/

CUtil::OperatingSystem CUtil::operatingSystem() {
    int ret = 0;
    
#ifdef _WIN32
    //define something for Windows (32-bit and 64-bit, this part is common)
#ifdef _WIN64
    //define something for Windows (64-bit only)
#else
    //define something for Windows (32-bit only)
#endif
    ret |= OS_Windows;
#elif __APPLE__
//#include "TargetConditionals.h"
#if TARGET_IPHONE_SIMULATOR
    ret |= OS_iPhoneSimulator;
#endif
#if TARGET_OS_IPHONE
    if([UIDevice currentDevice].userInterfaceIdiom == UIUserInterfaceIdiomPad)
        ret |= OS_iPad;
    else
        ret |= OS_iPhone;
#elif TARGET_OS_MAC
    ret |= OS_Mac;
#else
#   error "Unknown Apple platform"
#endif
#elif __linux__
    // linux
#elif __unix__ // all unices not caught above
    // Unix
#elif defined(_POSIX_VERSION)
    // POSIX
#else
#   error "Unknown compiler"
#endif
    return (OperatingSystem) ret;
}

QRect CUtil::screenSize() {
#if TARGET_OS_IOS
    const CGRect r = [[UIScreen mainScreen] bounds];
    return QRect(0, 0, r.size.width, r.size.height);
#else
    QSize size = QApplication::desktop()->size();
    return QRect(0, 0, size.width(), size.height());
#endif
}

float CUtil::devicePixelRatio() {
#if TARGET_OS_IOS
    return [[UIScreen mainScreen] scale];
#else
    return [[NSScreen mainScreen] backingScaleFactor];
#endif
}

QString CUtil::getMachineModel() {
    size_t len = 0;
    //    char *model = NULL;
    NSString *result=@"Unknown Mac";
    sysctlbyname("hw.model", NULL, &len, NULL, 0);
    if (len) {
        NSMutableData *data=[NSMutableData dataWithLength:len];
        sysctlbyname("hw.model", [data mutableBytes], &len, NULL, 0);
        result = [NSString stringWithUTF8String:(const char *)[data bytes]];
        //         model = (char *) malloc(len*sizeof(char));
        //         sysctlbyname("hw.model", model, &len, NULL, 0);
        // //        printf("%s\n", model);
        //         free(model);
    }
    // return QString::fromLocal8Bit(model);
    // return QString::fromUtf8(model);
    return QString::fromNSString(result);
}


Qt::ScreenOrientation CUtil::screenOrientation() {
    Qt::ScreenOrientation orientation;
#if TARGET_OS_IOS
    UIDeviceOrientation orient = [UIDevice currentDevice].orientation;
    switch(orient) {
    case UIDeviceOrientationPortrait:
        orientation = Qt::PortraitOrientation;
        break;
    case UIDeviceOrientationPortraitUpsideDown:
        orientation = Qt::InvertedPortraitOrientation;
        break;
    case UIDeviceOrientationLandscapeLeft: // home button on the right side.
        orientation = Qt::LandscapeOrientation;
        break;
    case UIDeviceOrientationLandscapeRight: // home button on the left side.
        orientation = Qt::InvertedLandscapeOrientation;
        break;
    default:
        orientation = Qt::PrimaryOrientation;
    }
#else
    orientation = Qt::PrimaryOrientation;
#endif
    return orientation;
}
    


CUtil *CUtil_create(QObject *parent) {
    return new CUtilApple(parent);
}


// -------------------------------------------------------------------------------
//  FDDocumentMac
//
//
// -------------------------------------------------------------------------------
#pragma mark -
FDDocumentMac::FDDocumentMac(QObject *parent, DiagramDocument *_doc) :
FDDocument(parent),
doc(_doc) {
    doc.fdDoc = this;
}

FDDocumentMac::~FDDocumentMac() {
    NSLog(@"~FDDocumentMac()");
}

QUrl FDDocumentMac::url() const {
    return QUrl::fromNSURL(doc.fileURL);
}

QByteArray FDDocumentMac::diagramData() const {
    if(doc && doc.pickle) {
        return QByteArray::fromNSData(doc.pickle);
    } else {
        return QByteArray();
    }
}

void FDDocumentMac::updateDiagramData(const QByteArray &data) {
    [doc updatePickle:data.toNSData()];
}

QStringList FDDocumentMac::fileList() const {
    QStringList ret;
    for(NSString *relativePath in doc.fileEntries){
        ret << QString::fromNSString(relativePath);
    }
    for(NSString *relativePath in doc.importedFiles){
        ret << QString::fromNSString(relativePath);
    }
    return ret;
}


void FDDocumentMac::save(bool quietly) {
#if TARGET_OS_IOS
    [doc saveToURL:doc.fileURL forSaveOperation:UIDocumentSaveForOverwriting completionHandler:^(BOOL success) {
        if(success) {
            [doc updateChangeCount:UIDocumentChangeCleared];
             NSLog(@"Saved doc: %@", [doc.fileURL path]);
             if(!quietly) {
                 emit saved();
             }
        }
    }];
#else
    NSError *theError = NULL;
    [doc writeSafelyToURL:doc.fileURL ofType:DocumentType forSaveOperation:NSSaveOperation error:&theError];
    if(!theError) {
        [doc updateChangeCount:NSChangeCleared];
        if(!quietly) {
            emit saved();
        }
    }

//    [doc autosaveWithImplicitCancellability:NO completionHandler:^(NSError *errorOrNil){
//        (void) errorOrNil;
//
//        NSLog(@"[self updateChangeCount:NSChangeCleared]; %@", errorOrNil);
//        [doc updateChangeCount:NSChangeCleared];
//        if(!quietly) {
//            emit saved();
//        }
//    }];
#endif
}

void FDDocumentMac::saveAs(const QUrl &url) {
    NSError *outError = nil;
#if TARGET_OS_IOS
    [doc saveToURL:url.toNSURL() forSaveOperation:UIDocumentSaveForCreating completionHandler:^(BOOL success) {
        if(success) {
            NSLog(@"Saved doc as: %@", url.toNSURL());
            emit savedAs(url);
        } else {
            NSLog(@"Could not save document as %@", doc.fileURL);
        }
    }];
#else
    [doc writeToURL:url.toNSURL() ofType:DocumentType
                        forSaveOperation:NSSaveToOperation
                     originalContentsURL:doc.fileURL
                                   error:&outError];
    if(outError == nil) {
        NSLog(@"Saved doc as: %@", url.toNSURL());
        emit savedAs(url);
    } else {
        NSLog(@"Could not save document as %@", doc.fileURL);
        NSLog(@"%@", outError);
    }
#endif
}


void FDDocumentMac::close() {
#if TARGET_OS_IOS
    [doc closeWithCompletionHandler:nil];
#else
    [doc close];
#endif
}

void FDDocumentMac::addFile(const QString &src, const QString &relativePath) {
    if([doc addFile:relativePath.toNSString() fromFile:src.toNSString()]) {
        emit fileAdded(relativePath);
    }
}

void FDDocumentMac::removeFile(const QString &relativePath) {
    if([doc removeFile:relativePath.toNSString()]) {
        emit fileRemoved(relativePath);
    }
}

void FDDocumentMac::renameFile(const QString &oldPath, const QString &newPath) {
    [doc renameFile:oldPath.toNSString() :newPath.toNSString()];
}

void FDDocumentMac::onDocChanged() {
    emit changed();
}


//void FDDocumentMac::deleteFile(const QString &relativePath) {
//    QString filePath(this->url().toLocalFile() + "/" + relativePath);
//    QFile f(filePath);
//    if(!f.exists() || !f.remove()) { // in case I missed something about NSDocument
//        qDebug() << "Could not delete file:" << filePath;
//    } else {
//        qDebug() << "Deleted file:" << filePath;
//    }
//}


        // Apple docs says let users rename docs in the Finder
        //void FDDocumentMac::rename(const QUrl &url) {
        //    QUrl newUrl(_newUrl);
        //    NSURL *url = newUrl.toNSURL();
        //    if(![[url pathExtension] isEqualToString:FileExtension]) {
        //        url = [url URLByAppendingPathExtension:FileExtension];
        //    }
        //    [doc moveToURL:url completionHandler:^void (NSError *error) {
        //        if(error) {
        //            NSLog(@"%@", error);
        //        } else {
        //            deregisterDocument(doc);
        //            registerDocument(newUrl, doc);
        //            QUrl oldUrl = getUrlForDoc(doc);
        //            NSLog(@"Moved: %@ => %@", oldUrl.toNSURL(), newUrl.toNSURL());
        //            emit CUtil::instance()->fileRenamed(oldUrl, newUrl);
        //        }
        //    }];
        //}
        //
        




#if 0

#include <iostream>
#include <cxxabi.h>
#include <string>
#include <stdio.h>
#include <vector>
#include <algorithm>
#include <memory>

class StackTraceGenerator
{
private:

    //  this is a pure utils class
    //  cannot be instantiated
    //
    StackTraceGenerator() = delete;
    StackTraceGenerator(const StackTraceGenerator&) = delete;
    StackTraceGenerator& operator=(const StackTraceGenerator&) = delete;
    ~StackTraceGenerator() = delete;

public:

    static std::vector<std::string> GetTrace()
    {
        std::vector<std::string> stackFrames;

        //  record stack trace upto 128 frames
        void *callstack[128];

        // collect stack frames
        int i, frames = backtrace((void**) callstack, 128);

        // get the human-readable symbols (mangled)
        char** strs = backtrace_symbols((void**) callstack, frames);

        stackFrames.reserve(frames);

        for (i = 0; i < frames; ++i)
        {
            char functionSymbol[1024] = {};
            char moduleName[1024] = {};
            int  offset = 0;
            char addr[48] = {};

            /*

             Typically this is how the backtrace looks like:

             0   <app/lib-name>     0x0000000100000e98 _Z5tracev + 72
             1   <app/lib-name>     0x00000001000015c1 _ZNK7functorclEv + 17
             2   <app/lib-name>     0x0000000100000f71 _Z3fn0v + 17
             3   <app/lib-name>     0x0000000100000f89 _Z3fn1v + 9
             4   <app/lib-name>     0x0000000100000f99 _Z3fn2v + 9
             5   <app/lib-name>     0x0000000100000fa9 _Z3fn3v + 9
             6   <app/lib-name>     0x0000000100000fb9 _Z3fn4v + 9
             7   <app/lib-name>     0x0000000100000fc9 _Z3fn5v + 9
             8   <app/lib-name>     0x0000000100000fd9 _Z3fn6v + 9
             9   <app/lib-name>     0x0000000100001018 main + 56
             10  libdyld.dylib      0x00007fff91b647e1 start + 0

             */

            // split the string, take out chunks out of stack trace
            // we are primarily interested in module, function and address
            sscanf(strs[i], "%*s %s %s %s %*s %d",
                   (char *) &moduleName, (char *) &addr, (char *) &functionSymbol, &offset);

            int   validCppName = 0;
            //  if this is a C++ library, symbol will be demangled
            //  on success function returns 0
            //
            char* functionName = abi::__cxa_demangle(functionSymbol,
                                                     NULL, 0, &validCppName);

            char stackFrame[4096] = {};
            if (validCppName == 0) // success
            {
                sprintf(stackFrame, "(%s)\t0x%s — %s + %d",
                        moduleName, addr, functionName, offset);
            }
            else
            {
                //  in the above traceback (in comments) last entry is not
                //  from C++ binary, last frame, libdyld.dylib, is printed
                //  from here
                sprintf(stackFrame, "(%s)\t0x%s — %s + %d",
                        moduleName, addr, functionName, offset);
            }

            if (functionName)
            {
                free(functionName);
            }

            std::string frameStr(stackFrame);
            stackFrames.push_back(frameStr);
        }
        free(strs);

        return stackFrames;
    }
};

struct StackTracePrinter {
    void operator()() {
        auto frames = StackTraceGenerator::GetTrace();
        std::for_each(frames.cbegin(), frames.cend(),
                      [](const std::string& frame)
                          {
                              std::cout << frame << std::endl;
                          }
            );
    }    
};

#endif // 0

void CUtil::dev_printBacktrace() {
#if 0
    StackTracePrinter stPrinter;
    stPrinter();
#endif
}

bool CUtil::dev_amIBeingDebugged() {
    return AmIBeingDebugged();
}

