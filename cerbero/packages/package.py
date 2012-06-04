# cerbero - a multi-platform build system for Open Source software
# Copyright (C) 2012 Andoni Morales Alastruey <ylatuya@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os

from cerbero.build.filesprovider import FilesProvider
from cerbero.enums import License
from cerbero.packages import PackageType


class PackageBase(object):
    '''
    Base class for packages with the common field to describe a package

    @cvar name: name of the package
    @type name: str
    @cvar shortdesc: Short description of the package
    @type shortdesc: str
    @cvar longdesc: Long description of the package
    @type longdesc: str
    @cvar version: version of the package
    @type version: str
    @cvar codename: codename of the release
    @type codename: str
    @cvar uuid: unique id for this package
    @type uuid: str
    @cvar license: package license
    @type license: License
    @cvar vendor: vendor for this package
    @type vendor: str
    @cvar org: organization for this package (eg: net.foo.bar)
    @type org: str
    @cvar url: url for this pacakge
    @type url: str
    @cvar sys_deps: system dependencies for this package
    @type sys_deps: dict
    @cvar ignore_package_prefix: don't use the package prefix set in the config
    @type ignore_package_prefix: bool
    @cvar resources_license: filename of the .txt license file
    @type resources_license: str
    @cvar resources_license_rtf: filename of .rtf license file
    @type resources_license_rtf: str
    @cvar resources_icon: filename of the icon image
    @type resources_icon: str
    @cvar resources_backgound = filename of the background image
    @type resources_backgound = str
    '''
    name = 'default'
    shortdesc = 'default'
    longdesc = 'default'
    version = '1.0'
    codename = None
    org = 'default'
    uuid = None
    license = License.GPL
    vendor = 'default'
    url = 'default'
    ignore_package_prefix = False
    sys_deps = {}
    resources_license = 'license.txt'
    resources_license_rtf = 'license.txt'
    resources_icon = 'icon.ico'
    resources_background = 'background.png'

    def __init__(self, config, store):
        self.config = config
        self.store = store
        self.package_mode = PackageType.RUNTIME

    def prepare(self):
        '''
        Can be overrided by subclasses to modify conditionally the package
        '''
        pass

    def load_files(self):
        pass

    def package_dir(self):
        '''
        Gets the directory path where this package is stored

        @return: directory path
        @rtype: str
        '''
        return os.path.dirname(self.__file__)

    def relative_path(self, path):
        '''
        Gets a path relative to the package's directory

        @return: absolute path relative to the pacakge's directory
        @rtype: str
        '''
        return os.path.abspath(os.path.join(self.package_dir(), path))

    def files_list(self):
        raise NotImplemented("'files_list' must be implemented by subclasses")

    def devel_files_list(self):
        raise NotImplemented("'devel_files_list' must be implemented by "
                             "subclasses")

    def all_files_list(self):
        raise NotImplemented("'all_files_list' must be implemented by "
                             "subclasses")

    def set_mode(self, package_type):
        self.package_mode = package_type

    def get_install_dir(self):
        try:
            return self.install_dir[self.config.target_platform]
        except:
            return self.config.install_dir

    def get_sys_deps(self):
        if self.config.target_distro_version in self.sys_deps:
            return self.sys_deps[self.config.target_distro_version]
        if self.config.target_distro in self.sys_deps:
            return self.sys_deps[self.config.target_distro]
        return []

    def __str__(self):
        return self.name

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        # Return relative path for resources
        if name.startswith('resources'):
            attr = self.relative_path(attr)
        elif name == 'name':
            attr += self.package_mode
        elif name == 'shortdesc':
            if self.package_mode == PackageType.DEVEL:
                attr += ' (Development Files)'
        elif name == 'uuid':
            if self.package_mode == PackageType.DEVEL:
                if attr is not None:
                    # Used the change the upgrade code for the devel package
                    uuid = list(attr)
                    if uuid[0] != '0':
                        uuid[0] = '0'
                    else:
                        uuid[0] = '1'
                    attr = ''.join(uuid)
        return attr


class Package(PackageBase):
    '''
    Describes a set of files to produce disctribution packages for the
    different target platforms

    @cvar deps: list of packages dependencies
    @type deps: list
    @cvar files: list of files included in this package
    @type files: list
    @cvar platform_files: dict of platform files included in this package
    @type platform_files: dict
    @cvar files_devel: list of devel files included in this package
    @type files_devel: list
    @cvar platform_files_devel: dict of platform devel files included in
                                this package
    @type platform_files_Devel: dict
    @cvar osx_framework_library: name and link for the Framework library
    @type osx_framework_library: tuple
    '''

    deps = list()
    files = list()
    platform_files = dict()
    files_devel = list()
    platform_files_devel = dict()
    osx_framework_library = None

    def __init__(self, config, store, cookbook):
        PackageBase.__init__(self, config, store)
        self.cookbook = cookbook
        self.load_files()

    def load_files(self):
        self._files = self.files + \
                self.platform_files.get(self.config.target_platform, [])
        self._files_devel = self.files_devel + \
                self.platform_files_devel.get(self.config.target_platform, [])
        self._parse_files()

    def recipes_dependencies(self):
        deps = [x.split(':')[0] for x in self._files]
        deps.extend([x.split(':')[0] for x in self._files_devel])
        for name in self.deps:
            p = self.store.get_package(name)
            deps += p.recipes_dependencies()
        return deps

    def recipes_licenses(self):
        return self._list_licenses(self._recipes_files)

    def devel_recipes_licenses(self):
        licenses = self._list_licenses(self._recipes_files_devel)
        for recipe_name, categories in self._recipes_files.iteritems():
            # also add development licenses for recipe from which used the
            # 'libs' category
            if len(categories) == 0 or FilesProvider.LIBS_CAT in categories:
                r = self.cookbook.get_recipe(recipe_name)
                if recipe_name in licenses:
                    licenses[recipe_name].update(
                            r.list_licenses_by_categories(categories))
                else:
                    licenses[recipe_name] = \
                            r.list_licenses_by_categories(categories)
        return licenses

    def files_list(self):
        files = []
        for recipe_name, categories in self._recipes_files.iteritems():
            recipe = self.cookbook.get_recipe(recipe_name)
            if len(categories) == 0:
                rfiles = recipe.dist_files_list()
            else:
                rfiles = recipe.files_list_by_categories(categories)
            files.extend(rfiles)
        return sorted(files)

    def devel_files_list(self):
        files = []
        for recipe, categories in self._recipes_files.iteritems():
            # only add development files for recipe from which used the 'libs'
            # category
            if len(categories) == 0 or FilesProvider.LIBS_CAT in categories:
                rfiles = self.cookbook.get_recipe(recipe).devel_files_list()
                files.extend(rfiles)
        for recipe, categories in self._recipes_files_devel.iteritems():
            recipe = self.cookbook.get_recipe(recipe)
            if not categories:
                rfiles = recipe.devel_files_list()
            else:
                rfiles = recipe.files_list_by_categories(categories)
            files.extend(rfiles)
        return sorted(files)

    def all_files_list(self):
        files = self.files_list()
        files.extend(self.devel_files_list())
        return sorted(files)

    def _parse_files(self):
        self._recipes_files = {}
        for r in self._files:
            l = r.split(':')
            self._recipes_files[l[0]] = l[1:]
        self._recipes_files_devel = {}
        for r in self._files_devel:
            l = r.split(':')
            self._recipes_files_devel[l[0]] = l[1:]

    def _list_licenses(self, recipes_files):
        licenses = {}
        for recipe_name, categories in recipes_files.iteritems():
            r = self.cookbook.get_recipe(recipe_name)
            # Package.files|files_devel|platform_files|platform_files_devel = \
            #        [recipe:category]
            #  => licenses = {recipe_name: {category: category_licenses}}
            # Package.files|files_devel|platform_files|platform_files_devel = \
            #        [recipe]
            #  => licenses = {recipe_name: {None: recipe_licenses}}
            licenses[recipe_name] = r.list_licenses_by_categories(categories)
        return licenses


class MetaPackage(PackageBase):
    '''
    Group of packages used to build an installer package

    @cvar packages: list of packages grouped in this meta package
    @type packages: list
    @cvar platform_packages: list of platform packages
    @type platform_packages: dict
    @cvar icon: filename of the package icon
    @type icon: str
    @cvar root_env_var: name of the environment variable with the prefix
    @type root_env_var: str
    '''

    packages = []
    root_env_var = 'CERBERO_SDK_ROOT'
    platform_packages = {}

    def __init__(self, config, store):
        PackageBase.__init__(self, config, store)

    def list_packages(self):
        return [p[0] for p in self.packages]

    def recipes_dependencies(self):
        deps = []
        for package in self.store.get_package_deps(self.name, True):
            deps.extend(package.recipes_dependencies())
        return list(set(deps))

    def files_list(self):
        return self._list_files(Package.files_list)

    def devel_files_list(self):
        return self._list_files(Package.devel_files_list)

    def all_files_list(self):
        return self._list_files(Package.all_files_list)

    def get_root_env_var(self):
        return (self.root_env_var % {'arch': self.config.target_arch}).upper()

    def get_wix_upgrade_code(self):
        m = self.package_mode
        p = self.config.target_arch
        return self.wix_upgrade_code[m][p]

    def _list_files(self, func):
        # for each package, call the function that list files
        files = []
        for package in self.store.get_package_deps(self.name):
            files.extend(func(package))
        files.sort()
        return files

    def __getattribute__(self, name):
        if name == 'packages':
            attr = PackageBase.__getattribute__(self, name)
            ret = attr[:]
            platform_attr_name = 'platform_%s' % name
            if hasattr(self, platform_attr_name):
                platform_attr = PackageBase.__getattribute__(self,
                        platform_attr_name)
                if self.config.target_platform in platform_attr:
                    platform_list = platform_attr[self.config.target_platform]
                    ret.extend(platform_list)
            return ret
        else:
            return PackageBase.__getattribute__(self, name)
