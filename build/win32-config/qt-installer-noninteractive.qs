var installer = gui.createInstaller();
installer.installationStarted.connect(function(){
    installer.addComponent("qt.qt5.5152.win64_msvc2019_64");
    installer.addComponent("qt.qt5.5152.qtsources");
    installer.addComponent("qt.qt5.5152.qttools");
    installer.addComponent("qt.qt5.5152.qtbase.private");  // Add other private modules as needed
});

installer.start();
installer.finishButtonClicked.connect(installer.quit);
