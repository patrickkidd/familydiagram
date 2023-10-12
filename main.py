def main():
    import sys

    import python_init
    python_init.init_dev()

    if not '-s' in sys.argv and not '--server' in sys.argv:
        from optparse import OptionParser
        parser = OptionParser()
        parser.add_option("-s", "--server", dest="server",
                          help="Run as server", action="store_true", default=False)
        parser.add_option("-a", "--attach", dest="attach",
                          help="Wait for a debugger to attach to this process", action='store_true', default=False)
        parser.add_option("-d", "--debug", dest="debug",
                          help="Run in debugger", action='store_true', default=False)
        parser.add_option("-P", "--profile", dest="profile",
                          help="Run in profiler", action='store_true', default=False)
        parser.add_option("-n", "--prefs-name", dest="prefs_name",
                          help="What alias to load preferences from, useful for debugging multiple instances.")
        parser.add_option("-m", "--module", dest="module",
                          help="Run main() in module", default='app')
        parser.add_option("-M", "--mainwindow", dest="mainwindow", action='store_true',
                          help="Run main() in module in MainWindow (-m) required", default=False)
        parser.add_option("-q", "--qml-module", dest="qml_module",
                          help="Run an isolated qml module", default=None)
        parser.add_option("-v", "--version", dest="version", action="store_true",
                          help="Print the version", default=False)
        options, args = parser.parse_args(sys.argv)
        
        if options.version:

            import os.path, importlib
            ROOT = os.path.realpath(os.path.dirname(__file__))
            spec = importlib.util.spec_from_file_location("version", os.path.join(ROOT, 'pkdiagram', 'version.py'))
            version = importlib.util.module_from_spec(spec)  
            spec.loader.exec_module(version)
            print(version.VERSION)
            return

        modname = 'pkdiagram.' + options.module
        __import__(modname)
        mod = globals()[options.module] = sys.modules[modname]
        if options.debug:
            import pdb
            if hasattr(mod, 'main'):
                pdb.run(options.module + '.main()')
            elif hasattr(mod, '__test__'):
                pdb.run(options.module + '.__test__()')
        elif options.profile:
            import cProfile
            if hasattr(mod, 'main'):
                cProfile.run(options.module + '.main()')
            elif hasattr(mod, '__test__'):
                cProfile.run(options.module + '.__test__()')
        elif options.qml_module:
            import pkdiagram.util
            main_qml = pkdiagram.util.import_source('main_qml', 'bin/main_qml.py')
            main_qml.run(options.qml_module)
        else:
            if hasattr(mod, 'main'):
                if options.module == 'app':
                    mod.main(options.attach, options.prefs_name)
                else:
                    mod.main()
            elif hasattr(mod, '__test__'):
                from pkdiagram import util
                util.modTest(mod.__test__,
                             loadfile=(not hasattr(mod, 'TEST_NO_FILE')),
                             useMW=options.mainwindow)
    else: # server
        from pkdiagram import server
        parser = server.Parser()
        argv = list(sys.argv)
        if '-s' in argv:
            argv.remove('-s')
        if '--server' in argv:
            argv.remove('--server')
        options, args = parser.parse_args(argv)
        server.main(options=options)

        
if __name__ == '__main__':
    main()
