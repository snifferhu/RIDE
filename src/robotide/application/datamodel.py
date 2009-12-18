#  Copyright 2008-2009 Nokia Siemens Networks Oyj
#  
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  
#      http://www.apache.org/licenses/LICENSE-2.0
#  
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import operator

from robotide.model import TestSuiteFactory, RESOURCEFILECACHE
from robotide.errors import DataError, SerializationError
from robotide import context


class DataModel(object):

    def __init__(self, path=None):
        self.resources = []
        self.suite = None
        self._open(path)

    def _open(self, path):
        if not path:
            return
        try:
            self._open_suite(path)
        except DataError:
            try:
                self.open_resource(path)
            except DataError:
                raise DataError("Given file '%s' is not a valid Robot Framework "
                                "test case or resource file" % path)

    def _open_suite(self, path):
        self.suite = TestSuiteFactory(path)
        self._resolve_imported_resources(self.suite)

    def open_resource(self, path, datafile=None):
        resource = RESOURCEFILECACHE.load_resource(path, datafile)
        if not resource:
            return None
        if resource not in self.resources:
            self.resources.append(resource)
            return resource
        return None

    def _resolve_imported_resources(self, datafile):
        resources = datafile.get_resources()
        for res in resources:
            if res not in self.resources:
                self.resources.append(res)
        for item in datafile.suites + resources:
            self._resolve_imported_resources(item)

    def get_all_keywords(self):
        kws = []
        if self.suite:
            kws = self.suite.get_keywords()
            for s in self.suite.suites:
                kws.extend(s.get_keywords())
        for res in self.resources:
            kws.extend(res.get_keywords())
        kws = self._remove_duplicates(kws)
        kws.sort(key=operator.attrgetter('name'))
        return kws

    def _remove_duplicates(self, kws):
        kws_by_name = {}
        for kw in kws:
            kws_by_name[kw.longname] = kw
        return kws_by_name.values()

    def get_files_without_format(self, datafile=None):
        if not self.suite:
            return []
        if datafile:
            datafiles = [datafile]
        else:
            datafiles = [self.suite] + self.suite.suites
        return [ df for df in datafiles if df.dirty and not df.has_format() ]

    def get_root_suite_dir_path(self):
        return self.suite.get_dir_path()

    def is_directory_suite(self):
        return self.suite.is_directory_suite
 
    def is_dirty(self):
        if self.suite and self._is_suite_dirty(self.suite):
            return True
        for res in self.resources:
            if res.dirty:
                return True
        return False

    def _is_suite_dirty(self, suite):
        if suite.dirty:
            return True
        for s in suite.suites:
            if self._is_suite_dirty(s):
                return True
        return False

    def serialize(self, datafile=None):
        # TODO: split to single file save and save all
        errors = []
        datafiles = self._get_files_to_serialize(datafile)
        for df in datafiles:
            try:
                df.serialize(recursive=datafile is None)
            except SerializationError, err:
                errors.append('%s: %s\n' % (df.source, str(err)))
        if errors:
            context.LOG.error('Following file(s) could not be saved:\n\n%s' %
                              '\n'.join(errors))

    def _get_files_to_serialize(self, datafile):
        if datafile:
            return [datafile]
        if self.suite:
            return [self.suite] + self.resources
        return []
