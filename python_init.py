def init_dev():

    try:
        import pdytools  # type: ignore

        IS_BUNDLE = True
    except:
        import os.path

        IS_BUNDLE = False

    ## Import Paths

    ## pyqtdeploy requires extension plugins (e.g. six.py, typing_extensions.py, etc) to be .py files
    ## That existing in the root dir. But these plugin files get imported instead of their actual
    ## counterparts. So move the root dir to the back of the search path so entries in `lib/site-packages``
    ## override them.
    if not IS_BUNDLE:
        import importlib.util
        import sys, site

        def import_from_path(module_name, fpath):
            spec = importlib.util.spec_from_file_location(module_name, fpath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module

        sitepackages_path = site.getsitepackages()
        familydiagram_path = os.path.dirname(__file__)

        # import_from_path(os.path.join(sitepackages_path, 'typing_extensions'))
        # import_from_path('vedana', os.path.join(familydiagram_path, 'vedana', '__init__.py'))

        familydiagram_path = os.path.dirname(__file__)
        for path in list(sys.path):
            if os.path.isdir(path) and os.path.normpath(path) == familydiagram_path:
                sys.path.remove(path)
        # _pkdiagram_path = os.path.join(familydiagram_path, 'pkdiagram', '_pkdiagram', 'build', '_pkdiagram', 'build', 'lib.macosx-12.6-x86_64-cpython-310')
        # sys.path.insert(0, _pkdiagram_path)
        vendor_path = os.path.join(familydiagram_path, "lib", "site-packages")
        sys.path.insert(0, vendor_path)
        sys.path.append(familydiagram_path)
        server_path = os.path.join(familydiagram_path, "server")
        sys.path.append(server_path)
