# -*- coding: utf-8 -*-
#
# Copyright 2015 MarkLogic Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# File History
# ------------
#
# Paul Hoehne       03/01/2015     Initial development
# Paul Hoehne       03/08/2014     Added support for field indexes

"""
Database related classes for manipulating MarkLogic databases
"""

from __future__ import unicode_literals, print_function, absolute_import

import sys

import requests
import json
import logging
from marklogic.models.forest import Forest
from marklogic.models.utilities import files
from marklogic.models.utilities.utilities import PropertyLists
from marklogic.models.utilities.validators import *
from marklogic.models.utilities.exceptions import *
from marklogic.models.database.fragment import FragmentRoot, FragmentParent
from marklogic.models.database.index import ElementRangeIndex, AttributeRangeIndex
from marklogic.models.database.index import PathRangeIndex, FieldRangeIndex
from marklogic.models.database.index import GeospatialElementIndex
from marklogic.models.database.index import GeospatialPathIndex
from marklogic.models.database.index import GeospatialElementChildIndex
from marklogic.models.database.index import GeospatialElementPairIndex
from marklogic.models.database.index import GeospatialElementAttributePairIndex
from marklogic.models.database.mergeblackout import MergeBlackout
from marklogic.models.database.mergeblackout import MergeBlackoutRecurringDuration
from marklogic.models.database.mergeblackout import MergeBlackoutRecurringStartEnd
from marklogic.models.database.mergeblackout import MergeBlackoutRecurringAllDay
from marklogic.models.database.mergeblackout import MergeBlackoutOneTimeDuration
from marklogic.models.database.mergeblackout import MergeBlackoutOneTimeStartEnd
from marklogic.models.database.scheduledbackup import ScheduledDatabaseBackup, ScheduledDatabaseBackupOnce
from marklogic.models.database.scheduledbackup import ScheduledDatabaseBackupWeekly
from marklogic.models.database.backup import DatabaseBackup, DatabaseRestore
from marklogic.models.database.path import PathNamespace
from marklogic.models.database.lexicon import ElementWordLexicon
from marklogic.models.database.lexicon import AttributeWordLexicon
from marklogic.models.database.namelist import NameList
from marklogic.models.database.through import PhraseThrough, PhraseAround
from marklogic.models.database.through import ElementWordQueryThrough
from marklogic.models.database.ruleset import RuleSet
from marklogic.models.database.field import Field, RootField, PathField, FieldPath, WordQuery, IncludedElement, ExcludedElement

class Database(PropertyLists):
    """
    The Database class encapsulates a MarkLogic database.  It provides
    methods to set/get database attributes.  The use of methods will
    allow IDEs with tooling to provide auto-completion hints.
    """
    def __init__(self, name, hostname='$ML-LOCALHOST'):
        """
        Initialize the database object to either create a database or
        lookup the existing database information

        :param name: The database name
        :param hostname: Optional host name, used if forests are created

        :return: The database object with default data
        """
        self._config = {
            'database-name': name,
            'forest': [
                name + '-Forest-001'
            ],
            'security-database': 'Security',
            'schema-database': 'Schemas',
            'enabled': True,
            'language': 'en'
        }
        self.name = name # separate so we can rename databases
        self.etag = None
        self.hostname = hostname

    def set_database_name(self, name):
        """
        Sets the database name.

        :param name: The database name

        :return: The database object
        """
        self._config['database-name'] = name
        return self

    def database_name(self):
        """
        The database name.

        :return: The name
        """
        if 'database-name' in self._config:
            return self._config['database-name']
        return None

    def set_enabled(self, enabled=True):
        """
        Set the flag to enable or disable a database.

        :param enabled: The enable status

        :return: the database object
        """
        validate_boolean(enabled)
        self._config['enabled'] = enabled
        return self

    def enabled(self):
        """
        Returns the enable status

        :return: The database enable status
        """
        if 'enabled' in self._config:
            return self._config['enabled']
        return None

    def set_security_database_name(self, db='Security'):
        """
        Sets the security database.

        This is the name of the database
        in which security related documents will be stored.

        :param db: The name of the security database

        :return: The database object
        """
        self._config['security-database'] = db
        return self

    def security_database_name(self):
        """
        The security database.

        This is the name of the database
        in which security related documents will be stored.

        :return: The security database name
        """
        if 'security-database' in self._config:
            return self._config['security-database']
        return None

    def set_triggers_database_name(self, db='Triggers'):
        """
        Sets the database that contains triggers.

        This is the name of the database
        in which triggers will be stored.

        :param db: The name of the triggers database

        :return: The database object
        """
        self._config['triggers-database'] = db
        return self

    def triggers_database_name(self):
        """
        The database that contains triggers.

        This is the name of the database
        in which triggers will be stored.

        :return: The name of the triggers database
        """
        if 'triggers-database' in self._config:
            return self._config['triggers-database']
        return None

    def set_schema_database_name(self, db='Schemas'):
        """
        Sets the database that contains schemas.

        This is the name of the database
        in which schemas will be stored.

        :param db: The name of the schema database

        :return: The database object
        """
        self._config['schema-database'] = db
        return self

    def schema_database_name(self):
        """
        The database that contains schemas.

        This is the name of the database
        in which schemas will be stored.

        :return: The name of the schema database
        """
        if 'schema-database' in self._config:
            return self._config['schema-database']
        return None

    def set_forest_names(self, forests):
        """
        Sets the names of the forests of the database.

        If a database is created from this database object, the named
        forests will be attached to the database. The forests will be
        created if necessary.

        :param forests: A list of forest names

        :return: The database object
        """
        validate_list_of_strings(forests)
        self._config['forest'] = forests
        return self

    def add_forest_name(self, forest):
        """
        Add a new forest name to the names of the forests of the database.

        If a database is created from this database object, the named
        forests will be attached to the database. The forests will be
        created if necessary.

        :param forest: The forest name

        :return: The database object
        """
        return self.add_to_property_list('forest', forest)

    def set_forest_names(self, forests):
        """
        Set the names of the forests of the database.

        If a database is created from this database object, the named
        forests will be attached to the database. The forests will be
        created if necessary.

        :param forest: The forest name

        :return: The database object
        """
        return self.set_property_list('forest', forests)

    def forest_names(self):
        """
        The names of the forests attached to the database.

        :return: The attached forests
        """
        if 'forest' in self._config:
            return self._config['forest']
        return None

    def set_language(self, language):
        """
        Sets the default language assumed for content (if xml:lang
        encoding is absent)

        *language* specifies the default language for content
        in this database. Any content without an ``xml:lang``
        attribute will be indexed in the language specifed
        here.

        :param language: The language abbreviation

        :return: The database object
        """
        validate_string(language)
        self._config['language'] = language
        return self

    def language(self):
        """
        The default language assumed for content (if xml:lang
        encoding is absent)

        *language* specifies the default language for content
        in this database. Any content without an ``xml:lang``
        attribute will be indexed in the language specifed
        here.

        :return: The default language for the database.
        """
        if 'language' in self._config:
            return self._config['language']
        return None

    def set_stemmed_searches(self, which='basic'):
        """
        Enable stemmed word searches (slower document loads
        and larger database files).

        Stemmed searches specifies whether index terms should
        be included in the database files to support stemming.
        When set to ``basic``, basic stemming is enabled, and
        the shortest stem of each word is indexed. When set
        to ``advanced``, all stems of each word are indexed.
        When set to ``decompounding``, all stems are indexed,
        and smaller component words of large compound words
        are also indexed. Each successive level of stemming
        improves recall of word searches, but also causes slower
        document loads and larger database files. Use ``off``
        to disable stemming.

        :param which: The stemmed search option

        :return: The database object
        """
        validate_stemmed_searches_type(which)
        self._config['stemmed-searches'] = which
        return self

    def stemmed_searches(self):
        """
        Returns the type of stemming currently associated with the database.

        See :meth:`set_stemmed_searches`.

        :return: The type of stemmed search
        """
        if 'stemmed-searches' in self._config:
            return self._config['stemmed-searches']
        return None

    def set_word_searches(self, enabled=False):
        """
        Sets enable unstemmed word searches (slower document loads
        and larger database files).

        *word searches* specifies whether index terms should
        be included in the database files to support fast word
        searches. When this parameter is true, word searches
        are faster, but document loading is slower and the
        database files are larger.

        :param enabled: Enable stemmed word searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['word-searches'] = enabled
        return self

    def word_searches(self):
        """
        Enable unstemmed word searches (slower document loads
        and larger database files).

        *word searches* specifies whether index terms should
        be included in the database files to support fast word
        searches. When this parameter is true, word searches
        are faster, but document loading is slower and the
        database files are larger.

        :return: Stemmed word searches enabled
        """
        if 'word-searches' in self._config:
            return self._config['word-searches']
        return None

    def set_word_positions(self, enabled=False):
        """
        Sets index word positions for faster phrase and near searches
        (slower document loads and larger database files).

        *word positions* specifies whether index data should
        be included in the database files to enable proximity
        searches (``cts:near-query``). When this parameter
        is true, positional searches are possible, but document
        loading is slower and the database files are larger.

        :param enabled: Enable searching on word positions

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['word-positions'] = enabled
        return self

    def word_positions(self):
        """
        Index word positions for faster phrase and near searches
        (slower document loads and larger database files).

        *word positions* specifies whether index data should
        be included in the database files to enable proximity
        searches (``cts:near-query``). When this parameter
        is true, positional searches are possible, but document
        loading is slower and the database files are larger.

        :return: Word positions are enabled
        """
        if 'word-positions' in self._config:
            return self._config['word-positions']
        return None

    def set_fast_phrase_searches(self, enabled=True):
        """
        Sets enable faster phrase searches (slower document loads
        and larger database files).

        *fast phrase searches* specifies whether index terms
        should be included in the database files to support
        fast phrase searches. When this parameter is true,
        phrase searches are faster, but document loading is
        slower and the database files are larger.

        :param enabled:  Enable faster phrase searching

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-phrase-searches'] = enabled
        return self

    def fast_phrase_searches(self):
        """
        Enable faster phrase searches (slower document loads
        and larger database files).

        *fast phrase searches* specifies whether index terms
        should be included in the database files to support
        fast phrase searches. When this parameter is true,
        phrase searches are faster, but document loading is
        slower and the database files are larger.

        :return: Fast phrase searches enabled
        """
        if 'fast-phrase-searches' in self._config:
            return self._config['fast-phrase-searches']
        return None

    def set_fast_reverse_searches(self, enabled=True):
        """
        Sets enable faster reverse searches (slower document loads
        and larger database files).

        *fast reverse searches* (valid alerting license key
        required) specifies whether index terms should be included
        in the database files to support fast reverse searches.
        When this parameter is true, cts:reverse-query searches
        are faster, but document loading is slower and the
        database files are larger.

        :param enabled: Faster reverse searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-reverse-searches'] = enabled
        return self

    def fast_reverse_searches(self):
        """
        Enable faster reverse searches (slower document loads
        and larger database files).

        *fast reverse searches* (valid alerting license key
        required) specifies whether index terms should be included
        in the database files to support fast reverse searches.
        When this parameter is true, cts:reverse-query searches
        are faster, but document loading is slower and the
        database files are larger.

        :return: Fast reverse searches enabled
        """
        if 'fast-reverse-searches' in self._config:
            return self._config['fast-reverse-searches']
        return None

    def set_triple_index(self, enabled=False):
        """
        Sets enable the RDF triple index (slower document loads
        and larger database files).

        *triple index* (valid semantics license key required)
        specifies whether index terms should be included in
        the database files to support SPARQL execution over
        RDF triples. When this parameter is true, sem:sparql()
        can be used, but document loading is slower and the
        database files are larger.

        :param enabled: Enable the triple index

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['triple-index'] = enabled
        return self

    def triple_index(self):
        """
        Enable the RDF triple index (slower document loads
        and larger database files).

        *triple index* (valid semantics license key required)
        specifies whether index terms should be included in
        the database files to support SPARQL execution over
        RDF triples. When this parameter is true, sem:sparql()
        can be used, but document loading is slower and the
        database files are larger.

        :return: The triple index enabled
        """
        if 'triple-index' in self._config:
            return self._config['triple-index']
        return None

    def set_triple_positions(self, enabled=False):
        """
        Sets index triple positions for faster near searches involving
        cts:triple-range-query (slower document loads and larger
        database files).

        *triple positions* specifies whether index data is
        included which speeds up the performance of proximity
        queries that use the ``cts:triple-range-query`` function.
        Triple positions also improve the accuracy of the ``item-frequency``
        option of ``cts:triples``.

        :param enabled: Enable triple positions

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['triple-positions'] = enabled
        return self

    def triple_positions(self):
        """
        Index triple positions for faster near searches involving
        cts:triple-range-query (slower document loads and larger
        database files).

        *triple positions* specifies whether index data is
        included which speeds up the performance of proximity
        queries that use the ``cts:triple-range-query`` function.
        Triple positions also improve the accuracy of the ``item-frequency``
        option of ``cts:triples``.

        :return: Triple positions enabled
        """
        if 'triple-positions' in self._config:
            return self._config['triple-positions']
        return None

    def set_fast_case_sensitive_searches(self, enabled=True):
        """
        Sets enable faster case sensitive searches (slower document
        loads and larger database files).

        *fast case sensitive searches* specifies whether index
        terms should be included in the database files to support
        fast case-sensitive searches. When this parameter is
        true, case-sensitive searches are faster, but document
        loading is slower and the database files are larger.

        :param enabled: Enable faster case sensitive searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-case-sensitive-searches'] = enabled
        return self

    def fast_case_sensitive_searches(self):
        """
        Enable faster case sensitive searches (slower document
        loads and larger database files).

        *fast case sensitive searches* specifies whether index
        terms should be included in the database files to support
        fast case-sensitive searches. When this parameter is
        true, case-sensitive searches are faster, but document
        loading is slower and the database files are larger.

        :return: Fast case sensitive searches enabled
        """
        if 'fast-case-sensitive-searches' in self._config:
            return self._config['fast-case-sensitive-searches']
        return None

    def set_fast_diacritic_sensitive_searches(self, enabled=True):
        """
        Sets enable faster diacritic sensitive searches (slower
        document loads and larger database files).

        *fast diacritic sensitive searches* specifies whether
        index terms should be included in the database files
        to support fast diacritic-sensitive searches. When
        this parameter is true, diacritic-sensitive searches
        are faster, but document loading is slower and the
        database files are larger.

        :param enabled: Fast diacritic sensitive searches enabled.

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-diacritic-sensitive-searches'] = enabled
        return self

    def fast_diacritic_sensitive_searches(self):
        """
        Enable faster diacritic sensitive searches (slower
        document loads and larger database files).

        *fast diacritic sensitive searches* specifies whether
        index terms should be included in the database files
        to support fast diacritic-sensitive searches. When
        this parameter is true, diacritic-sensitive searches
        are faster, but document loading is slower and the
        database files are larger.

        :return: Fast diacritic sensitive searches enabled
        """
        if 'fast-diacritic-sensitive-searches' in self._config:
            return self._config['fast-diacritic-sensitive-searches']
        return None

    def set_fast_element_word_searches(self, enabled=True):
        """
        Sets enable faster element-word searches (slower document
        loads and larger database files).

        *fast element word searches* specifies whether index
        terms should be included in the database files to support
        fast element-word searches. When this parameter is
        true, element-word searches are faster, but document
        loading is slower and the database files are larger.

        :param enabled: Enable fast element word searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-element-word-searches'] = enabled
        return self

    def fast_element_word_searches(self):
        """
        Enable faster element-word searches (slower document
        loads and larger database files).

        *fast element word searches* specifies whether index
        terms should be included in the database files to support
        fast element-word searches. When this parameter is
        true, element-word searches are faster, but document
        loading is slower and the database files are larger.

        :return: Fast element word searches enabled
        """
        if 'fast-element-word-searches' in self._config:
            return self._config['fast-element-word-searches']
        return None

    def set_element_word_positions(self, enabled=False):
        """
        Sets index element word positions for faster element-based
        phrase and near searches (slower document loads and
        larger database files).

        *element word positions* specifies whether index data
        should be included in the database files to enable
        proximity searches (``cts:near-query``) within specific
        XML elements or JSON properties. You must also enable
        *word positions* in order to perform element position
        searches. When this parameter is true, positional searches
        are possible within an XML element or JSON property,
        but document loading is slower and the database files
        are larger.

        :param enabled: Enable element word positions

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['element-word-positions'] = enabled
        return self

    def element_word_positions(self):
        """
        Index element word positions for faster element-based
        phrase and near searches (slower document loads and
        larger database files).

        *element word positions* specifies whether index data
        should be included in the database files to enable
        proximity searches (``cts:near-query``) within specific
        XML elements or JSON properties. You must also enable
        *word positions* in order to perform element position
        searches. When this parameter is true, positional searches
        are possible within an XML element or JSON property,
        but document loading is slower and the database files
        are larger.

        :return: Fast element word searches enabled
        """
        if 'element-word-positions' in self._config:
            return self._config['element-word-positions']
        return None

    def set_fast_element_phrase_searches(self, enabled=True):
        """
        Sets enable faster element phrase searches (slower document
        loads and larger database files).

        *fast element phrase searches* specifies whether index
        terms should be included in the database files to enable
        fast element-phrase searches. When this parameter is
        true, element-phrase searches are faster, but document
        loading is slower and the database files are larger.

        :param enabled: Enable fast element phrase searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-element-phrase-searches'] = enabled
        return self

    def fast_element_phrase_searches(self):
        """
        Enable faster element phrase searches (slower document
        loads and larger database files).

        *fast element phrase searches* specifies whether index
        terms should be included in the database files to enable
        fast element-phrase searches. When this parameter is
        true, element-phrase searches are faster, but document
        loading is slower and the database files are larger.

        :return: Fast element phrase searches enabled
        """
        if 'fast-element-phrase-searches' in self._config:
            return self._config['fast-element-phrase-searches']
        return None

    def set_element_value_positions(self, enabled=False):
        """
        Sets index element value positions for faster near searches
        involving element-value-query (slower document loads
        and larger database files).

        *element value positions* specifies whether index data
        is included which speeds up the performance of proximity
        queries that use the ``cts:element-value-query`` function.
        Turn this index off if you are not interested in proximity
        queries and if you want to conserve disk space and
        decrease loading time.

        :param enabled: Enable element value positions

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['element-value-positions'] = enabled
        return self

    def element_value_positions(self):
        """
        Index element value positions for faster near searches
        involving element-value-query (slower document loads
        and larger database files).

        *element value positions* specifies whether index data
        is included which speeds up the performance of proximity
        queries that use the ``cts:element-value-query`` function.
        Turn this index off if you are not interested in proximity
        queries and if you want to conserve disk space and
        decrease loading time.

        :return: Element value positions enabled
        """
        if 'element-value-positions' in self._config:
            return self._config['element-value-positions']
        return None

    def set_attribute_value_positions(self, enabled=False):
        """
        Sets index attribute value positions for faster near searches
        involving element-attribute-value-query (slower document
        loads and larger database files).

        *attribute value positions* specifies whether index
        data is included which speeds up the performance of
        proximity queries that use the ``cts:element-attribute-value-query``
        function. Turn this index off if you are not interested
        in proximity queries and if you want to conserve disk
        space and decrease loading time.

        :param enabled: Attribute value positions

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['attribute-value-positions'] = enabled
        return self

    def attribute_value_positions(self):
        """
        Index attribute value positions for faster near searches
        involving element-attribute-value-query (slower document
        loads and larger database files).

        *attribute value positions* specifies whether index
        data is included which speeds up the performance of
        proximity queries that use the ``cts:element-attribute-value-query``
        function. Turn this index off if you are not interested
        in proximity queries and if you want to conserve disk
        space and decrease loading time.

        :return: Attribute value positions enabled
        """
        if 'attribute-value-positions' in self._config:
            return self._config['attribute-value-positions']
        return None

    def set_field_value_searches(self, enabled=False):
        """
        Sets index field values for faster searches involving field-value-query
        (slower document loads and larger database files).

        *field value searches* specifies whether index data
        is included which speeds up the performance of field
        value queries that use the ``cts:field-value-query``
        function. Turn this index off if you are not interested
        in field value queries and if you want to conserve
        disk space and decrease loading time.

        :param enabled: Field value searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['field-value-searches'] = enabled
        return self

    def field_value_searches(self):
        """
        Index field values for faster searches involving field-value-query
        (slower document loads and larger database files).

        *field value searches* specifies whether index data
        is included which speeds up the performance of field
        value queries that use the ``cts:field-value-query``
        function. Turn this index off if you are not interested
        in field value queries and if you want to conserve
        disk space and decrease loading time.

        :return: Field value searches enabled
        """
        if 'field-value-searches' in self._config:
            return self._config['field-value-searches']
        return None

    def set_field_value_positions(self, enabled=False):
        """
        Sets index field value positions for faster near searches
        involving field-value-query (slower document loads
        and larger database files).

        *field value positions* specifies whether index data
        is included which speeds up the performance of proximity
        queries that use the ``cts:field-value-query`` function.
        Turn this index off if you are not interested in proximity
        queries and if you want to conserve disk space and
        decrease loading time.

        :param enabled: Field value positions

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['field-value-positions'] = enabled
        return self

    def field_value_positions(self):
        """
        Index field value positions for faster near searches
        involving field-value-query (slower document loads
        and larger database files).

        *field value positions* specifies whether index data
        is included which speeds up the performance of proximity
        queries that use the ``cts:field-value-query`` function.
        Turn this index off if you are not interested in proximity
        queries and if you want to conserve disk space and
        decrease loading time.

        :return: Field value positions enabled
        """
        if 'field-value-positions' in self._config:
            return self._config['field-value-positions']
        return None

    def set_three_character_searches(self, enabled=False):
        """
        Sets enable wildcard searches and faster character-based
        XQuery predicates using three or more characters (slower
        document loads and larger database files).

        *three character searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains three or more consecutive
        non-wildcard characters (for example, abc*). When combined
        with a codepoint *word lexicon*, speeds the performance
        of any wildcard search (including searches with fewer
        than three consecutive non-wildcard characters). MarkLogic
        recommends combining the *three character search* index
        with a codepoint collation *word lexicon*. When this
        parameter is true, character searches are faster, but
        document loading is slower and the database files are
        larger.

        :param enabled: Three character wildcard searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['three-character-searches'] = enabled
        return self

    def three_character_searches(self):
        """
        Enable wildcard searches and faster character-based
        XQuery predicates using three or more characters (slower
        document loads and larger database files).

        *three character searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains three or more consecutive
        non-wildcard characters (for example, abc*). When combined
        with a codepoint *word lexicon*, speeds the performance
        of any wildcard search (including searches with fewer
        than three consecutive non-wildcard characters). MarkLogic
        recommends combining the *three character search* index
        with a codepoint collation *word lexicon*. When this
        parameter is true, character searches are faster, but
        document loading is slower and the database files are
        larger.

        :return: Three character searches enabled
        """
        if 'three-character-searches' in self._config:
            return self._config['three-character-searches']
        return None

    def set_three_character_word_positions(self, enabled=False):
        """
        Sets index word positions for three-character searches only
        when three-character-searches are enabled (slower document
        loads and larger database files).

        *three character word positions* specifies whether
        index data should be included in the database files
        to enable proximity searches (``cts:near-query``) within
        wildcard queries. You must also enable *three character
        searches* in order to perform wildcard position searches.
        When this parameter is true, positional searches are
        possible within a wildcard query, but document loading
        is slower and the database files are larger.

        :param enabled: Three character word positions

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['three-character-word-positions'] = enabled
        return self

    def three_character_word_positions(self):
        """
        Index word positions for three-character searches only
        when three-character-searches are enabled (slower document
        loads and larger database files).

        *three character word positions* specifies whether
        index data should be included in the database files
        to enable proximity searches (``cts:near-query``) within
        wildcard queries. You must also enable *three character
        searches* in order to perform wildcard position searches.
        When this parameter is true, positional searches are
        possible within a wildcard query, but document loading
        is slower and the database files are larger.

        :return: Three character word positions enabled
        """
        if 'three-character-word-positions' in self._config:
            return self._config['three-character-word-positions']
        return None

    def set_fast_element_character_searches(self, enabled=False):
        """
        Sets enable element wildcard searches and element-character-based
        XQuery predicates (slower document loads and larger
        database files).

        *fast element character searches* specifies whether
        index terms should be included in the database files
        to enable element wildcard searches and faster character-based
        XQuery predicates. When this parameter is true, element-character
        searches are faster, but document loading is slower
        and the database files are larger.

        :param enabled: Fast element character searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-element-character-searches'] = enabled
        return self

    def fast_element_character_searches(self):
        """
        Enable element wildcard searches and element-character-based
        XQuery predicates (slower document loads and larger
        database files).

        *fast element character searches* specifies whether
        index terms should be included in the database files
        to enable element wildcard searches and faster character-based
        XQuery predicates. When this parameter is true, element-character
        searches are faster, but document loading is slower
        and the database files are larger.

        :return: Fast element character searches
        """
        if 'fast-element-character-searches' in self._config:
            return self._config['fast-element-character-searches']
        return None

    def set_trailing_wildcard_searches(self, enabled=False):
        """
        Sets enable trailing wildcard searches (slower document
        loads and larger database files).

        *trailing wildcard searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains one or more consecutive
        non-wildcard characters at the beginning of the word,
        with the wildcard at the end of the word (for example,
        abc*). When this parameter is true, character searches
        are faster, but document loading is slower and the
        database files are larger.

        :param enabled: Wild card searches enabled

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['trailing-wildcard-searches'] = enabled
        return self

    def trailing_wildcard_searches(self):
        """
        Enable trailing wildcard searches (slower document
        loads and larger database files).

        *trailing wildcard searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains one or more consecutive
        non-wildcard characters at the beginning of the word,
        with the wildcard at the end of the word (for example,
        abc*). When this parameter is true, character searches
        are faster, but document loading is slower and the
        database files are larger.

        :return: Trailing wild card searches enabled
        """
        if 'trailing-wildcard-searches' in self._config:
            return self._config['trailing-wildcard-searches']
        return None

    def set_trailing_wildcard_word_positions(self, enabled=False):
        """
        Sets index word positions for trailing-wildcard searches
        only when trailing-wildcard-searches are enabled (slower
        document loads and larger database files).

        *trailing wildcard word positions* specifies whether
        index data should be included in the database files
        to enable proximity searches (``cts:near-query``) within
        trailing wildcard queries. You must also enable *trailing
        wildcard searches* in order to perform trailing wildcard
        position searches. When this parameter is true, positional
        searches are possible within a trailing wildcard query,
        but document loading is slower and the database files
        are larger.

        :param enabled: Index word positions for trailing wildcard searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['trailing-wildcard-word-positions'] = enabled
        return self

    def trailing_wildcard_word_positions(self):
        """
        Index word positions for trailing-wildcard searches
        only when trailing-wildcard-searches are enabled (slower
        document loads and larger database files).

        *trailing wildcard word positions* specifies whether
        index data should be included in the database files
        to enable proximity searches (``cts:near-query``) within
        trailing wildcard queries. You must also enable *trailing
        wildcard searches* in order to perform trailing wildcard
        position searches. When this parameter is true, positional
        searches are possible within a trailing wildcard query,
        but document loading is slower and the database files
        are larger.

        :return: Index word positions enabled
        """
        if 'trailing-wildcard-word-positions' in self._config:
            return self._config['trailing-wildcard-word-positions']
        return None

    def set_fast_element_trailing_wildcard_searches(self, enabled=False):
        """
        Sets enable element trailing wildcard searches (slower document
        loads and larger database files).

        *fast element trailing wildcard searches* specifies
        whether index terms should be included in the database
        files to enable element trailing wildcard searches
        and faster character-based XQuery predicates. When
        this parameter is true, element-trailing-wildcard searches
        are faster, but document loading is slower and the
        database files are larger.

        :param enabled: Enable trailing wildcard searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['fast-element-trailing-wildcard-searches'] = enabled
        return self

    def fast_element_trailing_wildcard_searches(self):
        """
        Enable element trailing wildcard searches (slower document
        loads and larger database files).

        *fast element trailing wildcard searches* specifies
        whether index terms should be included in the database
        files to enable element trailing wildcard searches
        and faster character-based XQuery predicates. When
        this parameter is true, element-trailing-wildcard searches
        are faster, but document loading is slower and the
        database files are larger.

        :return: Fast element trailing wildcard searches enabled
        """
        if 'fast-element-trailing-wildcard-searches' in self._config:
            return self._config['fast-element-trailing-wildcard-searches']
        return None

    def set_two_character_searches(self, enabled=False):
        """
        Sets enable wildcard searches and faster character-based
        XQuery predicates using two character (slower document
        loads and larger database files).

        *two character searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains two consecutive non-wildcard
        character (for example, ``ab*``). This index is not
        needed if you have *three character searches* and a
        *word lexicon*.

        :param enabled: Enable two character wildcard searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['two-character-searches'] = enabled
        return self

    def two_character_searches(self):
        """
        Enable wildcard searches and faster character-based
        XQuery predicates using two character (slower document
        loads and larger database files).

        *two character searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains two consecutive non-wildcard
        character (for example, ``ab*``). This index is not
        needed if you have *three character searches* and a
        *word lexicon*.

        :return: Two character wildcard searches enabled
        """
        if 'two-character-searches' in self._config:
            return self._config['two-character-searches']
        return None

    def set_one_character_searches(self, enabled=False):
        """
        Sets enable wildcard searches and faster character-based
        XQuery predicates using one character (slower document
        loads and larger database files).

        *one character searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains a single non-wildcard character
        (for example, ``a*``). This index is not needed if
        you have *three character searches* and a *word lexicon*.

        :param enabled: Enable one character wildcard searches

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['one-character-searches'] = enabled
        return self

    def one_character_searches(self):
        """
        Enable wildcard searches and faster character-based
        XQuery predicates using one character (slower document
        loads and larger database files).

        *one character searches* specifies whether indexes
        should be created to enable wildcard searches where
        the search pattern contains a single non-wildcard character
        (for example, ``a*``). This index is not needed if
        you have *three character searches* and a *word lexicon*.

        :return: One character wildcard searches enabled
        """
        if 'one-character-searches' in self._config:
            return self._config['one-character-searches']
        return None

    def set_uri_lexicon(self, enabled=True):
        """
        Sets maintain a lexicon of document URIs (slower document
        loads and larger database files).

        *uri lexicon* specifies whether to create a lexicon
        of all of the URIs in the database. The URI lexicon
        allows you to quickly list all of the URIs in the database
        and to perform lexicon-based queries on the URIs.

        :param enabled: Enable URI lexicon

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['uri-lexicon'] = enabled
        return self

    def uri_lexicon(self):
        """
        Maintain a lexicon of document URIs (slower document
        loads and larger database files).

        *uri lexicon* specifies whether to create a lexicon
        of all of the URIs in the database. The URI lexicon
        allows you to quickly list all of the URIs in the database
        and to perform lexicon-based queries on the URIs.

        :return: URI lexicon enabled
        """
        if 'uri-lexicon' in self._config:
            return self._config['uri-lexicon']
        return None

    def set_collection_lexicon(self, enabled=False):
        """
        Sets maintain a lexicon of collection URIs (slower document
        loads and larger database files).

        *collection lexicon* specifies whether to create a
        lexicon of all of the collection URIs in the database.
        The collection lexicon allows you to quickly list all
        of the collection URIs in the database and to perform
        lexicon-based queries on the URIs.

        :param enabled: Enable collection URI lexicon

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['collection-lexicon'] = enabled
        return self

    def collection_lexicon(self):
        """
        Maintain a lexicon of collection URIs (slower document
        loads and larger database files).

        *collection lexicon* specifies whether to create a
        lexicon of all of the collection URIs in the database.
        The collection lexicon allows you to quickly list all
        of the collection URIs in the database and to perform
        lexicon-based queries on the URIs.

        :return: Collection lexicon enabled
        """
        if 'collection-lexicon' in self._config:
            return self._config['collection-lexicon']
        return None

    def set_reindexer_enable(self, enabled=True):
        """
        Sets enable automatic reindexing after configuration changes.

        *reindexer enable* specifies whether indexes are automatically
        rebuilt in the background after index configuration
        settings are changed. When set to true, index configuration
        changes automatically initiate a background reindexing
        operation on the entire database. When set to false,
        any new index settings take effect for future documents
        loaded into the database; existing documents retain
        the old settings until they are reloaded or until you
        set reindexer enabled to true.

        :param enabled:

        :return:
        """
        validate_boolean(enabled)
        self._config['reindexer-enable'] = enabled
        return self

    def reindexer_enable(self):
        """
        Enable automatic reindexing after configuration changes.

        *reindexer enable* specifies whether indexes are automatically
        rebuilt in the background after index configuration
        settings are changed. When set to true, index configuration
        changes automatically initiate a background reindexing
        operation on the entire database. When set to false,
        any new index settings take effect for future documents
        loaded into the database; existing documents retain
        the old settings until they are reloaded or until you
        set reindexer enabled to true.

        :return: Automatic reindexing enabled
        """
        if 'reindexer-enable' in self._config:
            return self._config['reindexer-enable']
        return None

    def set_reindexer_throttle(self, limit=5):
        """
        Sets larger numbers mean work harder at reindexing.

        *reindexer throttle* sets the priority of system resources
        devoted to reindexing. Reindexing occurs in batches,
        where each batch is approximately 200 fragments. When
        set to 5 (the default), the reindexer works aggressively,
        starting the next batch of reindexing soon after finishing
        the previous batch. When set to 4, it waits longer
        between batches, when set to 3 it waits longer still,
        and so on until when it is set to 1, it waits the longest.
        Therefore, higher numbers give reindexing a higher
        priority and uses the most system resources.

        :param limit: The level of system resources

        :return: The database object
        """
        validate_integer_range(limit, 1, 5)
        self._config['reindexer-throttle'] = limit
        return self

    def reindexer_throttle(self):
        """
        Larger numbers mean work harder at reindexing.

        *reindexer throttle* sets the priority of system resources
        devoted to reindexing. Reindexing occurs in batches,
        where each batch is approximately 200 fragments. When
        set to 5 (the default), the reindexer works aggressively,
        starting the next batch of reindexing soon after finishing
        the previous batch. When set to 4, it waits longer
        between batches, when set to 3 it waits longer still,
        and so on until when it is set to 1, it waits the longest.
        Therefore, higher numbers give reindexing a higher
        priority and uses the most system resources.

        :return: The level of system resources
        """
        if 'reindexer-throttle' in self._config:
            return self._config['reindexer-throttle']
        return None

    def set_reindexer_timestamp(self, limit=0):
        """
        Sets reindex/refragment all fragments with timestamps less
        than or equal to the timestamp specified. 0 means no
        forced reindexing.

        *reindexer timestamp* specifies the timestamp of fragments
        to force a reindex/refragment operation. Click the
        get current timestamp button to enter the current system
        timestamp. When you set this parameter to a timestamp
        and *reindex enable* is set to ``true``, it causes
        a reindex and refragment operation on all fragments
        in the database that have a timestamp equal to or less
        than the specified timestamp. Note that if you restore
        a database that has a timestamp set, if there are fragments
        in the restored content that are older than the specified
        timestamp, they will start to reindex as soon as they
        are restored.

        :param limit: Reindexer timestamp

        :return: The document object
        """
        self._config['reindexer-timestamp'] = limit
        return self

    def reindexer_timestamp(self):
        """
        Reindex/refragment all fragments with timestamps less
        than or equal to the timestamp specified. 0 means no
        forced reindexing.

        *reindexer timestamp* specifies the timestamp of fragments
        to force a reindex/refragment operation. Click the
        get current timestamp button to enter the current system
        timestamp. When you set this parameter to a timestamp
        and *reindex enable* is set to ``true``, it causes
        a reindex and refragment operation on all fragments
        in the database that have a timestamp equal to or less
        than the specified timestamp. Note that if you restore
        a database that has a timestamp set, if there are fragments
        in the restored content that are older than the specified
        timestamp, they will start to reindex as soon as they
        are restored.

        :return: Reindexer timestamp in milliseconds
        """
        if 'reindexer-timestamp' in self._config:
            return self._config['reindexer-timestamp']
        return None

    def set_directory_creation(self, which='manual'):
        """
        Sets automatically (for WebDAV) or manually manage directories

        *directory creation* specifies whether directories
        are automatically created in the database when documents
        are created. The default for a new database is *manual*.
        The settings are:

        *automatic* specifies that a directory hierarchy is
        automatically created to match the URI of a document
        or a directory that is created. This is the recommended
        setting, especially if you are accessing the database
        with a WebDAV Server or if you are using it as a Modules
        database.*manual* specifies that directories must be
        manually created. No directory hierarchy is enforced.
        *manual-enforced* is the same as manual, except it
        raises an error if the parent directory does not exist
        when creating a document or directory. For example,
        in order to create a document with the URI http://marklogic/file.xml,
        the directory http://marklogic/ must first exist.

        :param which: The method of directory configuration

        :return: The database object
        """
        validate_directory_creation(which)
        self._config['directory-creation'] = which
        return self

    def directory_creation(self):
        """
        Automatically (for WebDAV) or manually manage directories

        *directory creation* specifies whether directories
        are automatically created in the database when documents
        are created. The default for a new database is *manual*.
        The settings are:

        *automatic* specifies that a directory hierarchy is
        automatically created to match the URI of a document
        or a directory that is created. This is the recommended
        setting, especially if you are accessing the database
        with a WebDAV Server or if you are using it as a Modules
        database.*manual* specifies that directories must be
        manually created. No directory hierarchy is enforced.
        *manual-enforced* is the same as manual, except it
        raises an error if the parent directory does not exist
        when creating a document or directory. For example,
        in order to create a document with the URI http://marklogic/file.xml,
        the directory http://marklogic/ must first exist.

        :return: Directory creation method
        """
        if 'directory-creation' in self._config:
            return self._config['directory-creation']
        return None

    def set_maintain_last_modified(self, enabled=False):
        """
        Sets maintain last-modified properties of documents.

        *maintain last modified* specifies whether to include
        a timestamp on the properties document for each document
        in the database.

        :param enabled: Maintain last-modified

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['maintain-last-modified'] = enabled
        return self

    def maintain_last_modified(self):
        """
        Maintain last-modified properties of documents.

        *maintain last modified* specifies whether to include
        a timestamp on the properties document for each document
        in the database.

        :return: Maintain last modified
        """
        if 'maintain-last-modified' in self._config:
            return self._config['maintain-last-modified']
        return None

    def set_maintain_directory_last_modified(self, enabled=False):
        """
        Sets maintain last-modified properties of directories.

        *maintain directory last modified* specifies whether
        to include a timestamp on the properties for each directory
        in the database.

        :param enabled: Maintain last-modified

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['maintain-directory-last-modified'] = enabled
        return self

    def maintain_directory_last_modified(self):
        """
        Maintain last-modified properties of directories.

        *maintain directory last modified* specifies whether
        to include a timestamp on the properties for each directory
        in the database.

        :return: Maintain directory last modified property enabled
        """
        if 'maintain-directory-last-modified' in self._config:
            return self._config['maintain-directory-last-modified']
        return None

    def set_inherit_permissions(self, enabled=False):
        """
        Sets new document default permissions include parent directory
        permissions.

        *inherit permissions* specifies whether documents and
        directories will inherit default permissions from the
        parent directory.

        :param enabled: Inherit document permissions from parent

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['inherit-permissions'] = enabled
        return self

    def inherit_permissions(self):
        """
        New document default permissions include parent directory
        permissions.

        *inherit permissions* specifies whether documents and
        directories will inherit default permissions from the
        parent directory.

        :return: Inherit document permissions from parent enabled
        """
        if 'inherit-permissions' in self._config:
            return self._config['inherit-permissions']
        return None

    def set_inherit_collections(self, enabled=False):
        """
        Sets new document default collections include parent directory
        collections.

        *inherit collections* specifies whether documents and
        directories will inherit default collections from the
        parent directory.

        :param enabled: Inherit collection from parent directory

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['inherit-collections'] = enabled
        return self

    def inherit_collections(self):
        """
        New document default collections include parent directory
        collections.

        *inherit collections* specifies whether documents and
        directories will inherit default collections from the
        parent directory.

        :return: Inherit default collections enabled
        """
        if 'inherit-collections' in self._config:
            return self._config['inherit-collections']
        return None

    def set_inherit_quality(self, enabled=False):
        """
        Sets new document default quality is inherited parent directory
        quality.

        *inherit quality* specifies whether documents and directories
        will inherit default quality settings from the parent
        directory.

        :param enabled: Inherit parent directory quality

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['inherit-quality'] = enabled
        return self

    def inherit_quality(self):
        """
        New document default quality is inherited parent directory
        quality.

        *inherit quality* specifies whether documents and directories
        will inherit default quality settings from the parent
        directory.

        :return: Inherity document quality
        """
        if 'inherit-quality' in self._config:
            return self._config['inherit-quality']
        return None

    def set_in_memory_limit(self, limit=262144):
        """
        Sets the maximum number of fragments in an in-memory stand.

        *in memory limit* specifies the maximum number of fragments
        in an in-memory stand. An in-memory stand contains
        the latest version of any new or changed fragments.
        Periodically, in-memory stands are written to disk
        as a new stand in the forest. Also, if a stand accumulates
        a number of fragments beyond this limit, it is automatically
        saved to disk by a background thread.

        :param limit: In memory fragment limit

        :return: The database object
        """
        self._config['in-memory-limit'] = limit
        return self

    def in_memory_limit(self):
        """
        The maximum number of fragments in an in-memory stand.

        *in memory limit* specifies the maximum number of fragments
        in an in-memory stand. An in-memory stand contains
        the latest version of any new or changed fragments.
        Periodically, in-memory stands are written to disk
        as a new stand in the forest. Also, if a stand accumulates
        a number of fragments beyond this limit, it is automatically
        saved to disk by a background thread.

        :return: In memory fragment limit
        """
        if 'in-memory-limit' in self._config:
            return self._config['in-memory-limit']
        return None

    def set_in_memory_list_size(self, limit=512):
        """
        Sets size of the in-memory list storage, in megabytes.

        *in memory list size* specifies the amount of cache
        and buffer memory to be allocated for managing termlist
        data for an in-memory stand.

        :param limit: The in memory list storage in megabytes

        :return: The database object
        """
        self._config['in-memory-list-size'] = limit
        return self

    def in_memory_list_size(self):
        """
        Size of the in-memory list storage, in megabytes.

        *in memory list size* specifies the amount of cache
        and buffer memory to be allocated for managing termlist
        data for an in-memory stand.

        :return: The in memory list storage size in megabytes
        """
        if 'in-memory-list-size' in self._config:
            return self._config['in-memory-list-size']
        return None

    def set_in_memory_tree_size(self, limit=128):
        """
        Sets size of the in-memory tree storage, in megabytes.

        *in memory tree size* specifies the amount of cache
        and buffer memory to be allocated for managing fragment
        data for an in-memory stand.

        :param limit: In memory tree storage size

        :return: The database object
        """
        self._config['in-memory-tree-size'] = limit
        return self

    def in_memory_tree_size(self):
        """
        Size of the in-memory tree storage, in megabytes.

        *in memory tree size* specifies the amount of cache
        and buffer memory to be allocated for managing fragment
        data for an in-memory stand.

        :return: In memory tree storage size
        """
        if 'in-memory-tree-size' in self._config:
            return self._config['in-memory-tree-size']
        return None

    def set_in_memory_range_index_size(self, limit=16):
        """
        Sets size of the in-memory range index storage, in megabytes.

        *in memory range index size* specifies the amount
        of cache and buffer memory to be allocated for managing
        range index data for an in-memory stand.

        :param limit: The in memory range index size

        :return: The database object
        """
        self._config['in-memory-range-index-size'] = limit
        return self

    def in_memory_range_index_size(self):
        """
        Size of the in-memory range index storage, in megabytes.

        *in memory range index size* specifies the amount
        of cache and buffer memory to be allocated for managing
        range index data for an in-memory stand.

        :return: The in-memory range index size
        """
        if 'in-memory-range-index-size' in self._config:
            return self._config['in-memory-range-index-size']
        return None

    def set_in_memory_reverse_index_size(self, limit=16):
        """
        Sets size of the in-memory reverse index storage, in megabytes.

        *in memory reverse index size* specifies the amount
        of cache and buffer memory to be allocated for managing
        reverse index data for an in-memory stand.

        :param limit: In memory reverse index size

        :return: The database object
        """
        self._config['in-memory-reverse-index-size'] = limit
        return self

    def in_memory_reverse_index_size(self):
        """
        Size of the in-memory reverse index storage, in megabytes.

        *in memory reverse index size* specifies the amount
        of cache and buffer memory to be allocated for managing
        reverse index data for an in-memory stand.

        :return: In memory reverse index size
        """
        if 'in-memory-reverse-index-size' in self._config:
            return self._config['in-memory-reverse-index-size']
        return None

    def set_in_memory_triple_index_size(self, limit=64):
        """
        Sets size of the in-memory triple index storage, in megabytes.

        *in memory triple index size* specifies the amount
        of cache and buffer memory to be allocated for managing
        triple index data for an in-memory stand.

        :param limit: The in memory triple index size

        :return: The database object
        """
        self._config['in-memory-triple-index-size'] = limit
        return self

    def in_memory_triple_index_size(self):
        """
        Size of the in-memory triple index storage, in megabytes.

        *in memory triple index size* specifies the amount
        of cache and buffer memory to be allocated for managing
        triple index data for an in-memory stand.

        :return: In memory triple index size
        """
        if 'in-memory-triple-index-size' in self._config:
            return self._config['in-memory-triple-index-size']
        return None

    def set_large_size_threshold(self, limit=1024):
        """
        Sets size threshold for large objects, in kilobytes.

        *large size threshold* specifies the size threshold
        for the system to decide whether to treat a document
        as "large".

        :param limit: Size limit for large objects

        :return: The database object
        """
        self._config['large-size-threshold'] = limit
        return self

    def large_size_threshold(self):
        """
        Size threshold for large objects, in kilobytes.

        *large size threshold* specifies the size threshold
        for the system to decide whether to treat a document
        as "large".

        :return: The large size threshold
        """
        if 'large-size-threshold' in self._config:
            return self._config['large-size-threshold']
        return None

    def set_locking(self, which='fast'):
        """
        Sets specifies how robust transaction locking should be.

        *locking* specifies how robust transaction locking
        should be. When set to ``strict``, locking enforces
        mutual exclusion on existing documents and on new documents.
        When set to ``fast``, locking enforces mutual exclusion
        on existing and new documents. Instead of locking all
        the forests on new documents, it uses a hash function
        to select one forest to lock. In general, this is faster
        than strict. However, for a short period of time after
        a new forest is added, some of the transactions need
        to be retried internally. When set to ``off``, locking
        does not enforce mutual exclusion on existing documents
        or on new documents; only use this setting if you are
        sure all documents you are loading are new (a new bulk
        load, for example), otherwise you might create duplicate
        URIs in the database.

        :param which: The type of transaction logging

        :return: The database object
        """
        validate_locking_type(which)
        self._config['locking'] = which
        return self

    def locking(self):
        """
        Specifies how robust transaction locking should be.

        *locking* specifies how robust transaction locking
        should be. When set to ``strict``, locking enforces
        mutual exclusion on existing documents and on new documents.
        When set to ``fast``, locking enforces mutual exclusion
        on existing and new documents. Instead of locking all
        the forests on new documents, it uses a hash function
        to select one forest to lock. In general, this is faster
        than strict. However, for a short period of time after
        a new forest is added, some of the transactions need
        to be retried internally. When set to ``off``, locking
        does not enforce mutual exclusion on existing documents
        or on new documents; only use this setting if you are
        sure all documents you are loading are new (a new bulk
        load, for example), otherwise you might create duplicate
        URIs in the database.

        :return: The transaction locking
        """
        if 'locking' in self._config:
            return self._config['locking']
        return None

    def set_journaling(self, which='fast'):
        """
        Sets specifies how robust transaction journaling should
        be.

        *journaling* specifies how robust transaction journaling
        should be. When set to ``strict``, the journal protects
        against MarkLogic Server process failures, host operating
        system kernel failures, and host hardware failures.
        When set to ``fast``, the journal protects against
        MarkLogic Server process failures but not against host
        operating system kernel failures or host hardware failures.
        When set to ``off``, the journal does not protect against
        MarkLogic Server process failures, host operating system
        kernel failures, or host hardware failures.

        :param which:The type of journaling

        :return: The database object
        """
        validate_locking_type(which)
        self._config['journaling'] = which
        return self

    def journaling(self):
        """
        Specifies how robust transaction journaling should
        be.

        *journaling* specifies how robust transaction journaling
        should be. When set to ``strict``, the journal protects
        against MarkLogic Server process failures, host operating
        system kernel failures, and host hardware failures.
        When set to ``fast``, the journal protects against
        MarkLogic Server process failures but not against host
        operating system kernel failures or host hardware failures.
        When set to ``off``, the journal does not protect against
        MarkLogic Server process failures, host operating system
        kernel failures, or host hardware failures.

        :return: The journaling
        """
        if 'journaling' in self._config:
            return self._config['journaling']
        return None

    def set_journal_size(self, limit=682):
        """
        Sets size of each journal file, in megabytes.

        *journal size* specifies the amount of disk storage
        to be allocated for each transaction journal.

        :param limit: The journal size

        :return: The database object
        """
        self._config['journal-size'] = limit
        return self

    def journal_size(self):
        """
        Size of each journal file, in megabytes.

        *journal size* specifies the amount of disk storage
        to be allocated for each transaction journal.

        :return: The journal size
        """
        if 'journal-size' in self._config:
            return self._config['journal-size']
        return None

    def set_journal_count(self, limit=2):
        """
        The journal count

        :param limit:The journal count

        :return: The database object
        """
        self._config['journal-count'] = limit
        return self

    def journal_count(self):
        """
        The journal count

        :return: The journal count
        """
        if 'journal-count' in self._config:
            return self._config['journal-count']
        return None

    def set_preallocate_journals(self, enabled=False):
        """
        Sets allocate journal files before executing transactions.

        *preallocate journals* specifies whether the transaction
        journal files should be allocated in the filesystem
        before executing any transactions. When set to true,
        initializing a forest may be slower, but subsequent
        loading will be faster.

        :param enabled:Pre-allocate journal files

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['preallocate-journals'] = enabled
        return self

    def preallocate_journals(self):
        """
        Allocate journal files before executing transactions.

        *preallocate journals* specifies whether the transaction
        journal files should be allocated in the filesystem
        before executing any transactions. When set to true,
        initializing a forest may be slower, but subsequent
        loading will be faster.

        :return: Pre-allocate journal files
        """
        if 'preallocate-journals' in self._config:
            return self._config['preallocate-journals']
        return None

    def set_preload_mapped_data(self, enabled=False):
        """
        Sets preload memory mapped forest information while mounting
        forest.

        *preload mapped data* specifies whether memory mapped
        data (for example, range indexes and word lexicons)
        are loaded immediately into memory when a stand is
        opened. If you do not preload the mapped data, it will
        be paged into memory dynamically when a query needs
        it.

        :param enabled: Preload memory mapped forest information

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['preload-mapped-data'] = enabled
        return self

    def preload_mapped_data(self):
        """
        Preload memory mapped forest information while mounting
        forest.

        *preload mapped data* specifies whether memory mapped
        data (for example, range indexes and word lexicons)
        are loaded immediately into memory when a stand is
        opened. If you do not preload the mapped data, it will
        be paged into memory dynamically when a query needs
        it.

        :return: Preload memory mapped forest information
        """
        if 'preload-mapped-data' in self._config:
            return self._config['preload-mapped-data']
        return None

    def set_preload_replica_mapped_data(self, enabled=False):
        """
        Sets preload memory mapped forest information while mounting
        replica forest.

        *preload mapped replica data* specifies whether memory
        mapped data (for example, range indexes and word lexicons)
        are loaded immediately into memory when a stand is
        opened. The setting of preload-replica-mapped-data
        is ignored if preload-mapped-data is set to false.

        :param enabled:Preload mapped replica forest information

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['preload-replica-mapped-data'] = enabled
        return self

    def preload_replica_mapped_data(self):
        """
        Preload memory mapped forest information while mounting
        replica forest.

        *preload mapped replica data* specifies whether memory
        mapped data (for example, range indexes and word lexicons)
        are loaded immediately into memory when a stand is
        opened. The setting of preload-replica-mapped-data
        is ignored if preload-mapped-data is set to false.

        :return: Preload mapped replica forest information
        """
        if 'preload-replica-mapped-data' in self._config:
            return self._config['preload-replica-mapped-data']
        return None

    def set_range_index_optimize(self, which='facet-time'):
        """
        Sets specifies how to optimize range indexes.

        *range index optimize* specifies how range indexes
        are to be optimized. When set to ``facet-time``, range
        indexes are optimized to minimize the amount of CPU
        time used. When set to ``memory-size``, range indexes
        are optimized to minimize the amount of memory used.

        :param which:Range index optimization option

        :return: The database object
        """
        validate_range_index_optimize_options(which)
        self._config['range-index-optimize'] = which
        return self

    def range_index_optimize(self):
        """
        Specifies how to optimize range indexes.

        *range index optimize* specifies how range indexes
        are to be optimized. When set to ``facet-time``, range
        indexes are optimized to minimize the amount of CPU
        time used. When set to ``memory-size``, range indexes
        are optimized to minimize the amount of memory used.

        :return: Range index optimization type
        """
        if 'range-index-optimize' in self._config:
            return self._config['range-index-optimize']
        return None

    def set_positions_list_max_size(self, limit=256):
        """
        Sets maximum size of a positions-containing list, in megabytes.
        Lists longer than this have positions discarded.

        *positions list max size* specifies the maximum size,
        in megabytes, of the position list portion of the index
        for a given term. If the position list size for a given
        term grows larger than the limit specified, then the
        position information for that term is discarded. The
        default value is 256, the minimum value is 1, and the
        maximum value is 512. For example, position queries
        (``cts:near-query``) for frequently occurring words
        that have reached this limit (words like , , , and
        so on) are resolved without using the indexes. Even
        though those types of words are resolved without using
        the indexes, this limit helps improve performance by
        making the indexes smaller and more efficient to the
        data actually loaded in the database.

        :param limit:Max position containing list size

        :return: The database object
        """
        self._config['positions-list-max-size'] = limit
        return self

    def positions_list_max_size(self):
        """
        Maximum size of a positions-containing list, in megabytes.
        Lists longer than this have positions discarded.

        *positions list max size* specifies the maximum size,
        in megabytes, of the position list portion of the index
        for a given term. If the position list size for a given
        term grows larger than the limit specified, then the
        position information for that term is discarded. The
        default value is 256, the minimum value is 1, and the
        maximum value is 512. For example, position queries
        (``cts:near-query``) for frequently occurring words
        that have reached this limit (words like , , , and
        so on) are resolved without using the indexes. Even
        though those types of words are resolved without using
        the indexes, this limit helps improve performance by
        making the indexes smaller and more efficient to the
        data actually loaded in the database.

        :return: The maximum position containing list size
        """
        if 'positions-list-max-size' in self._config:
            return self._config['positions-list-max-size']
        return None

    def set_format_compatibility(self, which='automatic'):
        """
        Sets version of on-disk forest format.

        *format compatibility* specifies the version compatibility
        that MarkLogic Server applies to the indexes for this
        database during request evaluation. Setting this to
        a value other than ``automatic`` specifies that all
        forest data has the specified on-disk format, and it
        disables the automatic checking for index compatibility
        information. The automatic detection occurs during
        database startup and after any database configuration
        changes, and can take some time and system resources
        for very large forests and for very large clusters.
        The default value of ``automatic`` is recommended for
        most installations.

        :param which:On disk forest format

        :return: The database object
        """
        validate_format_compatibility_options(which)
        self._config['format-compatibility'] = which
        return self

    def format_compatibility(self):
        """
        Version of on-disk forest format.

        *format compatibility* specifies the version compatibility
        that MarkLogic Server applies to the indexes for this
        database during request evaluation. Setting this to
        a value other than ``automatic`` specifies that all
        forest data has the specified on-disk format, and it
        disables the automatic checking for index compatibility
        information. The automatic detection occurs during
        database startup and after any database configuration
        changes, and can take some time and system resources
        for very large forests and for very large clusters.
        The default value of ``automatic`` is recommended for
        most installations.

        :return: The on-disk forest format
        """
        if 'format-compatibility' in self._config:
            return self._config['format-compatibility']
        return None

    def set_index_detection(self, which='automatic'):
        """
        Sets handling of differences between the current configuration
        of database indexes and on-disk settings.

        *index detection* specifies whether to auto-detect
        index compatibility between the content and the current
        database settings. This detection occurs during database
        startup and after any database configuration changes,
        and can take some time and system resources for very
        large forests and for very large clusters. Setting
        this to ``none`` also causes queries to use the current
        database index settings, even if some settings have
        not completed reindexing. The default value of ``automatic``
        is recommended for most installations.

        :param which:How to handle differences in configuration settings

        :return: The database object
        """
        validate_index_detection_options(which)
        self._config['index-detection'] = which
        return self

    def index_detection(self):
        """
        Handling of differences between the current configuration
        of database indexes and on-disk settings.

        *index detection* specifies whether to auto-detect
        index compatibility between the content and the current
        database settings. This detection occurs during database
        startup and after any database configuration changes,
        and can take some time and system resources for very
        large forests and for very large clusters. Setting
        this to ``none`` also causes queries to use the current
        database index settings, even if some settings have
        not completed reindexing. The default value of ``automatic``
        is recommended for most installations.

        :return: How to handle differences in configuration settings
        """
        if 'index-detection' in self._config:
            return self._config['index-detection']
        return None

    def set_expunge_locks(self, which='none'):
        """
        Sets garbage collection of timed locks that have expired.

        *expunge locks* specifies if MarkLogic Server will
        automatically expunge any lock fragments created using
        ``xdmp:lock-acquire`` with specified timeouts. Setting
        this ``automatic`` causes a background task to run
        regularly to clean up expired lock fragments. The default
        setting is ``none``, meaning lock fragments will remain
        in the database after the locks expire (although they
        will no longer be locking any documents) until they
        are explicitly removed with ``xdmp:lock-release``.

        :param which:Garbage collect timed locks

        :return: The database object
        """
        validate_expunge_locks_options(which)
        self._config['expunge-locks'] = which
        return self

    def expunge_locks(self):
        """
        Garbage collection of timed locks that have expired.

        *expunge locks* specifies if MarkLogic Server will
        automatically expunge any lock fragments created using
        ``xdmp:lock-acquire`` with specified timeouts. Setting
        this ``automatic`` causes a background task to run
        regularly to clean up expired lock fragments. The default
        setting is ``none``, meaning lock fragments will remain
        in the database after the locks expire (although they
        will no longer be locking any documents) until they
        are explicitly removed with ``xdmp:lock-release``.

        :return: How to garbage collect timed locks
        """
        if 'expunge-locks' in self._config:
            return self._config['expunge-locks']
        return None

    def set_tf_normalization(self, which='scaled-log'):
        """
        Sets what kind of TF normalization to apply.

        *tf normalization* specifies whether to use the default
        term-frequency normalization (``scaled-log``), which
        scales the term frequency based on the size of the
        document, or to use the ``unscaled-log``, which uses
        term frequency as a function of the actual term frequency
        in a document, regardless of the document size, or
        to choose an intermediate level of scaling with lower
        impact than the default document size-based scaling.

        :param which: The term frequency normalization

        :return: The database object
        """
        validate_term_frequency_normalization_options(which)
        self._config['tf-normalization'] = which
        return self

    def tf_normalization(self):
        """
        What kind of TF normalization to apply.

        *tf normalization* specifies whether to use the default
        term-frequency normalization (``scaled-log``), which
        scales the term frequency based on the size of the
        document, or to use the ``unscaled-log``, which uses
        term frequency as a function of the actual term frequency
        in a document, regardless of the document size, or
        to choose an intermediate level of scaling with lower
        impact than the default document size-based scaling.

        :return: The term frequency normalization option
        """
        if 'tf-normalization' in self._config:
            return self._config['tf-normalization']
        return None

    def set_merge_priority(self, which='lower'):
        """
        Sets the CPU scheduler priority for merges.

        *merge priority* specifies the CPU scheduler priority
        at which merges should run. The settings are:

        *normal* specifies the same CPU scheduler priority
        as for requests.

        *lower* specifies a lower CPU scheduler priority than
        for requests.

        Merges always run with normal priority on forests with
        more than 16 stands.

        :param which:CPU scheduling hint for merges

        :return: The database object
        """
        validate_merge_priority_options(which)
        self._config['merge-priority'] = which
        return self

    def merge_priority(self):
        """
        The CPU scheduler priority for merges.

        *merge priority* specifies the CPU scheduler priority
        at which merges should run. The settings are:

        *normal* specifies the same CPU scheduler priority
        as for requests.

        *lower* specifies a lower CPU scheduler priority than
        for requests.

        Merges always run with normal priority on forests with
        more than 16 stands.

        :return: CPU scheduling hint for merges
        """
        if 'merge-priority' in self._config:
            return self._config['merge-priority']
        return None

    def set_merge_max_size(self, limit=32768):
        """
        Sets maximum allowable size (in megabytes) for merges, or
        0 for no limit.

        *merge max size* specifies the maximum size, in megabytes,
        of a stand that will result from a merge. If a stand
        grows beyond the specified size, it will not be merged.
        If two stands would be larger than the specified size
        if merged, they will not be merged together. If you
        set this to smaller sizes, large merges (which may
        require more disk and CPU resources) will be prevented.
        Set this to 0 to allow any sized stand to merge. The
        default is 32768 (32G), which provides a good balance
        between keeping the number of stands low and preventing
        merges from needing large amounts of free disk space.
        Use care when setting this to a non-zero value lower
        than the default value, however, as this can prevent
        merges which are ultimately required for the system
        to maintain performance levels and to allow optimized
        updates to the system. It is possible for a stand larger
        than the merge-max-size to merge if the stand has enough
        deleted fragments to trigger the merge min ratio; in
        this case, MarkLogic will do a single-stand merge,
        merging out the deleted fragments (even if the resulting
        stand is larger than the merge-max-size value specified).

        :param limit:Size in megabytes

        :return: The database object
        """
        self._config['merge-max-size'] = limit
        return self

    def merge_max_size(self):
        """
        Maximum allowable size (in megabytes) for merges, or
        0 for no limit.

        *merge max size* specifies the maximum size, in megabytes,
        of a stand that will result from a merge. If a stand
        grows beyond the specified size, it will not be merged.
        If two stands would be larger than the specified size
        if merged, they will not be merged together. If you
        set this to smaller sizes, large merges (which may
        require more disk and CPU resources) will be prevented.
        Set this to 0 to allow any sized stand to merge. The
        default is 32768 (32G), which provides a good balance
        between keeping the number of stands low and preventing
        merges from needing large amounts of free disk space.
        Use care when setting this to a non-zero value lower
        than the default value, however, as this can prevent
        merges which are ultimately required for the system
        to maintain performance levels and to allow optimized
        updates to the system. It is possible for a stand larger
        than the merge-max-size to merge if the stand has enough
        deleted fragments to trigger the merge min ratio; in
        this case, MarkLogic will do a single-stand merge,
        merging out the deleted fragments (even if the resulting
        stand is larger than the merge-max-size value specified).
        """
        if 'merge-max-size' in self._config:
            return self._config['merge-max-size']
        return None

    def set_merge_min_size(self, limit=1024):
        """
        Sets stands with fewer than this number of fragments are
        merged together.

        *merge min size* specifies the minimum number of fragments
        that stands can contain. Two or more Stands with fewer
        than this number of fragments are automatically merged.

        :param limit:Minimum stand count for merge

        :return: The database object
        """
        self._config['merge-min-size'] = limit
        return self

    def merge_min_size(self):
        """
        Stands with fewer than this number of fragments are
        merged together.

        *merge min size* specifies the minimum number of fragments
        that stands can contain. Two or more Stands with fewer
        than this number of fragments are automatically merged.

        :return: Minimum stand count for merge
        """
        if 'merge-min-size' in self._config:
            return self._config['merge-min-size']
        return None

    def set_merge_min_ratio(self, limit=2):
        """
        Sets larger ratios trigger more merges.

        *merge min ratio* specifies the minimum ratio between
        the number of stand fragments. Stands with a fragment
        count below this ratio relative to all smaller stands
        are automatically merged with the smaller stands. Specify
        a positive integer for the merge min ratio.

        :param limit: The marge min ratio

        :return: The database object
        """
        self._config['merge-min-ratio'] = limit
        return self

    def merge_min_ratio(self):
        """
        Larger ratios trigger more merges.

        *merge min ratio* specifies the minimum ratio between
        the number of stand fragments. Stands with a fragment
        count below this ratio relative to all smaller stands
        are automatically merged with the smaller stands. Specify
        a positive integer for the merge min ratio.

        :return: The marge min ratio
        """
        if 'merge-min-ratio' in self._config:
            return self._config['merge-min-ratio']
        return None

    def set_merge_timestamp(self, limit=0):
        """
        Sets the earliest system timestamp allowed for requests,
        or 0 to indicate the timestamp corresponding to the
        time of latest merge. Merges discard information about
        earlier timestamps. Entering a value of type xs:dateTime
        will have it automatically converted to its corresponding
        timestamp. A negative value indicates a timestamp relative
        to the time of the latest merge, at ten million ticks
        per second. For example, -6000000000 means ten minutes
        before the latest merge. A value in red indicates that
        you have filled in the text field with the current
        timestamp, but have not clicked ok to save the value
        to your config file.

        *merge timestamp* specifies the timestamp stored on
        merged stands. This is used for point-in-time queries,
        and determines when space occupied by deleted fragments
        and old versions of fragments may be reclaimed by the
        database. If a fragment is deleted or updated at a
        time after the merge timestamp, then the old version
        of the fragment is retained for use in point-in-time
        queries. Set this to 0 (the default) to let the system
        reclaim the maximum amount of disk space during merge
        activities. A setting of 0 will remove all deleted
        and updated fragments when a merge occurs. Set this
        to 1 before loading or updating any content to create
        a complete archive of the changes to the database over
        time. Set this to the current timestamp (by clicking
        the *current timestamp* button) to preserve all versions
        of content from this point on. Set this to a negative
        number to specify a window of timestamp values, relative
        to the last merge, at ten million ticks per second.
        The timestamp is a number maintained by MarkLogic Server
        that increments every time a change occurs in any of
        the databases in a system (including configuration
        changes from any host in a cluster). To set to the
        current timestamp, click the *current timestamp* button;
        the timestamp is displayed in in red until you press
        OK to activate the timestamp for future merges. For
        details on point-in-time queries, see the .

        :param limit:Minimum value

        :return: The database object
        """
        self._config['merge-timestamp'] = limit
        return self

    def merge_timestamp(self):
        """
        The earliest system timestamp allowed for requests,
        or 0 to indicate the timestamp corresponding to the
        time of latest merge. Merges discard information about
        earlier timestamps. Entering a value of type xs:dateTime
        will have it automatically converted to its corresponding
        timestamp. A negative value indicates a timestamp relative
        to the time of the latest merge, at ten million ticks
        per second. For example, -6000000000 means ten minutes
        before the latest merge. A value in red indicates that
        you have filled in the text field with the current
        timestamp, but have not clicked ok to save the value
        to your config file.

        *merge timestamp* specifies the timestamp stored on
        merged stands. This is used for point-in-time queries,
        and determines when space occupied by deleted fragments
        and old versions of fragments may be reclaimed by the
        database. If a fragment is deleted or updated at a
        time after the merge timestamp, then the old version
        of the fragment is retained for use in point-in-time
        queries. Set this to 0 (the default) to let the system
        reclaim the maximum amount of disk space during merge
        activities. A setting of 0 will remove all deleted
        and updated fragments when a merge occurs. Set this
        to 1 before loading or updating any content to create
        a complete archive of the changes to the database over
        time. Set this to the current timestamp (by clicking
        the *current timestamp* button) to preserve all versions
        of content from this point on. Set this to a negative
        number to specify a window of timestamp values, relative
        to the last merge, at ten million ticks per second.
        The timestamp is a number maintained by MarkLogic Server
        that increments every time a change occurs in any of
        the databases in a system (including configuration
        changes from any host in a cluster). To set to the
        current timestamp, click the *current timestamp* button;
        the timestamp is displayed in in red until you press
        OK to activate the timestamp for future merges. For
        details on point-in-time queries, see the .

        :return: Minimum value
        """
        if 'merge-timestamp' in self._config:
            return self._config['merge-timestamp']
        return None

    def set_retain_until_backup(self, enabled=False):
        """
        Sets retain deleted fragments until backup.

        *retain until backup* specifies whether the deleted
        fragments are retained since the last full or incremental
        backup.
        """
        self._config['retain-until-backup'] = enabled
        return self

    def set_rebalancer_enable(self, enabled=True):
        """
        Sets enable automatic rebalancing after configuration changes.

        *rebalancer enable* specifies whether rebalancing are
        automatically performed in the background after configuration
        settings are changed. When set to true, configuration
        changes automatically initiate a background rebalancing
        operation on the entire database.

        :param enabled: Enable automatic rebalancing

        :return: The database object
        """
        validate_boolean(enabled)
        self._config['rebalancer-enable'] = enabled
        return self

    def rebalancer_enable(self):
        """
        Enable automatic rebalancing after configuration changes.

        *rebalancer enable* specifies whether rebalancing are
        automatically performed in the background after configuration
        settings are changed. When set to true, configuration
        changes automatically initiate a background rebalancing
        operation on the entire database.

        :return: Enable automatic rebalancing
        """
        if 'rebalancer-enable' in self._config:
            return self._config['rebalancer-enable']
        return None

    def set_rebalancer_throttle(self, limit=5):
        """
        Sets larger numbers mean work harder at rebalancing.

        *rebalancer throttle* sets the priority of system resources
        devoted to rebalancing. Rebalancing occurs in batches,
        where each batch is approximately 200 fragments. When
        set to 5 (the default), the rebalancer works aggressively,
        starting the next batch of rebalancing soon after finishing
        the previous batch. When set to 4, it waits longer
        between batches, when set to 3 it waits longer still,
        and so on until when it is set to 1, it waits the longest.
        Therefore, higher numbers give rebalancing a higher
        priority and uses the most system resources.

        :param limit:The relative amount of resources to dedicate to rebalancing

        :return: The database object
        """
        validate_integer_range(limit, 1, 5)
        self._config['rebalancer-throttle'] = limit
        return self

    def rebalancer_throttle(self):
        """
        Larger numbers mean work harder at rebalancing.

        *rebalancer throttle* sets the priority of system resources
        devoted to rebalancing. Rebalancing occurs in batches,
        where each batch is approximately 200 fragments. When
        set to 5 (the default), the rebalancer works aggressively,
        starting the next batch of rebalancing soon after finishing
        the previous batch. When set to 4, it waits longer
        between batches, when set to 3 it waits longer still,
        and so on until when it is set to 1, it waits the longest.
        Therefore, higher numbers give rebalancing a higher
        priority and uses the most system resources.

        :return: The relative amount of resources to dedicate to rebalancing
        """
        if 'rebalancer-throttle' in self._config:
            return self._config['rebalancer-throttle']
        return None

    def set_assignment_policy(self, which='bucket'):
        """
        Sets the policy to use for assignment and rebalancing.

        *assignment policy* specifies what policy to use for
        assignment and rebalancing. The default for a new database
        is *bucket*. The settings are: *legacy* specifies the
        policy that already exists on MarkLogic 6. *bucket*
        specifies a policy that first assigns a document to
        a logical bucket based on its URI then assigns the
        bucket to a forest. *range* specifies a policy that
        assigns a document based on its data correspondent
        to the "partition key" of the database.

        :param which:The policy for assignment and rebalancing

        :return: The database object
        """
        validate_assignment_policy_options(which)
        self._config['assignment-policy'] = {"assignment-policy-name": which}
        return self

    def assignment_policy(self):
        """
        The policy to use for assignment and rebalancing.

        *assignment policy* specifies what policy to use for
        assignment and rebalancing. The default for a new database
        is *bucket*. The settings are: *legacy* specifies the
        policy that already exists on MarkLogic 6. *bucket*
        specifies a policy that first assigns a document to
        a logical bucket based on its URI then assigns the
        bucket to a forest. *range* specifies a policy that
        assigns a document based on its data correspondent
        to the "partition key" of the database.

        :return: The policy for assignment and rebalancing
        """
        if 'assignment-policy' in self._config:
            return self._config['assignment-policy']
        return None

    def path_namespaces(self):
        """
        Return the path namespaces defined or None, if no path namespaces
        are defined.

        :return: The path namespaces or none
        """
        if 'path-namespace' in self._config:
            return self._config['path-namespace']
        return None

    def add_path_namespace(self, path):
        """
        Add a path namespace for use by field paths.

        :param path: The PathNamespace

        :return: The database object
        """
        return self.add_to_property_list('path-namespace', path, PathNamespace)

    def set_path_namespaces(self, paths):
        if isinstance(paths, PathNamespace):
            self._config['path-namespace'] = [ paths ]
        else:
            if type(paths) is not list:
                raise ValidationError("List of paths expected.", repr(paths))
            for path in paths:
                if not(isinstance(path, PathNamespace)):
                    raise ValidationError("List of paths expected.", repr(path))
            self._config['path-namespace'] = paths

    def element_word_lexicons(self):
        """
        Return the word lexicons defined or None, if no lexicons
        are defined.

        :return: The lexicons or None
        """
        if 'element-word-lexicon' in self._config:
            return self._config['element-word-lexicon']
        return None

    def add_element_word_lexicon(self, lexicon):
        """
        Add a lexicon.

        :param lexicon: The lexicon.

        :return: The database object
        """
        return self.add_to_property_list('element-word-lexicon',
                                         lexicon, ElementWordLexicon)

    def set_element_word_lexicons(self, lexicons):
        self._config['element-word-lexicon'] \
          = assert_list_of_type(lexicons, ElementWordLexicon)

    def attribute_word_lexicons(self):
        """
        Return the attribute lexicons defined or None, if no lexicons
        are defined.

        :return: The lexicons or None
        """
        if 'element-attribute-word-lexicon' in self._config:
            return self._config['element-attribute-word-lexicon']
        return None

    def add_attribute_word_lexicon(self, lexicon):
        """
        Add an attribute lexicon.

        :param lexicon: The lexicon

        :return: The database object
        """
        return self.add_to_property_list('element-attribute-word-lexicon',
                                         lexicon, AttributeWordLexicon)

    def set_attribute_word_lexicons(self, lexicons):
        if isinstance(lexicons, AttributeWordLexicon):
            self._config['element-attribute-word-lexicon'] = [ lexicons ]
        else:
            if type(lexicons) is not list:
                raise ValidationError("List of lexicons expected.", repr(lexicons))
            for lexicon in lexicons:
                if not(isinstance(lexicon, AttributeWordLexicon)):
                    raise ValidationError("List of lexicons expected.", repr(lexicon))
            self._config['element-attribute-word-lexicon'] = lexicons

    def phrase_throughs(self):
        """
        Return the phrase throughs defined or None, if no phrase throughs
        are defined.

        :return: The throughs or None
        """
        if 'phrase-through' in self._config:
            return self._config['phrase-through']
        return None

    def add_phrase_through(self, through):
        """
        Add a phrase through.

        :param through: The phrase through.

        :return: The database object
        """
        return self.add_to_property_list('phrase-through',
                                         through, PhraseThrough)

    def set_phrase_throughs(self, throughs):
        self._config['phrase-through'] \
          = assert_list_of_type(throughs, PhraseThrough)

    def phrase_arounds(self):
        """
        Return the phrase arounds defined or None, if no phrase arounds
        are defined.

        :return: The arounds or None
        """
        if 'phrase-around' in self._config:
            return self._config['phrase-around']
        return None

    def add_phrase_around(self, around):
        """
        Add a phrase around.

        :param around: The phrase around.

        :return: The database object
        """
        return self.add_to_property_list('phrase-around',
                                         around, PhraseAround)

    def set_phrase_arounds(self, arounds):
        self._config['phrase-around'] \
          = assert_list_of_type(arounds, PhraseAround)

    def element_word_query_throughs(self):
        """
        Return the word query throughs defined or None, if no query throughs
        are defined.

        :return: The query throughs or None
        """
        if 'element-word-query-through' in self._config:
            return self._config['element-word-query_through']
        return None

    def add_element_word_query_through(self, query_through):
        """
        Add a query through.

        :param query_through: The query through.

        :return: The database object
        """
        return self.add_to_property_list('element-word-query-through',
                                         query_through, ElementWordQueryThrough)

    def set_element_word_query_throughs(self, query_throughs):
        if isinstance(query_throughs, ElementWordQueryThrough):
            self._config['element-word-query-through'] = [ query_throughs ]
        else:
            if type(query_throughs) is not list:
                raise ValidationError("List of query throughs expected.", repr(query_throughs))
            for query_through in query_throughs:
                if not(isinstance(query_through, ElementWordQueryThrough)):
                    raise ValidationError("List of query_throughs expected.", repr(query_through))
            self._config['element-word-query_through'] = query_throughs

    def default_rulesets(self):
        """
        Return the default rule sets or None, if no default rule sets
        are defined.

        :return: The default rule sets or None
        """
        if 'default-ruleset' in self._config:
            return self._config['default-ruleset']
        return None

    def add_default_ruleset(self, ruleset):
        """
        Add a default rule set.

        :param ruleset: The rule set.

        :return: The database object
        """
        return self.add_to_property_list('default-ruleset', ruleset, RuleSet)

    def set_rulesets(self, rulesets):
        """
        Set the default rulesets.
        """
        return self.set_property_list('default-ruleset', rulesets, RuleSet)

    def fragment_roots(self):
        """
        The fragment roots.
        """
        if 'fragment-root' in self._config:
            return self._config['fragment-root']
        return None

    def add_fragment_root(self, root):
        """
        Add a fragment root.
        """
        return self.add_to_property_list('fragment-root', root, FragmentRoot)

    def remove_fragment_root(self, root):
        """
        Remove a fragment root.
        """
        return self.remove_from_property_list('fragment-root', root, FragmentRoot)

    def set_fragment_roots(self, roots):
        """
        Set the fragment roots.
        """
        return self.set_property_list('fragment-root', roots, FragmentRoot)

    def fragment_parents(self):
        """
        The fragment parents.
        """
        if 'fragment-parent' in self._config:
            return self._config['fragment-parent']
        return None

    def add_fragment_parent(self, parent):
        """
        Add a fragment parent.
        """
        return self.add_to_property_list('fragment-parent', parent, FragmentParent)

    def remove_fragment_parent(self, parent):
        """
        Remove a fragment parent.
        """
        return self.remove_from_property_list('fragment-parent',
                                              parent, FragmentParent)

    def set_fragment_parents(self, parents):
        """
        Set the fragment parents.
        """
        return self.set_property_list('fragment-parent', parents, FragmentParent)

    def merge_blackouts(self):
        """
        The merge blackouts
        """
        if 'merge-blackout' in self._config:
            return self._config['merge-blackout']
        return None

    def set_merge_blackouts(self, blackouts):
        """
        Set the list of merge blackouts.
        """
        return self.set_property_list('merge-blackout', blackouts, MergeBlackout)

    def add_merge_blackout(self, merge_blackout):
        """
        Add a merge blackout.
        """
        return self.add_to_property_list('merge-blackout',
                                         merge_blackout, MergeBlackout)

    def remove_merge_blackout(self, merge_blackout):
        """
        Remove a merge blackout.
        """
        return self.remove_from_property_list('merge-blackout',
                                              merge_blackout, MergeBlackout)

    def scheduled_backups(self):
        """
        The scheduled backups.
        """
        if 'database-backup' in self._config:
            return self._config['database-backup']
        return None

    def set_scheduled_backups(self, backups):
        """
        Set the scheduled backups.
        """
        return self.set_property_list('database-backup',
                                      backups, ScheduledDatabaseBackup)

    def add_scheduled_backup(self, backup):
        """
        Add a scheduled backup.
        """
        return self.add_to_property_list('database-backup',
                                         backup, ScheduledDatabaseBackup)

    def remove_scheduled_backup(self, backup):
        """
        Remove a scheduled backup.
        """
        return self.remove_from_property_list('database-backup',
                                              backup, ScheduledDatabaseBackup)

    # ============================================================

    def backup(self, conn, backup_dir, forests=None,
               journal_archiving=False, journal_archive_path=None,
               lag_limit=30,
               incremental=False, incremental_dir=None):
        """
        Start a database backup.
        """
        return DatabaseBackup.backup(conn, self.name, backup_dir, forests,
                                     journal_archiving, journal_archive_path,
                                     lag_limit,
                                     incremental, incremental_dir)

    def restore(self, conn, backup_dir, forests=None,
                journal_archiving=False, journal_archive_path=None,
                incremental=False, incremental_dir=None):
        """
        Start a database restore.
        """
        return DatabaseRestore.restore(conn, self.name, backup_dir, forests,
                                       journal_archiving, journal_archive_path,
                                       incremental, incremental_dir)

    def clear(self, conn):
        """
        Clear the database.
        """
        payload = {
            'operation': 'clear-database',
            }

        uri = "http://{0}:{1}/manage/v2/databases/{2}" \
          .format(conn.host, conn.management_port, self.name)

        response = requests.post(uri, json=payload, auth=conn.auth,
                                 headers={'content-type': 'application/json',
                                          'accept': 'application/json'})

        if response.status_code > 299:
            raise UnexpectedManagementAPIResponse(response.text)

        return

    def merge(self, conn):
        """
        Initiate a merge on the database.
        """
        payload = {
            'operation': 'merge-database',
            }

        uri = "http://{0}:{1}/manage/v2/databases/{2}" \
          .format(conn.host, conn.management_port, self.name)

        response = requests.post(uri, json=payload, auth=conn.auth,
                                 headers={'content-type': 'application/json',
                                          'accept': 'application/json'})

        if response.status_code > 299:
            raise UnexpectedManagementAPIResponse(response.text)

        return

    def reindex(self, conn):
        """
        Initiate a re-index on the database.
        """
        payload = {
            'operation': 'reindex-database',
            }

        uri = "http://{0}:{1}/manage/v2/databases/{2}" \
          .format(conn.host, conn.management_port, self.name)

        response = requests.post(uri, json=payload, auth=conn.auth,
                                 headers={'content-type': 'application/json',
                                          'accept': 'application/json'})

        if response.status_code > 299:
            raise UnexpectedManagementAPIResponse(response.text)

        return

    # ============================================================

    def create(self, connection):
        """
        Create a new database defined by these parameters on the given connection.

        :param connection: The server connection

        :return: The database object
        """
        uri = "http://{0}:{1}/manage/v2/databases" \
          .format(connection.host, connection.management_port)

        forest_names = []
        # unicode doesn't exist in Python 3
        if sys.version_info[0] < 3:
            for forest_info in self._config['forest']:
                if isinstance(forest_info, str) or isinstance(forest_info, unicode):
                    new_forest = Forest(forest_info, host=self.hostname)
                    new_forest.create(connection)
                    forest_names.append(forest_info)

                elif isinstance(forest_info, Forest):
                    forest_info.create(connection)
                    forest_names.append(forest_info.name())
        else:
            for forest_info in self._config['forest']:
                if isinstance(forest_info, str):
                    new_forest = Forest(forest_info, host=self.hostname)
                    new_forest.create(connection)
                    forest_names.append(forest_info)

                elif isinstance(forest_info, Forest):
                    forest_info.create(connection)
                    forest_names.append(forest_info.name())

        self._config['forest'] = forest_names

        response = requests.post(uri, json=self._config, auth=connection.auth)
        if response.status_code > 299:
            raise UnexpectedManagementAPIResponse(response.text)

        return self

    def read(self, connection):
        """
        Loads the database from the MarkLogic server. This will refresh
        the properties of the object.

        :param connection: The connection to a MarkLogic server
        :return: The server object
        """
        database = Server.lookup(connection, self.database_name())
        if database is None:
            return None
        else:
            self._config = database._config
            self.etag = database.etag
            return self

    def update(self, connection):
        """
        Save the configuration changes with the given connection.
        If the database already exists on the
        given connection, then you can update the settings with this method.

        :param connection:The server connection

        :return: The database object
        """
        uri = "http://{0}:{1}/manage/v2/databases/{2}/properties" \
          .format(connection.host, connection.management_port, self.name)

        headers = {}
        if self.etag is not None:
            headers['if-match'] = self.etag

        struct = self.marshal()
        response = requests.put(uri, json=struct, auth=connection.auth,
                                headers=headers)

        if response.status_code > 299:
            raise UnexpectedManagementAPIResponse(response.text)

        # In case we renamed it
        self.name = self._config['database-name']

        return self

    def delete(self, connection):
        """
        Remove the given database and all its forests.

        :param connection: The server connection

        :return: The database object
        """
        uri = "http://{0}:{1}/manage/v2/databases/{2}?forest-delete=data" \
          .format(connection.host, connection.management_port, self.name)
        response = requests.delete(uri, auth=connection.auth)

        if response.status_code > 299 and not response.status_code == 404:
            raise UnexpectedManagementAPIResponse(response.text)

        return self

    def load_file(self, connection, path, uri, collections=None, content_type="application/json"):
        """
        Load a given file into a given database.

        :param connection: The server connection
        :param path: The path to the file
        :param uri: The uri for the file contents in the database
        :param collections: A list of collections
        :param content_type: The content type of the data

        :return: The database object
        """
        doc_url = "http://{0}:{1}/v1/documents?uri={2}&database={3}" \
          .format(connection.host, connection.port, uri, self.name)

        if collections is not None:
            for collection in collections:
                doc_url += ("&collection=" + collection)

        with open(path) as data_file:
            file_data = data_file.read()
            response = requests.put(doc_url, data=file_data, auth=connection.auth,
                                    headers={'content-type': content_type})
            if response.status_code > 299:
                raise UnexpectedAPIResponse(response.text)

        return self

    def load_directory_files(self, connection, path, prefix="/", collections=None, content_type="application/json"):
        """
        Load all the given files in a directory.  It will combine the prefix with the filename to generate
        a uri for the file on the server.

        :param connection: The server connection
        :param path: The path to the directory
        :param prefix: The prefix to the individuals files
        :param collections: A list of collections to use for the files
        :param content_type: The content type of the files

        :return: The database object
        """
        file_list = files.walk_directories(path)
        for result in file_list:
            self.load_file(connection, result['partial-directory'], prefix + result['filename'],
                           collections=collections, content_type=content_type)
        return self

    def load_directory(self, connection, path, prefix="/", collections=None, content_type="application/json"):
        """
        Load all the file in a directory, preserving the partial path between the directory root and the
        file.  So a file located at /data/files/myfile.xml, with a prefix parameter of '/data' will be
        loaded as /files/myfile.xml.  (Using the default prefix).

        :param connection: The server connection
        :param path: The path to the directory root
        :param prefix: The prefix to use when constructing the server URI for the file
        :param collections: The collections to use for the files
        :param content_type: The content type of the files

        :return: The database object
        """
        file_list = files.walk_directories(path)
        for result in file_list:
            self.load_file(connection, result['partial-directory'], prefix + result['partial-directory'],
                           collections=collections, content_type=content_type)
        return self

    @classmethod
    def lookup(cls, connection, name):
        """
        Lookup a database configuration by name.

        :param name:The name of the database
        :param connection:The server connection

        :return: The database configuration
        """
        uri = "http://{0}:{1}/manage/v2/databases/{2}/properties" \
          .format(connection.host, connection.management_port, name)

        logging.info("Reading database configuration: {0}".format(name))

        response = requests.get(uri, auth=connection.auth,
                                headers={'accept': 'application/json'})

        result = None
        if response.status_code == 200:
            result = Database.unmarshal(json.loads(response.text))
            if 'etag' in response.headers:
                result.etag = response.headers['etag']

        elif response.status_code != 404:
            raise UnexpectedManagementAPIResponse(response.text)

        return result

    @classmethod
    def list_databases(cls, connection):
        uri = "http://{0}:{1}/manage/v2/databases".format(connection.host, connection.management_port)
        response = requests.get(uri, auth=connection.auth, headers={'accept': 'application/json'})

        if response.status_code == 200:
            response_json = json.loads(response.text)
            db_count = response_json['database-default-list']['list-items']['list-count']['value']

            result = []
            if db_count > 0:
                for item in response_json['database-default-list']['list-items']['list-item']:
                    result.append(Database(item['nameref']))
        else:
            raise UnexpectedManagementAPIResponse(response.text)

        return result


    @classmethod
    def unmarshal(cls, config):
        result = Database("temp")
        result._config = config
        result.name = result._config['database-name']

        olist = []
        if 'range-element-index' in result._config:
            for index in result._config['range-element-index']:
                temp = ElementRangeIndex(index['scalar-type'],
                                         index['namespace-uri'],
                                         index['localname'],
                                         index['collation'],
                                         index['range-value-positions'] == 'true',
                                         index['invalid-values'])
                olist.append(temp)
        result._config['range-element-index'] = olist

        olist = []
        if 'range-field-index' in result._config:
            for index in result._config['range-field-index']:
                temp = FieldRangeIndex(index['scalar-type'],
                                       index['field-name'],
                                       index['collation'],
                                       index['range-value-positions'] == 'true',
                                       index['invalid-values'])
                olist.append(temp)
        result._config['range-field-index'] = olist

        olist = []
        if 'range-element-attribute-index' in result._config:
            for index in result._config['range-element-attribute-index']:
                temp = AttributeRangeIndex(index['scalar-type'],
                                           index['parent-namespace-uri'],
                                           index['parent-localname'],
                                           index['namespace-uri'],
                                           index['localname'],
                                           index['collation'],
                                           index['range-value-positions'] == 'true',
                                           index['invalid-values'])
                olist.append(temp)
        result._config['range-element-attribute-index'] = olist

        olist = []
        if 'range-path-index' in result._config:
            for index in result._config['range-path-index']:
                temp = PathRangeIndex(index['scalar-type'],
                                      index['path-expression'],
                                      index['collation'],
                                      index['range-value-positions'] == 'true',
                                      index['invalid-values'])
                olist.append(temp)
        result._config['range-path-index'] = olist

        olist = []
        if 'geospatial-element-index' in result._config:
            for index in result._config['geospatial-element-index']:
                temp = GeospatialElementIndex(index['namespace-uri'],
                                              index['localname'],
                                              index['coordinate-system'],
                                              index['point-format'],
                                              index['range-value-positions'] == 'true',
                                              index['invalid-values'])
                olist.append(temp)
        result._config['geospatial-element-index'] = olist

        olist = []
        if 'geospatial-path-index' in result._config:
            for index in result._config['geospatial-path-index']:
                temp = GeospatialPathIndex(index['path-expression'],
                                           index['coordinate-system'],
                                           index['point-format'],
                                           index['range-value-positions'] == 'true',
                                           index['invalid-values'])
                olist.append(temp)
        result._config['geospatial-path-index'] = olist

        olist = []
        if 'geospatial-element-child-index' in result._config:
            for index in result._config['geospatial-element-child-index']:
                temp = GeospatialElementChildIndex(
                          index['parent-namespace-uri'],
                          index['parent-localname'],
                          index['namespace-uri'],
                          index['localname'],
                          index['coordinate-system'],
                          index['point-format'],
                          index['range-value-positions'] == 'true',
                          index['invalid-values'])
                olist.append(temp)
        result._config['geospatial-element-child-index'] = olist

        olist = []
        if 'geospatial-element-pair-index' in result._config:
            for index in result._config['geospatial-element-pair-index']:
                temp = GeospatialElementPairIndex(
                          index['parent-namespace-uri'],
                          index['parent-localname'],
                          index['longitude-namespace-uri'],
                          index['longitude-localname'],
                          index['latitude-namespace-uri'],
                          index['latitude-localname'],
                          index['coordinate-system'],
                          index['range-value-positions'] == 'true',
                          index['invalid-values'])
                olist.append(temp)
        result._config['geospatial-element-pair-index'] = olist

        olist = []
        if 'geospatial-element-attribute-pair-index' in result._config:
            for index in result._config['geospatial-element-attribute-pair-index']:
                temp = GeospatialElementAttributePairIndex(
                          index['parent-namespace-uri'],
                          index['parent-localname'],
                          index['longitude-namespace-uri'],
                          index['longitude-localname'],
                          index['latitude-namespace-uri'],
                          index['latitude-localname'],
                          index['coordinate-system'],
                          index['range-value-positions'] == 'true',
                          index['invalid-values'])
                olist.append(temp)
        result._config['geospatial-element-attribute-pair-index'] = olist

        olist = []
        if 'fragment-root' in result._config:
            for root in result._config['fragment-root']:
                temp = FragmentRoot(root['namespace-uri'],root['localname'])
                olist.append(temp)
        result._config['fragment-root'] = olist

        olist = []
        if 'fragment-parent' in result._config:
            for root in result._config['fragment-parent']:
                temp = FragmentParent(root['namespace-uri'],root['localname'])
                olist.append(temp)
        result._config['fragment-parent'] = olist

        olist = []
        if 'merge-blackout' in result._config:
            for blackout in result._config['merge-blackout']:
                temp = None
                if (blackout['blackout-type'] == 'recurring'
                    and blackout['period'] is None):
                    temp = MergeBlackout.recurringAllDay(
                        blackout['merge-priority'],
                        blackout['limit'],
                        blackout['day'])
                elif (blackout['blackout-type'] == 'recurring'
                      and 'duration' in blackout['period']):
                    temp = MergeBlackout.recurringDuration(
                        blackout['merge-priority'],
                        blackout['limit'],
                        blackout['day'],
                        blackout['period']['start-time'],
                        blackout['period']['duration'])
                elif (blackout['blackout-type'] == 'recurring'
                      and 'end-time' in blackout['period']):
                    temp = MergeBlackout.recurringStartEnd(
                        blackout['merge-priority'],
                        blackout['limit'],
                        blackout['day'],
                        blackout['period']['start-time'],
                        blackout['period']['end-time'])
                elif (blackout['blackout-type'] == 'once'
                      and 'end-time' in blackout['period']):
                    temp = MergeBlackout.oneTimeStartEnd(
                        blackout['merge-priority'],
                        blackout['limit'],
                        blackout['period']['start-date'],
                        blackout['period']['start-time'],
                        blackout['period']['end-date'],
                        blackout['period']['end-time'])
                elif (blackout['blackout-type'] == 'once'
                      and 'duration' in blackout['period']):
                    temp = MergeBlackout.oneTimeDuration(
                        blackout['merge-priority'],
                        blackout['limit'],
                        blackout['period']['start-date'],
                        blackout['period']['start-time'],
                        blackout['period']['duration'])
                else:
                    raise UnexpectedManagementAPIResponse("Unparseable merge blackout period")

                olist.append(temp)
        result._config['merge-blackout'] = olist

        olist = []
        if 'database-backup' in result._config:
            for backup in result._config['database-backup']:
                incremental = None
                if 'incremental' in backup:
                    incremental = backup['incremental']

                temp = None
                if (backup['backup-type'] == 'minutely'):
                    temp = ScheduledDatabaseBackup.minutely(
                        backup['backup-directory'],
                        backup['backup-period'],
                        backup['max-backups'],
                        backup['backup-security-database'],
                        backup['backup-schemas-database'],
                        backup['backup-triggers-database'],
                        backup['include-replicas'],
                        incremental,
                        backup['journal-archiving'],
                        backup['journal-archive-path'],
                        backup['journal-archive-lag-limit'])
                elif (backup['backup-type'] == 'hourly'):
                    temp = ScheduledDatabaseBackup.hourly(
                        backup['backup-directory'],
                        backup['backup-period'],
                        backup['backup-start-time'],
                        backup['max-backups'],
                        backup['backup-security-database'],
                        backup['backup-schemas-database'],
                        backup['backup-triggers-database'],
                        backup['include-replicas'],
                        incremental,
                        backup['journal-archiving'],
                        backup['journal-archive-path'],
                        backup['journal-archive-lag-limit'])
                elif (backup['backup-type'] == 'daily'):
                    temp = ScheduledDatabaseBackup.daily(
                        backup['backup-directory'],
                        backup['backup-period'],
                        backup['backup-start-time'],
                        backup['max-backups'],
                        backup['backup-security-database'],
                        backup['backup-schemas-database'],
                        backup['backup-triggers-database'],
                        backup['include-replicas'],
                        incremental,
                        backup['journal-archiving'],
                        backup['journal-archive-path'],
                        backup['journal-archive-lag-limit'])
                elif (backup['backup-type'] == 'weekly'):
                    temp = ScheduledDatabaseBackup.weekly(
                        backup['backup-directory'],
                        backup['backup-period'],
                        backup['backup-day'],
                        backup['backup-start-time'],
                        backup['max-backups'],
                        backup['backup-security-database'],
                        backup['backup-schemas-database'],
                        backup['backup-triggers-database'],
                        backup['include-replicas'],
                        incremental,
                        backup['journal-archiving'],
                        backup['journal-archive-path'],
                        backup['journal-archive-lag-limit'])
                elif (backup['backup-type'] == 'monthly'):
                    temp = ScheduledDatabaseBackup.monthly(
                        backup['backup-directory'],
                        backup['backup-period'],
                        backup['backup-month-day'],
                        backup['backup-start-time'],
                        backup['max-backups'],
                        backup['backup-security-database'],
                        backup['backup-schemas-database'],
                        backup['backup-triggers-database'],
                        backup['include-replicas'],
                        incremental,
                        backup['journal-archiving'],
                        backup['journal-archive-path'],
                        backup['journal-archive-lag-limit'])
                elif (backup['backup-type'] == 'once'):
                    temp = ScheduledDatabaseBackup.once(
                        backup['backup-directory'],
                        backup['backup-start-date'],
                        backup['backup-start-time'],
                        backup['max-backups'],
                        backup['backup-security-database'],
                        backup['backup-schemas-database'],
                        backup['backup-triggers-database'],
                        backup['include-replicas'],
                        incremental,
                        backup['journal-archiving'],
                        backup['journal-archive-path'],
                        backup['journal-archive-lag-limit'])
                else:
                    raise UnexpectedManagementAPIResponse("Unparseable backup")
                temp._config['backup-id'] = backup['backup-id']
                olist.append(temp)
        result._config['database-backup'] = olist

        olist = []
        if 'path-namespace' in result._config:
            for path in result._config['path-namespace']:
                temp = PathNamespace(
                    path['prefix'],
                    path['namespace-uri'])
                olist.append(temp)
        result._config['path-namespace'] = olist

        olist = []
        if 'element-word-lexicon' in result._config:
            for path in result._config['element-word-lexicon']:
                temp = ElementWordLexicon(
                    path['namespace-uri'],
                    path['localname'],
                    path['collation'])
                olist.append(temp)
        result._config['element-word-lexicon'] = olist

        olist = []
        if 'element-attribute-word-lexicon' in result._config:
            for path in result._config['element-attribute-word-lexicon']:
                temp = AttributeWordLexicon(
                    path['parent-namespace-uri'],
                    path['parent-localname'],
                    path['namespace-uri'],
                    path['localname'],
                    path['collation'])
                olist.append(temp)
        result._config['element-attribute-word-lexicon'] = olist

        olist = []
        if 'element-word-query-through' in result._config:
            for path in result._config['element-word-query-through']:
                temp = ElementWordQueryThrough(
                    path['namespace-uri'],
                    path['localname'])
                olist.append(temp)
        result._config['element-word-query-through'] = olist

        olist = []
        if 'phrase-through' in result._config:
            for path in result._config['phrase-through']:
                temp = PhraseThrough(
                    path['namespace-uri'],
                    path['localname'])
                olist.append(temp)
        result._config['phrase-through'] = olist

        olist = []
        if 'phrase-around' in result._config:
            for path in result._config['phrase-around']:
                temp = PhraseAround(
                    path['namespace-uri'],
                    path['localname'])
                olist.append(temp)
        result._config['phrase-around'] = olist

        olist = []
        if 'default-ruleset' in result._config:
            for path in result._config['default-ruleset']:
                temp = RuleSet(
                    path['location'])
                olist.append(temp)
        result._config['default-ruleset'] = olist

        olist = []
        if 'field' in result._config:
            for field in result._config['field']:
                name = field['field-name']
                if 'field-path' in field:
                    paths = []
                    for path in field['field-path']:
                        paths.append(FieldPath(
                            path['path'], path['weight']))
                    temp = PathField(name, paths)
                else:
                    root = False
                    if 'include-root' in field:
                        root = (field['include-root'] == 'true')
                    if field['field-name'] == "":
                        temp = WordQuery(root)
                    else:
                        temp = RootField(name, root)
                temp.unmarshal(field)
                olist.append(temp)
        result._config['field'] = olist

        return result

    def marshal(self):
        struct = { }
        for key in self._config:
            if (key == 'range-element-index'
                or key == 'range-field-index'
                or key == 'range-element-attribute-index'
                or key == 'range-path-index'
                or key == 'geospatial-element-index'
                or key == 'geospatial-path-index'
                or key == 'geospatial-element-child-index'
                or key == 'geospatial-element-pair-index'
                or key == 'geospatial-element-attribute-pair-index'
                or key == 'fragment-root'
                or key == 'fragment-parent'
                or key == 'element-word-lexicon'
                or key == 'element-attribute-word-lexicon'
                or key == 'element-word-query-through'
                or key == 'phrase-through'
                or key == 'phrase-around'
                or key == 'default-ruleset'
                or key == 'path-namespace'
                or key == 'database-backup'
                or key == 'merge-blackout'):
                jlist = []
                for index in self._config[key]:
                    jlist.append(index._config)
                struct[key] = jlist
            elif key == "field":
                fstruct = []
                for field in self._config['field']:
                    fstruct.append(field.marshal())
                struct[key] = fstruct
            else:
                struct[key] = self._config[key];
        return struct

    def add_index(self, index_def):
        """
        Add a new index to the database configuration.

        The index isn't actually created on the server until
        the server configuration is saved.

        :param index_def: The index definition

        :return: The database configuration.
        """
        # N.B. Get these in the right order because it's a class hierarchy
        if isinstance(index_def, ElementRangeIndex):
            return self.add_to_property_list('range-element-index',
                                             index_def, ElementRangeIndex)
        elif isinstance(index_def, AttributeRangeIndex):
            return self.add_to_property_list('range-element-attribute-index',
                                             index_def, AttributeRangeIndex)
        elif isinstance(index_def, FieldRangeIndex):
            return self.add_to_property_list('range-field-index',
                                             index_def, FieldRangeIndex)
        elif isinstance(index_def, PathRangeIndex):
            return self.add_to_property_list('range-path-index',
                                             index_def, PathRangeIndex)
        elif isinstance(index_def, GeospatialElementChildIndex):
            return self.add_to_property_list('geospatial-element-child-index',
                                             index_def, GeospatialElementChildIndex)
        elif isinstance(index_def, GeospatialElementAttributePairIndex):
            return self.add_to_property_list('geospatial-element-attribute-pair-index',
                                             index_def, GeospatialElementAttributePairIndex)
        elif isinstance(index_def, GeospatialElementPairIndex):
            return self.add_to_property_list('geospatial-element-pair-index',
                                             index_def, GeospatialElementPairIndex)
        elif isinstance(index_def, GeospatialElementIndex):
            return self.add_to_property_list('geospatial-element-index',
                                             index_def, GeospatialElementIndex)
        elif isinstance(index_def, GeospatialPathIndex):
            return self.add_to_property_list('geospatial-path-index',
                                             index_def, GeospatialPathIndex)
        else:
            raise ValidationError('Not an index', index_def)

    def element_range_indexes(self):
        """
        The element range indexes.
        """
        if 'range-element-index' in self._config:
            return self._config['range-element-index']
        return None

    def field_range_indexes(self):
        """
        The field range indexes.
        """
        if 'range-field-index' in self._config:
            return self._config['range-field-index']
        return None

    def attribute_range_indexes(self):
        """
        The attribute range indexes.
        """
        if 'range-element-attribute-index' in self._config:
            return self._config['range-element-attribute-index']
        return None

    def path_range_indexes(self):
        """
        The path range indexes.
        """
        if 'range-path-index' in self._config:
            return self._config['range-path-index']
        return None

    def geospatial_element_indexes(self):
        """
        The geospatial element indexes.
        """
        if 'geospatial-element-index' in self._config:
            return self._config['geospatial-element-index']
        return None

    def geospatial_path_indexes(self):
        """
        The geospatial path indexes.
        """
        if 'geospatial-path-index' in self._config:
            return self._config['geospatial-path-index']
        return None

    def geospatial_element_child_indexes(self):
        """
        The geospatial element child indexes.
        """
        if 'geospatial-element-child-index' in self._config:
            return self._config['geospatial-element-child-index']
        return None

    def geospatial_element_pair_indexes(self):
        """
        The geospatial element pair indexes.
        """
        if 'geospatial-element-pair-index' in self._config:
            return self._config['geospatial-element-pair-index']
        return None

    def geospatial_element_attribute_pair_indexes(self):
        """
        The geospatial element attribute pair indexes.
        """
        if 'geospatial-element-attribute-pair-index' in self._config:
            return self._config['geospatial-element-attribute-pair-index']
        return None

    def fields(self):
        """
        The fields.

        Note: The list of fields does not include the word query settings
        that happen to be stored in the server configuration as a field
        with an empty name.
        """
        # The field named "" is special, it's the word query settings
        fields = []
        if 'field' in self._config:
            for field in self._config['field']:
                if field.field_name() is not None:
                    fields.append(field)
            return fields
        else:
            return None

    def add_field(self, field):
        value = assert_type(field, Field)
        if value.field_name() is None:
            raise ValidationError('Fields must have a non-empty name', value)
        return self.add_to_property_list('field', field, Field)

    def set_fields(self, fields):
        values = assert_list_of_type(fields, Field)
        for value in values:
            if value.field_name() is None:
                raise ValidationError('Fields must have a non-empty name', value)
        return self.set_property_list('field', fields, Field)

    def word_query(self):
        if 'field' in self._config:
            for field in self._config['field']:
                if field.field_name() is None:
                    return field
        return WordQuery(False)

    def set_word_query(self, word_query):
        changed = False
        fields = []
        if 'field' in self._config:
            fields = self._config['field']
        for index, item in enumerate(fields):
            if item.field_name() == "":
                items[index] = assert_type(word_query, WordQuery)
                changed = True
        if not changed:
            fields.append(assert_type(word_query, WordQuery))
        self._config['field'] = fields

    def get_document(self, conn, document_uri, content_type='*/*'):
        doc_url = "http://{0}:{1}/v1/documents?uri={2}&database={3}" \
          .format(conn.host, conn.port, document_uri, self.name)

        response = requests.get(doc_url, auth=conn.auth, headers={'accept': content_type})
        if response.status_code == 404:
            return None
        elif response.status_code == 200:
            return response.text
        else:
            raise UnexpectedAPIResponse(response.text)

